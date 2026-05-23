"""Public landing endpoints для витрины lab.raftforge.art и raftforge.art/projects.

Без auth (публичные). Данные тянутся через httpx из docs (`/api/v1/site/*`).
Кэш 30с — чтобы не дёргать docs на каждый клик.

Caddy для `raftforge.art` ставит `X-URL-Prefix: /projects`, тогда
ссылки на тайлах и CSS становятся `/projects/...`. Для `lab.raftforge.art`
prefix пуст — поведение прежнее.

Маршруты:
  GET /site/index            — HTML главной (список проектов)
  GET /site/page/{slug}      — HTML страницы проекта
  GET /site/static/style.css — общий CSS
"""
import hashlib
import html
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.config import settings
from app.services.markdown import render_md


router = APIRouter(prefix="/site", tags=["landing"])


# NB: фигурные скобки удвоены — этот snippet встраивается в строки,
# которые потом проходят через `.format(...)`. После format → одинарные.
_PERMS_WATCH_JS = """\
<script>
(function(){{
  var lastVersion = null;
  var inflight = false;
  function applyNav(d){{
    document.querySelectorAll("[data-nav]").forEach(function(el){{
      var key = el.getAttribute("data-nav");
      var visible = false;
      if (key === "profile") visible = !!(d && d.authenticated);
      else visible = !!(d && d.nav && d.nav[key]);
      if (visible) el.removeAttribute("hidden");
      else el.setAttribute("hidden", "");
    }});
  }}
  function check(){{
    if (inflight) return;
    inflight = true;
    fetch("/auth/whoami", {{ credentials: "include", cache: "no-store" }})
      .then(function(r){{ return r.ok ? r.json() : null; }})
      .then(function(d){{
        inflight = false;
        if (!d) return;
        if (lastVersion !== null && d.version !== lastVersion) {{
          location.reload();
        }} else {{
          lastVersion = d.version;
          applyNav(d);
        }}
      }})
      .catch(function(){{ inflight = false; }});
  }}
  check();
  document.addEventListener("click", check, true);
  document.addEventListener("submit", check, true);
  document.addEventListener("visibilitychange", function(){{
    if (document.visibilityState === "visible") check();
  }});
}})();
</script>
"""


_FAVICON_LINK = (
    '<link rel="icon" href="data:image/svg+xml,'
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
    "%3E%3Ctext y='.9em' font-size='90'"
    "%3E%E2%9A%92%EF%B8%8F%3C/text%3E%3C/svg%3E\">"
)


_LAYOUT = """\
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css_href}">
""" + _FAVICON_LINK + """
</head>
<body>
{topnav}
<main class="page">{body}</main>
""" + _PERMS_WATCH_JS + """\
</body>
</html>
"""

