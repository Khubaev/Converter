"""Сценарий: сконвертировать документ через реестр адаптеров."""

from converter.application.converter_registry import ConverterRegistry
from converter.application.dto import ConvertDocumentCommand
from converter.domain.models import ConversionArtifactBundle, ConversionPair


class ConvertDocument:
    """Оркестратор. Не знает ни про PDF, ни про PyMuPDF."""

    def __init__(self, registry: ConverterRegistry) -> None:
        self._registry = registry

    def execute(self, command: ConvertDocumentCommand) -> ConversionArtifactBundle:
        pair = ConversionPair(source=command.source_format, target=command.target_format)
        converter = self._registry.resolve(pair)
        return converter.convert(command.content, command.filename, command.options)
