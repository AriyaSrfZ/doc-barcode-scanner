"""
A minimal web console for this service. There's no login form here -
auth lives in identity-service, not this service - so the console asks
for a bearer token (pasted from wherever you got it: identity-service's
/auth/login, or your own app's login flow) and uses it for every API
call from then on, stored in the browser's localStorage.

This is deliberately thin: it's a real UI backed by the same JSON API
documented in docs/API.md, not a separate code path with its own logic.
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["console"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/console")
def console(request: Request):
    return templates.TemplateResponse("console.html", {"request": request})
