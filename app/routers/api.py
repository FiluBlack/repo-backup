"""JSON routes. These return models and appear in /docs."""

from fastapi import APIRouter

from app.providers import SettingsDep
from app.schemas.status import Status
from app.services import status as status_service

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status", response_model=Status)
def read_status(settings: SettingsDep) -> Status:
    return Status(**status_service.collect(settings.app_name))
