"""NegMAS App - Vue.js version entry point."""

import asyncio
import os
import signal
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich import box


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    from .routers.scenarios import get_loader
    from .services.registry_service import initialize_registry

    console = Console()

    # Initialize registry with virtual negotiators/mechanisms
    console.print("[yellow]Initializing registry...[/yellow]")
    try:
        results = await asyncio.to_thread(initialize_registry)
        console.print(
            f"[green]✓ Registry initialized: "
            f"{results['virtual_negotiators']} virtual negotiators, "
            f"{results['virtual_mechanisms']} virtual mechanisms[/green]"
        )
    except Exception as e:
        console.print(f"[red]✗ Registry initialization failed: {e}[/red]")

    # Start background scenario registration
    console.print("[yellow]Starting background scenario registration...[/yellow]")
    loader = get_loader()

    async def register_scenarios():
        try:
            count = await asyncio.to_thread(loader.ensure_scenarios_registered)
            console.print(f"[green]✓ Registered {count} scenarios[/green]")
        except Exception as e:
            console.print(f"[red]✗ Registration failed: {e}[/red]")

    # Don't wait for registration to complete - let it run in background
    asyncio.create_task(register_scenarios())

    yield

    # Shutdown
    # Nothing to clean up currently


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
    filters_router,
)

