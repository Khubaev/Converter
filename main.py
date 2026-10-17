"""Точка входа CLI: реестр адаптеров и сценарий записи на диск."""

from converter.composition import build_cli_use_case, build_registry
from converter.presentation.cli import run_cli


def main(argv: list[str] | None = None) -> int:
    """Запускает CLI с реестром конвертеров."""
    registry = build_registry()
    return run_cli(build_cli_use_case(registry), registry, argv)


if __name__ == "__main__":
    raise SystemExit(main())