_STYLE_CSS = """\
:root{--bg:#0e0f12;--fg:#e7e9ee;--muted:#8b93a3;--accent:#ff6a3d;--card:#16181d;--border:#23262d}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.topnav{display:flex;align-items:center;gap:24px;padding:14px 24px;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
.topnav .brand-link{display:flex;align-items:center;gap:10px;color:var(--fg);font-weight:600;font-size:17px;text-decoration:none;margin-right:auto}
.topnav .brand-link:hover{text-decoration:none}
.topnav .topnav-logo{width:28px;height:28px;border-radius:6px;background:linear-gradient(135deg,var(--accent),#c2410c);display:grid;place-items:center;color:#fff;font-weight:700;font-size:15px}
.topnav .nav-links{display:flex;gap:6px}
.topnav .nav-links a{color:var(--muted);text-decoration:none;padding:6px 14px;border-radius:6px;font-size:15px}
.topnav .nav-links a:hover{color:var(--fg);background:rgba(255,255,255,0.04);text-decoration:none}
.topnav .nav-links a.active{color:var(--accent);background:rgba(255,106,61,0.10)}
@media(max-width:600px){.topnav{padding:12px 16px;gap:12px}.topnav .brand-link span:not(.topnav-logo){display:none}.topnav .nav-links a{padding:6px 10px;font-size:14px}}

.page{max-width:920px;margin:0 auto;padding:48px 24px}
h1,h2,h3{line-height:1.25;margin:1.4em 0 .5em}
h1{font-size:34px;font-weight:700;margin-top:0}
h2{font-size:24px}
h3{font-size:19px;color:var(--muted)}
p{margin:.7em 0}
code{background:var(--card);padding:1px 6px;border-radius:4px;font-size:.92em}
pre{background:var(--card);padding:14px;border-radius:8px;overflow-x:auto;border:1px solid var(--border)}
pre code{background:none;padding:0}
blockquote{border-left:3px solid var(--accent);padding:2px 14px;color:var(--muted);margin:1em 0}
table{border-collapse:collapse;margin:1em 0}
th,td{border:1px solid var(--border);padding:6px 12px}
th{background:var(--card)}

.lead{color:var(--muted);font-size:18px;margin-top:6px;margin-bottom:32px}
.back{display:inline-block;color:var(--muted);font-size:14px;margin-bottom:18px}
.back:hover{color:var(--fg)}

.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-top:24px}
.tile{display:flex;flex-direction:column;align-items:center;gap:10px;padding:24px 12px;background:var(--card);border:1px solid var(--border);border-radius:12px;transition:transform .15s,border-color .15s}
.tile:hover{transform:translateY(-2px);border-color:var(--accent);text-decoration:none}
.avatar{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:#fff;letter-spacing:-1px}
.tile-title{color:var(--fg);font-weight:600;font-size:15px;text-align:center}

.empty{color:var(--muted);text-align:center;padding:48px 0}

.proj-head{display:flex;align-items:center;gap:18px;margin-bottom:8px}
.proj-head .avatar{width:56px;height:56px;font-size:24px}

/* me-page (порт стилей auth-сервиса под raftforge-переменные) */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:28px 32px}
.card .head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}
.card .head h1{margin:0;word-break:break-all;font-size:1.4rem;font-weight:600}
.card h2{font-size:.95rem;margin:26px 0 8px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.06em}
.card input[type=text],.card input[type=number],.card input[type=email],.card input[type=password]{display:block;width:100%;margin-top:4px;padding:9px 11px;background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;font:inherit}
.card input:focus{outline:none;border-color:var(--accent)}
.card button{padding:10px;background:var(--accent);color:#000;border:none;border-radius:6px;font:inherit;font-weight:600;cursor:pointer}
.card button:hover{filter:brightness(1.1)}
.card button.secondary{background:transparent;color:var(--fg);border:1px solid var(--border);padding:6px 14px;font-weight:500}
.card button.secondary:hover{filter:none;background:rgba(255,255,255,.06)}
.card button.danger{background:#5a2a2a;color:#fff;padding:3px 10px;font-weight:700;line-height:1}
.card button.danger:hover{filter:brightness(1.15)}
dl.kv{display:grid;grid-template-columns:max-content 1fr;gap:6px 14px;margin:0 0 12px}
dl.kv dt{color:var(--muted);font-size:.85rem}
dl.kv dd{margin:0;word-break:break-all}
table.list{width:100%;border-collapse:collapse;margin:8px 0 4px;font-size:.88rem}
table.list th{text-align:left;color:var(--muted);font-weight:normal;padding:6px 8px;border-bottom:1px solid var(--border)}
table.list td{padding:8px;border-bottom:1px solid #2a2a2a;vertical-align:middle}
table.list tr:last-child td{border-bottom:none}
table.list td.ua{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.75rem;color:var(--muted);word-break:break-all}
form.inline{display:inline;margin:0}
form.inline-form{display:flex;gap:8px;align-items:center;margin:14px 0 6px}
form.inline-form input{margin:0}
form.inline-form input[name=name]{flex:1}
form.inline-form input[name=expires_in_days]{width:130px}
form.inline-form button{padding:9px 18px;margin:0}
.card .muted{color:var(--muted);font-size:.85rem;margin:14px 0 0}
.badge{background:var(--accent);color:#000;padding:2px 10px;border-radius:12px;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.badge.muted{background:var(--card);color:var(--muted);border:1px solid var(--border)}

nav.tabs{display:flex;gap:4px;border-bottom:1px solid var(--border);margin:18px 0 16px;flex-wrap:wrap}
nav.tabs .tab{background:transparent;color:var(--muted);border:0;border-bottom:2px solid transparent;padding:8px 14px;cursor:pointer;font:inherit;font-weight:500;margin:0 0 -1px;border-radius:0}
nav.tabs .tab:hover{color:var(--fg);filter:none;background:transparent}
nav.tabs .tab.active{color:var(--fg);border-bottom-color:var(--accent)}
section.panel[hidden]{display:none}
label.superadmin-label{display:inline-flex;align-items:center;gap:6px;margin:0;font-size:.85rem;color:var(--muted);white-space:nowrap}
label.superadmin-label input[type=checkbox]{margin:0}
form.users-create-form input[name=email]{flex:1}
form.users-create-form input[name=password]{flex:1}

.matrix-wrap{overflow-x:auto;margin:8px 0 4px}
table.matrix{border-collapse:collapse;font-size:.82rem}
table.matrix th,table.matrix td{padding:6px 10px;text-align:center;border:1px solid #2a2a2a}
table.matrix thead th{color:var(--muted);font-weight:normal;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.78rem;background:#16181d;white-space:nowrap}
table.matrix tbody th.user-col{text-align:left;font-weight:normal;color:var(--fg);white-space:nowrap;padding-right:16px;background:#16181d;position:sticky;left:0}
table.matrix thead th.user-col{text-align:left;position:sticky;left:0;z-index:1}
table.matrix td.cell{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);min-width:44px}
table.matrix td.cell-set{color:var(--fg)}
table.matrix td.lvl-200{background:rgba(110,180,250,.10)}
table.matrix td.lvl-300{background:rgba(255,106,61,.13)}
table.matrix td.cell-sa{color:var(--accent);font-weight:700}
.badge.sa{background:var(--accent);color:#000}

@media(max-width:600px){
  .page{padding:24px 16px}
  h1{font-size:26px}
  .tiles{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px}
  .card{padding:20px 18px}
  table.list{font-size:.82rem}
  table.list td.ua{display:none}
}
"""


