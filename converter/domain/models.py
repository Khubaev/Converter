"""Объекты-значения домена. Не зависят от библиотек конвертации."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from converter.domain.exceptions import InvalidRenderOptionsError, UnsupportedConversionError

MIN_DPI = 36
MAX_DPI = 600
MIN_JPEG_QUALITY = 1
MAX_JPEG_QUALITY = 100
MAX_MERGED_PIXELS = 40_000_000


class DocumentFormat(str, Enum):
    """Известные форматы. Новые значения добавляются по мере появления адаптеров."""

    PDF = "pdf"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"

    @classmethod
    def parse(cls, value: str | DocumentFormat) -> DocumentFormat:
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower().lstrip(".")
        aliases = {
            "jpg": cls.JPEG,
            "jpeg": cls.JPEG,
            "pdf": cls.PDF,
            "png": cls.PNG,
            "webp": cls.WEBP,
        }
        fmt = aliases.get(normalized)
        if fmt is None:
            raise UnsupportedConversionError(
                f"Неизвестный формат: {value}. "
                f"Допустимы: {', '.join(sorted(aliases))}."
            )
        return fmt

    @classmethod
    def from_filename(cls, filename: str) -> DocumentFormat:
        from pathlib import Path

        suffix = Path(filename).suffix
        if not suffix:
            raise UnsupportedConversionError(
                f"Не удалось определить формат по имени файла: {filename}"
            )
        return cls.parse(suffix)

    @property
    def media_type(self) -> str:
        return {
            DocumentFormat.PDF: "application/pdf",
            DocumentFormat.JPEG: "image/jpeg",
            DocumentFormat.PNG: "image/png",
            DocumentFormat.WEBP: "image/webp",
        }[self]

    @property
    def extension(self) -> str:
        return {
            DocumentFormat.PDF: ".pdf",
            DocumentFormat.JPEG: ".jpg",
            DocumentFormat.PNG: ".png",
            DocumentFormat.WEBP: ".webp",
        }[self]


@dataclass(frozen=True, slots=True)
class ConversionPair:
    """Пара source → target, по которой реестр выбирает адаптер."""

    source: DocumentFormat
    target: DocumentFormat

    def __post_init__(self) -> None:
        if self.source == self.target:
            raise UnsupportedConversionError(
                f"Исходный и целевой формат совпадают: {self.source.value}"
            )


class OutputLayout(str, Enum):
    """Как отдавать многостраничный результат."""

    SEPARATE = "separate"
    SINGLE = "single"

    @classmethod
    def parse(cls, value: str | OutputLayout) -> OutputLayout:
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise InvalidRenderOptionsError(
                f"layout должен быть одним из: {allowed}."
            ) from exc


@dataclass(frozen=True, slots=True)
class ConversionOptions:
    """Параметры конвертации. Адаптер берёт нужные поля, остальные игнорирует."""

    dpi: int = 150
    quality: int = 90
    layout: OutputLayout = OutputLayout.SEPARATE
    password: str | None = None

    def __post_init__(self) -> None:
        layout = OutputLayout.parse(self.layout)
        object.__setattr__(self, "layout", layout)
        if isinstance(self.dpi, bool) or not isinstance(self.dpi, int):
            raise InvalidRenderOptionsError("DPI должен быть целым числом.")
        if not MIN_DPI <= self.dpi <= MAX_DPI:
            raise InvalidRenderOptionsError(
                f"DPI должен быть от {MIN_DPI} до {MAX_DPI}."
            )
        if isinstance(self.quality, bool) or not isinstance(self.quality, int):
            raise InvalidRenderOptionsError("Качество должно быть целым числом.")
        if not MIN_JPEG_QUALITY <= self.quality <= MAX_JPEG_QUALITY:
            raise InvalidRenderOptionsError(
                f"Качество должно быть от {MIN_JPEG_QUALITY} до {MAX_JPEG_QUALITY}."
            )


# Обратная совместимость для PDF→JPEG адаптера.
RenderOptions = ConversionOptions


@dataclass(frozen=True, slots=True)
class MediaFile:
    """Один выходной файл любой природы (JPEG, PNG, PDF, …)."""

    filename: str
    content: bytes
    media_type: str

    def __post_init__(self) -> None:
        if not self.filename:
            raise ValueError("Имя файла не может быть пустым.")
        if not self.content:
            raise ValueError("Содержимое файла не может быть пустым.")
        if not self.media_type:
            raise ValueError("media_type не может быть пустым.")


@dataclass(frozen=True, slots=True)
class ConversionArtifactBundle:
    """Набор выходных файлов после конвертации."""

    source_name: str
    source_format: DocumentFormat
    target_format: DocumentFormat
    files: tuple[MediaFile, ...]
    page_count: int
    layout: OutputLayout = OutputLayout.SEPARATE

    def __post_init__(self) -> None:
        if not self.files:
            raise ValueError("Набор артефактов не может быть пустым.")
        if self.page_count < 1:
            raise ValueError("page_count должен быть >= 1.")

    @property
    def is_single_file(self) -> bool:
        return len(self.files) == 1


@dataclass(frozen=True, slots=True)
class PageImage:
    """Растрированная страница. Формат байтов задаёт адаптер (обычно JPEG)."""

    page_number: int
    width: int
    height: int
    content: bytes

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Номер страницы начинается с 1.")
        if self.width < 1 or self.height < 1:
            raise ValueError("Размер страницы должен быть положительным.")
        if not self.content:
            raise ValueError("Содержимое страницы не может быть пустым.")

    def __repr__(self) -> str:
        return (
            f"PageImage(page_number={self.page_number}, width={self.width}, "
            f"height={self.height}, bytes={len(self.content)})"
        )


@dataclass(frozen=True, slots=True)
class OcrPageResult:
    """Текст одной страницы / одного изображения."""

    page_number: int
    text: str

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Номер страницы начинается с 1.")


@dataclass(frozen=True, slots=True)
class OcrDocumentResult:
    """Склеенный результат OCR по документу."""

    pages: tuple[OcrPageResult, ...]
    full_text: str

    @property
    def page_count(self) -> int:
        return len(self.pages)
