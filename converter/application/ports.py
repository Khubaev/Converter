"""Порты сценария. Адаптеры снаружи реализуют эти контракты."""

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from converter.application.jobs import ConversionJob
from converter.domain.models import (
    ConversionArtifactBundle,
    ConversionOptions,
    ConversionPair,
    PageImage,
)


class DocumentConverter(Protocol):
    """Конвертер одной или нескольких пар source → target."""

    @property
    def pairs(self) -> tuple[ConversionPair, ...]:
        """Какие пары умеет этот адаптер."""

    def supports(self, pair: ConversionPair) -> bool:
        """True, если адаптер берёт эту пару."""

    def convert(
        self,
        content: bytes,
        filename: str,
        options: ConversionOptions,
    ) -> ConversionArtifactBundle:
        """Конвертирует документ из памяти в набор выходных файлов."""


class PdfRenderer(Protocol):
    """Деталь PDF→JPEG адаптера: рендер страниц."""

    def render(
        self,
        source: Path,
        options: ConversionOptions,
        password: str | None = None,
    ) -> Iterator[PageImage]:
        """Возвращает страницы по одной."""


class ImageStore(Protocol):
    """Деталь CLI: сохранение страниц на диск."""

    def save(
        self,
        output_dir: Path,
        file_stem: str,
        pages: Iterator[PageImage],
    ) -> tuple[Path, ...]:
        """Пишет страницы в каталог."""


class JpegStacker(Protocol):
    """Деталь PDF→JPEG: склейка страниц в один JPEG."""

    def stack(self, pages: Sequence[PageImage], quality: int) -> PageImage:
        """Вертикальная лента."""


class ConversionJobRepository(Protocol):
    """Хранит асинхронные задания конвертации и их результат."""

    def add(self, job: ConversionJob) -> None:
        """Создаёт новое задание."""

    def get(self, job_id: str) -> ConversionJob | None:
        """Возвращает задание или None, если id неизвестен."""

    def save(self, job: ConversionJob) -> None:
        """Обновляет состояние существующего задания."""


class TextRecognizer(Protocol):
    """OCR одного изображения → plain text."""

    def recognize(self, image: bytes, filename: str) -> str:
        """Возвращает распознанный текст. Пустая строка, если текста нет."""


class RecognizedTextPublisher(Protocol):
    """Отправляет JSON распознанного текста на внешнюю сборку."""

    def publish(self, payload: Mapping[str, object]) -> object:
        """POST JSON и возвращает тело ответа. Бросает ConverterError при сбое."""