def _avatar_color(slug: str) -> str:
    digest = hashlib.md5(slug.encode("utf-8")).digest()
    hue = digest[0] / 255 * 360
    return f"hsl({hue:.0f},55%,42%)"


def _avatar_letter(title: str) -> str:
    for ch in title.strip():
        if ch.isprintable() and not ch.isspace():
            return ch.upper()
    return "?"


def _avatar_html(title: str, slug: str, css_class: str = "avatar") -> str:
    color = _avatar_color(slug)
    letter = html.escape(_avatar_letter(title))
    return f'<div class="{css_class}" style="background:{color}">{letter}</div>'


def _prefix(request: Request) -> str:
    p = request.headers.get("X-URL-Prefix", "").strip().rstrip("/")
    return p


def _topnav(prefix: str, active: str) -> str:
    home_href = "/" if prefix else "https://raftforge.art/"
    tools_href = "/tools/" if prefix else "https://raftforge.art/tools/"
    projects_href = f"{prefix}" if prefix else "https://raftforge.art/projects"
    profile_href = "/me/" if prefix else "https://raftforge.art/me/"
    system_href = "/system/" if prefix else "https://raftforge.art/system/"
    # nav-key соответствует ключу в whoami.nav (tools/projects/system).
    # JS на фронтенде скрывает табы по этим data-nav-атрибутам.
    items = [
        ("home", "Главная", home_href, None),
        ("tools", "Инструменты", tools_href, "tools"),
        ("projects", "Проекты", projects_href, "projects"),
        ("system", "Система", system_href, "system"),
        ("profile", "Кабинет", profile_href, "profile"),
    ]
    parts = []
    for key, label, href, nav_key in items:
        attrs = ""
        if key == active:
            attrs += ' class="active"'
        if nav_key:
            attrs += f' data-nav="{nav_key}" hidden'
        parts.append(f'<a href="{href}"{attrs}>{label}</a>')
    return (
        '<nav class="topnav">'
        f'<a class="brand-link" href="{home_href}">'
        '<span class="topnav-logo">R</span><span>RaftForge</span>'
        "</a>"
        f'<div class="nav-links">{"".join(parts)}</div>'
        "</nav>"
    )


