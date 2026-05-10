"""Server-side proxy raftforge.art/me/* → auth-сервис.

Вытягивает HTML страницу профиля из auth (http://auth:8014/me), извлекает
main-блок, переписывает все form action="/X" на "/me/X" и оборачивает в
_LAYOUT из landing.py (общий topnav raftforge.art).

Cookies (auth_session shared .raftforge.art + auth_csrf host-only) ходят
браузер → ln_dev_app → auth и обратно. Set-Cookie от auth прокидывается в
ответ браузеру as-is.

POST-actions (logout, tokens, sessions, deploy-permits) — простой проxy
form-data. auth отвечает 303 на /me, location переписываем на /me/.
"""
import re
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.api.landing import _LAYOUT, _STYLE_CSS, _topnav


router = APIRouter(prefix="/me", tags=["me-proxy"])

AUTH_BASE_URL = "http://auth:8014"
AUTH_HOST_HEADER = "auth.raftforge.art"

_MAIN_RE = re.compile(r"<main[^>]*>(.*?)</main>", re.DOTALL)
_ACTION_REWRITE = re.compile(
    r'action="(/(?:logout|tokens|sessions|deploy-permits|users)([^"]*))"'
)


def _rewrite_actions(html: str) -> str:
    return _ACTION_REWRITE.sub(r'action="/me\1"', html)


def _client_kwargs(request: Request) -> dict:
    headers = {
        "Host": AUTH_HOST_HEADER,
        "User-Agent": request.headers.get("user-agent", "ln_dev_app/me_proxy"),
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "raftforge.art",
    }
    if request.client:
        headers["X-Forwarded-For"] = request.client.host
    return {
        "base_url": AUTH_BASE_URL,
        "timeout": 10.0,
        "follow_redirects": False,
        "headers": headers,
        "cookies": dict(request.cookies),
    }


def _propagate(r: httpx.Response, response: Response) -> None:
    """Скопировать Set-Cookie и Location из ответа auth.

    auth редиректит на `/me` или `/me#<tab>` — переписываем в `/me/`
    (FastAPI prefix наш — со слэшем), сохраняя fragment.
    """
    for name, value in r.headers.multi_items():
        ln = name.lower()
        if ln == "set-cookie":
            response.headers.append("set-cookie", value)
        elif ln == "location":
            if value == "/me":
                response.headers["location"] = "/me/"
            elif value.startswith("/me#"):
                response.headers["location"] = "/me/" + value[3:]
            elif value == "/login":
                response.headers["location"] = "/"
            else:
                response.headers["location"] = value


@router.get("/static/style.css")
async def me_style() -> Response:
    return Response(content=_STYLE_CSS, media_type="text/css")


@router.get("/", response_class=HTMLResponse)
async def me_page(request: Request) -> Response:
    async with httpx.AsyncClient(**_client_kwargs(request)) as client:
        r = await client.get("/me")

    ctype = (r.headers.get("content-type") or "").lower()
    if r.status_code == 200 and "text/html" in ctype:
        m = _MAIN_RE.search(r.text)
        inner = m.group(1) if m else r.text
        inner = _rewrite_actions(inner)
        full = _LAYOUT.format(
            title="Кабинет — RaftForge",
            css_href="/me/static/style.css",
            topnav=_topnav("", "profile"),
            body=inner,
        )
        resp = HTMLResponse(content=full)
        _propagate(r, resp)
        return resp

    # 3xx или иной — пробрасываем как есть.
    resp = Response(content=r.content, status_code=r.status_code, media_type=ctype or None)
    _propagate(r, resp)
    return resp


async def _post_action(auth_path: str, request: Request) -> Response:
    body = await request.body()
    ct = request.headers.get("content-type", "application/x-www-form-urlencoded")
    async with httpx.AsyncClient(**_client_kwargs(request)) as client:
        r = await client.post(auth_path, content=body, headers={"content-type": ct})
    resp = Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))
    _propagate(r, resp)
    return resp


@router.post("/logout")
async def me_logout(request: Request) -> Response:
    return await _post_action("/logout", request)


@router.post("/tokens")
async def me_tokens_create(request: Request) -> Response:
    return await _post_action("/tokens", request)


@router.post("/tokens/{token_id}/revoke")
async def me_tokens_revoke(token_id: str, request: Request) -> Response:
    return await _post_action(f"/tokens/{token_id}/revoke", request)


@router.post("/sessions/{session_id}/revoke")
async def me_sessions_revoke(session_id: str, request: Request) -> Response:
    return await _post_action(f"/sessions/{session_id}/revoke", request)


@router.post("/deploy-permits")
async def me_permits_create(request: Request) -> Response:
    return await _post_action("/deploy-permits", request)


@router.post("/deploy-permits/{permit_id}/revoke")
async def me_permits_revoke(permit_id: str, request: Request) -> Response:
    return await _post_action(f"/deploy-permits/{permit_id}/revoke", request)


@router.post("/users")
async def me_users_create(request: Request) -> Response:
    return await _post_action("/users", request)


@router.post("/users/{user_id}/setpw")
async def me_users_setpw(user_id: int, request: Request) -> Response:
    return await _post_action(f"/users/{user_id}/setpw", request)
