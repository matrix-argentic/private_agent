"""Tests for the chat CLI command."""

from click.testing import CliRunner

from main import cli


def test_chat_help(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["chat", "--help"])
    assert result.exit_code == 0
    assert "query" in result.output


def test_chat_requires_query(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["chat"])
    assert result.exit_code != 0
    assert "Missing option" in result.output
