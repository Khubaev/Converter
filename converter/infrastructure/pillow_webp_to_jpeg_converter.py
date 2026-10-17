"""Адаптер DocumentConverter: WebP → JPEG на Pillow."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from converter.application.ports import JpegStacker
from converter.domain.exceptions import InvalidImageError
from converter.domain.models import (
    ConversionArtifactBundle,
    ConversionOptions,
    ConversionPair,
    DocumentFormat,
    MediaFile,
    OutputLayout,
    PageImage,
)
from converter.infrastructure.pymupdf_jpeg_stacker import PyMuPdfJpegStacker

_RIFF_MAGIC = b"RIFF"
_WEBP_MARK = b"WEBP"
_PAIR = ConversionPair(source=DocumentFormat.WEBP, target=DocumentFormat.JPEG)
_WHITE = (255, 255, 255)


class PillowWebpToJpegConverter:
    """Конвертирует один кадр или анимацию WebP в JPEG. DPI не меняет размер."""

    def __init__(self, stacker: JpegStacker | None = None) -> None:
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
        pages = self._decode(content, Path(filename).name, options.quality)
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
            source_format=DocumentFormat.WEBP,
            target_format=DocumentFormat.JPEG,
            files=files,
            page_count=len(pages),
            layout=options.layout,
        )

    def _validate(self, content: bytes, filename: str) -> str:
        name = Path(filename).name
        if not name:
            raise InvalidImageError(Path("upload.webp"), "не передано имя файла")
        if Path(name).suffix.lower() != ".webp":
            raise InvalidImageError(Path(name), "ожидался файл с расширением .webp")
        if not content:
            raise InvalidImageError(Path(name), "файл пустой")
        if not _looks_like_webp(content):
            raise InvalidImageError(Path(name), "содержимое не похоже на WebP")
        stem = Path(name).stem.strip()
        if not stem:
            raise InvalidImageError(Path(name), "имя файла без расширения пустое")
        return stem

    def _decode(self, content: bytes, filename: str, quality: int) -> tuple[PageImage, ...]:
        path = Path(filename)
        try:
            image = Image.open(BytesIO(content))
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise InvalidImageError(path, "не удалось прочитать WebP") from exc

        try:
            if (image.format or "").upper() != "WEBP":
                raise InvalidImageError(path, "содержимое не является WebP")
            frame_count = int(getattr(image, "n_frames", 1) or 0)
            if frame_count < 1:
                raise InvalidImageError(path, "в WebP нет кадров")
            pages: list[PageImage] = []
            for index in range(frame_count):
                image.seek(index)
                frame = image.copy()
                transposed = ImageOps.exif_transpose(frame)
                if transposed is not None:
                    frame = transposed
                jpeg = _encode_jpeg(frame, quality)
                pages.append(
                    PageImage(
                        page_number=index + 1,
                        width=frame.width,
                        height=frame.height,
                        content=jpeg,
                    )
                )
        except InvalidImageError:
            raise
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            raise InvalidImageError(path, "не удалось декодировать кадр WebP") from exc
        finally:
            image.close()
        return tuple(pages)


def _looks_like_webp(content: bytes) -> bool:
    return len(content) >= 12 and content[:4] == _RIFF_MAGIC and content[8:12] == _WEBP_MARK


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    """JPEG не хранит альфу: прозрачные пиксели кладём на белый фон."""
    flattened = _flatten(image)
    buffer = BytesIO()
    flattened.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def _flatten(image: Image.Image) -> Image.Image:
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode in {"RGBA", "LA"}:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, _WHITE)
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if image.mode == "RGB":
        return image
    return image.convert("RGB")
