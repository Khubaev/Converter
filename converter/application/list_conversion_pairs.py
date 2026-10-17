"""Сценарий: отдать список зарегистрированных пар конвертации."""

from converter.application.converter_registry import ConverterRegistry
from converter.domain.models import ConversionPair


class ListConversionPairs:
    """Читает реестр — для GET /formats и справки CLI."""

    def __init__(self, registry: ConverterRegistry) -> None:
        self._registry = registry

    def execute(self) -> tuple[ConversionPair, ...]:
        return self._registry.list_pairs()
