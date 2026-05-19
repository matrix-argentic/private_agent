"""Auth routes — register, login, me."""

from fastapi import Depends

from app.server.dependency.dependency import get_auth_service, get_current_user
from app.server.router.router import api_router
from app.server.schema.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.service.auth import AuthService


@api_router.post("/auth/register", status_code=201)
def register(
    req: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return auth_service.register(req)


@api_router.post("/auth/login")
def login(
    req: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return auth_service.authenticate(req)


@api_router.get("/auth/me")
def me(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return current_user
