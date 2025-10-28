import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError

# Carrega variáveis do .env
from dotenv import load_dotenv
load_dotenv()

ALGO = os.getenv("JWT_ALGORITHM", "HS256")
SECRET = os.getenv("APP_SECRET") or os.getenv("SECRET_KEY") or "dev-secret"

class AuthError(Exception):
    """Erro genérico de autenticação"""
    pass

def create_access_token(username: str, expires_hours: int = 24) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=expires_hours)
    payload = {"sub": username, "exp": exp}
    token = jwt.encode(payload, SECRET, algorithm=ALGO)
    return token

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        sub = payload.get("sub")
        if not sub:
            raise AuthError("Token inválido: campo 'sub' ausente")
        return sub
    except JWTError as e:
        raise AuthError(f"Falha ao verificar token: {e}")

def check_credentials(username: str, password: str) -> bool:
    app_user = os.getenv("APP_USER", "admin")
    app_pass = os.getenv("APP_PASS", "admin123")
    return username == app_user and password == app_pass
