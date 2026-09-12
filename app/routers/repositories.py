from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.providers import SettingsDep
from app.rendering import templates

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_class=HTMLResponse)
def repositories(request: Request, settings: SettingsDep) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "repositories/index.html",
        {
            "title": settings.app_name,
            "heading": f"Hello from {settings.app_name}",
        },
    )
