from display_inspector.app import app


def main() -> None:
    import os

    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
