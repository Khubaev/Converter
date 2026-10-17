"""Сценарий CLI: конвертация файла с диска и сохранение артефактов в каталог."""

import os
from pathlib import Path

from converter.application.convert_document import ConvertDocument
from converter.application.dto import (
    ConversionFilesResult,
    ConvertDocumentCommand,
    ConvertDocumentToFilesCommand,
)
from converter.domain.exceptions import InvalidPdfError, OutputPathError, PdfNotFoundError
from converter.domain.models import DocumentFormat, MediaFile


class ConvertDocumentToFiles:
    """Читает файл, гоняет ConvertDocument, атомарно пишет результат на диск."""

    def __init__(self, convert_document: ConvertDocument) -> None:
        self._convert_document = convert_document

    def execute(self, command: ConvertDocumentToFilesCommand) -> ConversionFilesResult:
        source = command.source_path.expanduser().resolve()
        output_dir = command.output_dir.expanduser().resolve()
        self._ensure_source(source, command.source_format)
        self._ensure_output_dir(source, output_dir)

        bundle = self._convert_document.execute(
            ConvertDocumentCommand(
                content=source.read_bytes(),
                filename=source.name,
                source_format=command.source_format,
                target_format=command.target_format,
                options=command.options,
            )
        )
        files = self._save_bundle(output_dir, bundle.files)
        return ConversionFilesResult(
            source_path=source,
            output_dir=output_dir,
            files=files,
            page_count=bundle.page_count,
            source_format=command.source_format,
            target_format=command.target_format,
            bundle=bundle,
        )

    def _ensure_source(self, source: Path, source_format: DocumentFormat) -> None:
        if not source.is_file():
            raise PdfNotFoundError(source)
        if source.stat().st_size == 0:
            raise InvalidPdfError(source, "файл пустой")
        allowed = {source_format.extension.lower()}
        if source_format == DocumentFormat.JPEG:
            allowed.update({".jpg", ".jpeg"})
        if source.suffix.lower() not in allowed:
            raise InvalidPdfError(
                source,
                f"ожидался файл с расширением {', '.join(sorted(allowed))}",
            )

    def _ensure_output_dir(self, source: Path, output_dir: Path) -> None:
        if output_dir == source:
            raise OutputPathError(output_dir, "каталог вывода совпадает с исходным файлом")
        if output_dir.exists() and not output_dir.is_dir():
            raise OutputPathError(output_dir, "по этому пути уже лежит файл")
        try:
            output_dir.relative_to(source)
        except ValueError:
            return
        raise OutputPathError(
            output_dir,
            "каталог вывода не может находиться внутри исходного файла",
        )

    def _save_bundle(self, output_dir: Path, files: tuple[MediaFile, ...]) -> tuple[Path, ...]:
        created = not output_dir.exists()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OutputPathError(output_dir, "нет прав на создание каталога") from exc

        pending: list[tuple[Path, Path]] = []
        try:
            for media in files:
                final_path = output_dir / Path(media.filename).name
                temp_path = output_dir / f".{final_path.name}.{os.getpid()}.part"
                try:
                    temp_path.write_bytes(media.content)
                except OSError as exc:
                    raise OutputPathError(output_dir, "не удалось записать временный файл") from exc
                pending.append((temp_path, final_path))
            for temp_path, final_path in pending:
                try:
                    temp_path.replace(final_path)
                except OSError as exc:
                    raise OutputPathError(output_dir, "не удалось сохранить результат") from exc
        except Exception:
            for temp_path, _ in pending:
                temp_path.unlink(missing_ok=True)
            if created:
                try:
                    output_dir.rmdir()
                except OSError:
                    pass
            raise
        return tuple(final_path for _, final_path in pending)
