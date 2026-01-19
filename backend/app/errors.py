class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int, field_errors=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field_errors = field_errors or {}


def error_payload(trace_id: str, code: str, message: str, field_errors=None):
    payload = {
        "trace_id": trace_id or "",
        "error": {
            "code": code,
            "message": message,
        },
    }
    if field_errors:
        payload["error"]["field_errors"] = field_errors
    return payload
