"""
Prometheus metrics for FastAPI (Phase 3).
"""

from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_prometheus(app) -> None:
    settings = get_settings()
    if not settings.prometheus_enabled:
        logger.info("Prometheus metrics disabled")
        return

    try:
        import importlib.metadata as importlib_metadata
        from prometheus_fastapi_instrumentator import Instrumentator

        version = importlib_metadata.version("prometheus-fastapi-instrumentator")
        major, minor = (int(x) for x in version.split(".")[:2])
        if (major, minor) < (8, 0):
            logger.warning(
                "prometheus-fastapi-instrumentator {} is too old for this FastAPI version; "
                "upgrade with: pip install 'prometheus-fastapi-instrumentator>=8.0.1'",
                version,
            )
            return

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/metrics", "/api/v1/health"],
        ).instrument(app).expose(
            app,
            endpoint="/metrics",
            include_in_schema=False,
        )
        logger.info("Prometheus metrics exposed at /metrics")
    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed — metrics disabled")
