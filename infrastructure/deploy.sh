#!/usr/bin/env bash
#
# deploy.sh - Deploy Drift documentation infrastructure using CloudFormation
#
# Usage:
#   ./infrastructure/deploy.sh [--region REGION]
#
# Parameters are read from infrastructure/parameters.json
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
REGION="us-west-2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMETERS_FILE="$SCRIPT_DIR/parameters.json"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--region REGION]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${GREEN}Drift Documentation Infrastructure Deployment${NC}            ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if parameters file exists
if [ ! -f "$PARAMETERS_FILE" ]; then
    echo -e "${RED}Error: parameters.json not found${NC}"
    echo ""
    echo "Create $PARAMETERS_FILE with the following format:"
    echo ""
    cat << 'EOF'
[
  {
    "ParameterKey": "ProjectName",
    "ParameterValue": "drift"
  },
  {
    "ParameterKey": "Environment",
    "ParameterValue": "production"
  },
  {
    "ParameterKey": "BaseDomain",
    "ParameterValue": "driftai.dev"
  },
  {
    "ParameterKey": "HostedZoneId",
    "ParameterValue": "Z1234567890ABC"
  },
  {
    "ParameterKey": "DocsCertificateArn",
    "ParameterValue": "arn:aws:acm:us-east-1:123456789012:certificate/..."
  }
]
EOF
    echo ""
    echo "See infrastructure/parameters.json.example for a template."
    exit 1
fi

# Read parameters from file
PROJECT_NAME=$(jq -r '.[] | select(.ParameterKey=="ProjectName") | .ParameterValue' "$PARAMETERS_FILE")
ENVIRONMENT=$(jq -r '.[] | select(.ParameterKey=="Environment") | .ParameterValue' "$PARAMETERS_FILE")
BASE_DOMAIN=$(jq -r '.[] | select(.ParameterKey=="BaseDomain") | .ParameterValue' "$PARAMETERS_FILE")

if [ -z "$PROJECT_NAME" ] || [ "$PROJECT_NAME" = "null" ]; then
    echo -e "${RED}Error: ProjectName not found in parameters.json${NC}"
    exit 1
fi

if [ -z "$ENVIRONMENT" ] || [ "$ENVIRONMENT" = "null" ]; then
    ENVIRONMENT="production"
fi

if [ -z "$BASE_DOMAIN" ] || [ "$BASE_DOMAIN" = "null" ]; then
    echo -e "${RED}Error: BaseDomain not found in parameters.json${NC}"
    exit 1
fi

# Derive resource names from parameters
BUCKET_NAME="${PROJECT_NAME}-docs-${ENVIRONMENT}"
STACK_NAME="${PROJECT_NAME}-docs-infrastructure"
DEPLOYMENT_USER="${PROJECT_NAME}-docs-deployer-${ENVIRONMENT}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project Name:    $PROJECT_NAME"
echo "  Environment:     $ENVIRONMENT"
echo "  Base Domain:     $BASE_DOMAIN"
echo "  Docs URL:        https://docs.${BASE_DOMAIN}"
echo "  Bucket Name:     $BUCKET_NAME"
echo "  Stack Name:      $STACK_NAME"
echo "  Region:          $REGION"
echo ""

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    2>/dev/null || echo "")

if [ -n "$STACK_EXISTS" ]; then
    echo -e "${YELLOW}Stack exists - updating...${NC}"
    OPERATION="update-stack"
else
    echo -e "${GREEN}Creating new stack...${NC}"
    OPERATION="create-stack"
fi

# Deploy CloudFormation stack
echo ""
echo -e "${YELLOW}→${NC} Deploying CloudFormation stack..."

aws cloudformation $OPERATION \
    --stack-name "$STACK_NAME" \
    --template-body "file://$SCRIPT_DIR/docs-infrastructure.yaml" \
    --parameters "file://$PARAMETERS_FILE" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    || {
        if [ "$OPERATION" = "update-stack" ]; then
            echo -e "${YELLOW}No updates to perform (stack is already up to date)${NC}"
        else
            echo -e "${RED}Stack deployment failed${NC}"
            exit 1
        fi
    }

# Wait for stack to complete
if [ "$OPERATION" = "create-stack" ]; then
    echo ""
    echo -e "${YELLOW}→${NC} Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
else
    echo ""
    echo -e "${YELLOW}→${NC} Waiting for stack update to complete..."
    aws cloudformation wait stack-update-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION" 2>/dev/null || true
fi

# Get stack outputs
echo ""
echo -e "${YELLOW}→${NC} Retrieving stack outputs..."

OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs' \
    --output json)

DOCS_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DocsBucketName") | .OutputValue')
DOCS_DIST_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DocsDistributionId") | .OutputValue')
DOCS_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DocumentationURL") | .OutputValue')
USER_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DeploymentUserArn") | .OutputValue')

echo ""
echo -e "${GREEN}✓ Stack deployment complete!${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Stack Outputs:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Docs Bucket:     $DOCS_BUCKET"
echo "  Distribution ID: $DOCS_DIST_ID"
echo "  Documentation:   $DOCS_URL"
echo "  Deployment User: $DEPLOYMENT_USER"
echo "  User ARN:        $USER_ARN"
echo ""

# Save configuration (non-sensitive info only)
echo -e "${YELLOW}→${NC} Saving configuration to infrastructure/config.sh..."

cat > "$SCRIPT_DIR/config.sh" << EOF
# Drift Documentation Infrastructure Configuration
# Generated: $(date)
# DO NOT COMMIT THIS FILE - IT'S IN .gitignore

export DOCS_S3_BUCKET="$DOCS_BUCKET"
export DOCS_CLOUDFRONT_ID="$DOCS_DIST_ID"
export DOCS_URL="$DOCS_URL"
export AWS_REGION="$REGION"
export DEPLOYMENT_USER="$DEPLOYMENT_USER"

# For credentials, either:
# 1. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY manually
# 2. Or use AWS_PROFILE for AWS CLI profile
# export AWS_PROFILE="docs-deployer"
EOF

echo -e "${GREEN}✓ Configuration saved!${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "1. Set up GitHub secrets (for CI/CD):"
echo "   ${YELLOW}./infrastructure/setup-github-secrets.sh${NC}"
echo ""
echo "2. Load configuration (for local use):"
echo "   ${YELLOW}source infrastructure/config.sh${NC}"
echo ""
echo "3. Build and deploy documentation:"
echo "   ${YELLOW}./scripts/build-docs.sh && ./scripts/deploy-docs.sh${NC}"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
