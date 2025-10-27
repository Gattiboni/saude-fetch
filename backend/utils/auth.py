import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError

ALGO = "HS256"

def _secret() -> str:
    s = os.environ.get("APP_SECRET") or "dev-secret"
    return s

def create_access_token(username: str, expires_hours: int = 24) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=expires_hours)
    payload = {"sub": username, "exp": exp}
    token = jwt.encode(payload, _secret(), algorithm=ALGO)
    return token

class AuthError(Exception):
    pass

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGO])
        sub = payload.get("sub")
        if not sub:
            raise AuthError("invalid token: sub missing")
        return sub
    except JWTError as e:
        raise AuthError(str(e))

def check_credentials(username: str, password: str) -> bool:
    app_user = os.environ.get("APP_USER", "admin")
    app_pass = os.environ.get("APP_PASS", "admin")
    return username == app_user and password == app_pass
