"""Ошибки домена. Внешние слои переводят свои сбои в эти исключения."""

from pathlib import Path


class ConverterError(Exception):
    """Базовая ошибка конвертера, понятная вызывающему коду."""


class UnsupportedConversionError(ConverterError):
    """Пара форматов не поддерживается или формат неизвестен."""


class InvalidRenderOptionsError(ConverterError):
    """DPI, качество или layout нарушают допустимые границы."""


class PdfNotFoundError(ConverterError):
    """Исходный PDF отсутствует или это не файл."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"PDF не найден: {path}")
        self.path = path


class InvalidPdfError(ConverterError):
    """Файл не является читаемым PDF."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Некорректный PDF ({path}): {reason}")
        self.path = path
        self.reason = reason


class InvalidImageError(ConverterError):
    """Файл не является читаемым изображением заявленного формата."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Некорректное изображение ({path}): {reason}")
        self.path = path
        self.reason = reason


class PdfPasswordRequiredError(ConverterError):
    """Документ зашифрован, а пароль не передан или не подошёл."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"PDF защищён паролем: {path}")
        self.path = path


class EmptyPdfError(ConverterError):
    """В документе нет страниц, сохранять нечего."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"В PDF нет страниц: {path}")
        self.path = path


class OutputPathError(ConverterError):
    """Каталог результата нельзя создать или использовать."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Невозможно записать результат в {path}: {reason}")
        self.path = path
        self.reason = reason


class OcrError(ConverterError):
    """Сбой распознавания текста."""


class AssemblyDispatchError(ConverterError):
    """Сбой отправки распознанного текста на сборку."""


class AssemblyNotConfiguredError(AssemblyDispatchError):
    """Адрес сборки не задан или некорректен."""

    def __init__(
        self,
        message: str = (
            "Сборка не настроена: задайте PATH_N8N=https://... в файле .env "
            "и перезапустите api.py"
        ),
    ) -> None:
        super().__init__(message)


class OcrNotConfiguredError(OcrError):
    """OCR не настроен (нет токена или провайдера)."""

    def __init__(
        self,
        message: str = (
            "VK Vision не настроен: создайте файл .env в корне проекта "
            "и задайте VK_VISION_OAUTH_TOKEN=..., затем перезапустите api.py"
        ),
    ) -> None:
        super().__init__(message)
