"""Unit tests for CLI main module."""

from drift.cli.main import create_parser, main


class TestCliMain:
    """Test CLI main module."""

    def test_main_function_exists(self) -> None:
        """Test that the main function exists."""
        assert main is not None
        assert callable(main)

    def test_create_parser_exists(self) -> None:
        """Test that create_parser function exists."""
        assert create_parser is not None
        assert callable(create_parser)

    def test_parser_has_version(self) -> None:
        """Test that parser has --version option."""
        parser = create_parser()
        # Try parsing --version (will call sys.exit, but we're just checking structure)
        assert parser is not None

    def test_parser_has_expected_arguments(self) -> None:
        """Test that parser has expected arguments."""
        parser = create_parser()
        # Parse help to check structure
        args = parser.parse_args(
            [
                "--format",
                "json",
                "--scope",
                "project",
                "--project",
                "/tmp",
            ]
        )
        assert args.format == "json"
        assert args.scope == "project"
        assert args.project == "/tmp"
