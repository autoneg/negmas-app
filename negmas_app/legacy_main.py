"""NegMAS App - Legacy Alpine.js version (DEPRECATED).

⚠️  WARNING: This is the deprecated Alpine.js version.
    Use 'negmas-app' for the modern Vue.js version.

This command is kept for temporary comparison purposes only.
The Alpine.js version is located in _store/alpine_version/
"""

import subprocess
import sys
from pathlib import Path
from typing import Annotated
import urllib.request
import urllib.error

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
    tournament_router,
    sources_router,
)

# Path configuration - point to archived Alpine.js version
PROJECT_ROOT = Path(__file__).parent.parent
ALPINE_DIR = PROJECT_ROOT / "_store" / "alpine_version"
TEMPLATES_DIR = ALPINE_DIR / "templates"
STATIC_DIR = ALPINE_DIR / "static"

# Create FastAPI app for legacy version
app = FastAPI(
    title="NegMAS App (Legacy Alpine.js)",
    description="Run and monitor negotiations using NegMAS - Legacy Alpine.js version",
    version="0.1.0-legacy",
)

# Mount static files from archived location
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates from archived location
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include routers (same as Vue version)
app.include_router(scenarios_router)
app.include_router(negotiators_router)
app.include_router(negotiation_router)
app.include_router(settings_router)
app.include_router(genius_router)
app.include_router(mechanisms_router)
app.include_router(tournament_router)
app.include_router(sources_router)


@app.get("/")
async def home(request: Request):
    """Render the Alpine.js home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/identity")
async def identity():
    """Return app identity for verification."""
    return {
        "app": "negmas-legacy",
        "version": app.version,
    }


# Typer CLI app
cli = typer.Typer(
    name="negmas-legacy",
    help="NegMAS App - Legacy Alpine.js version (DEPRECATED - use 'negmas-app' instead)",
    no_args_is_help=False,
)


@cli.command()
def run(
    port: Annotated[int, typer.Option(help="Port to run the server on")] = 8019,
    host: Annotated[str, typer.Option(help="Host to bind the server to")] = "127.0.0.1",
    reload: Annotated[
        bool, typer.Option(help="Enable auto-reload on file changes")
    ] = False,
    log_level: Annotated[
        str, typer.Option(help="Log level (debug, info, warning, error, critical)")
    ] = "info",
) -> None:
    """Run the legacy Alpine.js version of NegMAS App.

    ⚠️  WARNING: This is the deprecated Alpine.js version.
        Use 'negmas-app' for the modern Vue.js version.
    """
    import uvicorn

    typer.echo("⚠️  WARNING: Running LEGACY Alpine.js version")
    typer.echo("   Use 'negmas-app' for the modern Vue.js version")
    typer.echo(f"\nStarting legacy server at http://{host}:{port}\n")

    uvicorn.run(
        "negmas_app.legacy_main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


@cli.command()
def kill(
    port: Annotated[int, typer.Option(help="Port to kill")] = 8019,
    force: Annotated[
        bool,
        typer.Option(
            "--force", "-f", help="Kill without checking if it's negmas-legacy"
        ),
    ] = False,
) -> None:
    """Kill the legacy server process."""
    result = subprocess.run(
        ["lsof", "-ti", f":{port}"],
        capture_output=True,
        text=True,
    )

    pids = result.stdout.strip()
    if not pids:
        typer.echo(f"No process found on port {port}")
        sys.exit(0)

    # Verify it's negmas-legacy (unless --force)
    if not force:
        try:
            url = f"http://127.0.0.1:{port}/api/identity"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                import json

                data = json.loads(response.read().decode())
                if data.get("app") not in ["negmas-legacy", "negmas-app"]:
                    typer.echo(
                        f"Process on port {port} is not negmas-legacy. Use --force/-f to kill anyway.",
                        err=True,
                    )
                    sys.exit(1)
        except Exception:
            pass  # Likely not running, will try to kill anyway

    # Kill the PIDs
    killed = []
    for pid in pids.split("\n"):
        if pid:
            subprocess.run(["kill", "-9", pid], check=False)
            killed.append(pid)

    if killed:
        typer.echo(f"Killed process(es) {', '.join(killed)} on port {port}")


@cli.command()
def restart(
    port: Annotated[int, typer.Option(help="Port to run the server on")] = 8019,
    host: Annotated[str, typer.Option(help="Host to bind the server to")] = "127.0.0.1",
    reload: Annotated[
        bool, typer.Option(help="Enable auto-reload on file changes")
    ] = False,
    log_level: Annotated[
        str, typer.Option(help="Log level (debug, info, warning, error, critical)")
    ] = "info",
) -> None:
    """Restart the legacy server."""
    typer.echo("Stopping existing server...")
    kill(port=port, force=True)

    import time

    time.sleep(0.5)

    typer.echo("\nStarting fresh server...")
    run(port=port, host=host, reload=reload, log_level=log_level)


if __name__ == "__main__":
    cli()
