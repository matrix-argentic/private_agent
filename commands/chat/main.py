"""Chat CLI command — send a chat query."""

import click


@click.command("chat", help="发送聊天 query")
@click.option("-q", "--query", required=True, help="query 内容")
def run(query: str) -> None:
    from app.agent.config.config import get_agent_config
    from app.agent.service import AgentServiceImpl

    cfg = get_agent_config()
    svc = AgentServiceImpl(cfg)
    result = svc.chat(query)
    click.echo(result)
