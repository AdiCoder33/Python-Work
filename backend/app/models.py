from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["admin", "user"]
    username: str


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)
    role: Literal["admin", "user"]


class CreateUserResponse(BaseModel):
    user_id: str
    username: str
    role: Literal["admin", "user"]


class TaskCreateRequest(BaseModel):
    sub_division: str = Field(..., min_length=1)
    account_code: Literal["Spill", "New"]
    number_of_works: int = Field(..., ge=0)
    estimate_amount: float = Field(..., ge=0)
    agreement_amount: float = Field(..., ge=0)
    exp_upto_31_03_2025: float = Field(..., ge=0)
    exp_upto_last_month: float = Field(..., ge=0)
    exp_during_this_month: float = Field(..., ge=0)
    works_completed: int = Field(..., ge=0)


class UserStatusRequest(BaseModel):
    is_active: int = Field(..., ge=0, le=1)


class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class ComputedFields(BaseModel):
    balance_amount_as_on_01_04_2025: float
    total_exp_during_year: float
    total_value_work_done_from_beginning: float
    balance_works: int


class TaskCreateResponse(BaseModel):
    status: str
    sno: int
    created_at: str
    computed: ComputedFields


class TaskRecord(BaseModel):
    sno: int
    sub_division: str
    account_code: str
    number_of_works: int
    estimate_amount: float
    agreement_amount: float
    exp_upto_31_03_2025: float
    balance_amount_as_on_01_04_2025: float
    exp_upto_last_month: float
    exp_during_this_month: float
    total_exp_during_year: float
    total_value_work_done_from_beginning: float
    works_completed: int
    balance_works: int
    created_by: str
    created_at: str


class UserRecord(BaseModel):
    user_id: str
    username: str
    role: Literal["admin", "user"]
    is_active: int
    created_at: str
    last_login_at: str


class AdminTasksResponse(BaseModel):
    items: list[TaskRecord]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class Totals(BaseModel):
    number_of_works: int
    estimate_amount: float
    agreement_amount: float
    exp_upto_31_03_2025: float
    balance_amount_as_on_01_04_2025: float
    exp_upto_last_month: float
    exp_during_this_month: float
    total_exp_during_year: float
    total_value_work_done_from_beginning: float
    works_completed: int
    balance_works: int


class AccountCodeTotals(BaseModel):
    account_code: Literal["Spill", "New"]
    totals: Totals


class SubDivisionTotals(BaseModel):
    sub_division: str
    totals: Totals
    by_account_code: list[AccountCodeTotals]


class SummaryResponse(BaseModel):
    grand_totals: Totals
    by_sub_division: list[SubDivisionTotals]


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: dict[str, str] | None = None


class ErrorResponse(BaseModel):
    trace_id: str
    error: ErrorDetail
