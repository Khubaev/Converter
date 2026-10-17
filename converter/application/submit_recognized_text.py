"""Сценарий: отправить уже распознанный текст JSON-ом на сборку."""

from dataclasses import dataclass

from converter.application.assembly_prompts import AssemblyPrompt, resolve_assembly_prompt
from converter.application.get_conversion_job import GetConversionJob, JobNotFoundError
from converter.application.jobs import ConversionJob
from converter.application.parse_assembly_response import parse_assembly_response
from converter.application.ports import RecognizedTextPublisher
from converter.application.recognize_conversion_result import RecognitionNotReadyError


@dataclass(frozen=True, slots=True)
class SubmittedAssembly:
    """Промпт, с которым ушёл текст, и уже разобранный документ из ответа."""

    prompt_id: str
    prompt_title: str
    document: object


class SubmitRecognizedText:
    """Берёт OCR, сохранённый на задании, и публикует его через порт сборки."""

    def __init__(self, get_job: GetConversionJob, publisher: RecognizedTextPublisher) -> None:
        self._get_job = get_job
        self._publisher = publisher

    def execute(self, job_id: str, prompt_id: str, prompt_text: str | None = None) -> SubmittedAssembly:
        job = self._get_job.execute(job_id)
        if job.recognition is None:
            raise RecognitionNotReadyError(job_id, "Сначала распознайте текст")
        prompt, text = resolve_assembly_prompt(prompt_id, prompt_text)
        raw = self._publisher.publish(self._payload(job, prompt, text))
        return SubmittedAssembly(
            prompt_id=prompt.id,
            prompt_title=prompt.title,
            document=parse_assembly_response(raw),
        )

    def _payload(self, job: ConversionJob, prompt: AssemblyPrompt, prompt_text: str) -> dict[str, object]:
        recognition = job.recognition
        if recognition is None:
            raise RecognitionNotReadyError(job.id, "Сначала распознайте текст")
        return {
            "job_id": job.id,
            "filename": job.filename,
            "source_format": job.source_format.value,
            "page_count": recognition.page_count,
            "full_text": recognition.full_text,
            "pages": [
                {"page": page.page_number, "text": page.text}
                for page in recognition.pages
            ],
            "prompt_id": prompt.id,
            "prompt_title": prompt.title,
            "prompt": prompt_text,
        }


__all__ = ["JobNotFoundError", "RecognitionNotReadyError", "SubmitRecognizedText"]
