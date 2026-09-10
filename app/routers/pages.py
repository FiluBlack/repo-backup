"""HTML routes. These render templates and are read by a browser."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.providers import SettingsDep
from app.services import status as status_service
from app.rendering import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, settings: SettingsDep) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": settings.app_name,
            "heading": f"Hello from {settings.app_name}",
            "status": status_service.collect(settings.app_name),
        },
    )
