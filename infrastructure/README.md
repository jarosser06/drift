# Drift Documentation Infrastructure

CloudFormation-based infrastructure for hosting Drift documentation on S3 + CloudFront.

## Quick Setup

```bash
# 1. Set up SSL certificate (us-east-1 for CloudFront)
./infrastructure/setup-certificate.sh

# 2. Create parameters file
cp infrastructure/parameters.json.example infrastructure/parameters.json
# Edit parameters.json with your values from certificate setup

# 3. Deploy infrastructure
./infrastructure/deploy.sh

# 4. Set up GitHub secrets
./infrastructure/setup-github-secrets.sh
```

## Infrastructure Components

### S3 Bucket
- **Purpose**: Hosts Sphinx-generated HTML documentation
- **Access**: CloudFront Origin Access Control (OAC)
- **Versioning**: Enabled (30-day retention for old versions)
- **Encryption**: Server-side encryption enabled

### CloudFront Distribution
- **Domain**: docs.driftai.dev
- **SSL**: ACM certificate (us-east-1 region required)
- **Caching**: Optimized for static content
- **CORS**: Enabled with preflight support
- **Error Pages**: Custom 404 handling

### Route53 Records
- A record (IPv4) pointing to CloudFront
- AAAA record (IPv6) pointing to CloudFront

### IAM Deployment User
- **Purpose**: CI/CD deployments from GitHub Actions
- **Permissions**:
  - S3: Read, write, delete objects in docs bucket
  - CloudFront: Create invalidations
  - CloudFormation: Read stack information

## Deployment

### Initial Setup

1. **Set up ACM certificate** (one-time):
   ```bash
   ./infrastructure/setup-certificate.sh
   ```

   This will:
   - Request certificate for docs.driftai.dev
   - Create DNS validation record in Route53
   - Wait for validation to complete
   - Display certificate ARN

2. **Create parameters file**:
   ```bash
   cp infrastructure/parameters.json.example infrastructure/parameters.json
   ```

   Edit `parameters.json` with values from certificate setup:
   ```json
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
       "ParameterValue": "Z..."
     },
     {
       "ParameterKey": "DocsCertificateArn",
       "ParameterValue": "arn:aws:acm:us-east-1:..."
     }
   ]
   ```

3. **Deploy infrastructure**:
   ```bash
   ./infrastructure/deploy.sh
   ```

   Creates:
   - S3 bucket: `drift-docs-production`
   - CloudFront distribution
   - Route53 DNS records
   - IAM deployment user
   - Outputs saved to `infrastructure/config.sh`

4. **Set up GitHub secrets** (for CI/CD):
   ```bash
   ./infrastructure/setup-github-secrets.sh
   ```

   Sets these secrets:
   - `AWS_DOCS_ACCESS_KEY_ID`
   - `AWS_DOCS_SECRET_ACCESS_KEY`
   - `AWS_DOCS_REGION`
   - `AWS_DOCS_BUCKET`
   - `AWS_DOCS_CLOUDFRONT_ID`

### Update Existing Stack

```bash
./infrastructure/deploy.sh
```

CloudFormation will update only changed resources.

### Rotate Access Keys

```bash
./infrastructure/setup-github-secrets.sh --rotate
```

Deletes old keys and creates new ones.

## Configuration

After deployment, configuration is saved to `infrastructure/config.sh`:

```bash
export DOCS_S3_BUCKET="drift-docs-production"
export DOCS_CLOUDFRONT_ID="E..."
export DOCS_URL="https://docs.driftai.dev"
export AWS_REGION="us-west-2"
export DEPLOYMENT_USER="drift-docs-deployer-production"
```

**Load configuration**:
```bash
source infrastructure/config.sh
```

**Add credentials** (for local deployment):
```bash
export AWS_ACCESS_KEY_ID="<access-key-id>"
export AWS_SECRET_ACCESS_KEY="<secret-access-key>"
```

Or use AWS CLI profile:
```bash
export AWS_PROFILE="docs-deployer"
```

## Documentation Deployment

### Automated (GitHub Actions)

Documentation is automatically deployed on releases via `.github/workflows/release.yml`.

### Manual Deployment

```bash
# Load configuration
source infrastructure/config.sh

# Build and deploy
./scripts/build-docs.sh
./scripts/deploy-docs.sh
```

## Security

### Sensitive Files (Git Ignored)

The following files are automatically ignored by `.gitignore`:
- `infrastructure/config.sh` - Contains deployment configuration
- `infrastructure/parameters.json` - Contains certificate ARN and zone ID
- `*.pem`, `*.key` - Private keys

### Access Key Management

**Never commit access keys to Git!**

For GitHub Actions, credentials are stored as repository secrets.

**Rotate access keys regularly**:
```bash
./infrastructure/setup-github-secrets.sh --rotate
```

## Cost Estimation

**S3 Storage**:
- ~$0.023 per GB/month (Standard tier)
- Typical docs size: ~10-50MB
- Monthly cost: ~$0.001-0.002

**CloudFront**:
- First 1 TB/month: $0.085 per GB
- 10 GB requests (free tier): $0
- Cache invalidations: $0.005 per path

**Route53**:
- Hosted zone: $0.50/month
- Queries: $0.40 per million queries

**Estimated monthly cost**:
- Small project: ~$1-5/month
- Medium project: ~$5-20/month

## Troubleshooting

### "Stack already exists"
The deployment script automatically updates existing stacks.

### "Access Denied" when deploying
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check you're using deployment user credentials
3. Verify IAM policy is attached

### "Certificate validation timeout"
- DNS propagation can take 5-30 minutes
- Check Route53 for CNAME validation record
- Verify certificate status: `aws acm describe-certificate --certificate-arn <ARN> --region us-east-1`

### "CloudFront distribution not updating"
- CloudFront deployments can take 15-30 minutes
- Check distribution status in AWS console
- Invalidations may take a few minutes to propagate

## Cleanup

To delete the infrastructure:

```bash
# Empty the S3 bucket first
aws s3 rm s3://drift-docs-production --recursive

# Delete the CloudFormation stack
aws cloudformation delete-stack \
  --stack-name drift-docs-infrastructure \
  --region us-west-2

# Delete access keys
aws iam delete-access-key \
  --user-name drift-docs-deployer-production \
  --access-key-id <access-key-id>

# Delete ACM certificate (optional)
aws acm delete-certificate \
  --certificate-arn <certificate-arn> \
  --region us-east-1
```

## References

- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [CloudFront + S3 Best Practices](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)
- [ACM Certificate Validation](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
