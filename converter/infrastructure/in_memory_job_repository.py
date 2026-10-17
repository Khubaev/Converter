"""Адаптер ConversionJobRepository: задания и JPEG живут в памяти процесса."""

from datetime import datetime, timedelta, timezone
from threading import RLock

from converter.application.jobs import ConversionJob

_DEFAULT_JOB_TTL = timedelta(minutes=5)


class InMemoryJobRepository:
    """Подходит для одного инстанса API. Задание живёт не дольше ttl."""

    def __init__(self, ttl: timedelta = _DEFAULT_JOB_TTL) -> None:
        if ttl.total_seconds() <= 0:
            raise ValueError("Срок жизни задания должен быть больше нуля.")
        self._ttl = ttl
        self._jobs: dict[str, ConversionJob] = {}
        self._lock = RLock()

    def add(self, job: ConversionJob) -> None:
        with self._lock:
            self._drop_expired_locked()
            if job.id in self._jobs:
                raise ValueError(f"Задание уже существует: {job.id}")
            if job.expires_at is None:
                job.expires_at = job.created_at + self._ttl
            if self._is_expired(job):
                job.release_payload()
                return
            self._jobs[job.id] = job

    def get(self, job_id: str) -> ConversionJob | None:
        with self._lock:
            self._drop_expired_locked()
            return self._jobs.get(job_id)

    def save(self, job: ConversionJob) -> None:
        with self._lock:
            self._drop_expired_locked()
            if self._is_expired(job):
                self._forget_locked(job.id)
                return
            if job.id not in self._jobs:
                raise KeyError(f"Задание не найдено: {job.id}")
            self._jobs[job.id] = job

    def purge_expired(self) -> int:
        with self._lock:
            return self._drop_expired_locked()

    def _drop_expired_locked(self) -> int:
        expired = [job_id for job_id, job in self._jobs.items() if self._is_expired(job)]
        for job_id in expired:
            self._forget_locked(job_id)
        return len(expired)

    def _forget_locked(self, job_id: str) -> None:
        job = self._jobs.pop(job_id, None)
        if job is not None:
            job.release_payload()

    def _is_expired(self, job: ConversionJob, now: datetime | None = None) -> bool:
        if job.expires_at is None:
            return False
        current = now or datetime.now(timezone.utc)
        return current >= job.expires_at
