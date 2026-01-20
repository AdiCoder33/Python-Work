from datetime import datetime, timedelta, timezone
from io import BytesIO
import threading
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from .auth import create_access_token, hash_password, verify_password
from .audit import log_event, ensure_audit_file
from .backup import run_daily_backup, run_export_backup
from .deps import require_admin, require_auth
from .excel_store import (
    append_task,
    append_user,
    delete_task,
    ensure_tasks_file,
    ensure_users_file,
    get_task_by_sno,
    find_user,
    list_users,
    list_tasks,
    update_task,
    update_last_login,
    update_user_password,
    update_user_status,
    TASK_COLUMN_DEFS,
    TASK_COLUMNS,
    TASK_TOTAL_COLUMNS,
)
from .errors import ApiError, error_payload
from .models import (
    AdminTasksResponse,
    AccountCodeTotals,
    ComputedFields,
    CreateUserRequest,
    CreateUserResponse,
    LoginRequest,
    PasswordResetRequest,
    SummaryResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDeleteResponse,
    TaskRecord,
    TaskUpdateRequest,
    Totals,
    TokenResponse,
    SubDivisionTotals,
    UserStatusRequest,
    UserRecord,
)
from .rate_limit import RateLimiter
from .config import BACKUP_RETENTION_DAYS


COLUMN_DEF_MAP = {col["name"]: col for col in TASK_COLUMN_DEFS}

app = FastAPI(title="Capital Works API")
rate_limiter = RateLimiter()
_backup_state = {"last_date": None, "started": False}


def get_request_meta(request: Request):
    trace_id = getattr(request.state, "trace_id", "")
    ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    return trace_id, ip, user_agent


def build_error_response(request: Request, code: str, message: str, status_code: int, field_errors=None):
    trace_id = getattr(request.state, "trace_id", "")
    payload = error_payload(trace_id, code, message, field_errors)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers={"X-Trace-Id": trace_id},
    )


