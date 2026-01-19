from datetime import datetime, timedelta, timezone
from io import BytesIO
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from .auth import create_access_token, hash_password, verify_password
from .deps import require_admin, require_auth
from .excel_store import (
    append_task,
    append_user,
    ensure_tasks_file,
    ensure_users_file,
    find_user,
    list_tasks,
    copy_tasks_backup,
    update_last_login,
    TASK_COLUMN_DEFS,
    TASK_COLUMNS,
    TASK_TOTAL_COLUMNS,
)
from .models import (
    AdminTasksResponse,
    AccountCodeTotals,
    ComputedFields,
    CreateUserRequest,
    CreateUserResponse,
    LoginRequest,
    SummaryResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskRecord,
    Totals,
    TokenResponse,
    SubDivisionTotals,
)


app = FastAPI(title="Capital Works API")
COLUMN_DEF_MAP = {col["name"]: col for col in TASK_COLUMN_DEFS}


def iso_now():
    return datetime.now(timezone.utc).isoformat()

def parse_datetime_value(value: str):
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_date_param(value: str, is_end: bool):
    if value is None or value == "":
        return None
    parsed = parse_datetime_value(value)
    if parsed is None:
        return None
    if "T" not in value and " " not in value:
        if is_end:
            parsed = parsed + timedelta(days=1) - timedelta(microseconds=1)
    return parsed


def apply_filters(records, sub_division, account_code, date_from, date_to):
    filtered = []
    sub_division_filter = (sub_division or "").strip().lower()
    for record in records:
        if account_code and record.get("account_code") != account_code:
            continue
        if sub_division_filter:
            value = str(record.get("sub_division") or "").lower()
            if sub_division_filter not in value:
                continue
        if date_from or date_to:
            created_at = parse_datetime_value(record.get("created_at"))
            if created_at is None:
                continue
            if date_from and created_at < date_from:
                continue
            if date_to and created_at > date_to:
                continue
        filtered.append(record)
    return filtered


def sort_records(records, sort_by, order):
    if sort_by not in COLUMN_DEF_MAP:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_by.")
    reverse = order == "desc"
    col_def = COLUMN_DEF_MAP[sort_by]

    def sort_key(record):
        value = record.get(sort_by)
        if col_def["type"] == "text":
            return str(value or "").lower()
        if col_def["type"] == "date":
            parsed = parse_datetime_value(value)
            return parsed or datetime.min.replace(tzinfo=timezone.utc)
        return value if value is not None else 0

    return sorted(records, key=sort_key, reverse=reverse)


def compute_totals(records):
    totals = {key: 0 for key in TASK_TOTAL_COLUMNS}
    for record in records:
        for key in TASK_TOTAL_COLUMNS:
            totals[key] += record.get(key, 0) or 0
    return totals


def totals_to_model(data):
    return Totals(
        number_of_works=int(data.get("number_of_works", 0)),
        estimate_amount=float(data.get("estimate_amount", 0)),
        agreement_amount=float(data.get("agreement_amount", 0)),
        exp_upto_31_03_2025=float(data.get("exp_upto_31_03_2025", 0)),
        balance_amount_as_on_01_04_2025=float(data.get("balance_amount_as_on_01_04_2025", 0)),
        exp_upto_last_month=float(data.get("exp_upto_last_month", 0)),
        exp_during_this_month=float(data.get("exp_during_this_month", 0)),
        total_exp_during_year=float(data.get("total_exp_during_year", 0)),
        total_value_work_done_from_beginning=float(
            data.get("total_value_work_done_from_beginning", 0)
        ),
        works_completed=int(data.get("works_completed", 0)),
        balance_works=int(data.get("balance_works", 0)),
    )

@app.on_event("startup")
def startup():
    ensure_users_file()
    ensure_tasks_file()


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = find_user(request.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if int(user.get("is_active", 0)) != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    last_login = iso_now()
    update_last_login(request.username, last_login)

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token, role=user["role"], username=user["username"])


@app.post("/admin/users", response_model=CreateUserResponse)
def create_user(request: CreateUserRequest, user=Depends(require_admin)):
    user_id = str(uuid.uuid4())
    created_at = iso_now()
    new_user = {
        "user_id": user_id,
        "username": request.username,
        "password_hash": hash_password(request.password),
        "role": request.role,
        "is_active": 1,
        "created_at": created_at,
        "last_login_at": "",
    }
    try:
        append_user(new_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return CreateUserResponse(user_id=user_id, username=request.username, role=request.role)


@app.post("/tasks", response_model=TaskCreateResponse)
def create_task(request: TaskCreateRequest, user=Depends(require_auth)):
    if request.works_completed > request.number_of_works:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Works completed cannot exceed number of works.",
        )

    balance_amount = request.agreement_amount - request.exp_upto_31_03_2025
    if balance_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Balance amount as on 01-04-2025 cannot be negative.",
        )

    total_exp_during_year = request.exp_upto_last_month + request.exp_during_this_month
    total_value_work_done = request.exp_upto_31_03_2025 + total_exp_during_year
    balance_works = request.number_of_works - request.works_completed

    created_at = iso_now()
    task_data = {
        "sub_division": request.sub_division,
        "account_code": request.account_code,
        "number_of_works": request.number_of_works,
        "estimate_amount": request.estimate_amount,
        "agreement_amount": request.agreement_amount,
        "exp_upto_31_03_2025": request.exp_upto_31_03_2025,
        "balance_amount_as_on_01_04_2025": balance_amount,
        "exp_upto_last_month": request.exp_upto_last_month,
        "exp_during_this_month": request.exp_during_this_month,
        "total_exp_during_year": total_exp_during_year,
        "total_value_work_done_from_beginning": total_value_work_done,
        "works_completed": request.works_completed,
        "balance_works": balance_works,
        "created_by": user["username"],
        "created_at": created_at,
    }

    sno = append_task(task_data)

    return TaskCreateResponse(
        status="success",
        sno=sno,
        created_at=created_at,
        computed=ComputedFields(
            balance_amount_as_on_01_04_2025=balance_amount,
            total_exp_during_year=total_exp_during_year,
            total_value_work_done_from_beginning=total_value_work_done,
            balance_works=balance_works,
        ),
    )


