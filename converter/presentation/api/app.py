"""Фабрика FastAPI-приложения. Корень композиции для HTTP-слоя."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from converter.application.convert_document import ConvertDocument
from converter.application.converter_registry import ConverterRegistry
from converter.application.enqueue_conversion import EnqueueConversion
from converter.application.get_conversion_job import GetConversionJob
from converter.application.get_conversion_result import GetConversionResult
from converter.application.list_conversion_pairs import ListConversionPairs
from converter.application.pack_artifact_bundle import PackArtifactBundle
from converter.application.recognize_conversion_result import RecognizeConversionResult
from converter.application.run_conversion_job import RunConversionJob
from converter.application.submit_recognized_text import SubmitRecognizedText
from converter.composition import build_registry
from converter.infrastructure.in_memory_job_repository import InMemoryJobRepository
from converter.infrastructure.n8n_text_publisher import N8nRecognizedTextPublisher
from converter.infrastructure.settings import load_env_file
from converter.infrastructure.vk_vision_text_recognizer import VkVisionTextRecognizer
from converter.presentation.api.dependencies import ApiContainer
from converter.presentation.api.routes import DEFAULT_MAX_UPLOAD_BYTES, build_router

_WEB_STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "static"
_INDEX_HTML = _WEB_STATIC_DIR / "index.html"


def build_api_container(registry: ConverterRegistry | None = None) -> ApiContainer:
    """Связывает HTTP-сценарии с реестром, jobs и OCR."""
    load_env_file()
    reg = registry or build_registry()
    jobs = InMemoryJobRepository()
    convert_document = ConvertDocument(reg)
    get_job = GetConversionJob(jobs)
    recognizer = VkVisionTextRecognizer()
    return ApiContainer(
        enqueue=EnqueueConversion(jobs, reg),
        run_job=RunConversionJob(jobs, convert_document),
        get_job=get_job,
        get_result=GetConversionResult(get_job, PackArtifactBundle()),
        list_pairs=ListConversionPairs(reg),
        recognize=RecognizeConversionResult(get_job, recognizer, jobs),
        submit_text=SubmitRecognizedText(get_job, N8nRecognizedTextPublisher()),
    )


def create_app(
    container: ApiContainer | None = None,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> FastAPI:
    """Собирает приложение. container можно подменить в тестах."""
    api = container or build_api_container()
    app = FastAPI(
        title="Document Converter",
        description=(
            "Асинхронный API конвертации документов и OCR через VK Vision. "
            "Сейчас: pdf→jpeg, webp→jpeg, text/recognize и отправка текста на сборку."
        ),
        version="2.1.0",
    )
    app.state.container = api
    app.include_router(build_router(api, max_upload_bytes=max_upload_bytes))
    app.mount("/static", StaticFiles(directory=_WEB_STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def ui_index() -> FileResponse:
        return FileResponse(_INDEX_HTML)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
