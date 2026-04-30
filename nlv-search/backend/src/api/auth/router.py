from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from src.api.auth.deps import get_current_user, oauth2_scheme
from src.api.auth.schemas import AuthResponse, UserCreate, UserRead
from src.core import security
from src.core.config import settings
from src.infra.postgres.auth import User
from src.infra.postgres.database import get_session
from src.infra.redis.auth_blacklist import blacklist_token
from src.services.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    summary="Register a new user",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserCreate,
    session=Depends(get_session),
) -> AuthResponse:
    """Register a new user account and return an access token."""

    service = AuthService(session)

    try:
        user = await service.register_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    access_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=settings.auth_access_token_timedelta,
    )
    logger.info(f"Auth: user '{user.username}' registered")
    return AuthResponse(access_token=access_token, user=user)


@router.post("/login", summary="Obtain access token", response_model=AuthResponse)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_session),
) -> AuthResponse:
    """Authenticate with username/password and return a Bearer access token."""

    logger.info(f"Auth: login attempt for user '{form_data.username}'")
    service = AuthService(session)
    user = await service.authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning(f"Auth: invalid credentials for user '{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=settings.auth_access_token_timedelta,
    )
    logger.info(f"Auth: issued access token for user '{user.username}'")
    return AuthResponse(access_token=access_token, user=user)


@router.get("/me", summary="Get current user", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Return the profile of the currently authenticated user."""

    return UserRead.model_validate(current_user)


@router.post("/logout", summary="Logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(token: str = Depends(oauth2_scheme)) -> None:
    """Revoke the current Bearer token by adding it to the blacklist."""

    ttl_seconds = security.get_token_ttl_seconds(token)

    try:
        await blacklist_token(token, ttl_seconds)
        logger.info(f"Auth: logout, token revoked for {ttl_seconds} seconds")

    except Exception:
        logger.exception("Auth: failed to blacklist token on logout")

    return None


@router.delete(
    "/me",
    summary="Delete current user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    """Permanently delete the currently authenticated user account."""

    service = AuthService(session)
    await service.delete_user(current_user)
    logger.info(f"Auth: user '{current_user.username}' deleted self")
    return None
