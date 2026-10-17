"""HTTP API на FastAPI: асинхронная постановка заданий и выдача JPEG."""

from converter.presentation.api.app import create_app

__all__ = ["create_app"]
