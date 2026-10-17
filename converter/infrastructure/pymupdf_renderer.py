"""Адаптер порта PdfRenderer. Единственное место, где импортируется PyMuPDF."""

from collections.abc import Iterator
from pathlib import Path

import pymupdf

from converter.domain.exceptions import (
    EmptyPdfError,
    InvalidPdfError,
    PdfPasswordRequiredError,
)
from converter.domain.models import ConversionOptions, PageImage

_PDF_POINT_DPI = 72


class PyMuPdfRenderer:
    """Растеризует страницы PDF в RGB и кодирует их в JPEG."""

    def render(
        self,
        source: Path,
        options: ConversionOptions,
        password: str | None = None,
    ) -> Iterator[PageImage]:
        """Открывает документ на время итерации и закрывает его в конце."""
        try:
            document = pymupdf.open(source)
        except Exception as exc:
            raise InvalidPdfError(source, "файл повреждён или это не PDF") from exc

        try:
            self._unlock(document, source, password)
            if document.page_count == 0:
                raise EmptyPdfError(source)
            # Ошибки потребителя (запись на диск) здесь не перехватываются.
            yield from self._render_pages(document, source, options)
        finally:
            document.close()

    def _unlock(self, document: pymupdf.Document, source: Path, password: str | None) -> None:
        if not document.needs_pass:
            return
        authenticated = password is not None and document.authenticate(password) > 0
        if not authenticated:
            raise PdfPasswordRequiredError(source)

    def _render_pages(
        self,
        document: pymupdf.Document,
        source: Path,
        options: ConversionOptions,
    ) -> Iterator[PageImage]:
        zoom = options.dpi / _PDF_POINT_DPI
        matrix = pymupdf.Matrix(zoom, zoom)
        for index in range(document.page_count):
            try:
                page = document.load_page(index)
                pixmap = page.get_pixmap(
                    matrix=matrix,
                    alpha=False,
                    colorspace=pymupdf.csRGB,
                )
                content = pixmap.tobytes("jpeg", jpg_quality=options.quality)
            except Exception as exc:
                raise InvalidPdfError(source, f"не удалось растеризовать страницу {index + 1}") from exc
            if not content.startswith(b"\xff\xd8"):
                raise InvalidPdfError(source, f"страница {index + 1} не закодировалась в JPEG")
            yield PageImage(
                page_number=index + 1,
                width=pixmap.width,
                height=pixmap.height,
                content=content,
            )
