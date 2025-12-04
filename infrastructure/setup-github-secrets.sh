#!/usr/bin/env bash
#
# setup-github-secrets.sh - Set up GitHub secrets for documentation deployment
#
# Usage:
#   ./infrastructure/setup-github-secrets.sh [--rotate]
#
# Requires:
#   - GitHub CLI (gh) installed and authenticated
#   - AWS CLI configured with appropriate permissions
#   - infrastructure/config.sh exists (run deploy.sh first)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.sh"

ROTATE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --rotate)
            ROTATE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--rotate]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${GREEN}GitHub Secrets Setup for Documentation Deployment${NC}        ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: config.sh not found${NC}"
    echo "Run ./infrastructure/deploy.sh first to create infrastructure"
    exit 1
fi

# Load configuration
source "$CONFIG_FILE"

# Verify required variables
if [ -z "$DEPLOYMENT_USER" ] || [ -z "$AWS_REGION" ] || [ -z "$DOCS_S3_BUCKET" ] || [ -z "$DOCS_CLOUDFRONT_ID" ]; then
    echo -e "${RED}Error: Required variables not found in config.sh${NC}"
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  Deployment User: $DEPLOYMENT_USER"
echo "  AWS Region:      $AWS_REGION"
echo "  S3 Bucket:       $DOCS_S3_BUCKET"
echo "  CloudFront ID:   $DOCS_CLOUDFRONT_ID"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}Warning: GitHub CLI (gh) not installed${NC}"
    echo ""
    echo "Install GitHub CLI: https://cli.github.com/"
    echo ""
    echo "Or set secrets manually in GitHub repository settings:"
    echo "  Settings → Secrets and variables → Actions → New repository secret"
    echo ""
    MANUAL_MODE=true
else
    MANUAL_MODE=false
    echo -e "${GREEN}✓ GitHub CLI found${NC}"
fi

# Rotate existing keys if requested
if [ "$ROTATE" = true ]; then
    echo ""
    echo -e "${YELLOW}→${NC} Rotating access keys..."

    # List and delete existing keys
    EXISTING_KEYS=$(aws iam list-access-keys \
        --user-name "$DEPLOYMENT_USER" \
        --query 'AccessKeyMetadata[].AccessKeyId' \
        --output text)

    if [ -n "$EXISTING_KEYS" ]; then
        for KEY_ID in $EXISTING_KEYS; do
            echo "  Deleting key: $KEY_ID"
            aws iam delete-access-key \
                --user-name "$DEPLOYMENT_USER" \
                --access-key-id "$KEY_ID"
        done
        echo -e "${GREEN}✓ Old keys deleted${NC}"
    else
        echo "  No existing keys found"
    fi
fi

# Create new access key
echo ""
echo -e "${YELLOW}→${NC} Creating new access key for $DEPLOYMENT_USER..."

ACCESS_KEY_OUTPUT=$(aws iam create-access-key \
    --user-name "$DEPLOYMENT_USER" \
    --output json)

ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.SecretAccessKey')

if [ -z "$ACCESS_KEY_ID" ] || [ -z "$SECRET_ACCESS_KEY" ]; then
    echo -e "${RED}Error: Failed to create access key${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Access key created${NC}"
echo ""

# Set GitHub secrets
if [ "$MANUAL_MODE" = true ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Manual Setup Required${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Add these secrets to your GitHub repository:"
    echo ""
    echo "  Secret Name: AWS_DOCS_ACCESS_KEY_ID"
    echo "  Value:       $ACCESS_KEY_ID"
    echo ""
    echo "  Secret Name: AWS_DOCS_SECRET_ACCESS_KEY"
    echo "  Value:       $SECRET_ACCESS_KEY"
    echo ""
    echo "  Secret Name: AWS_DOCS_REGION"
    echo "  Value:       $AWS_REGION"
    echo ""
    echo "  Secret Name: AWS_DOCS_BUCKET"
    echo "  Value:       $DOCS_S3_BUCKET"
    echo ""
    echo "  Secret Name: AWS_DOCS_CLOUDFRONT_ID"
    echo "  Value:       $DOCS_CLOUDFRONT_ID"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Save these credentials securely!${NC}"
    echo "The secret access key will not be shown again."
    echo ""
else
    echo -e "${YELLOW}→${NC} Setting GitHub repository secrets..."

    # Set each secret
    echo "$ACCESS_KEY_ID" | gh secret set AWS_DOCS_ACCESS_KEY_ID
    echo "$SECRET_ACCESS_KEY" | gh secret set AWS_DOCS_SECRET_ACCESS_KEY
    echo "$AWS_REGION" | gh secret set AWS_DOCS_REGION
    echo "$DOCS_S3_BUCKET" | gh secret set AWS_DOCS_BUCKET
    echo "$DOCS_CLOUDFRONT_ID" | gh secret set AWS_DOCS_CLOUDFRONT_ID

    echo -e "${GREEN}✓ GitHub secrets set successfully!${NC}"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Setup Complete!${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Secrets added to GitHub repository:"
    echo "  ✓ AWS_DOCS_ACCESS_KEY_ID"
    echo "  ✓ AWS_DOCS_SECRET_ACCESS_KEY"
    echo "  ✓ AWS_DOCS_REGION"
    echo "  ✓ AWS_DOCS_BUCKET"
    echo "  ✓ AWS_DOCS_CLOUDFRONT_ID"
    echo ""
fi

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Verify GitHub Actions workflow:"
echo "   Check .github/workflows/release.yml for docs deployment step"
echo ""
echo "2. Test documentation deployment:"
echo "   ${YELLOW}source infrastructure/config.sh${NC}"
echo "   ${YELLOW}./scripts/deploy-docs.sh${NC}"
echo ""

if [ "$ROTATE" = true ]; then
    echo -e "${GREEN}Key rotation complete!${NC}"
    echo ""
fi