# ── Кэш на 30с для site-данных из docs ───────────────────────────────────────
_CACHE_TTL = 30.0
_cache: dict[str, tuple[float, object]] = {}


async def _docs_get(path: str):
    """GET docs/api/v1/site/{path} с кэшем 30с (по path)."""
    now = time.monotonic()
    cached = _cache.get(path)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    async with httpx.AsyncClient(base_url=settings.docs_api_url, timeout=5.0) as c:
        r = await c.get(f"/api/v1/site{path}")
        r.raise_for_status()
        data = r.json()
    _cache[path] = (now, data)
    return data


@router.get("/index", response_class=HTMLResponse)
async def landing_index(request: Request) -> HTMLResponse:
    try:
        projects = await _docs_get("/projects")
    except httpx.HTTPError:
        projects = []

    prefix = _prefix(request)
    css_href = f"{prefix}/static/style.css" if prefix else "/site/static/style.css"

    if not projects:
        body = (
            "<h1>Проекты</h1>"
            '<p class="lead">Витрина проектов пока пуста.</p>'
            '<div class="empty">Здесь появятся карточки проектов с <code>kind=project_root</code>, '
            "у которых есть <code>website_base</code> и заполнен <code>slug</code>.</div>"
        )
    else:
        tiles = []
        for p in projects:
            slug = p["slug"]
            title = p.get("title") or slug
            t = html.escape(title)
            s = html.escape(slug)
            tile_href = f"{prefix}/p/{s}" if prefix else f"/p/{s}"
            tiles.append(
                f'<a class="tile" href="{tile_href}">'
                f'{_avatar_html(title, slug)}'
                f'<span class="tile-title">{t}</span>'
                f"</a>"
            )
        body = (
            "<h1>Проекты</h1>"
            '<p class="lead">Личная мастерская проектов и сервисов.</p>'
            f'<div class="tiles">{"".join(tiles)}</div>'
        )

    return HTMLResponse(
        _LAYOUT.format(
            title="Проекты — RaftForge",
            css_href=css_href,
            topnav=_topnav(prefix, "projects"),
            body=body,
        )
    )


@router.get("/page/{slug}", response_class=HTMLResponse)
async def landing_page(slug: str, request: Request) -> HTMLResponse:
    try:
        page = await _docs_get(f"/p/{slug}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return HTMLResponse(
                _LAYOUT.format(
                    title="404 — RaftForge",
                    css_href="/site/static/style.css",
                    topnav=_topnav(_prefix(request), "projects"),
                    body=f"<h1>Проект «{html.escape(slug)}» не найден</h1>",
                ),
                status_code=404,
            )
        raise

    title = page.get("title") or slug
    body_md = page.get("bodyMd") or ""
    content_html = render_md(body_md) if body_md else "<p>Контент пока не добавлен.</p>"

    prefix = _prefix(request)
    css_href = f"{prefix}/static/style.css" if prefix else "/site/static/style.css"
    back_href = f"{prefix}" if prefix else "/"

    title_safe = html.escape(title)
    body = (
        f'<a class="back" href="{back_href}">← к проектам</a>'
        '<div class="proj-head">'
        f'{_avatar_html(title, slug)}'
        f"<h1>{title_safe}</h1>"
        "</div>"
        f'<div class="content">{content_html}</div>'
    )
    return HTMLResponse(
        _LAYOUT.format(
            title=f"{title_safe} — RaftForge",
            css_href=css_href,
            topnav=_topnav(prefix, "projects"),
            body=body,
        )
    )


@router.get("/static/style.css")
async def landing_style() -> Response:
    return Response(content=_STYLE_CSS, media_type="text/css")