@app.get("/admin/tasks", response_model=AdminTasksResponse)
def get_tasks(
    user=Depends(require_admin),
    sort_by: str = Query("sno"),
    order: str = Query("asc"),
    sub_division: str | None = Query(None),
    account_code: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order.")
    if account_code not in (None, "", "Spill", "New"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_code."
        )

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from.")

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to.")

    records = list_tasks()
    records = apply_filters(records, sub_division, account_code, date_from_parsed, date_to_parsed)
    records = sort_records(records, sort_by, order)

    total_items = len(records)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    page_items = records[start:end]

    return AdminTasksResponse(
        items=[TaskRecord(**item) for item in page_items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@app.get("/admin/summary", response_model=SummaryResponse)
def get_summary(
    user=Depends(require_admin),
    sub_division: str | None = Query(None),
    account_code: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    if account_code not in (None, "", "Spill", "New"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_code."
        )

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from.")

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to.")

    records = list_tasks()
    records = apply_filters(records, sub_division, account_code, date_from_parsed, date_to_parsed)

    grand_totals = totals_to_model(compute_totals(records))
    grouped = {}
    for record in records:
        sub_key = record.get("sub_division") or ""
        acct_key = record.get("account_code") or ""
        group = grouped.setdefault(
            sub_key, {"totals": {key: 0 for key in TASK_TOTAL_COLUMNS}, "accounts": {}}
        )
        totals = group["totals"]
        for key in TASK_TOTAL_COLUMNS:
            totals[key] += record.get(key, 0) or 0

        acct_group = group["accounts"].setdefault(
            acct_key, {key: 0 for key in TASK_TOTAL_COLUMNS}
        )
        for key in TASK_TOTAL_COLUMNS:
            acct_group[key] += record.get(key, 0) or 0

    sub_items = []
    for sub_div, data in sorted(grouped.items(), key=lambda item: item[0].lower()):
        account_items = []
        for acct_code in sorted(data["accounts"].keys()):
            if acct_code not in ("Spill", "New"):
                continue
            account_items.append(
                AccountCodeTotals(
                    account_code=acct_code,
                    totals=totals_to_model(data["accounts"][acct_code]),
                )
            )
        sub_items.append(
            SubDivisionTotals(
                sub_division=sub_div,
                totals=totals_to_model(data["totals"]),
                by_account_code=account_items,
            )
        )

    return SummaryResponse(grand_totals=grand_totals, by_sub_division=sub_items)


@app.get("/admin/export")
def export_tasks(
    user=Depends(require_admin),
    sort_by: str = Query("sno"),
    order: str = Query("asc"),
    sub_division: str | None = Query(None),
    account_code: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order.")
    if account_code not in (None, "", "Spill", "New"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_code."
        )

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from.")

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to.")

    try:
        copy_tasks_backup()
    except Exception:
        pass

    records = list_tasks()
    records = apply_filters(records, sub_division, account_code, date_from_parsed, date_to_parsed)
    records = sort_records(records, sort_by, order)

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    ws.append(TASK_COLUMNS)
    for record in records:
        ws.append([record.get(col, "") for col in TASK_COLUMNS])

    ws.append([])
    ws.append(["Grand Totals"])
    ws.append(TASK_TOTAL_COLUMNS)
    totals = compute_totals(records)
    ws.append([totals.get(col, 0) for col in TASK_TOTAL_COLUMNS])

    ws.append([])
    ws.append(["Sub-Division Totals"])
    ws.append(["sub_division", "account_code"] + TASK_TOTAL_COLUMNS)

    grouped = {}
    for record in records:
        sub_key = record.get("sub_division") or ""
        acct_key = record.get("account_code") or ""
        group = grouped.setdefault(
            sub_key,
            {
                "all": {key: 0 for key in TASK_TOTAL_COLUMNS},
                "accounts": {},
            },
        )
        for key in TASK_TOTAL_COLUMNS:
            group["all"][key] += record.get(key, 0) or 0

        acct_totals = group["accounts"].setdefault(
            acct_key, {key: 0 for key in TASK_TOTAL_COLUMNS}
        )
        for key in TASK_TOTAL_COLUMNS:
            acct_totals[key] += record.get(key, 0) or 0

    for sub_div, data in sorted(grouped.items(), key=lambda item: item[0].lower()):
        ws.append(
            [sub_div, "All"] + [data["all"].get(col, 0) for col in TASK_TOTAL_COLUMNS]
        )
        for acct_code in sorted(data["accounts"].keys()):
            totals_row = data["accounts"][acct_code]
            ws.append(
                [sub_div, acct_code]
                + [totals_row.get(col, 0) for col in TASK_TOTAL_COLUMNS]
            )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
