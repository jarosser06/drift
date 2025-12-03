#!/bin/bash
# Distribution build and publish script for Drift
# Builds distribution packages and publishes them to PyPI or TestPyPI
# Usage: ./distro.sh <command> [options]
#
# Commands:
#   build           Build distribution packages
#   push            Upload distribution to PyPI
#
# Options:
#   --clean         Clean previous builds before building
#   --test          Upload to TestPyPI instead of PyPI (use with push)

set -e

COMMAND=""
CLEAN=false
TEST=false

# Show usage
show_usage() {
    echo "Usage: ./distro.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  build           Build distribution packages"
    echo "  push            Upload distribution to PyPI"
    echo ""
    echo "Options:"
    echo "  --clean         Clean previous builds before building"
    echo "  --test          Upload to TestPyPI instead of PyPI (use with push)"
    echo ""
    echo "Examples:"
    echo "  ./distro.sh build --clean        # Clean and build distribution"
    echo "  ./distro.sh push --test          # Upload to TestPyPI"
    echo "  ./distro.sh push                 # Upload to PyPI"
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

COMMAND=$1
shift

for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN=true
            ;;
        --test)
            TEST=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo ""
            show_usage
            exit 1
            ;;
    esac
done

# Validate command
case $COMMAND in
    build|push)
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo ""
        show_usage
        exit 1
        ;;
esac

# Build command
do_build() {
    echo "=================================="
    echo "Building distribution for ai-drift"
    echo "=================================="

    # Clean previous builds if requested
    if [ "$CLEAN" = true ] || [ -d "dist" ]; then
        echo ""
        echo "Cleaning previous builds..."
        rm -rf dist/ build/ *.egg-info src/*.egg-info
        echo "✓ Cleaned dist/, build/, and *.egg-info directories"
    fi

    # Build distribution packages
    echo ""
    echo "Building distribution packages..."
    if uv run python -m build; then
        echo ""
        echo "✓ Build completed successfully"
    else
        echo ""
        echo "✗ Build failed"
        exit 1
    fi

    # List generated files
    echo ""
    echo "Generated distribution files:"
    ls -lh dist/

    # Validate packages with twine
    echo ""
    echo "Validating packages with twine check..."
    if uv run twine check dist/*; then
        echo ""
        echo "✓ All distribution packages are valid"
    else
        echo ""
        echo "✗ Twine validation failed"
        exit 1
    fi

    echo ""
    echo "=================================="
    echo "✓ Distribution ready for upload!"
    echo "=================================="
    echo ""
    echo "Next steps:"
    echo "  Test on TestPyPI:  ./distro.sh push --test"
    echo "  Upload to PyPI:    ./distro.sh push"
    echo ""
}

# Push command
do_push() {
    # Check if dist directory exists
    if [ ! -d "dist" ]; then
        echo "Error: dist/ directory not found"
        echo "Run './distro.sh build' first to create distribution packages"
        exit 1
    fi

    # Check if there are files in dist
    if [ -z "$(ls -A dist/)" ]; then
        echo "Error: No distribution files found in dist/"
        echo "Run './distro.sh build' first to create distribution packages"
        exit 1
    fi

    if [ "$TEST" = true ]; then
        echo "=================================="
        echo "Uploading to TestPyPI"
        echo "=================================="
        echo ""
        echo "Note: You'll need TestPyPI credentials"
        echo "Create an account at: https://test.pypi.org"
        echo "Generate API token at: https://test.pypi.org/manage/account/token/"
        echo ""

        if uv run twine upload --repository testpypi dist/*; then
            echo ""
            echo "✓ Successfully uploaded to TestPyPI!"
            echo ""
            echo "Test installation:"
            echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ai-drift"
        else
            echo ""
            echo "✗ Upload to TestPyPI failed"
            exit 1
        fi
    else
        echo "=================================="
        echo "Uploading to PyPI"
        echo "=================================="
        echo ""
        echo "⚠️  WARNING: You are about to publish to the REAL PyPI!"
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " -r
        echo
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Upload cancelled"
            exit 0
        fi

        echo "Note: You'll need PyPI credentials"
        echo "Create an account at: https://pypi.org"
        echo "Generate API token at: https://pypi.org/manage/account/token/"
        echo ""

        if uv run twine upload dist/*; then
            echo ""
            echo "✓ Successfully uploaded to PyPI!"
            echo ""
            echo "Install with:"
            echo "  pip install ai-drift"
            echo ""
            echo "View on PyPI:"
            echo "  https://pypi.org/project/ai-drift/"
        else
            echo ""
            echo "✗ Upload to PyPI failed"
            exit 1
        fi
    fi

    echo ""
    echo "=================================="
}

# Execute command
case $COMMAND in
    build)
        do_build
        ;;
    push)
        do_push
        ;;
esac
