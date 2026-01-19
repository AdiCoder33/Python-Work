from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from .auth import decode_token
from .errors import ApiError


bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials is None:
        raise ApiError("AUTH_FAILED", "Not authenticated.", status.HTTP_401_UNAUTHORIZED)
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise ApiError("AUTH_FAILED", "Invalid token.", status.HTTP_401_UNAUTHORIZED)

    username = payload.get("sub")
    role = payload.get("role")
    if not username or role not in ("admin", "user"):
        raise ApiError("AUTH_FAILED", "Invalid token.", status.HTTP_401_UNAUTHORIZED)
    return {"username": username, "role": role}


def require_admin(user=Depends(require_auth)):
    if user["role"] != "admin":
        raise ApiError("NOT_AUTHORIZED", "Admin access required.", status.HTTP_403_FORBIDDEN)
    return user
