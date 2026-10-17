"""Схемы ответов API. Не содержат бизнес-логики."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from converter.application.jobs import ConversionJob, JobStatus
from converter.domain.models import ConversionPair, DocumentFormat, OutputLayout


class ConversionPairResponse(BaseModel):
    """Одна зарегистрированная пара source → target."""

    source: DocumentFormat
    target: DocumentFormat

    @classmethod
    def from_pair(cls, pair: ConversionPair) -> "ConversionPairResponse":
        return cls(source=pair.source, target=pair.target)


class JobAcceptedResponse(BaseModel):
    """Ответ сразу после загрузки документа."""

    job_id: str
    status: JobStatus
    source_format: DocumentFormat
    target_format: DocumentFormat
    layout: OutputLayout
    message: str = "Конвертация поставлена в очередь"


class JobStatusResponse(BaseModel):
    """Текущее состояние задания."""

    job_id: str
    status: JobStatus
    filename: str
    source_format: DocumentFormat
    target_format: DocumentFormat
    layout: OutputLayout
    page_count: int | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
    result_ready: bool = False

    @classmethod
    def from_job(cls, job: ConversionJob) -> "JobStatusResponse":
        return cls(
            job_id=job.id,
            status=job.status,
            filename=job.filename,
            source_format=job.source_format,
            target_format=job.target_format,
            layout=job.layout,
            page_count=job.page_count,
            error=job.error,
            created_at=job.created_at,
            finished_at=job.finished_at,
            result_ready=job.status == JobStatus.COMPLETED and job.bundle is not None,
        )


class ErrorResponse(BaseModel):
    """Единый формат ошибки для клиента."""

    detail: str


class OcrPageResponse(BaseModel):
    """Текст одной страницы."""

    page: int
    text: str


class OcrResultResponse(BaseModel):
    """Ответ OCR по заданию конвертации."""

    job_id: str
    page_count: int
    full_text: str
    pages: list[OcrPageResponse]


class AssemblyPromptResponse(BaseModel):
    """Вариант предварительного промпта для сборки."""

    id: str
    title: str
    prompt: str


class AssemblyDispatchRequest(BaseModel):
    """Тело отправки: какой промпт приложить к распознанному тексту."""

    prompt_id: str
    prompt: str | None = None


class AssemblyDispatchResponse(BaseModel):
    """Ответ после отправки: документ уже без оболочки output и экранирования."""

    job_id: str
    prompt_id: str
    prompt_title: str
    document: Any
    message: str = "Документ разобран"
