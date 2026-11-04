"""Web routes and dashboard interactions."""

from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from webserver.schemas import GPIOConfig, GPIOOutputConfig
from webserver.services.config_service import (
    build_config_snapshot,
    delete_config,
    ensure_input,
    ensure_output,
    load_config,
    save_config,
)

router = APIRouter()
templates = Jinja2Templates(directory="webserver/templates")


@router.get("/")
def root_redirect():
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/dashboard")
def read_dashboard(request: Request, message: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "configurations": build_config_snapshot(),
            "message": message,
        },
    )


@router.post("/dashboard/input")
def dashboard_create_or_update_input(
    gpio: int = Form(...),
    edge: str = Form("rising"),
    pull_down: str | None = Form(None),
):
    result = ensure_input(
        GPIOConfig(
            gpio=gpio,
            edge=edge,
            pull_down=pull_down == "true",
        )
    )
    message = result.get("message", result.get("error", "Input gespeichert"))
    return RedirectResponse(url=f"/dashboard?message={quote_plus(str(message))}", status_code=303)


@router.post("/dashboard/output")
def dashboard_create_or_update_output(
    gpio: int = Form(...),
    state: str = Form("low"),
):
    result = ensure_output(GPIOOutputConfig(gpio=gpio, state=state))
    message = result.get("message", result.get("error", "Output gespeichert"))
    return RedirectResponse(url=f"/dashboard?message={quote_plus(str(message))}", status_code=303)


@router.post("/dashboard/delete/{gpio}")
def dashboard_delete_gpio(gpio: int):
    result = delete_config(gpio)
    return RedirectResponse(url=f"/dashboard?message={quote_plus(result['message'])}", status_code=303)


@router.post("/dashboard/save")
def dashboard_save_config():
    result = save_config()
    return RedirectResponse(url=f"/dashboard?message={quote_plus(result['message'])}", status_code=303)


@router.post("/dashboard/load")
def dashboard_load_config():
    result = load_config()
    message = result.get("message", result.get("error", "Konfiguration geladen"))
    return RedirectResponse(url=f"/dashboard?message={quote_plus(str(message))}", status_code=303)
