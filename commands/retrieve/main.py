"""Retrieve CLI command — search documents."""

import click


@click.command("retrieve", help="查找文档")
@click.option("-q", "--query", required=True, help="查找的 query")
@click.option("--top-k", default=5, type=int, show_default=True, help="返回的结果数量")
def run(query: str, top_k: int) -> None:
    from app.service.search import search as rag_search

    results = rag_search(query, top_k)
    if results:
        for r in results:
            click.echo(r)
    else:
        click.echo("No documents found.")
