"""Auth service — password hashing, JWT, register, authenticate."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException

from app.core.config import AuthConfig
from app.repository.user import UserRepository
from app.server.models.user import UserModel
from app.server.schema.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, config: AuthConfig) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.jwt_expire_minutes)
    payload["exp"] = expire
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_token(token: str, config: AuthConfig) -> dict:
    return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])


class AuthService:
    def __init__(self, user_repo: UserRepository, config: AuthConfig):
        self._user_repo = user_repo
        self._config = config

    def register(self, req: RegisterRequest) -> TokenResponse:
        if self._user_repo.get_by_username(req.username):
            raise HTTPException(status_code=409, detail="用户名已存在")
        if self._user_repo.get_by_email(req.email):
            raise HTTPException(status_code=409, detail="邮箱已被注册")

        now = datetime.now(timezone.utc).isoformat()
        model = UserModel(
            id=uuid.uuid4().hex,
            username=req.username,
            email=req.email,
            hashed_password=hash_password(req.password),
            created_at=now,
        )
        self._user_repo.create(model)

        token = create_access_token(
            {"sub": model.id, "username": model.username}, self._config
        )
        return TokenResponse(access_token=token)

    def authenticate(self, req: LoginRequest) -> TokenResponse:
        user = self._user_repo.get_by_username(req.username)
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_access_token(
            {"sub": user.id, "username": user.username}, self._config
        )
        return TokenResponse(access_token=token)

    def get_current_user(self, token: str) -> UserResponse:
        try:
            payload = decode_access_token(token, self._config)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token 已过期")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="无效的 Token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token 中缺少用户标识")

        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        return UserResponse.model_validate(user)
