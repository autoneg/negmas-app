"""NegMAS App - Vue.js version entry point."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated

import typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from .routers import (
    scenarios_router,
    negotiators_router,
    negotiation_router,
    settings_router,
    genius_router,
    mechanisms_router,
    tournament_router,
    sources_router,
    components_router,
    cache_router,
)

# Create FastAPI app
app = FastAPI(
    title="NegMAS App",
    description="Vue.js frontend for NegMAS - Run and monitor negotiations",
    version="0.1.0",
)

# Add CORS middleware for development (Vite dev server runs on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",  # Vite dev server
        "http://127.0.0.1:5174",
        "http://localhost:8019",  # Backend
        "http://127.0.0.1:8019",
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
app.include_router(components_router)
app.include_router(cache_router)


@app.get("/api/identity")
async def identity():
    """Return app identity for verification.

    Used by the kill command to verify that the process on a port is negmas-app.
    """
    return {
        "app": "negmas-app",
        "version": app.version,
    }


# Typer CLI app
cli = typer.Typer(
    name="negmas-app",
    help="NegMAS App - A Vue.js GUI for running and monitoring negotiations",
    no_args_is_help=False,
)


@cli.command()
def run(
    port: Annotated[
        int, typer.Option(help="Port for the frontend (user-facing)")
    ] = 5174,
    backend_port: Annotated[int, typer.Option(help="Port for the backend API")] = 8019,
    host: Annotated[str, typer.Option(help="Host to bind servers to")] = "127.0.0.1",
    log_level: Annotated[
        str,
        typer.Option(help="Backend log level (debug, info, warning, error, critical)"),
    ] = "info",
    dev: Annotated[
        bool, typer.Option("--dev", help="Enable development mode with auto-reload")
    ] = True,
) -> None:
    """Run the NegMAS App (both backend and frontend servers).

    This command starts:
    - FastAPI backend API server (default port 8019)
    - Vite frontend dev server (default port 5174)

    The --port option controls the frontend port (what users access).
    Use --backend-port to change the backend API port if needed.

    Press Ctrl+C to stop both servers.
    """
    import atexit

    # Get the project root directory
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "src" / "frontend"

    if not frontend_dir.exists():
        typer.echo(f"Error: Frontend directory not found at {frontend_dir}", err=True)
        sys.exit(1)

    # Check if npm is installed
    npm_check = subprocess.run(["which", "npm"], capture_output=True)
    if npm_check.returncode != 0:
        typer.echo("Error: npm not found. Please install Node.js and npm.", err=True)
        sys.exit(1)

    # Check if node_modules exists, if not run npm install
    if not (frontend_dir / "node_modules").exists():
        typer.echo("Installing frontend dependencies (first time only)...")
        install_result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=False,
        )
        if install_result.returncode != 0:
            typer.echo("Error: npm install failed", err=True)
            sys.exit(1)

    processes = []

    def cleanup():
        """Kill all child processes on exit."""
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception:
                pass

    atexit.register(cleanup)

    try:
        typer.echo(f"Starting NegMAS App...")
        typer.echo(f"Backend API: http://{host}:{backend_port}")
        typer.echo(f"Frontend: http://{host}:{port}")
        typer.echo("Press Ctrl+C to stop both servers\n")

        # Start backend server
        typer.echo("Starting backend server...")
        reload_flag = "--reload" if dev else ""
        backend_args = [
            sys.executable,
            "-m",
            "uvicorn",
            "negmas_app.main:app",
            "--host",
            host,
            "--port",
            str(backend_port),
            "--log-level",
            log_level,
        ]
        if dev:
            backend_args.append("--reload")

        backend_proc = subprocess.Popen(backend_args, cwd=project_root)
        processes.append(backend_proc)

        # Give backend a moment to start
        time.sleep(1)

        # Start frontend server
        typer.echo("Starting frontend server...")
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(port), "--host", host],
            cwd=frontend_dir,
        )
        processes.append(frontend_proc)

        # Wait a moment for frontend to start
        time.sleep(2)

        typer.echo(f"\n✓ Both servers are running!")
        typer.echo(f"✓ Open your browser to: http://{host}:{port}\n")

        # Wait for processes
        while True:
            # Check if any process has died
            for proc in processes:
                if proc.poll() is not None:
                    typer.echo(
                        f"\nError: A server process stopped unexpectedly", err=True
                    )
                    cleanup()
                    sys.exit(1)
            time.sleep(1)

    except KeyboardInterrupt:
        typer.echo("\n\nStopping servers...")
        cleanup()
        typer.echo("All servers stopped.")
        sys.exit(0)
    except Exception as e:
        typer.echo(f"\nError: {e}", err=True)
        cleanup()
        sys.exit(1)


def _kill_processes(
    backend_port: int = 8019,
    frontend_port: int = 5174,
    force: bool = False,
    exit_on_error: bool = True,
) -> bool:
    """Internal function to kill negmas-app processes.

    Returns True if any processes were killed, False otherwise.
    If exit_on_error is True, will call sys.exit(1) on verification failure.
    """
    import urllib.request
    import urllib.error

    killed_any = False

    # Kill backend
    result = subprocess.run(
        ["lsof", "-ti", f":{backend_port}"],
        capture_output=True,
        text=True,
    )

    pids = result.stdout.strip()
    if pids:
        # Check if it's negmas-app backend (unless --force)
        if not force:
            try:
                url = f"http://127.0.0.1:{backend_port}/api/identity"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=2) as response:
                    import json

                    data = json.loads(response.read().decode())
                    if data.get("app") != "negmas-app":
                        typer.echo(
                            f"Process on port {backend_port} is not negmas-app backend. Use --force/-f to kill anyway.",
                            err=True,
                        )
                        if exit_on_error:
                            sys.exit(1)
                        return False
            except urllib.error.URLError:
                pass  # Likely not running, will try to kill anyway
            except Exception:
                pass  # Likely not running, will try to kill anyway

        # Kill backend PIDs
        killed = []
        for pid in pids.split("\n"):
            if pid:
                subprocess.run(["kill", "-9", pid], check=False)
                killed.append(pid)

        if killed:
            typer.echo(
                f"Killed backend process(es) {', '.join(killed)} on port {backend_port}"
            )
            killed_any = True

    # Kill frontend
    result = subprocess.run(
        ["lsof", "-ti", f":{frontend_port}"],
        capture_output=True,
        text=True,
    )

    pids = result.stdout.strip()
    if pids:
        # Kill frontend PIDs (no verification needed, just kill)
        killed = []
        for pid in pids.split("\n"):
            if pid:
                subprocess.run(["kill", "-9", pid], check=False)
                killed.append(pid)

        if killed:
            typer.echo(
                f"Killed frontend process(es) {', '.join(killed)} on port {frontend_port}"
            )
            killed_any = True

    if not killed_any:
        typer.echo(
            f"No processes found on ports {backend_port} (backend) or {frontend_port} (frontend)"
        )

    return killed_any


@cli.command()
def kill(
    backend_port: Annotated[int, typer.Option(help="Backend port to kill")] = 8019,
    frontend_port: Annotated[int, typer.Option(help="Frontend port to kill")] = 5174,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Kill without checking if it's negmas-app"),
    ] = False,
) -> None:
    """Kill negmas-app processes (both backend and frontend).

    By default, kills processes on both default ports (backend: 8019, frontend: 5174).
    Use --force/-f to kill any process on those ports without verification.
    """
    _kill_processes(backend_port=backend_port, frontend_port=frontend_port, force=force)
    sys.exit(0)


@cli.command()
def start(
    port: Annotated[
        int, typer.Option(help="Port for the frontend (user-facing)")
    ] = 5174,
    backend_port: Annotated[int, typer.Option(help="Port for the backend API")] = 8019,
    host: Annotated[str, typer.Option(help="Host to bind servers to")] = "127.0.0.1",
    log_level: Annotated[
        str,
        typer.Option(help="Backend log level (debug, info, warning, error, critical)"),
    ] = "info",
    dev: Annotated[
        bool, typer.Option("--dev", help="Enable development mode with auto-reload")
    ] = True,
) -> None:
    """Start the NegMAS App (synonym for 'run').

    This command is identical to 'run' - it starts both backend and frontend servers.
    Use whichever command you prefer: 'negmas-app start' or 'negmas-app run'.
    """
    run(port=port, backend_port=backend_port, host=host, log_level=log_level, dev=dev)


@cli.command()
def restart(
    port: Annotated[
        int, typer.Option(help="Port for the frontend (user-facing)")
    ] = 5174,
    backend_port: Annotated[int, typer.Option(help="Port for the backend API")] = 8019,
    host: Annotated[str, typer.Option(help="Host to bind servers to")] = "127.0.0.1",
    log_level: Annotated[
        str,
        typer.Option(help="Backend log level (debug, info, warning, error, critical)"),
    ] = "info",
    dev: Annotated[
        bool, typer.Option("--dev", help="Enable development mode with auto-reload")
    ] = True,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Kill without checking if it's negmas-app"),
    ] = False,
) -> None:
    """Restart the NegMAS App (kill existing processes and start new ones).

    Kills any existing negmas-app processes, then starts fresh servers.
    """
    typer.echo("Stopping existing servers...")

    # Call internal kill function (don't exit on completion)
    _kill_processes(
        backend_port=backend_port, frontend_port=port, force=force, exit_on_error=False
    )

    # Wait a moment for ports to be released
    time.sleep(0.5)

    # Call start command
    typer.echo("\nStarting fresh servers...")
    start(port=port, backend_port=backend_port, host=host, log_level=log_level, dev=dev)


if __name__ == "__main__":
    cli()
