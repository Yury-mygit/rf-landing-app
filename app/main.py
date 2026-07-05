from fastapi import FastAPI

from app.api.info import router as info_router
from app.api.tools import router as tools_router
from app.config import settings


app = FastAPI(title=settings.service_name)
app.include_router(info_router)
app.include_router(tools_router)
