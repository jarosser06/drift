#!/usr/bin/env bash
#
# setup-certificate.sh - Guide for setting up ACM certificate for CloudFront
#
# CloudFront requires certificates in us-east-1 region
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN="docs.driftai.dev"
REGION="us-east-1"  # CloudFront requires certificates in us-east-1

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${GREEN}ACM Certificate Setup for CloudFront${NC}                      ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Important Notes:${NC}"
echo "  - CloudFront requires certificates in us-east-1 region"
echo "  - Domain validation via Route53 is automated"
echo "  - Certificate must be validated before deploying infrastructure"
echo ""

echo -e "${YELLOW}Domain to certify:${NC} $DOMAIN"
echo -e "${YELLOW}AWS Region:${NC} $REGION (required for CloudFront)"
echo ""

# Check if certificate already exists
echo -e "${YELLOW}→${NC} Checking for existing certificates..."
EXISTING_CERTS=$(aws acm list-certificates \
    --region "$REGION" \
    --query "CertificateSummaryList[?DomainName=='$DOMAIN'].CertificateArn" \
    --output text)

if [ -n "$EXISTING_CERTS" ]; then
    echo -e "${GREEN}✓ Found existing certificate(s):${NC}"
    echo "$EXISTING_CERTS"
    echo ""
    read -p "$(echo -e ${YELLOW}Do you want to create a new certificate anyway? [y/N]:${NC} )" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${GREEN}Using existing certificate.${NC}"
        echo "Add this ARN to your infrastructure/parameters.json:"
        echo ""
        echo "  {\"ParameterKey\": \"DocsCertificateArn\", \"ParameterValue\": \"$EXISTING_CERTS\"}"
        echo ""
        exit 0
    fi
fi

# Request certificate
echo ""
echo -e "${YELLOW}→${NC} Requesting ACM certificate for $DOMAIN..."

CERT_ARN=$(aws acm request-certificate \
    --domain-name "$DOMAIN" \
    --validation-method DNS \
    --region "$REGION" \
    --query 'CertificateArn' \
    --output text)

if [ -z "$CERT_ARN" ]; then
    echo -e "${RED}Error: Failed to request certificate${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Certificate requested:${NC} $CERT_ARN"
echo ""

# Wait for DNS validation records to be available
echo -e "${YELLOW}→${NC} Waiting for DNS validation records..."
sleep 5

# Get validation record
VALIDATION_RECORD=$(aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --region "$REGION" \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord' \
    --output json)

VALIDATION_NAME=$(echo "$VALIDATION_RECORD" | jq -r '.Name')
VALIDATION_VALUE=$(echo "$VALIDATION_RECORD" | jq -r '.Value')

if [ -z "$VALIDATION_NAME" ] || [ "$VALIDATION_NAME" = "null" ]; then
    echo -e "${RED}Error: Could not retrieve validation record${NC}"
    echo "You may need to wait a moment and run: aws acm describe-certificate --certificate-arn $CERT_ARN --region $REGION"
    exit 1
fi

echo -e "${GREEN}✓ DNS validation record retrieved${NC}"
echo ""
echo -e "${YELLOW}Validation Record:${NC}"
echo "  Name:  $VALIDATION_NAME"
echo "  Value: $VALIDATION_VALUE"
echo ""

# Attempt automatic validation via Route53
echo -e "${YELLOW}Attempting automatic validation via Route53...${NC}"
echo ""

# Find hosted zone ID for driftai.dev
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
    --query "HostedZones[?Name=='driftai.dev.'].Id" \
    --output text | cut -d'/' -f3)

if [ -z "$HOSTED_ZONE_ID" ]; then
    echo -e "${YELLOW}Warning: Could not find Route53 hosted zone for driftai.dev${NC}"
    echo ""
    echo "Manual steps required:"
    echo "1. Go to Route53 console"
    echo "2. Find your hosted zone for driftai.dev"
    echo "3. Add CNAME record:"
    echo "   Name:  $VALIDATION_NAME"
    echo "   Value: $VALIDATION_VALUE"
    echo ""
else
    echo -e "${GREEN}✓ Found hosted zone:${NC} $HOSTED_ZONE_ID"
    echo ""

    # Create change batch JSON
    CHANGE_BATCH=$(cat <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$VALIDATION_NAME",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [
          {
            "Value": "$VALIDATION_VALUE"
          }
        ]
      }
    }
  ]
}
EOF
)

    # Apply DNS record
    CHANGE_ID=$(aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch "$CHANGE_BATCH" \
        --query 'ChangeInfo.Id' \
        --output text)

    if [ -n "$CHANGE_ID" ]; then
        echo -e "${GREEN}✓ DNS validation record created${NC}"
        echo ""
        echo -e "${YELLOW}→${NC} Waiting for DNS propagation and certificate validation..."
        echo "   This may take a few minutes..."
        echo ""

        # Wait for certificate to be validated
        aws acm wait certificate-validated \
            --certificate-arn "$CERT_ARN" \
            --region "$REGION" && {
            echo -e "${GREEN}✓ Certificate validated successfully!${NC}"
        } || {
            echo -e "${YELLOW}Certificate validation is in progress...${NC}"
            echo "Check status with: aws acm describe-certificate --certificate-arn $CERT_ARN --region $REGION"
        }
    else
        echo -e "${RED}Error: Failed to create DNS record${NC}"
        echo "Please add the CNAME record manually in Route53."
    fi
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Certificate Setup Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Certificate ARN: $CERT_ARN"
echo "  Domain:          $DOMAIN"
echo "  Region:          $REGION"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Add certificate ARN to infrastructure/parameters.json:"
echo "   {\"ParameterKey\": \"DocsCertificateArn\", \"ParameterValue\": \"$CERT_ARN\"}"
echo ""
echo "2. Add hosted zone ID to infrastructure/parameters.json:"
echo "   {\"ParameterKey\": \"HostedZoneId\", \"ParameterValue\": \"$HOSTED_ZONE_ID\"}"
echo ""
echo "3. Deploy infrastructure:"
echo "   ./infrastructure/deploy.sh"
echo ""
