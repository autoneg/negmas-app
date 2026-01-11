"""Main FastAPI application for NegMAS App."""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .routers import negotiation

# Get the package directory
PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

app = FastAPI(
    title="NegMAS App",
    description="A modern browser-based GUI for running negotiations and tournaments using the NegMAS ecosystem",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include routers
app.include_router(negotiation.router, prefix="/negotiation", tags=["negotiation"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main application page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "active_page": "home"},
    )


def run():
    """Run the application server."""
    uvicorn.run(
        "negmas_app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    run()
