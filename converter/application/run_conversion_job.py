"""Сценарий: выполнить одно задание из очереди через ConvertDocument."""

from converter.application.convert_document import ConvertDocument
from converter.application.dto import ConvertDocumentCommand
from converter.application.jobs import JobStatus
from converter.application.ports import ConversionJobRepository
from converter.domain.exceptions import ConverterError


class RunConversionJob:
    """Берёт queued задание, гоняет ConvertDocument, пишет итог."""

    def __init__(self, jobs: ConversionJobRepository, convert_document: ConvertDocument) -> None:
        self._jobs = jobs
        self._convert_document = convert_document

    def execute(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            return

        job.mark_processing()
        self._jobs.save(job)
        try:
            bundle = self._convert_document.execute(
                ConvertDocumentCommand(
                    content=job.content,
                    filename=job.filename,
                    source_format=job.source_format,
                    target_format=job.target_format,
                    options=job.options,
                )
            )
        except ConverterError as exc:
            job.mark_failed(str(exc))
            self._jobs.save(job)
            return
        except Exception as exc:
            job.mark_failed(f"внутренняя ошибка конвертации: {exc}")
            self._jobs.save(job)
            return

        job.mark_completed(bundle)
        self._jobs.save(job)
