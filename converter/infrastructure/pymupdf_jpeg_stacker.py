"""Адаптер JpegStacker: склеивает JPEG страниц через Pixmap PyMuPDF."""

from collections.abc import Sequence

import pymupdf

from converter.domain.exceptions import ConverterError, InvalidRenderOptionsError
from converter.domain.models import (
    MAX_JPEG_QUALITY,
    MAX_MERGED_PIXELS,
    MIN_JPEG_QUALITY,
    PageImage,
)


class PyMuPdfJpegStacker:
    """Ставит страницы друг под другом на белом фоне и кодирует один JPEG."""

    def stack(self, pages: Sequence[PageImage], quality: int) -> PageImage:
        if not pages:
            raise ConverterError("Нечего склеивать: список страниц пуст.")
        if isinstance(quality, bool) or not isinstance(quality, int):
            raise InvalidRenderOptionsError("Качество JPEG должно быть целым числом.")
        if not MIN_JPEG_QUALITY <= quality <= MAX_JPEG_QUALITY:
            raise InvalidRenderOptionsError(
                f"Качество JPEG должно быть от {MIN_JPEG_QUALITY} до {MAX_JPEG_QUALITY}."
            )
        if len(pages) == 1:
            return pages[0]

        pixmaps = [self._load(page) for page in pages]
        width = max(pix.width for pix in pixmaps)
        height = sum(pix.height for pix in pixmaps)
        if width * height > MAX_MERGED_PIXELS:
            raise ConverterError(
                "Итоговое изображение слишком большое для склейки в один JPEG. "
                "Уменьшите DPI или используйте layout=separate."
            )

        # alpha=0: как у JPEG-страниц, иначе copy() падает на несовпадении alpha.
        canvas = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), 0)
        canvas.set_rect(canvas.irect, (255, 255, 255))

        # copy(src, bbox) копирует область bbox *из источника в те же координаты* холста.
        # Поэтому сдвигаем origin каждой страницы, а не передаём (x, y) как позицию вставки.
        offset_y = 0
        for pix in pixmaps:
            offset_x = (width - pix.width) // 2
            pix.set_origin(offset_x, offset_y)
            canvas.copy(pix, pix.irect)
            offset_y += pix.height

        content = canvas.tobytes("jpeg", jpg_quality=quality)
        return PageImage(
            page_number=1,
            width=canvas.width,
            height=canvas.height,
            content=content,
        )

    def _load(self, page: PageImage) -> pymupdf.Pixmap:
        if not page.content.startswith(b"\xff\xd8"):
            raise ConverterError(
                f"Страница {page.page_number} не является JPEG."
            )
        try:
            pixmap = pymupdf.Pixmap(page.content)
        except Exception as exc:
            raise ConverterError(
                f"Не удалось декодировать JPEG страницы {page.page_number}."
            ) from exc
        if pixmap.alpha or pixmap.n != 3:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
        return pixmap

