"""Командный интерфейс. Разбирает аргументы и вызывает сценарий через реестр."""

import argparse
import sys
from pathlib import Path

from converter.application.convert_document_to_files import ConvertDocumentToFiles
from converter.application.converter_registry import ConverterRegistry
from converter.application.dto import ConvertDocumentToFilesCommand
from converter.domain.exceptions import ConverterError
from converter.domain.models import (
    MAX_DPI,
    MAX_JPEG_QUALITY,
    MIN_DPI,
    MIN_JPEG_QUALITY,
    ConversionOptions,
    DocumentFormat,
    OutputLayout,
)


def run_cli(
    use_case: ConvertDocumentToFiles,
    registry: ConverterRegistry,
    argv: list[str] | None = None,
) -> int:
    """Запускает конвертацию. 0 — успех, 1 — ошибка входных данных."""
    args = _parse_args(argv, registry)
    output_dir = args.output or args.source.with_name(
        f"{args.source.stem}_{args.to}"
    )
    try:
        source_format = (
            DocumentFormat.parse(args.source_format)
            if args.source_format
            else DocumentFormat.from_filename(args.source.name)
        )
        target_format = DocumentFormat.parse(args.to)
        options = ConversionOptions(
            dpi=args.dpi,
            quality=args.quality,
            layout=OutputLayout.parse(args.layout),
            password=args.password,
        )
        result = use_case.execute(
            ConvertDocumentToFilesCommand(
                source_path=args.source,
                output_dir=output_dir,
                source_format=source_format,
                target_format=target_format,
                options=options,
            )
        )
    except ConverterError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(
        f"Готово: {result.page_count} стр. "
        f"[{result.source_format.value}->{result.target_format.value}, "
        f"{result.bundle.layout.value}] -> {result.output_dir}"
    )
    for path in result.files:
        print(f"  {path.name}")
    return 0


def _parse_args(argv: list[str] | None, registry: ConverterRegistry) -> argparse.Namespace:
    available = ", ".join(
        f"{p.source.value}->{p.target.value}" for p in registry.list_pairs()
    ) or "(нет пар)"
    parser = argparse.ArgumentParser(
        prog="converterPDF",
        description=f"Конвертер документов. Доступные пары: {available}",
    )
    parser.add_argument("source", type=Path, help="Путь к исходному файлу")
    parser.add_argument(
        "-t",
        "--to",
        default="jpeg",
        help="Целевой формат (по умолчанию jpeg)",
    )
    parser.add_argument(
        "--from",
        dest="source_format",
        default=None,
        help="Исходный формат (по умолчанию из расширения файла)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Каталог для результата (по умолчанию <имя>_<to> рядом с файлом)",
    )
    parser.add_argument(
        "-d",
        "--dpi",
        type=int,
        default=150,
        help=f"DPI для растеризации, {MIN_DPI}–{MAX_DPI} (по умолчанию 150)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=90,
        help=f"Качество, {MIN_JPEG_QUALITY}–{MAX_JPEG_QUALITY} (по умолчанию 90)",
    )
    parser.add_argument(
        "-l",
        "--layout",
        default=OutputLayout.SEPARATE.value,
        choices=[item.value for item in OutputLayout],
        help="separate — по файлу на страницу; single — один файл",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=None,
        help="Пароль, если документ защищён",
    )
    return parser.parse_args(argv)
