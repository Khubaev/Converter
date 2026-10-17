"""Сценарий: отдать упакованный результат завершённого задания."""

from converter.application.get_conversion_job import GetConversionJob, JobNotFoundError
from converter.application.jobs import JobStatus
from converter.application.pack_artifact_bundle import PackArtifactBundle, PackedArtifactResponse
from converter.domain.exceptions import ConverterError


class ResultNotReadyError(ConverterError):
    """Результат ещё не готов или задание завершилось ошибкой."""

    def __init__(self, job_id: str, message: str) -> None:
        super().__init__(message)
        self.job_id = job_id


class GetConversionResult:
    """Проверяет статус и упаковывает артефакты для скачивания."""

    def __init__(self, get_job: GetConversionJob, packer: PackArtifactBundle) -> None:
        self._get_job = get_job
        self._packer = packer

    def execute(self, job_id: str) -> PackedArtifactResponse:
        job = self._get_job.execute(job_id)
        if job.status == JobStatus.FAILED:
            raise ResultNotReadyError(job_id, job.error or "конвертация завершилась ошибкой")
        if job.status != JobStatus.COMPLETED or job.bundle is None:
            raise ResultNotReadyError(
                job_id,
                f"результат ещё не готов (статус: {job.status.value})",
            )
        return self._packer.execute(job.bundle)


__all__ = ["GetConversionResult", "JobNotFoundError", "ResultNotReadyError"]
