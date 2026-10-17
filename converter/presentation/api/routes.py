"""Маршруты конвертации. Оркестрация HTTP ↔ сценарии, без библиотек рендера."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from converter.application.assembly_prompts import AssemblyPromptError, list_assembly_prompts
from converter.application.dto import ConvertDocumentCommand
from converter.application.get_conversion_job import JobNotFoundError
from converter.application.get_conversion_result import ResultNotReadyError
from converter.application.jobs import JobStatus
from converter.application.recognize_conversion_result import RecognitionNotReadyError
from converter.domain.exceptions import (
    AssemblyDispatchError,
    AssemblyNotConfiguredError,
    ConverterError,
    OcrError,
    OcrNotConfiguredError,
)
from converter.domain.models import (
    MAX_DPI,
    MAX_JPEG_QUALITY,
    MIN_DPI,
    MIN_JPEG_QUALITY,
    ConversionOptions,
    DocumentFormat,
    OutputLayout,
)
from converter.presentation.api.dependencies import ApiContainer
from converter.presentation.api.schemas import (
    AssemblyDispatchRequest,
    AssemblyDispatchResponse,
    AssemblyPromptResponse,
    ConversionPairResponse,
    JobAcceptedResponse,
    JobStatusResponse,
    OcrPageResponse,
    OcrResultResponse,
)

DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def build_router(
    container: ApiContainer,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> APIRouter:
    """Создаёт роутер с уже связанными сценариями."""
    router = APIRouter(prefix="/api/v1", tags=["conversions"])

    @router.get(
        "/conversions/formats",
        response_model=list[ConversionPairResponse],
        summary="Список поддерживаемых пар source → target",
    )
    async def list_formats() -> list[ConversionPairResponse]:
        pairs = container.list_pairs.execute()
        return [ConversionPairResponse.from_pair(pair) for pair in pairs]

    @router.post(
        "/conversions",
        response_model=JobAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Загрузить документ и поставить конвертацию в очередь",
    )
    async def enqueue_conversion(
        background_tasks: BackgroundTasks,
        file: Annotated[UploadFile, File(description="Исходный файл")],
        target_format: Annotated[str, Form(description="Целевой формат, например jpeg")] = "jpeg",
        source_format: Annotated[
            str | None,
            Form(description="Исходный формат; по умолчанию из расширения файла"),
        ] = None,
        dpi: Annotated[int, Form(ge=MIN_DPI, le=MAX_DPI)] = 150,
        quality: Annotated[int, Form(ge=MIN_JPEG_QUALITY, le=MAX_JPEG_QUALITY)] = 90,
        layout: Annotated[
            str,
            Form(description="separate — файл на страницу; single — один файл"),
        ] = OutputLayout.SEPARATE.value,
        password: Annotated[str | None, Form()] = None,
    ) -> JobAcceptedResponse:
        filename = file.filename or "document.pdf"
        content = await file.read()
        if len(content) > max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер файла превышает {max_upload_bytes} байт",
            )

        try:
            parsed_source = (
                DocumentFormat.parse(source_format)
                if source_format
                else DocumentFormat.from_filename(filename)
            )
            parsed_target = DocumentFormat.parse(target_format)
            parsed_layout = OutputLayout.parse(layout)
            options = ConversionOptions(
                dpi=dpi,
                quality=quality,
                layout=parsed_layout,
                password=password or None,
            )
            command = ConvertDocumentCommand(
                content=content,
                filename=filename,
                source_format=parsed_source,
                target_format=parsed_target,
                options=options,
            )
            job = container.enqueue.execute(command)
        except ConverterError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        background_tasks.add_task(_run_job, container, job.id)
        return JobAcceptedResponse(
            job_id=job.id,
            status=job.status,
            source_format=job.source_format,
            target_format=job.target_format,
            layout=job.layout,
        )

    @router.get(
        "/conversions/{job_id}",
        response_model=JobStatusResponse,
        summary="Статус асинхронной конвертации",
    )
    async def get_status(job_id: str) -> JobStatusResponse:
        try:
            job = container.get_job.execute(job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JobStatusResponse.from_job(job)

    @router.get(
        "/conversions/{job_id}/result",
        summary="Скачать результат (файл или ZIP)",
        responses={
            200: {
                "content": {
                    "image/jpeg": {},
                    "application/zip": {},
                    "application/octet-stream": {},
                },
                "description": "Готовый файл",
            }
        },
    )
    async def download_result(job_id: str) -> Response:
        try:
            packed = container.get_result.execute(job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResultNotReadyError as exc:
            job = container.get_job.execute(job_id)
            code = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if job.status == JobStatus.FAILED
                else status.HTTP_409_CONFLICT
            )
            raise HTTPException(status_code=code, detail=str(exc)) from exc

        job = container.get_job.execute(job_id)
        return Response(
            content=packed.body,
            media_type=packed.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{packed.filename}"',
                "X-Page-Count": str(job.page_count or 0),
                "X-Source-Format": job.source_format.value,
                "X-Target-Format": job.target_format.value,
            },
        )

    @router.post(
        "/conversions/{job_id}/recognize",
        response_model=OcrResultResponse,
        summary="Распознать текст JPEG через VK Vision",
    )
    async def recognize_job(job_id: str) -> OcrResultResponse:
        try:
            result = await asyncio.to_thread(container.recognize.execute, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RecognitionNotReadyError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except OcrNotConfiguredError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except OcrError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except ConverterError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return OcrResultResponse(
            job_id=job_id,
            page_count=result.page_count,
            full_text=result.full_text,
            pages=[
                OcrPageResponse(page=page.page_number, text=page.text)
                for page in result.pages
            ],
        )

    @router.get(
        "/assembly/prompts",
        response_model=list[AssemblyPromptResponse],
        summary="Варианты предварительного промпта для сборки",
    )
    async def list_prompts() -> list[AssemblyPromptResponse]:
        return [
            AssemblyPromptResponse(id=prompt.id, title=prompt.title, prompt=prompt.text)
            for prompt in list_assembly_prompts()
        ]

    @router.post(
        "/conversions/{job_id}/assemble",
        response_model=AssemblyDispatchResponse,
        summary="Отправить распознанный текст и промпт JSON-ом на сборку",
    )
    async def assemble_job(job_id: str, body: AssemblyDispatchRequest) -> AssemblyDispatchResponse:
        try:
            result = await asyncio.to_thread(
                container.submit_text.execute,
                job_id,
                body.prompt_id,
                body.prompt,
            )
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RecognitionNotReadyError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except AssemblyPromptError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except AssemblyNotConfiguredError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except AssemblyDispatchError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except ConverterError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return AssemblyDispatchResponse(
            job_id=job_id,
            prompt_id=result.prompt_id,
            prompt_title=result.prompt_title,
            document=result.document,
        )

    return router


async def _run_job(container: ApiContainer, job_id: str) -> None:
    """Запускает синхронный сценарий конвертации в отдельном потоке."""
    await asyncio.to_thread(container.run_job.execute, job_id)
