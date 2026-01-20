"""NegMAS Vue App - FastAPI backend entry point."""

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from the original negmas_app
# We'll reuse the same routers since they just provide JSON APIs
from negmas_app.routers import (
    scenarios_router,
    negotiators_router,
    negotiation_router,
    settings_router,
    genius_router,
    mechanisms_router,
    tournament_router,
    sources_router,
)

# Create FastAPI app
app = FastAPI(
    title="NegMAS Vue App",
    description="Vue.js frontend for NegMAS - Run and monitor negotiations",
    version="0.1.0",
)

# Add CORS middleware for development (Vite dev server runs on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",  # Vite dev server
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scenarios_router)
app.include_router(negotiators_router)
app.include_router(negotiation_router)
app.include_router(settings_router)
app.include_router(genius_router)
app.include_router(mechanisms_router)
app.include_router(tournament_router)
app.include_router(sources_router)


@app.get("/api/identity")
async def identity():
    """Return app identity for verification.

    Used by the kill command to verify that the process on a port is negmas-vue.
    """
    return {
        "app": "negmas-vue",
        "version": app.version,
    }


# Typer CLI app
cli = typer.Typer(
    name="negmas-vue",
    help="NegMAS Vue App - A Vue.js GUI for running and monitoring negotiations",
    no_args_is_help=False,
)


@cli.command()
def run(
    port: Annotated[int, typer.Option(help="Port to run the server on")] = 8020,
    host: Annotated[str, typer.Option(help="Host to bind the server to")] = "127.0.0.1",
    reload: Annotated[
        bool, typer.Option(help="Enable auto-reload on file changes")
    ] = False,
    log_level: Annotated[
        str, typer.Option(help="Log level (debug, info, warning, error, critical)")
    ] = "info",
    workers: Annotated[
        int | None,
        typer.Option(help="Number of worker processes (incompatible with reload)"),
    ] = None,
    access_log: Annotated[bool, typer.Option(help="Enable access log")] = True,
) -> None:
    """Run the NegMAS Vue App backend server."""
    import uvicorn

    # Workers and reload are mutually exclusive
    if workers is not None and reload:
        typer.echo(
            "Warning: --workers is incompatible with --reload. Disabling reload.",
            err=True,
        )
        reload = False

    uvicorn.run(
        "negmas_vue.backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        workers=workers,
        access_log=access_log,
    )


@cli.command()
def kill(
    port: Annotated[int, typer.Option(help="Port to kill the process on")] = 8020,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Kill without checking if it's negmas-vue"),
    ] = False,
) -> None:
    """Kill the negmas-vue process running on the specified port.

    By default, only kills if the process is verified to be negmas-vue.
    Use --force/-f to kill any process on the port.
    """
    import urllib.request
    import urllib.error

    # Find PIDs using the port
    result = subprocess.run(
        ["lsof", "-ti", f":{port}"],
        capture_output=True,
        text=True,
    )

    pids = result.stdout.strip()
    if not pids:
        typer.echo(f"No process found on port {port}")
        sys.exit(0)

    # Check if it's negmas-vue (unless --force)
    if not force:
        try:
            url = f"http://127.0.0.1:{port}/api/identity"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                import json

                data = json.loads(response.read().decode())
                if data.get("app") != "negmas-vue":
                    typer.echo(
                        f"Process on port {port} is not negmas-vue. Use --force/-f to kill anyway.",
                        err=True,
                    )
                    sys.exit(1)
        except urllib.error.URLError:
            typer.echo(
                f"Could not verify process on port {port} is negmas-vue (connection failed). "
                "Use --force/-f to kill anyway.",
                err=True,
            )
            sys.exit(1)
        except Exception as e:
            typer.echo(
                f"Could not verify process on port {port} is negmas-vue: {e}. "
                "Use --force/-f to kill anyway.",
                err=True,
            )
            sys.exit(1)

    # Kill all PIDs found
    killed = []
    for pid in pids.split("\n"):
        if pid:
            subprocess.run(["kill", "-9", pid], check=False)
            killed.append(pid)

    if killed:
        typer.echo(f"Killed process(es) {', '.join(killed)} on port {port}")
    sys.exit(0)


@cli.command()
def restart(
    port: Annotated[int, typer.Option(help="Port to run the server on")] = 8020,
    host: Annotated[str, typer.Option(help="Host to bind the server to")] = "127.0.0.1",
    reload: Annotated[
        bool, typer.Option(help="Enable auto-reload on file changes")
    ] = False,
    log_level: Annotated[
        str, typer.Option(help="Log level (debug, info, warning, error, critical)")
    ] = "info",
    workers: Annotated[
        int | None,
        typer.Option(help="Number of worker processes (incompatible with reload)"),
    ] = None,
    access_log: Annotated[bool, typer.Option(help="Enable access log")] = True,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Kill without checking if it's negmas-vue"),
    ] = False,
) -> None:
    """Restart the NegMAS Vue App backend server (kill existing and start new).

    Kills any existing negmas-vue process on the port, then starts a new server.
    """
    import urllib.request
    import urllib.error

    # Find PIDs using the port
    result = subprocess.run(
        ["lsof", "-ti", f":{port}"],
        capture_output=True,
        text=True,
    )

    pids = result.stdout.strip()
    if pids:
        # Check if it's negmas-vue (unless --force)
        if not force:
            try:
                url = f"http://127.0.0.1:{port}/api/identity"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=2) as response:
                    import json

                    data = json.loads(response.read().decode())
                    if data.get("app") != "negmas-vue":
                        typer.echo(
                            f"Process on port {port} is not negmas-vue. Use --force/-f to kill anyway.",
                            err=True,
                        )
                        sys.exit(1)
            except urllib.error.URLError:
                typer.echo(
                    f"Could not verify process on port {port} is negmas-vue (connection failed). "
                    "Use --force/-f to kill anyway.",
                    err=True,
                )
                sys.exit(1)
            except Exception as e:
                typer.echo(
                    f"Could not verify process on port {port} is negmas-vue: {e}. "
                    "Use --force/-f to kill anyway.",
                    err=True,
                )
                sys.exit(1)

        # Kill all PIDs found
        killed = []
        for pid in pids.split("\n"):
            if pid:
                subprocess.run(["kill", "-9", pid], check=False)
                killed.append(pid)

        if killed:
            typer.echo(f"Killed process(es) {', '.join(killed)} on port {port}")

        # Wait a moment for the port to be released
        import time

        time.sleep(0.5)
    else:
        typer.echo(f"No existing process on port {port}")

    # Start new server
    typer.echo(f"Starting negmas-vue backend on {host}:{port}...")
    import uvicorn

    # Workers and reload are mutually exclusive
    if workers is not None and reload:
        typer.echo(
            "Warning: --workers is incompatible with --reload. Disabling reload.",
            err=True,
        )
        reload = False

    uvicorn.run(
        "negmas_vue.backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        workers=workers,
        access_log=access_log,
    )


if __name__ == "__main__":
    cli()