# Create FastAPI app with lifespan
app = FastAPI(
    title="NegMAS App",
    description="Vue.js frontend for NegMAS - Run and monitor negotiations",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(filters_router)


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

# Rich console for beautiful output
console = Console()


def check_and_setup_scenarios() -> bool:
    """Check if scenarios are set up, and if not, prompt user to set them up.

    Returns:
        True if scenarios are ready, False if user declined setup.
    """
    from .services.setup_service import SetupService
    from .services.scenario_cache_service import ScenarioCacheService

    scenarios_dir = Path.home() / "negmas" / "app" / "scenarios"

    # Check if scenarios directory exists and has content
    if scenarios_dir.exists():
        # Count scenario files
        scenario_files = list(scenarios_dir.rglob("*.yml")) + list(
            scenarios_dir.rglob("*.yaml")
        )
        if len(scenario_files) > 10:  # Arbitrary threshold - should have hundreds
            return True

    # Scenarios not set up - prompt user
    console.print()
    console.print(
        Panel(
            "[bold yellow]Scenarios Not Found[/bold yellow]\n\n"
            "NegMAS App requires scenarios to be extracted from the bundled scenarios.zip file.\n"
            f"Scenarios will be extracted to: [cyan]{scenarios_dir}[/cyan]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    # Ask if user wants to set up
    if not Confirm.ask("\nWould you like to extract scenarios now?", default=True):
        console.print(
            "[yellow]Scenarios not extracted. The app may not function properly.[/yellow]"
        )
        return False

    console.print()

    # Ask about cache options
    console.print("[bold]Cache Options[/bold]\n")

    # Create explanation table
    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("Cache Type", style="cyan", width=12)
    table.add_column("Description", width=50)
    table.add_column("Size", justify="right", width=10)

    table.add_row(
        "Info",
        "Basic scenario information (outcomes count, issue names, etc.)\n"
        "→ Speeds up scenario browsing",
        "~1 MB",
    )
    table.add_row(
        "Stats",
        "Pre-calculated statistics (Pareto frontier, Nash, Kalai, etc.)\n"
        "→ Speeds up initial scenario view and analysis",
        "~1-5 MB",
    )
    table.add_row(
        "Plots",
        "Pre-rendered outcome space visualizations\n"
        "→ Instant plot display, no calculation needed",
        "~10-20 MB",
    )

    console.print(table)
    console.print()

    # Ask about each cache type
    build_info = Confirm.ask("Build [cyan]info[/cyan] cache?", default=True)
    build_stats = Confirm.ask("Build [magenta]stats[/magenta] cache?", default=True)
    build_plots = Confirm.ask("Build [yellow]plots[/yellow] cache?", default=False)

    compact = False
    if build_stats:
        console.print("\n[dim]Stats Optimization:[/dim]")
        compact = Confirm.ask(
            "  Use [bold]compact[/bold] mode? (excludes Pareto frontier points, saves ~50% space)",
            default=False,
        )

    console.print()
    console.print(
        Panel(
            "Extracting scenarios and building caches...",
            title="[bold green]Setup Progress[/bold green]",
            border_style="green",
        )
    )

    # Extract scenarios (always include cache files if they exist in zip)
    try:
        stats = SetupService.copy_bundled_scenarios(
            target_dir=scenarios_dir,
            force=False,
            skip_cache=False,  # Include any pre-built cache files from zip
        )

        console.print(f"✓ Extracted {stats['copied']} scenario files")

        if stats["errors"]:
            console.print(
                f"[yellow]⚠ {len(stats['errors'])} errors during extraction[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]✗ Error extracting scenarios: {e}[/red]")
        return False

    # Build additional caches if requested
    if build_info or build_stats or build_plots:
        console.print("\nBuilding caches...")
        try:
            cache_service = ScenarioCacheService(scenarios_root=scenarios_dir)
            cache_results = cache_service.build_caches_with_progress(
                build_info=build_info,
                build_stats=build_stats,
                build_plots=build_plots,
                compact=compact,
                refresh=False,  # Don't rebuild what's already there
                console=console,
            )

            if build_info:
                console.print(
                    f"✓ Built {cache_results['info_created']} info cache files"
                )
            if build_stats:
                console.print(
                    f"✓ Built {cache_results['stats_created']} stats cache files"
                )
            if build_plots:
                console.print(
                    f"✓ Built {cache_results['plots_created']} plot cache files"
                )

        except Exception as e:
            console.print(f"[yellow]⚠ Error building caches: {e}[/yellow]")
            console.print(
                "[dim]You can build caches later using: negmas-app cache build scenarios --all[/dim]"
            )

    console.print()
    console.print("[bold green]✓ Setup complete![/bold green]\n")
    return True


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

    # Check if scenarios are set up, prompt if not
    if not check_and_setup_scenarios():
        typer.echo(
            "\nWarning: Scenarios not set up. You can set them up later with: negmas-app setup"
        )
        if not typer.confirm("Continue anyway?", default=False):
            typer.echo("Cancelled.")
            sys.exit(0)

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


@cli.command()
def setup(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing scenario files"),
    ] = False,
    skip_cache: Annotated[
        bool,
        typer.Option(
            "--skip-cache",
            help="Skip copying cache files (_info.yaml, _stats.yaml, _plot.webp)",
        ),
    ] = False,
) -> None:
    """Set up NegMAS App by extracting bundled scenarios to ~/negmas/app/scenarios/.

    This command extracts all bundled scenarios from scenarios.zip to your home directory.
    It will also check for Genius Bridge and offer to download it if not found.

    Safe to run multiple times:
    - Skips existing files by default (preserves your modifications)
    - Only copies missing files
    - Use --force to overwrite everything

    By default, includes pre-generated cache files for faster loading.

    Examples:
        negmas-app setup                  # Extract scenarios with cache files
        negmas-app setup --skip-cache     # Extract scenarios without cache files
        negmas-app setup --force          # Overwrite all existing files
    """
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from .services.setup_service import SetupService

    console = Console()

    console.print("\n[bold cyan]NegMAS App Setup[/bold cyan]")
    console.print()

    # Ensure user directories exist
    try:
        SetupService.ensure_user_directories()
        console.print("[green]✓[/green] Created user directories in ~/negmas/app/")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create directories: {e}", style="red")
        sys.exit(1)

    # Copy scenarios
    target_dir = SetupService.get_user_scenarios_path()
    console.print(f"\n[bold]Extracting scenarios to:[/bold] {target_dir}")

    if force:
        console.print("[yellow]⚠ Force mode: Will overwrite existing files[/yellow]")

    if skip_cache:
        console.print(
            "[dim]Skipping cache files (_info.yaml, _stats.yaml, _plot.webp)[/dim]"
        )

    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Extracting files...", total=None)

        try:
            stats = SetupService.copy_bundled_scenarios(
                target_dir=target_dir,
                force=force,
                skip_cache=skip_cache,
            )
        except FileNotFoundError as e:
            progress.stop()
            console.print(f"\n[red]✗[/red] {e}", style="red")
            sys.exit(1)
        except Exception as e:
            progress.stop()
            console.print(f"\n[red]✗[/red] Unexpected error: {e}", style="red")
            sys.exit(1)

    # Report results
    console.print()
    console.print("[bold green]Setup Complete![/bold green]")
    console.print()
    console.print(f"  Total files found:  {stats['total_files']}")
    console.print(f"  [green]Copied:         {stats['copied']}[/green]")
    if stats["skipped"] > 0:
        console.print(
            f"  [yellow]Skipped:        {stats['skipped']}[/yellow] [dim](already exist)[/dim]"
        )
    else:
        console.print(f"  [dim]Skipped:        {stats['skipped']}[/dim]")

    if stats["errors"]:
        console.print(f"  [red]Errors:         {len(stats['errors'])}[/red]")
        console.print()
        console.print("[red]Errors encountered:[/red]")
        for error in stats["errors"][:10]:  # Show first 10 errors
            console.print(f"  • {error}", style="red")
        if len(stats["errors"]) > 10:
            console.print(f"  ... and {len(stats['errors']) - 10} more errors")

    # Count scenarios
    scenario_count = SetupService.count_scenarios(target_dir)
    console.print()
    console.print(f"[bold cyan]{scenario_count} scenarios[/bold cyan] ready to use!")

    # Add helpful hint if files were skipped
    if stats["skipped"] > 0:
        console.print()
        console.print(
            "[dim]Tip: Existing files were preserved. Use --force to overwrite them.[/dim]"
        )

    console.print()

    # Check for Genius Bridge and offer to set it up
    genius_jar = Path.home() / "negmas" / "files" / "geniusbridge.jar"
    if not genius_jar.exists():
        console.print(
            "[yellow]⚠ Genius Bridge not found[/yellow] - Required for running Genius/ANAC agents"
        )
        console.print(f"   Expected location: {genius_jar}")
        console.print()

        if Confirm.ask("Would you like to download Genius Bridge now?", default=True):
            console.print()
            console.print("[bold]Running Genius Setup...[/bold]")
            console.print()

            # Run negmas genius-setup
            result = subprocess.run(
                [sys.executable, "-m", "negmas", "genius-setup"],
                capture_output=False,
            )

            if result.returncode == 0:
                console.print()
                console.print("[green]✓[/green] Genius Bridge setup complete!")
            else:
                console.print()
                console.print(
                    "[yellow]⚠[/yellow] Genius Bridge setup failed. You can run it manually later:"
                )
                console.print("   [bold]negmas genius-setup[/bold]")
        else:
            console.print(
                "[dim]You can set up Genius Bridge later with: negmas genius-setup[/dim]"
            )
        console.print()

    console.print("Start the app with: [bold]negmas-app run[/bold]")
    console.print()


@cli.command()
def update_scenarios(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing scenario files"),
    ] = False,
    skip_cache: Annotated[
        bool,
        typer.Option(
            "--skip-cache",
            help="Skip copying cache files (_info.yaml, _stats.yaml, _plot.webp)",
        ),
    ] = False,
) -> None:
    """Update scenarios from the bundled package to ~/negmas/app/scenarios/.

    This command updates scenarios by copying them from the package.
    By default, it skips existing files (preserves your modifications).
    Use --force to overwrite all files with package versions.

    Examples:
        negmas-app update-scenarios           # Update without overwriting existing files
        negmas-app update-scenarios --force   # Overwrite all with package versions
    """
    from rich.console import Console

    from .services.setup_service import SetupService

    console = Console()

    target_dir = SetupService.get_user_scenarios_path()

    if not target_dir.exists():
        console.print(
            "[yellow]User scenarios directory doesn't exist.[/yellow]",
            style="yellow",
        )
        console.print("Run [bold]negmas-app setup[/bold] first to initialize.")
        sys.exit(1)

    console.print("\n[bold cyan]Updating Scenarios[/bold cyan]")
    console.print()
    console.print(f"[bold]Target:[/bold] {target_dir}")

    if not force:
        console.print("[dim]Skipping existing files (use --force to overwrite)[/dim]")

    if skip_cache:
        console.print("[dim]Skipping cache files[/dim]")

    console.print()

    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Copying files...", total=None)
            stats = SetupService.copy_bundled_scenarios(
                target_dir=target_dir,
                force=force,
                skip_cache=skip_cache,
            )

        # Report results
        console.print()
        console.print("[bold green]Update Complete![/bold green]")
        console.print()
        console.print(f"  Total files found:  {stats['total_files']}")
        console.print(f"  [green]Copied:         {stats['copied']}[/green]")
        console.print(f"  [yellow]Skipped:        {stats['skipped']}[/yellow]")

        if stats["errors"]:
            console.print(f"  [red]Errors:         {len(stats['errors'])}[/red]")
            console.print()
            console.print("[red]Errors encountered:[/red]")
            for error in stats["errors"][:10]:
                console.print(f"  • {error}", style="red")
            if len(stats["errors"]) > 10:
                console.print(f"  ... and {len(stats['errors']) - 10} more errors")

        console.print()

    except FileNotFoundError as e:
        console.print(f"\n[red]✗[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗[/red] Unexpected error: {e}", style="red")
        sys.exit(1)


# ============================================================================
# Cache Management Commands
# ============================================================================

# Cache command group
cache_app = typer.Typer(
    name="cache",
    help="Manage cache files (scenarios, tournaments, etc.)",
    no_args_is_help=True,
)
cli.add_typer(cache_app, name="cache")

# Cache build subcommand group
cache_build_app = typer.Typer(
    name="build",
    help="Build cache files for various resources",
    no_args_is_help=True,
)
cache_app.add_typer(cache_build_app, name="build")

# Cache clear subcommand group
cache_clear_app = typer.Typer(
    name="clear",
    help="Clear cache files for various resources",
    no_args_is_help=True,
)
cache_app.add_typer(cache_clear_app, name="clear")


@cache_build_app.command("scenarios")
def cache_build_scenarios(
    path: Annotated[
        str | None,
        typer.Option(
            help="Custom path to scenarios directory (defaults to ~/negmas/app/scenarios/)"
        ),
    ] = None,
    info: Annotated[bool, typer.Option(help="Build info cache (_info.yaml)")] = False,
    stats: Annotated[
        bool, typer.Option(help="Build stats cache (_stats.yaml)")
    ] = False,
    plots: Annotated[
        bool, typer.Option(help="Build plot caches (_plot.webp or _plots/)")
    ] = False,
    all: Annotated[bool, typer.Option(help="Build all cache types")] = False,
    compact: Annotated[
        bool, typer.Option(help="Exclude Pareto frontier from stats (saves disk space)")
    ] = False,
    refresh: Annotated[
        bool,
        typer.Option(
            help="Force rebuild existing cache files (default: skip existing)"
        ),
    ] = False,
) -> None:
    """Build cache files for scenarios.

    By default, existing cache files are kept. Use --refresh to force rebuild.

    Examples:
        negmas-app cache build scenarios --info --stats
        negmas-app cache build scenarios --plots --refresh
        negmas-app cache build scenarios --all
        negmas-app cache build scenarios --stats --compact
        negmas-app cache build scenarios --path ~/my-scenarios --all
    """
    from .services.scenario_cache_service import ScenarioCacheService

    # If --all is specified, enable all cache types
    if all:
        info = stats = plots = True

    # If no flags specified, show error
    if not (info or stats or plots):
        console.print(
            "[red]Error:[/red] Must specify at least one cache type (--info, --stats, --plots, or --all)"
        )
        raise typer.Exit(1)

    # Convert path to Path object, default to ~/negmas/app/scenarios/
    if path:
        target_path = Path(path).expanduser().resolve()
    else:
        target_path = Path.home() / "negmas" / "app" / "scenarios"

    # Validate path exists
    if not target_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {target_path}")
        if not path:
            console.print(
                "[dim]Hint: Run 'negmas-app setup' to create the default scenarios directory[/dim]"
            )
        raise typer.Exit(1)

    # Build cache type list for display
    cache_types = []
    if info:
        cache_types.append("[cyan]info[/cyan]")
    if stats:
        stats_label = "[magenta]stats[/magenta]"
        if compact:
            stats_label += " [dim](compact)[/dim]"
        cache_types.append(stats_label)
    if plots:
        cache_types.append("[yellow]plots[/yellow]")

    mode_text = "[dim](refresh mode)[/dim]" if refresh else "[dim](skip existing)[/dim]"

    console.print(
        Panel(
            f"Building {', '.join(cache_types)} caches for [bold]scenarios[/bold] at [bold]{target_path}[/bold] {mode_text}",
            title="[bold green]Cache Build[/bold green]",
            border_style="green",
        )
    )

    cache_service = ScenarioCacheService(scenarios_root=target_path)

    # Build requested caches with progress bar
    results = cache_service.build_caches_with_progress(
        build_info=info,
        build_stats=stats,
        build_plots=plots,
        compact=compact,
        refresh=refresh,
        console=console,
    )

    # Display results in a nice table
    table = Table(
        title="Build Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right", style="bold")

    table.add_row("Total Scenarios", str(results["total"]))
    table.add_row("Successful", f"[green]{results['successful']}[/green]")
    table.add_row(
        "Failed", f"[red]{results['failed']}[/red]" if results["failed"] > 0 else "0"
    )

    if info:
        table.add_row("Info Files Created", f"[cyan]{results['info_created']}[/cyan]")
    if stats:
        table.add_row(
            "Stats Files Created", f"[magenta]{results['stats_created']}[/magenta]"
        )
        if results.get("stats_skipped", 0) > 0:
            table.add_row(
                "Stats Skipped (too large)",
                f"[yellow]{results['stats_skipped']}[/yellow]",
            )
    if plots:
        table.add_row(
            "Plot Files Created", f"[yellow]{results['plots_created']}[/yellow]"
        )

    console.print(table)

    if results.get("skipped"):
        console.print(
            f"\n[yellow]Scenarios skipped ({len(results['skipped'])}):[/yellow]"
        )
        for scenario_name, reason in results["skipped"][:10]:  # Show first 10
            console.print(f"  [yellow]•[/yellow] {scenario_name}: {reason}")
        if len(results["skipped"]) > 10:
            console.print(f"  [dim]... and {len(results['skipped']) - 10} more[/dim]")

    if results["errors"]:
        console.print(
            f"\n[yellow]Errors encountered ({len(results['errors'])}):[/yellow]"
        )
        for error in results["errors"][:10]:  # Show first 10 errors
            console.print(f"  [red]•[/red] {error}")
        if len(results["errors"]) > 10:
            console.print(f"  [dim]... and {len(results['errors']) - 10} more[/dim]")

    if results["failed"] == 0:
        console.print(
            "\n[bold green]✓[/bold green] Cache build completed successfully!"
        )
    else:
        console.print(
            f"\n[yellow]⚠[/yellow] Cache build completed with {results['failed']} failures"
        )


@cache_clear_app.command("scenarios")
def cache_clear_scenarios(
    path: Annotated[
        str | None,
        typer.Option(
            help="Custom path to scenarios directory (defaults to ~/negmas/app/scenarios/)"
        ),
    ] = None,
    info: Annotated[bool, typer.Option(help="Clear info cache (_info.yaml)")] = False,
    stats: Annotated[
        bool, typer.Option(help="Clear stats cache (_stats.yaml)")
    ] = False,
    plots: Annotated[
        bool, typer.Option(help="Clear plot caches (_plot.webp or _plots/)")
    ] = False,
    all: Annotated[bool, typer.Option(help="Clear all cache types")] = False,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation prompt")
    ] = False,
) -> None:
    """Clear cache files for scenarios.

    Examples:
        negmas-app cache clear scenarios --info --stats
        negmas-app cache clear scenarios --plots
        negmas-app cache clear scenarios --all
        negmas-app cache clear scenarios --path ~/my-scenarios --all
    """
    from .services.scenario_cache_service import ScenarioCacheService

    # If --all is specified, enable all cache types
    if all:
        info = stats = plots = True

    # If no flags specified, show error
    if not (info or stats or plots):
        console.print(
            "[red]Error:[/red] Must specify at least one cache type (--info, --stats, --plots, or --all)"
        )
        raise typer.Exit(1)

    # Convert path to Path object, default to ~/negmas/app/scenarios/
    if path:
        target_path = Path(path).expanduser().resolve()
    else:
        target_path = Path.home() / "negmas" / "app" / "scenarios"

    # Validate path exists
    if not target_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {target_path}")
        if not path:
            console.print(
                "[dim]Hint: Run 'negmas-app setup' to create the default scenarios directory[/dim]"
            )
        raise typer.Exit(1)

    # Build cache type list for confirmation
    cache_types = []
    if info:
        cache_types.append("[cyan]info[/cyan]")
    if stats:
        cache_types.append("[magenta]stats[/magenta]")
    if plots:
        cache_types.append("[yellow]plots[/yellow]")

    # Confirmation prompt
    if not force:
        console.print(
            f"\n[yellow]Warning:[/yellow] This will delete {', '.join(cache_types)} cache files for all scenarios in:"
        )
        console.print(f"  [bold]{target_path}[/bold]")
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    console.print(
        Panel(
            f"Clearing {', '.join(cache_types)} caches for [bold]scenarios[/bold] at [bold]{target_path}[/bold]",
            title="[bold red]Cache Clear[/bold red]",
            border_style="red",
        )
    )

    cache_service = ScenarioCacheService(scenarios_root=target_path)

    # Clear requested caches with progress bar
    results = cache_service.clear_caches_with_progress(
        clear_info=info,
        clear_stats=stats,
        clear_plots=plots,
        console=console,
    )

    # Display results in a nice table
    table = Table(
        title="Clear Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right", style="bold")

    table.add_row("Total Scenarios", str(results["total"]))

    if info:
        table.add_row("Info Files Deleted", f"[cyan]{results['info_deleted']}[/cyan]")
    if stats:
        table.add_row(
            "Stats Files Deleted", f"[magenta]{results['stats_deleted']}[/magenta]"
        )
    if plots:
        table.add_row(
            "Plot Files Deleted", f"[yellow]{results['plots_deleted']}[/yellow]"
        )

    console.print(table)

    if results["errors"]:
        console.print(
            f"\n[yellow]Errors encountered ({len(results['errors'])}):[/yellow]"
        )
        for error in results["errors"][:10]:  # Show first 10 errors
            console.print(f"  [red]•[/red] {error}")
        if len(results["errors"]) > 10:
            console.print(f"  [dim]... and {len(results['errors']) - 10} more[/dim]")

    total_deleted = (
        results.get("info_deleted", 0)
        + results.get("stats_deleted", 0)
        + results.get("plots_deleted", 0)
    )
    if total_deleted > 0:
        console.print(
            f"\n[bold green]✓[/bold green] Successfully cleared {total_deleted} cache files!"
        )
    else:
        console.print("\n[dim]No cache files found to clear.[/dim]")


if __name__ == "__main__":
    cli()
