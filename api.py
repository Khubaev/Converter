"""Точка входа HTTP API: uvicorn api:app --reload"""

from converter.presentation.api.app import create_app

app = create_app()


def main() -> None:
    """Запуск dev-сервера без отдельной команды uvicorn."""
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
