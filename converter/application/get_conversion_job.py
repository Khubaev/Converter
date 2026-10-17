"""Сценарий: отдать клиенту статус асинхронного задания."""

from converter.application.jobs import ConversionJob
from converter.application.ports import ConversionJobRepository
from converter.domain.exceptions import ConverterError


class JobNotFoundError(ConverterError):
    """Задание с таким id не найдено."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Задание не найдено: {job_id}")
        self.job_id = job_id


class GetConversionJob:
    """Читает задание из репозитория."""

    def __init__(self, jobs: ConversionJobRepository) -> None:
        self._jobs = jobs

    def execute(self, job_id: str) -> ConversionJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job
