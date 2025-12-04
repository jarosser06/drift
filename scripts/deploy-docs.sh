#!/bin/bash
# Deploy documentation to S3
# This script should be run as part of the release process or manually

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"

# Check if config exists
if [ ! -f "$PROJECT_ROOT/infrastructure/config.sh" ]; then
    echo "Error: infrastructure/config.sh not found"
    echo "Run ./infrastructure/deploy.sh first to create infrastructure"
    exit 1
fi

# Load configuration
source "$PROJECT_ROOT/infrastructure/config.sh"

# Verify required variables
if [ -z "$DOCS_S3_BUCKET" ] || [ -z "$DOCS_CLOUDFRONT_ID" ]; then
    echo "Error: Required configuration variables not set"
    echo "DOCS_S3_BUCKET and DOCS_CLOUDFRONT_ID must be defined in infrastructure/config.sh"
    exit 1
fi

echo "Deploying documentation to S3..."
echo "S3 Bucket: $DOCS_S3_BUCKET"
echo "CloudFront: $DOCS_CLOUDFRONT_ID"
echo ""

# Build documentation
echo "Building documentation..."
"$SCRIPT_DIR/build-docs.sh"

# Deploy to S3 root
echo "Deploying to S3..."
aws s3 sync "$DOCS_DIR/_build/html/" "s3://$DOCS_S3_BUCKET/" \
    --delete \
    --cache-control "public, max-age=3600"

# Invalidate CloudFront cache
echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id "$DOCS_CLOUDFRONT_ID" \
    --paths "/*"

echo ""
echo "Documentation deployed successfully!"
echo "S3 Location: s3://$DOCS_S3_BUCKET/"
echo "URL: $DOCS_URL"
echo ""
echo "Note: CloudFront invalidation may take a few minutes to propagate"
