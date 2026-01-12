"""NegMAS App - FastAPI entry point."""

from pathlib import Path
from typing import Annotated

import typer
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routers import (
    scenarios_router,
    negotiators_router,
    negotiation_router,
    settings_router,
    genius_router,
    mechanisms_router,
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
app.include_router(mechanisms_router)


@app.get("/")
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("index.html", {"request": request})


# Typer CLI app
cli = typer.Typer(
    name="negmas-app",
    help="NegMAS App - A GUI for running and monitoring negotiations",
    no_args_is_help=False,
)


@cli.command()
def run(
    port: Annotated[int, typer.Option(help="Port to run the server on")] = 8019,
    host: Annotated[str, typer.Option(help="Host to bind the server to")] = "127.0.0.1",
    reload: Annotated[
        bool, typer.Option(help="Enable auto-reload on file changes")
    ] = True,
    log_level: Annotated[
        str, typer.Option(help="Log level (debug, info, warning, error, critical)")
    ] = "info",
    workers: Annotated[
        int | None,
        typer.Option(help="Number of worker processes (incompatible with reload)"),
    ] = None,
    access_log: Annotated[bool, typer.Option(help="Enable access log")] = True,
) -> None:
    """Run the NegMAS App server."""
    import uvicorn

    # Workers and reload are mutually exclusive
    if workers is not None and reload:
        typer.echo(
            "Warning: --workers is incompatible with --reload. Disabling reload.",
            err=True,
        )
        reload = False

    uvicorn.run(
        "negmas_app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        workers=workers,
        access_log=access_log,
    )


if __name__ == "__main__":
    cli()
