"""NegMAS Helper - CLI tool for cache management and other support tasks."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel
from rich.table import Table
from rich import box

from .services.scenario_cache_service import ScenarioCacheService

# Rich console for beautiful output
console = Console()

# Typer CLI app
cli = typer.Typer(
    name="negmas-helper",
    help="NegMAS Helper - Support tools for negmas-app",
    no_args_is_help=True,
)

# Cache command group
cache_app = typer.Typer(
    name="cache",
    help="Manage cache files (scenarios, tournaments, etc.)",
    no_args_is_help=True,
)
cli.add_typer(cache_app, name="cache")


@cache_app.command("build")
def cache_build(
    target: Annotated[
        str, typer.Argument(help="Cache target: 'scenarios'")
    ] = "scenarios",
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
) -> None:
    """Build cache files for scenarios.

    Examples:
        negmas-helper cache build scenarios --info --stats
        negmas-helper cache build scenarios --plots
        negmas-helper cache build scenarios --all
        negmas-helper cache build scenarios --stats --compact
    """
    if target != "scenarios":
        console.print(
            f"[red]Error:[/red] Unknown target '{target}'. Currently only 'scenarios' is supported."
        )
        raise typer.Exit(1)

    # If --all is specified, enable all cache types
    if all:
        info = stats = plots = True

    # If no flags specified, show error
    if not (info or stats or plots):
        console.print(
            "[red]Error:[/red] Must specify at least one cache type (--info, --stats, --plots, or --all)"
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

    console.print(
        Panel(
            f"Building {', '.join(cache_types)} caches for [bold]{target}[/bold]",
            title="[bold green]Cache Build[/bold green]",
            border_style="green",
        )
    )

    cache_service = ScenarioCacheService()

    # Build requested caches with progress bar
    results = cache_service.build_caches_with_progress(
        build_info=info,
        build_stats=stats,
        build_plots=plots,
        compact=compact,
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
    if plots:
        table.add_row(
            "Plot Files Created", f"[yellow]{results['plots_created']}[/yellow]"
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

    if results["failed"] == 0:
        console.print(
            "\n[bold green]✓[/bold green] Cache build completed successfully!"
        )
    else:
        console.print(
            f"\n[yellow]⚠[/yellow] Cache build completed with {results['failed']} failures"
        )


@cache_app.command("clear")
def cache_clear(
    target: Annotated[
        str, typer.Argument(help="Cache target: 'scenarios'")
    ] = "scenarios",
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
        negmas-helper cache clear scenarios --info --stats
        negmas-helper cache clear scenarios --plots
        negmas-helper cache clear scenarios --all
    """
    if target != "scenarios":
        console.print(
            f"[red]Error:[/red] Unknown target '{target}'. Currently only 'scenarios' is supported."
        )
        raise typer.Exit(1)

    # If --all is specified, enable all cache types
    if all:
        info = stats = plots = True

    # If no flags specified, show error
    if not (info or stats or plots):
        console.print(
            "[red]Error:[/red] Must specify at least one cache type (--info, --stats, --plots, or --all)"
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
            f"\n[yellow]Warning:[/yellow] This will delete {', '.join(cache_types)} cache files for all scenarios."
        )
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    console.print(
        Panel(
            f"Clearing {', '.join(cache_types)} caches for [bold]{target}[/bold]",
            title="[bold red]Cache Clear[/bold red]",
            border_style="red",
        )
    )

    cache_service = ScenarioCacheService()

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
