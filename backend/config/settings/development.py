"""Local development settings."""
import os
from .base import *  # noqa: F403

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv(
    "CORS_ALLOWED_ORIGINS", ""
).split(",") if origin.strip()]
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += ["rest_framework.renderers.BrowsableAPIRenderer"]  # noqa: F405
