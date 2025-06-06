"""
API endpoints package.

This package contains all the REST API endpoints organized by functionality.
Each module contains related endpoints with proper separation of concerns.
"""

from .workflows import router as workflows_router
from .tasks import router as tasks_router
from .health import router as health_router
from .system import router as system_router

__all__ = [
    "workflows_router",
    "tasks_router", 
    "health_router",
    "system_router"
]
