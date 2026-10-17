"""Корень композиции: реестр адаптеров и базовые сценарии."""

from converter.application.convert_document import ConvertDocument
from converter.application.convert_document_to_files import ConvertDocumentToFiles
from converter.application.converter_registry import ConverterRegistry
from converter.infrastructure.pillow_webp_to_jpeg_converter import PillowWebpToJpegConverter
from converter.infrastructure.pymupdf_pdf_to_jpeg_converter import PyMuPdfPdfToJpegConverter


def build_registry() -> ConverterRegistry:
    """Регистрирует все доступные пары конвертации."""
    registry = ConverterRegistry()
    registry.register(PyMuPdfPdfToJpegConverter())
    registry.register(PillowWebpToJpegConverter())
    return registry


def build_convert_document(registry: ConverterRegistry | None = None) -> ConvertDocument:
    return ConvertDocument(registry or build_registry())


def build_cli_use_case(registry: ConverterRegistry | None = None) -> ConvertDocumentToFiles:
    return ConvertDocumentToFiles(build_convert_document(registry))
