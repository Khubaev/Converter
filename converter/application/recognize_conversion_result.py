"""Сценарий: OCR готовых артефактов конвертации через TextRecognizer."""

from converter.application.get_conversion_job import GetConversionJob, JobNotFoundError
from converter.application.jobs import JobStatus
from converter.application.ports import ConversionJobRepository, TextRecognizer
from converter.domain.exceptions import ConverterError, OcrError
from converter.domain.models import OcrDocumentResult, OcrPageResult


class RecognitionNotReadyError(ConverterError):
    """Конвертация ещё не завершена — распознавать нечего."""

    def __init__(self, job_id: str, message: str) -> None:
        super().__init__(message)
        self.job_id = job_id


class RecognizeConversionResult:
    """Берёт completed job и гоняет каждое изображение в OCR по очереди."""

    def __init__(
        self,
        get_job: GetConversionJob,
        recognizer: TextRecognizer,
        jobs: ConversionJobRepository,
    ) -> None:
        self._get_job = get_job
        self._recognizer = recognizer
        self._jobs = jobs

    def execute(self, job_id: str) -> OcrDocumentResult:
        job = self._get_job.execute(job_id)
        if job.status == JobStatus.FAILED:
            raise RecognitionNotReadyError(
                job_id,
                job.error or "конвертация завершилась ошибкой",
            )
        if job.status != JobStatus.COMPLETED or job.bundle is None:
            raise RecognitionNotReadyError(
                job_id,
                f"результат конвертации ещё не готов (статус: {job.status.value})",
            )

        pages: list[OcrPageResult] = []
        for index, media in enumerate(job.bundle.files, start=1):
            try:
                text = self._recognizer.recognize(media.content, media.filename)
            except OcrError:
                raise
            except Exception as exc:
                raise OcrError(
                    f"Не удалось распознать страницу {index} ({media.filename}): {exc}"
                ) from exc
            pages.append(OcrPageResult(page_number=index, text=text.strip()))

        full_text = "\n\n".join(page.text for page in pages if page.text).strip()
        result = OcrDocumentResult(pages=tuple(pages), full_text=full_text)
        job.attach_recognition(result)
        self._jobs.save(job)
        return result


__all__ = [
    "JobNotFoundError",
    "RecognitionNotReadyError",
    "RecognizeConversionResult",
]