def map_status_to_code(status_code: int):
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "VALIDATION_ERROR"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "AUTH_FAILED"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "NOT_AUTHORIZED"
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "RATE_LIMITED"
    return "INTERNAL_ERROR"


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return build_error_response(request, exc.code, exc.message, exc.status_code, exc.field_errors)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = map_status_to_code(exc.status_code)
    message = str(exc.detail)
    field_errors = None
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message") or exc.detail.get("detail") or message
        field_errors = exc.detail.get("field_errors")
        if exc.detail.get("code"):
            code = exc.detail.get("code")
    return build_error_response(request, code, message, exc.status_code, field_errors)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    field_errors = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        parts = [str(part) for part in loc if part not in ("body", "query", "path")]
        key = ".".join(parts) if parts else "non_field"
        field_errors[key] = err.get("msg", "Invalid value")
    return build_error_response(
        request,
        "VALIDATION_ERROR",
        "Validation error.",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        field_errors,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return build_error_response(
        request, "INTERNAL_ERROR", "Internal server error.", status.HTTP_500_INTERNAL_SERVER_ERROR
    )
def iso_now():
    return datetime.now(timezone.utc).isoformat()


def backup_scheduler_loop():
    while True:
        try:
            today = datetime.now().date()
            last_date = _backup_state.get("last_date")
            if last_date != today:
                run_daily_backup(BACKUP_RETENTION_DAYS)
                _backup_state["last_date"] = today
        except Exception:
            pass
        time.sleep(3600)


def start_backup_scheduler():
    if _backup_state.get("started"):
        return
    _backup_state["started"] = True
    thread = threading.Thread(target=backup_scheduler_loop, daemon=True)
    thread.start()

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
        raise ApiError("VALIDATION_ERROR", "Invalid sort_by.", status.HTTP_400_BAD_REQUEST)
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


def compute_task_fields(payload):
    if payload.works_completed > payload.number_of_works:
        raise ApiError(
            "VALIDATION_ERROR",
            "Works completed cannot exceed number of works.",
            status.HTTP_400_BAD_REQUEST,
        )

    balance_amount = payload.agreement_amount - payload.exp_upto_31_03_2025
    if balance_amount < 0:
        raise ApiError(
            "VALIDATION_ERROR",
            "Balance amount as on 01-04-2025 cannot be negative.",
            status.HTTP_400_BAD_REQUEST,
        )

    total_exp_during_year = payload.exp_upto_last_month + payload.exp_during_this_month
    total_value_work_done = payload.exp_upto_31_03_2025 + total_exp_during_year
    balance_works = payload.number_of_works - payload.works_completed
    return balance_amount, total_exp_during_year, total_value_work_done, balance_works


def build_task_row(payload, created_by, created_at):
    balance_amount, total_exp_during_year, total_value_work_done, balance_works = compute_task_fields(
        payload
    )
    return {
        "sub_division": payload.sub_division,
        "account_code": payload.account_code,
        "number_of_works": payload.number_of_works,
        "estimate_amount": payload.estimate_amount,
        "agreement_amount": payload.agreement_amount,
        "exp_upto_31_03_2025": payload.exp_upto_31_03_2025,
        "balance_amount_as_on_01_04_2025": balance_amount,
        "exp_upto_last_month": payload.exp_upto_last_month,
        "exp_during_this_month": payload.exp_during_this_month,
        "total_exp_during_year": total_exp_during_year,
        "total_value_work_done_from_beginning": total_value_work_done,
        "works_completed": payload.works_completed,
        "balance_works": balance_works,
        "created_by": created_by,
        "created_at": created_at,
    }


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
    ensure_audit_file()
    start_backup_scheduler()


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request):
    trace_id, ip, user_agent = get_request_meta(request)
    allowed, reason = rate_limiter.check_and_add(payload.username, ip)
    if not allowed:
        log_event(
            action="auth.login_failed",
            actor=payload.username,
            role="",
            status="rate_limited",
            metadata={"reason": reason},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError(
            "RATE_LIMITED",
            "Too many login attempts. Try again later.",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    user = find_user(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        log_event(
            action="auth.login_failed",
            actor=payload.username,
            role="",
            status="failed",
            metadata={"reason": "invalid_credentials"},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError("AUTH_FAILED", "Invalid credentials.", status.HTTP_401_UNAUTHORIZED)

    if int(user.get("is_active", 0)) != 1:
        log_event(
            action="auth.login_failed",
            actor=payload.username,
            role=user.get("role", ""),
            status="failed",
            metadata={"reason": "inactive"},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError("NOT_AUTHORIZED", "User is inactive.", status.HTTP_403_FORBIDDEN)

    last_login = iso_now()
    update_last_login(payload.username, last_login)
    rate_limiter.reset_username(payload.username)

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    log_event(
        action="auth.login_success",
        actor=user["username"],
        role=user["role"],
        status="success",
        metadata={},
        trace_id=trace_id,
        ip=ip,
        user_agent=user_agent,
        ts=iso_now(),
    )
    return TokenResponse(access_token=token, role=user["role"], username=user["username"])


@app.get("/admin/users", response_model=list[UserRecord])
def get_users(
    request: Request,
    user=Depends(require_admin),
    q: str | None = Query(None),
    role: str | None = Query(None),
    is_active: int | None = Query(None, ge=0, le=1),
):
    if role not in (None, "", "admin", "user"):
        raise ApiError("VALIDATION_ERROR", "Invalid role.", status.HTTP_400_BAD_REQUEST)
    users = list_users(q=q, role=role, is_active=is_active)
    return [UserRecord(**item) for item in users]


@app.post("/admin/users", response_model=CreateUserResponse)
def create_user(payload: CreateUserRequest, request: Request, user=Depends(require_admin)):
    trace_id, ip, user_agent = get_request_meta(request)
    user_id = str(uuid.uuid4())
    created_at = iso_now()
    new_user = {
        "user_id": user_id,
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "is_active": 1,
        "created_at": created_at,
        "last_login_at": "",
    }
    try:
        append_user(new_user)
    except ValueError as exc:
        log_event(
            action="admin.user_create",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"reason": str(exc), "target_username": payload.username},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError("VALIDATION_ERROR", str(exc), status.HTTP_409_CONFLICT) from exc

    log_event(
        action="admin.user_create",
        actor=user["username"],
        role=user["role"],
        status="success",
        metadata={"target_username": payload.username, "role": payload.role},
        trace_id=trace_id,
        ip=ip,
        user_agent=user_agent,
        ts=iso_now(),
    )

    return CreateUserResponse(user_id=user_id, username=payload.username, role=payload.role)


@app.patch("/admin/users/{username}/status")
def update_user_active_status(
    username: str, payload: UserStatusRequest, request: Request, user=Depends(require_admin)
):
    trace_id, ip, user_agent = get_request_meta(request)
    updated = update_user_status(username, payload.is_active)
    if not updated:
        log_event(
            action="admin.user_disable_enable",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"reason": "user_not_found", "target_username": username},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError("VALIDATION_ERROR", "User not found.", status.HTTP_404_NOT_FOUND)

    log_event(
        action="admin.user_disable_enable",
        actor=user["username"],
        role=user["role"],
        status="success",
        metadata={
            "target_username": username,
            "is_active": payload.is_active,
        },
        trace_id=trace_id,
        ip=ip,
        user_agent=user_agent,
        ts=iso_now(),
    )
    return {"status": "success"}


@app.post("/admin/users/{username}/reset-password")
def reset_password(
    username: str, payload: PasswordResetRequest, request: Request, user=Depends(require_admin)
):
    trace_id, ip, user_agent = get_request_meta(request)
    password_hash = hash_password(payload.new_password)
    updated = update_user_password(username, password_hash)
    if not updated:
        log_event(
            action="admin.password_reset",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"reason": "user_not_found", "target_username": username},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError("VALIDATION_ERROR", "User not found.", status.HTTP_404_NOT_FOUND)

    log_event(
        action="admin.password_reset",
        actor=user["username"],
        role=user["role"],
        status="success",
        metadata={"target_username": username},
        trace_id=trace_id,
        ip=ip,
        user_agent=user_agent,
        ts=iso_now(),
    )
    return {"status": "success"}


@app.post("/tasks", response_model=TaskCreateResponse)
def create_task(payload: TaskCreateRequest, request: Request, user=Depends(require_auth)):
    trace_id, ip, user_agent = get_request_meta(request)
    try:
        created_at = iso_now()
        task_data = build_task_row(payload, user["username"], created_at)
        balance_amount = task_data["balance_amount_as_on_01_04_2025"]
        total_exp_during_year = task_data["total_exp_during_year"]
        total_value_work_done = task_data["total_value_work_done_from_beginning"]
        balance_works = task_data["balance_works"]

        sno = append_task(task_data)

        log_event(
            action="tasks.create_success",
            actor=user["username"],
            role=user["role"],
            status="success",
            metadata={"sno": sno},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )

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
    except ApiError:
        log_event(
            action="tasks.create_failed",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"reason": "validation_error"},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise
    except Exception as exc:
        log_event(
            action="tasks.create_failed",
            actor=user["username"],
            role=user["role"],
            status="error",
            metadata={"error": str(exc)},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise


@app.get("/tasks", response_model=AdminTasksResponse)
def get_user_tasks(
    user=Depends(require_auth),
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
        raise ApiError("VALIDATION_ERROR", "Invalid order.", status.HTTP_400_BAD_REQUEST)
    if account_code not in (None, "", "Spill", "New"):
        raise ApiError("VALIDATION_ERROR", "Invalid account_code.", status.HTTP_400_BAD_REQUEST)

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_from.", status.HTTP_400_BAD_REQUEST)

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_to.", status.HTTP_400_BAD_REQUEST)

    records = list_tasks()
    if user.get("role") != "admin":
        records = [record for record in records if record.get("created_by") == user["username"]]

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


@app.patch("/tasks/{sno}", response_model=TaskRecord)
def update_task_record(
    sno: int, payload: TaskUpdateRequest, request: Request, user=Depends(require_auth)
):
    trace_id, ip, user_agent = get_request_meta(request)
    existing = get_task_by_sno(sno)
    if not existing:
        raise ApiError("VALIDATION_ERROR", "Task not found.", status.HTTP_404_NOT_FOUND)
    if user.get("role") != "admin" and existing.get("created_by") != user.get("username"):
        raise ApiError("NOT_AUTHORIZED", "Not allowed to edit this task.", status.HTTP_403_FORBIDDEN)

    try:
        task_data = build_task_row(payload, existing.get("created_by"), existing.get("created_at"))
        updated = update_task(sno, task_data)
        if not updated:
            raise ApiError("VALIDATION_ERROR", "Task not found.", status.HTTP_404_NOT_FOUND)

        log_event(
            action="tasks.update_success",
            actor=user["username"],
            role=user["role"],
            status="success",
            metadata={"sno": sno},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        return TaskRecord(**updated)
    except ApiError:
        log_event(
            action="tasks.update_failed",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"sno": sno},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise
    except Exception as exc:
        log_event(
            action="tasks.update_failed",
            actor=user["username"],
            role=user["role"],
            status="error",
            metadata={"sno": sno, "error": str(exc)},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise


@app.delete("/tasks/{sno}", response_model=TaskDeleteResponse)
def delete_task_record(sno: int, request: Request, user=Depends(require_auth)):
    trace_id, ip, user_agent = get_request_meta(request)
    existing = get_task_by_sno(sno)
    if not existing:
        raise ApiError("VALIDATION_ERROR", "Task not found.", status.HTTP_404_NOT_FOUND)
    if user.get("role") != "admin" and existing.get("created_by") != user.get("username"):
        raise ApiError("NOT_AUTHORIZED", "Not allowed to delete this task.", status.HTTP_403_FORBIDDEN)

    try:
        deleted = delete_task(sno)
        if not deleted:
            raise ApiError("VALIDATION_ERROR", "Task not found.", status.HTTP_404_NOT_FOUND)

        log_event(
            action="tasks.delete_success",
            actor=user["username"],
            role=user["role"],
            status="success",
            metadata={"sno": sno},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        return TaskDeleteResponse(status="success", sno=sno)
    except ApiError:
        log_event(
            action="tasks.delete_failed",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"sno": sno},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise
    except Exception as exc:
        log_event(
            action="tasks.delete_failed",
            actor=user["username"],
            role=user["role"],
            status="error",
            metadata={"sno": sno, "error": str(exc)},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise


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
        raise ApiError("VALIDATION_ERROR", "Invalid order.", status.HTTP_400_BAD_REQUEST)
    if account_code not in (None, "", "Spill", "New"):
        raise ApiError("VALIDATION_ERROR", "Invalid account_code.", status.HTTP_400_BAD_REQUEST)

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_from.", status.HTTP_400_BAD_REQUEST)

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_to.", status.HTTP_400_BAD_REQUEST)

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
        raise ApiError("VALIDATION_ERROR", "Invalid account_code.", status.HTTP_400_BAD_REQUEST)

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_from.", status.HTTP_400_BAD_REQUEST)

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_to.", status.HTTP_400_BAD_REQUEST)

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
    request: Request,
    user=Depends(require_admin),
    sort_by: str = Query("sno"),
    order: str = Query("asc"),
    sub_division: str | None = Query(None),
    account_code: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    if order not in ("asc", "desc"):
        raise ApiError("VALIDATION_ERROR", "Invalid order.", status.HTTP_400_BAD_REQUEST)
    if account_code not in (None, "", "Spill", "New"):
        raise ApiError("VALIDATION_ERROR", "Invalid account_code.", status.HTTP_400_BAD_REQUEST)

    date_from_parsed = parse_date_param(date_from, is_end=False) if date_from else None
    if date_from and date_from_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_from.", status.HTTP_400_BAD_REQUEST)

    date_to_parsed = parse_date_param(date_to, is_end=True) if date_to else None
    if date_to and date_to_parsed is None:
        raise ApiError("VALIDATION_ERROR", "Invalid date_to.", status.HTTP_400_BAD_REQUEST)

    trace_id, ip, user_agent = get_request_meta(request)

    try:
        run_export_backup()
    except Exception as exc:
        log_event(
            action="admin.export_failed",
            actor=user["username"],
            role=user["role"],
            status="failed",
            metadata={"reason": "backup_failed", "error": str(exc)},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise ApiError("INTERNAL_ERROR", "Backup failed before export.", status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
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
    except Exception as exc:
        log_event(
            action="admin.export_failed",
            actor=user["username"],
            role=user["role"],
            status="error",
            metadata={"error": str(exc)},
            trace_id=trace_id,
            ip=ip,
            user_agent=user_agent,
            ts=iso_now(),
        )
        raise

    log_event(
        action="admin.export_success",
        actor=user["username"],
        role=user["role"],
        status="success",
        metadata={"total_items": len(records)},
        trace_id=trace_id,
        ip=ip,
        user_agent=user_agent,
        ts=iso_now(),
    )
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
