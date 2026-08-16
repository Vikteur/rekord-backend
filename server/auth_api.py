"""HTTP routes for signing in and managing DJ accounts.

`require_user` / `require_admin` are the dependencies every DJ-app route
hangs off: they turn the session cookie into a `CurrentUser` or raise 401/403
in the app's usual `{code, message}` error shape. Guest magic-link routes
(`/api/guest/*`) never use them — the token in the URL is that login.

The cookie holds only a random session token (HttpOnly, SameSite=Lax, Secure
behind HTTPS); everything about the user lives server-side.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from server import auth

router = APIRouter()

SESSION_COOKIE = "rm_session"


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _domain_error(exc: auth.AuthError) -> HTTPException:
    status = {
        "BAD_CREDENTIALS": 401,
        "ACCOUNT_DISABLED": 403,
        "RATE_LIMITED": 429,
        "DUPLICATE_USERNAME": 409,
        "NO_USER": 404,
        "LAST_ADMIN": 400,
    }.get(exc.code, 400)
    return _error(status, exc.code, str(exc))


# --- dependencies -----------------------------------------------------------

def require_user(request: Request) -> auth.CurrentUser:
    user = auth.session_user(request.cookies.get(SESSION_COOKIE, ""))
    if user is None:
        raise _error(401, "NOT_SIGNED_IN", "Sign in to use the DJ app.")
    return user


def require_admin(user: auth.CurrentUser = Depends(require_user)) -> auth.CurrentUser:
    if not user.is_admin:
        raise _error(403, "FORBIDDEN", "Only the admin can do that.")
    return user


# --- request bodies ---------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    display_name: str = ""
    password: str


class UserUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = None
    disabled: bool | None = None


# --- sign in / out ----------------------------------------------------------

def _me_payload(user: auth.CurrentUser) -> dict:
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
        }
    }


def _is_https(request: Request) -> bool:
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def _rate_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "?"
    return f"{host}:{username.strip().lower()}"


@router.post("/api/auth/login")
def login(request: Request, body: LoginRequest, response: Response) -> dict:
    key = _rate_key(request, body.username)
    try:
        auth.login_rate_check(key)
        user = auth.authenticate(body.username, body.password)
    except auth.AuthError as exc:
        if exc.code == "BAD_CREDENTIALS":
            auth.login_rate_record_failure(key)
        raise _domain_error(exc)
    response.set_cookie(
        SESSION_COOKIE,
        auth.create_session(user.id),
        max_age=auth.SESSION_TTL_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=_is_https(request),
        path="/",
    )
    return _me_payload(user)


@router.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    # Signing out an already-dead session is a successful no-op.
    auth.delete_session(request.cookies.get(SESSION_COOKIE, ""))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"signed_out": True}


@router.get("/api/me")
def me(user: auth.CurrentUser = Depends(require_user)) -> dict:
    return _me_payload(user)


# --- admin: DJ accounts -----------------------------------------------------

def _users_payload() -> dict:
    return {"users": auth.list_users()}


def _require_target(user_id: int) -> auth.CurrentUser:
    target = auth.get_user(user_id)
    if target is None:
        raise _error(404, "NO_USER", f"No account with id {user_id}.")
    return target


@router.get("/api/users")
def get_users(admin: auth.CurrentUser = Depends(require_admin)) -> dict:
    del admin
    return _users_payload()


@router.post("/api/users", status_code=201)
def create_user(
    body: UserCreate, admin: auth.CurrentUser = Depends(require_admin)
) -> dict:
    del admin
    try:
        # The admin stays singular: accounts created here are always DJs.
        auth.create_user(body.username, body.display_name, body.password, "dj")
    except auth.AuthError as exc:
        raise _domain_error(exc)
    return _users_payload()


@router.patch("/api/users/{user_id}")
def update_user(
    user_id: int, body: UserUpdate, admin: auth.CurrentUser = Depends(require_admin)
) -> dict:
    target = _require_target(user_id)
    if body.disabled and target.is_admin:
        raise _error(400, "LAST_ADMIN", "The admin account can't be switched off.")
    try:
        if body.display_name is not None:
            auth.set_display_name(user_id, body.display_name)
        if body.password is not None:
            auth.set_password(user_id, body.password)
        if body.disabled is not None:
            auth.set_disabled(user_id, body.disabled)
    except auth.AuthError as exc:
        raise _domain_error(exc)
    return _users_payload()


@router.delete("/api/users/{user_id}")
def delete_user(
    user_id: int, admin: auth.CurrentUser = Depends(require_admin)
) -> dict:
    target = _require_target(user_id)
    if target.is_admin:
        raise _error(400, "LAST_ADMIN", "The admin account can't be deleted.")
    auth.delete_user(user_id)
    return _users_payload()
