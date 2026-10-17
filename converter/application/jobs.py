"""Модель асинхронного задания конвертации. Живёт в слое приложения."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from converter.domain.models import (
    ConversionArtifactBundle,
    ConversionOptions,
    DocumentFormat,
    OcrDocumentResult,
)


class JobStatus(str, Enum):
    """Жизненный цикл задания, видимый клиенту API."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class ConversionJob:
    """Задание: входной документ, пара форматов, опции и итог."""

    id: str
    filename: str
    content: bytes
    source_format: DocumentFormat
    target_format: DocumentFormat
    options: ConversionOptions
    status: JobStatus = JobStatus.QUEUED
    error: str | None = None
    bundle: ConversionArtifactBundle | None = None
    recognition: OcrDocumentResult | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    @property
    def page_count(self) -> int | None:
        if self.bundle is None:
            return None
        return self.bundle.page_count

    @property
    def layout(self):
        return self.options.layout

    def mark_processing(self) -> None:
        self.status = JobStatus.PROCESSING
        self.error = None

    def mark_completed(self, bundle: ConversionArtifactBundle) -> None:
        self.status = JobStatus.COMPLETED
        self.bundle = bundle
        self.error = None
        self.finished_at = datetime.now(timezone.utc)
        self.content = b""

    def attach_recognition(self, result: OcrDocumentResult) -> None:
        """Сохраняет OCR, чтобы его можно было отправить на сборку отдельно."""
        self.recognition = result

    def mark_failed(self, message: str) -> None:
        self.status = JobStatus.FAILED
        self.error = message
        self.bundle = None
        self.finished_at = datetime.now(timezone.utc)
        self.content = b""
