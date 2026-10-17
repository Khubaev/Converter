"""Адаптер ConversionJobRepository: задания и JPEG живут в памяти процесса."""

from threading import RLock

from converter.application.jobs import ConversionJob


class InMemoryJobRepository:
    """Подходит для одного инстанса API. Для кластера нужен общий store."""

    def __init__(self) -> None:
        self._jobs: dict[str, ConversionJob] = {}
        self._lock = RLock()

    def add(self, job: ConversionJob) -> None:
        with self._lock:
            if job.id in self._jobs:
                raise ValueError(f"Задание уже существует: {job.id}")
            self._jobs[job.id] = job

    def get(self, job_id: str) -> ConversionJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def save(self, job: ConversionJob) -> None:
        with self._lock:
            if job.id not in self._jobs:
                raise KeyError(f"Задание не найдено: {job.id}")
            self._jobs[job.id] = job
