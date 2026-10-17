"""Адаптер порта ImageStore. Пишет JPEG на диск после успешного рендера всех страниц."""

import os
from collections.abc import Iterator
from pathlib import Path

from converter.domain.exceptions import ConverterError, OutputPathError
from converter.domain.models import PageImage


class FileSystemImageStore:
    """Сохраняет страницы как `<имя>_p001.jpg`. Замена файлов происходит только в конце."""

    def save(
        self,
        output_dir: Path,
        file_stem: str,
        pages: Iterator[PageImage],
    ) -> tuple[Path, ...]:
        """Сначала пишет временные файлы. Если рендер обрывается, исходные JPEG не трогает."""
        created_dir = self._prepare_dir(output_dir)
        pending: list[tuple[Path, Path]] = []
        try:
            for page in pages:
                final_path = output_dir / f"{file_stem}_p{page.page_number:03d}.jpg"
                temp_path = output_dir / f".{final_path.name}.{os.getpid()}.part"
                self._write_bytes(temp_path, page.content, output_dir)
                pending.append((temp_path, final_path))
            if not pending:
                raise ConverterError("Не получено ни одной страницы для сохранения.")
            for temp_path, final_path in pending:
                self._replace(temp_path, final_path, output_dir)
        except Exception:
            self._discard(pending, output_dir, created_dir)
            raise
        return tuple(final_path for _, final_path in pending)

    def _write_bytes(self, path: Path, content: bytes, output_dir: Path) -> None:
        try:
            path.write_bytes(content)
        except OSError as exc:
            raise OutputPathError(output_dir, "не удалось записать временный файл") from exc

    def _replace(self, source: Path, destination: Path, output_dir: Path) -> None:
        try:
            source.replace(destination)
        except OSError as exc:
            raise OutputPathError(output_dir, "не удалось сохранить JPEG") from exc

    def _prepare_dir(self, output_dir: Path) -> bool:
        if output_dir.exists() and not output_dir.is_dir():
            raise OutputPathError(output_dir, "по этому пути уже лежит файл")
        created = not output_dir.exists()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OutputPathError(output_dir, "нет прав на создание каталога") from exc
        return created

    def _discard(
        self,
        pending: list[tuple[Path, Path]],
        output_dir: Path,
        created_dir: bool,
    ) -> None:
        for temp_path, _ in pending:
            temp_path.unlink(missing_ok=True)
        if created_dir:
            try:
                output_dir.rmdir()
            except OSError:
                return
