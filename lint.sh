#!/bin/bash
# Linting script for Drift
# Usage: ./lint.sh [--fix] [--embedded]

set -e

FIX=false
EMBEDDED=false
EXIT_CODE=0

# Parse arguments
for arg in "$@"; do
    case $arg in
        --fix)
            FIX=true
            shift
            ;;
        --embedded)
            EMBEDDED=true
            shift
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./lint.sh [--fix] [--embedded]"
            exit 1
            ;;
    esac
done

echo "=================================="
echo "Running linters for Drift"
echo "=================================="

# Run flake8 with uv
echo ""
echo "Running flake8..."
if uv run flake8 src/drift/ tests/ --max-line-length=100 --extend-ignore=E203,W503; then
    echo "✓ flake8 passed"
else
    echo "✗ flake8 failed"
    EXIT_CODE=1
fi

# Run black with uv
echo ""
echo "Running black..."
if [ "$FIX" = true ]; then
    if uv run black src/drift/ tests/ --line-length=100; then
        echo "✓ black formatting applied"
    else
        echo "✗ black failed"
        EXIT_CODE=1
    fi
else
    if uv run black src/drift/ tests/ --line-length=100 --check; then
        echo "✓ black passed"
    else
        echo "✗ black failed (run with --fix to auto-format)"
        EXIT_CODE=1
    fi
fi

# Run isort with uv
echo ""
echo "Running isort..."
if [ "$FIX" = true ]; then
    if uv run isort src/drift/ tests/ --profile=black --line-length=100; then
        echo "✓ isort applied"
    else
        echo "✗ isort failed"
        EXIT_CODE=1
    fi
else
    if uv run isort src/drift/ tests/ --profile=black --line-length=100 --check; then
        echo "✓ isort passed"
    else
        echo "✗ isort failed (run with --fix to auto-sort)"
        EXIT_CODE=1
    fi
fi

# Run mypy with uv
echo ""
echo "Running mypy..."
if uv run mypy src/drift/ --ignore-missing-imports; then
    echo "✓ mypy passed"
else
    echo "✗ mypy failed"
    EXIT_CODE=1
fi

echo ""
echo "=================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All linters passed!"
else
    echo "✗ Some linters failed"
fi
echo "=================================="

# In embedded mode, always exit 0 (for CI/hooks)
if [ "$EMBEDDED" = true ]; then
    exit 0
fi

exit $EXIT_CODE
