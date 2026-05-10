import httpx
from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/api/info")
async def info():
    docs_ok = False
    auth_ok = False
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(f"{settings.docs_api_url}/api/info")
            docs_ok = r.status_code == 200
        except Exception:
            pass
        try:
            r = await client.get(f"{settings.auth_api_url}/whoami")
            auth_ok = r.status_code == 200
        except Exception:
            pass
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "deps": {
            "docs": "ok" if docs_ok else "fail",
            "auth": "ok" if auth_ok else "fail",
        },
    }
