"""Упаковка артефактов: один файл как есть, несколько — в ZIP."""

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from converter.domain.models import ConversionArtifactBundle


@dataclass(frozen=True, slots=True)
class PackedArtifactResponse:
    """Готовый бинарный ответ для HTTP."""

    body: bytes
    media_type: str
    filename: str


class PackArtifactBundle:
    """Готовит тело ответа. Не знает про FastAPI и конкретные форматы."""

    def execute(self, bundle: ConversionArtifactBundle) -> PackedArtifactResponse:
        if bundle.is_single_file:
            item = bundle.files[0]
            return PackedArtifactResponse(
                body=item.content,
                media_type=item.media_type,
                filename=item.filename,
            )
        stem = Path(bundle.source_name).stem.strip() or "document"
        return PackedArtifactResponse(
            body=self._zip_bytes(bundle),
            media_type="application/zip",
            filename=f"{stem}_{bundle.target_format.value}.zip",
        )

    def _zip_bytes(self, bundle: ConversionArtifactBundle) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in bundle.files:
                archive.writestr(item.filename, item.content)
        return buffer.getvalue()
