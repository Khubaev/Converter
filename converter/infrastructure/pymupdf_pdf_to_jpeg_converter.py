"""Адаптер DocumentConverter: PDF → JPEG на PyMuPDF."""

import tempfile
from pathlib import Path

from converter.application.ports import JpegStacker, PdfRenderer
from converter.domain.exceptions import InvalidPdfError
from converter.domain.models import (
    ConversionArtifactBundle,
    ConversionOptions,
    ConversionPair,
    DocumentFormat,
    MediaFile,
    OutputLayout,
)
from converter.infrastructure.pymupdf_jpeg_stacker import PyMuPdfJpegStacker
from converter.infrastructure.pymupdf_renderer import PyMuPdfRenderer

_PDF_MAGIC = b"%PDF"
_PAIR = ConversionPair(source=DocumentFormat.PDF, target=DocumentFormat.JPEG)


class PyMuPdfPdfToJpegConverter:
    """Единственное знание о PDF→JPEG. Сценарии видят только DocumentConverter."""

    def __init__(
        self,
        renderer: PdfRenderer | None = None,
        stacker: JpegStacker | None = None,
    ) -> None:
        self._renderer = renderer or PyMuPdfRenderer()
        self._stacker = stacker or PyMuPdfJpegStacker()

    @property
    def pairs(self) -> tuple[ConversionPair, ...]:
        return (_PAIR,)

    def supports(self, pair: ConversionPair) -> bool:
        return pair == _PAIR

    def convert(
        self,
        content: bytes,
        filename: str,
        options: ConversionOptions,
    ) -> ConversionArtifactBundle:
        stem = self._validate(content, filename)
        source = self._write_temp_pdf(content)
        try:
            pages = list(self._renderer.render(source, options, options.password))
        finally:
            source.unlink(missing_ok=True)

        page_count = len(pages)
        if options.layout == OutputLayout.SINGLE:
            merged = self._stacker.stack(pages, options.quality)
            files = (
                MediaFile(
                    filename=f"{stem}.jpg",
                    content=merged.content,
                    media_type=DocumentFormat.JPEG.media_type,
                ),
            )
        else:
            files = tuple(
                MediaFile(
                    filename=f"{stem}_p{page.page_number:03d}.jpg",
                    content=page.content,
                    media_type=DocumentFormat.JPEG.media_type,
                )
                for page in pages
            )
        return ConversionArtifactBundle(
            source_name=filename,
            source_format=DocumentFormat.PDF,
            target_format=DocumentFormat.JPEG,
            files=files,
            page_count=page_count,
            layout=options.layout,
        )

    def _validate(self, content: bytes, filename: str) -> str:
        name = Path(filename).name
        if not name:
            raise InvalidPdfError(Path("upload.pdf"), "не передано имя файла")
        if Path(name).suffix.lower() != ".pdf":
            raise InvalidPdfError(Path(name), "ожидался файл с расширением .pdf")
        if not content:
            raise InvalidPdfError(Path(name), "файл пустой")
        if not content.lstrip().startswith(_PDF_MAGIC):
            raise InvalidPdfError(Path(name), "содержимое не похоже на PDF")
        stem = Path(name).stem.strip()
        if not stem:
            raise InvalidPdfError(Path(name), "имя файла без расширения пустое")
        return stem

    def _write_temp_pdf(self, content: bytes) -> Path:
        handle = tempfile.NamedTemporaryFile(prefix="pdf2jpeg_", suffix=".pdf", delete=False)
        try:
            handle.write(content)
        finally:
            handle.close()
        return Path(handle.name)
