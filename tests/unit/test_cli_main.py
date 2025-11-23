"""Unit tests for CLI main module."""

from drift.cli.main import app


class TestCliMain:
    """Test CLI main module."""

    def test_app_exists(self) -> None:
        """Test that the Typer app exists."""
        assert app is not None

    def test_app_is_typer_instance(self) -> None:
        """Test that app is a Typer instance."""
        from typer import Typer

        assert isinstance(app, Typer)

    def test_app_has_callback(self) -> None:
        """Test that app has a registered callback."""
        assert hasattr(app, "registered_callback")

    def test_app_has_commands(self) -> None:
        """Test that app has registered commands."""
        assert hasattr(app, "registered_commands")
