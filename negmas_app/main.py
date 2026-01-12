"""NegMAS App - FastAPI entry point."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routers import (
    scenarios_router,
    negotiators_router,
    negotiation_router,
    settings_router,
    genius_router,
)

# Path configuration
APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

# Create FastAPI app
app = FastAPI(
    title="NegMAS App",
    description="Run and monitor negotiations using NegMAS",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include routers
app.include_router(scenarios_router)
app.include_router(negotiators_router)
app.include_router(negotiation_router)
app.include_router(settings_router)
app.include_router(genius_router)


@app.get("/")
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("index.html", {"request": request})


def main():
    """Run the app with uvicorn."""
    import uvicorn

    uvicorn.run(
        "negmas_app.main:app",
        host="127.0.0.1",
        port=8019,
        reload=True,
    )


if __name__ == "__main__":
    main()
