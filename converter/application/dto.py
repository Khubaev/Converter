"""Вход и выход сценариев конвертации."""

from dataclasses import dataclass
from pathlib import Path

from converter.domain.models import (
    ConversionArtifactBundle,
    ConversionOptions,
    DocumentFormat,
)


@dataclass(frozen=True, slots=True)
class ConvertDocumentCommand:
    """Запрос на конвертацию документа из памяти."""

    content: bytes
    filename: str
    source_format: DocumentFormat
    target_format: DocumentFormat
    options: ConversionOptions


@dataclass(frozen=True, slots=True)
class ConvertDocumentToFilesCommand:
    """Запрос на конвертацию файла с диска с записью результата в каталог."""

    source_path: Path
    output_dir: Path
    source_format: DocumentFormat
    target_format: DocumentFormat
    options: ConversionOptions


@dataclass(frozen=True, slots=True)
class ConversionFilesResult:
    """Результат CLI: пути записанных файлов."""

    source_path: Path
    output_dir: Path
    files: tuple[Path, ...]
    page_count: int
    source_format: DocumentFormat
    target_format: DocumentFormat
    bundle: ConversionArtifactBundle
