"""Контейнер зависимостей API. Заполняется в create_app."""

from dataclasses import dataclass

from converter.application.enqueue_conversion import EnqueueConversion
from converter.application.get_conversion_job import GetConversionJob
from converter.application.get_conversion_result import GetConversionResult
from converter.application.list_conversion_pairs import ListConversionPairs
from converter.application.ports import ConversionJobRepository
from converter.application.recognize_conversion_result import RecognizeConversionResult
from converter.application.run_conversion_job import RunConversionJob
from converter.application.submit_recognized_text import SubmitRecognizedText


@dataclass(slots=True)
class ApiContainer:
    """Собранные сценарии для роутеров FastAPI."""

    jobs: ConversionJobRepository
    enqueue: EnqueueConversion
    run_job: RunConversionJob
    get_job: GetConversionJob
    get_result: GetConversionResult
    list_pairs: ListConversionPairs
    recognize: RecognizeConversionResult
    submit_text: SubmitRecognizedText
