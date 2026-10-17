"""Сценарий: принять документ и поставить асинхронное задание в очередь."""

from pathlib import Path
from uuid import uuid4

from converter.application.converter_registry import ConverterRegistry
from converter.application.dto import ConvertDocumentCommand
from converter.application.jobs import ConversionJob, JobStatus
from converter.application.ports import ConversionJobRepository
from converter.domain.exceptions import UnsupportedConversionError
from converter.domain.models import ConversionPair, DocumentFormat


class EnqueueConversion:
    """Проверяет пару форматов через реестр и сохраняет задание queued."""

    def __init__(self, jobs: ConversionJobRepository, registry: ConverterRegistry) -> None:
        self._jobs = jobs
        self._registry = registry

    def execute(self, command: ConvertDocumentCommand) -> ConversionJob:
        if not command.content:
            raise UnsupportedConversionError("Файл пустой")
        pair = ConversionPair(source=command.source_format, target=command.target_format)
        # Падаем рано, до постановки в очередь, если адаптера нет.
        self._registry.resolve(pair)
        # ConversionOptions уже провалидированы при создании command.options.
        _ = command.options
        job = ConversionJob(
            id=str(uuid4()),
            filename=Path(command.filename).name or f"document{command.source_format.extension}",
            content=command.content,
            source_format=command.source_format,
            target_format=command.target_format,
            options=command.options,
            status=JobStatus.QUEUED,
        )
        self._jobs.add(job)
        return job
