from fastapi import FastAPI

from app.api.info import router as info_router
from app.api.landing import router as landing_router
from app.api.me_proxy import router as me_proxy_router
from app.api.system import router as system_router
from app.api.tools import router as tools_router
from app.config import settings


app = FastAPI(title=settings.service_name)
app.include_router(info_router)
app.include_router(landing_router)
app.include_router(me_proxy_router)
app.include_router(system_router)
app.include_router(tools_router)
