"""API routers for NegMAS App."""

from .scenarios import router as scenarios_router
from .negotiators import router as negotiators_router
from .negotiation import router as negotiation_router
from .settings import router as settings_router
from .genius import router as genius_router
from .mechanisms import router as mechanisms_router

__all__ = [
    "scenarios_router",
    "negotiators_router",
    "negotiation_router",
    "settings_router",
    "genius_router",
    "mechanisms_router",
]
