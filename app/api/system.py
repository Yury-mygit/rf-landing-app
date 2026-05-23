"""raftforge.art/system/* — раздел «Система»: iframe на rcu.raftforge.art.

Простой контейнер: топ-нав raftforge.art сверху + полноэкранный iframe.
Защищён в Caddy `auth_required rcu`; landing не делает дополнительной
авторизации — если запрос дошёл сюда, у юзера есть `rcu`.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.api.landing import _FAVICON_LINK, _PERMS_WATCH_JS, _topnav


router = APIRouter(prefix="/system", tags=["system"])

RCU_URL = "https://rcu.raftforge.art/"

_SYSTEM_LAYOUT = """\
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Система — RaftForge</title>
<link rel="stylesheet" href="/me/static/style.css">
""" + _FAVICON_LINK + """
<style>
:root{{--ext-bar-h:57px}}
body{{margin:0;overflow:hidden}}
iframe.rcu{{display:block;width:100%;height:calc(100vh - var(--ext-bar-h));border:0;background:var(--bg)}}
</style>
</head>
<body>
{topnav}
<iframe class="rcu" src="{rcu_url}" title="rcu — control plane"></iframe>
""" + _PERMS_WATCH_JS + """\
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def system_page() -> HTMLResponse:
    return HTMLResponse(
        _SYSTEM_LAYOUT.format(
            topnav=_topnav("", "system"),
            rcu_url=RCU_URL,
        )
    )
