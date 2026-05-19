"""Tests for the server CLI command."""

from click.testing import CliRunner

from main import cli


def test_server_help(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["server", "--help"])
    assert result.exit_code == 0
    assert "启动 RAG HTTP 服务" in result.output
    assert "--host" in result.output
    assert "--port" in result.output


def test_server_default_port_in_help(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["server", "--help"])
    assert result.exit_code == 0
    assert "8000" in result.output
