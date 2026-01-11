"""Negotiation router - handles all negotiation-related endpoints."""

import json
from typing import Literal

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from ..models import NegotiationParams
from ..services import (
    NegotiationService,
    get_negotiators,
    get_groups,
    search_negotiators,
)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter()
service = NegotiationService()


def parse_list(s: str) -> list[str]:
    """Parse comma-separated string to list."""
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_float_list(s: str) -> list[float]:
    """Parse comma-separated string to float list."""
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def parse_int_list(s: str) -> list[int]:
    """Parse comma-separated string to int list."""
    return [int(x.strip()) for x in s.split(",") if x.strip()]


@router.get("/", response_class=HTMLResponse)
async def negotiation_page(request: Request):
    """Render the negotiation configuration page."""
    return templates.TemplateResponse(
        "negotiation.html",
        {"request": request, "active_page": "negotiation"},
    )


@router.post("/run")
async def run_negotiation(
    request: Request,
    protocol: str = Form("SAO"),
    negotiators: str = Form("AspirationNegotiator,NaiveTitForTatNegotiator"),
    extend_negotiators: bool = Form(False),
    truncate_ufuns: bool = Form(False),
    mechanism_params: str = Form(""),
    share_ufuns: bool = Form(False),
    share_reserved_values: bool = Form(False),
    steps: str = Form(""),
    time_limit: str = Form(""),
    scenario: str = Form(""),
    reserved: str = Form(""),
    fraction: str = Form(""),
    discount: bool = Form(True),
    normalize: bool = Form(True),
    issues: str = Form(""),
    values_min: int = Form(2),
    values_max: int = Form(50),
    sizes: str = Form(""),
    reserved_values_min: float = Form(0.0),
    reserved_values_max: float = Form(1.0),
    rational: bool = Form(True),
    rational_fraction: str = Form(""),
    reservation_selector: str = Form("min"),
    issue_names: str = Form(""),
    os_name: str = Form(""),
    ufun_names: str = Form(""),
    numeric: bool = Form(False),
    linear: bool = Form(True),
    pareto_generator: str = Form(""),
    verbose: bool = Form(False),
    verbosity: int = Form(0),
    progress: bool = Form(True),
    history: bool = Form(False),
    stats: bool = Form(True),
    rank_stats: bool = Form(False),
    compact_stats: bool = Form(True),
    plot: bool = Form(True),
    only2d: bool = Form(False),
    simple_offers_view: bool = Form(False),
    annotations: bool = Form(True),
    show_agreement: bool = Form(True),
    pareto_dist: bool = Form(True),
    nash_dist: bool = Form(True),
    kalai_dist: bool = Form(True),
    max_welfare_dist: bool = Form(True),
    max_rel_welfare_dist: bool = Form(False),
    end_reason: bool = Form(True),
    show_reserved: bool = Form(True),
    total_time: bool = Form(True),
    relative_time: bool = Form(True),
    show_n_steps: bool = Form(True),
    plot_path: str = Form(""),
    save_path: str = Form(""),
    save_history: bool = Form(True),
    save_stats: bool = Form(True),
    save_type: str = Form("yml"),
    save_compact: bool = Form(True),
    fast: bool = Form(False),
    extra_paths: str = Form(""),
    raise_exceptions: bool = Form(False),
):
    """Start a negotiation and return a job ID for streaming results."""
    params = NegotiationParams(
        protocol=protocol,
        negotiators=parse_list(negotiators),
        extend_negotiators=extend_negotiators,
        truncate_ufuns=truncate_ufuns,
        params=parse_list(mechanism_params),
        share_ufuns=share_ufuns,
        share_reserved_values=share_reserved_values,
        steps=int(steps) if steps else None,
        time_limit=float(time_limit) if time_limit else None,
        scenario=scenario if scenario else None,
        reserved=parse_float_list(reserved),
        fraction=parse_float_list(fraction),
        discount=discount,
        normalize=normalize,
        issues=int(issues) if issues else None,
        values_min=values_min,
        values_max=values_max,
        sizes=parse_int_list(sizes),
        reserved_values_min=reserved_values_min,
        reserved_values_max=reserved_values_max,
        rational=rational,
        rational_fraction=parse_float_list(rational_fraction),
        reservation_selector=reservation_selector,
        issue_names=parse_list(issue_names),
        os_name=os_name if os_name else None,
        ufun_names=parse_list(ufun_names),
        numeric=numeric,
        linear=linear,
        pareto_generator=pareto_generator if pareto_generator else None,
        verbose=verbose,
        verbosity=verbosity,
        progress=progress,
        history=history,
        stats=stats,
        rank_stats=rank_stats,
        compact_stats=compact_stats,
        plot=plot,
        only2d=only2d,
        simple_offers_view=simple_offers_view,
        annotations=annotations,
        show_agreement=show_agreement,
        pareto_dist=pareto_dist,
        nash_dist=nash_dist,
        kalai_dist=kalai_dist,
        max_welfare_dist=max_welfare_dist,
        max_rel_welfare_dist=max_rel_welfare_dist,
        end_reason=end_reason,
        show_reserved=show_reserved,
        total_time=total_time,
        relative_time=relative_time,
        show_n_steps=show_n_steps,
        plot_path=plot_path if plot_path else None,
        save_path=save_path if save_path else None,
        save_history=save_history,
        save_stats=save_stats,
        save_type=save_type,
        save_compact=save_compact,
        fast=fast,
        extra_paths=parse_list(extra_paths),
        raise_exceptions=raise_exceptions,
    )

    job_id = service.create_job(params)
    return templates.TemplateResponse(
        "partials/negotiation_result.html",
        {"request": request, "job_id": job_id},
    )


@router.get("/stream/{job_id}")
async def stream_negotiation(job_id: str):
    """Stream negotiation output via Server-Sent Events."""

    async def event_generator():
        async for update in service.run_negotiation(job_id):
            event = update.pop("event")
            yield {"event": event, "data": json.dumps(update)}

    return EventSourceResponse(event_generator())


@router.get("/status/{job_id}")
async def get_negotiation_status(job_id: str):
    """Get the status of a negotiation job."""
    status = service.get_job_status(job_id)
    if not status:
        return {"error": "Job not found"}
    return status


@router.get("/negotiators/groups")
async def list_negotiator_groups():
    """Get all available negotiator groups with metadata."""
    return get_groups()


@router.get("/negotiators")
async def list_negotiators(
    group: str | None = Query(
        None, description="Filter by group (e.g., 'builtin', 'anac2019')"
    ),
    category: Literal["all", "winners", "finalists"] = Query(
        "all", description="Filter genius agents by competition results"
    ),
    search: str | None = Query(None, description="Search negotiators by name"),
):
    """
    List available negotiators with optional filtering.

    - **group**: Filter by group (builtin, basic, anac2010-anac2019)
    - **category**: For genius agents, filter by competition results (all, winners, finalists)
    - **search**: Search negotiators by name (case-insensitive substring match)
    """
    # Parse group parameter - can be comma-separated for multiple groups
    groups = None
    if group:
        groups = [g.strip() for g in group.split(",") if g.strip()]
        if len(groups) == 1:
            groups = groups[0]

    if search:
        negotiators = search_negotiators(search, group=groups, category=category)
    else:
        negotiators = get_negotiators(group=groups, category=category)

    return [
        {
            "name": n.name,
            "full_path": n.full_path,
            "group": n.group,
            "category": n.category,
        }
        for n in negotiators
    ]
