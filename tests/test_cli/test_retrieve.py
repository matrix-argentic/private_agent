"""Tests for the retrieve CLI command."""

from click.testing import CliRunner

from main import cli


def test_retrieve_help(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["retrieve", "--help"])
    assert result.exit_code == 0
    assert "查找文档" in result.output


def test_retrieve_requires_query(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["retrieve"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_retrieve_has_top_k_default(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["retrieve", "--help"])
    assert result.exit_code == 0
    assert "5" in result.output
