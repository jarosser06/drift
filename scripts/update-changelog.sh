#!/usr/bin/env bash
#
# update-changelog.sh - Update CHANGELOG.md with new version entry
#
# Usage:
#   ./scripts/update-changelog.sh <version> "<description>"
#   ./scripts/update-changelog.sh <version> "<item1>; <item2>; <item3>"
#
# Example:
#   ./scripts/update-changelog.sh 0.2.0 "Added new feature X; Fixed bug Y"
#
# This script:
# 1. Adds a new version entry to CHANGELOG.md
# 2. Formats entry with version, date, and description
# 3. Splits description by semicolons into separate bullet points
# 4. Preserves existing changelog entries
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
VERSION="$1"
DESCRIPTION="$2"

if [[ -z "$VERSION" ]]; then
    echo -e "${RED}Error: Version required${NC}" >&2
    echo "Usage: $0 <version> \"<description>\"" >&2
    echo "" >&2
    echo "Example:" >&2
    echo "  $0 0.2.0 \"Added new feature X; Fixed bug Y\"" >&2
    exit 1
fi

if [[ -z "$DESCRIPTION" ]]; then
    echo -e "${RED}Error: Description required${NC}" >&2
    echo "Usage: $0 <version> \"<description>\"" >&2
    exit 1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format '$VERSION'${NC}" >&2
    echo "Expected: MAJOR.MINOR.PATCH (e.g., 0.2.0)" >&2
    exit 1
fi

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHANGELOG="$PROJECT_ROOT/CHANGELOG.md"

if [ ! -f "$CHANGELOG" ]; then
    echo -e "${RED}Error: CHANGELOG.md not found${NC}" >&2
    exit 1
fi

# Get current date
DATE=$(date +"%Y-%m-%d")

echo -e "${YELLOW}→${NC} Updating CHANGELOG.md..." >&2
echo "" >&2
echo "Version: $VERSION" >&2
echo "Date:    $DATE" >&2
echo "Changes:" >&2

# Split description into items by semicolon
if [[ "$DESCRIPTION" == *";"* ]]; then
    # Split and display items
    IFS=";" read -ra ITEMS <<< "$DESCRIPTION"
    for item in "${ITEMS[@]}"; do
        # Trim whitespace
        item=$(echo "$item" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        if [[ -n "$item" ]]; then
            echo "  - $item" >&2
        fi
    done
else
    # Single item
    echo "  - $DESCRIPTION" >&2
fi
echo "" >&2

# Create temp file with new entry
TEMP_FILE=$(mktemp)

# Find the line with "## [Unreleased]" and insert after the next blank line
awk -v version="$VERSION" -v date="$DATE" -v desc="$DESCRIPTION" '
/^## \[Unreleased\]/ {
    print
    # Print the next line (should be blank)
    getline
    print
    # Insert new entry
    print "## [" version "] - " date
    print ""

    # Split description by semicolon
    if (index(desc, ";") > 0) {
        n = split(desc, items, ";")
        # Print each item as a bullet point
        for (i = 1; i <= n; i++) {
            # Trim whitespace
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", items[i])
            if (length(items[i]) > 0) {
                print "- " items[i]
            }
        }
    } else {
        # Single item
        print "- " desc
    }
    print ""
    next
}
{print}
' "$CHANGELOG" > "$TEMP_FILE"

# Replace original file
mv "$TEMP_FILE" "$CHANGELOG"

echo -e "${GREEN}✓ CHANGELOG.md updated successfully!${NC}" >&2
echo "" >&2
