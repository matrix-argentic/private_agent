"""Server CLI command — start the RAG HTTP server."""

import click


@click.command("server", help="启动 RAG HTTP 服务")
@click.option("--host", default="0.0.0.0", show_default=True, help="监听地址")
@click.option(
    "-p", "--port", default=8000, type=int, show_default=True, help="监听端口"
)
def run(host: str, port: int) -> None:
    import uvicorn

    from app.server.server import app

    uvicorn.run(
        app,
        host=host,
        port=port,
        timeout_graceful_shutdown=10,
    )
