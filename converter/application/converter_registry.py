"""Реестр адаптеров DocumentConverter по парам source → target."""

from converter.application.ports import DocumentConverter
from converter.domain.exceptions import UnsupportedConversionError
from converter.domain.models import ConversionPair


class ConverterRegistry:
    """Хранит адаптеры. Один адаптер может закрывать несколько пар."""

    def __init__(self) -> None:
        self._converters: list[DocumentConverter] = []

    def register(self, converter: DocumentConverter) -> None:
        """Добавляет адаптер. Повторная регистрация той же пары запрещена."""
        for pair in converter.pairs:
            existing = self._find(pair)
            if existing is not None:
                raise ValueError(
                    f"Пара {pair.source.value}->{pair.target.value} уже зарегистрирована"
                )
        self._converters.append(converter)

    def resolve(self, pair: ConversionPair) -> DocumentConverter:
        """Возвращает адаптер для пары или бросает UnsupportedConversionError."""
        converter = self._find(pair)
        if converter is None:
            raise UnsupportedConversionError(
                f"Конвертация {pair.source.value} -> {pair.target.value} не поддерживается. "
                f"Доступно: {self._available_label()}"
            )
        return converter

    def list_pairs(self) -> tuple[ConversionPair, ...]:
        """Все зарегистрированные пары в порядке регистрации."""
        pairs: list[ConversionPair] = []
        for converter in self._converters:
            pairs.extend(converter.pairs)
        return tuple(pairs)

    def _find(self, pair: ConversionPair) -> DocumentConverter | None:
        for converter in self._converters:
            if converter.supports(pair):
                return converter
        return None

    def _available_label(self) -> str:
        pairs = self.list_pairs()
        if not pairs:
            return "(нет зарегистрированных пар)"
        return ", ".join(f"{p.source.value}->{p.target.value}" for p in pairs)
