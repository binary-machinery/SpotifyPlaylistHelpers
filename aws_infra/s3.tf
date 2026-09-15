data "aws_caller_identity" "current" {}

# Regions launched before August 2022 (us-east-1 among them) deliver ELB access logs
# from a per-region AWS account rather than from the log delivery service principal.
# Drop this data source and its policy statement if the stack ever moves to a newer region.
data "aws_elb_service_account" "current" {}

locals {
  load_balancer_log_prefix = "lb-${var.env}-logs"

  # Fixed layout the load balancer writes to: <prefix>/AWSLogs/<account-id>/...
  load_balancer_log_objects = "${aws_s3_bucket.load_balancer_logs.arn}/${local.load_balancer_log_prefix}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
}

resource "aws_s3_bucket" "load_balancer_logs" {
  # Bucket names are globally unique, so the account id keeps this from colliding
  # with another account's bucket, the same way the Terraform state bucket is named.
  bucket = "sph-${var.env}-lb-logs-${data.aws_caller_identity.current.account_id}"

  # Logs accumulate outside Terraform's view, and a non-empty bucket blocks destroy.
  force_destroy = var.env == "dev"

  tags = {
    Name = "sph-${var.env}-lb-logs"
  }
}

resource "aws_s3_bucket_public_access_block" "load_balancer_logs" {
  bucket = aws_s3_bucket.load_balancer_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "load_balancer_logs" {
  bucket = aws_s3_bucket.load_balancer_logs.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "load_balancer_logs" {
  bucket = aws_s3_bucket.load_balancer_logs.id

  # Load balancer access logs support SSE-S3 only, a KMS key silently breaks delivery.
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "load_balancer_logs" {
  bucket = aws_s3_bucket.load_balancer_logs.id

  rule {
    id     = "expire-access-logs"
    status = "Enabled"

    filter {}

    expiration {
      days = var.load_balancer_log_retention_days
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_policy" "load_balancer_logs" {
  bucket = aws_s3_bucket.load_balancer_logs.id
  policy = data.aws_iam_policy_document.load_balancer_logs.json

  # A public access block rejects policies it considers public, so settle it first.
  depends_on = [aws_s3_bucket_public_access_block.load_balancer_logs]
}

data "aws_iam_policy_document" "load_balancer_logs" {
  statement {
    sid       = "AllowLogDeliveryServicePrincipal"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = [local.load_balancer_log_objects]

    principals {
      type        = "Service"
      identifiers = ["logdelivery.elasticloadbalancing.amazonaws.com"]
    }

    # Confused deputy guard: only this account's load balancers may write here.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:elasticloadbalancing:${var.region}:${data.aws_caller_identity.current.account_id}:loadbalancer/app/*"]
    }
  }

  statement {
    sid       = "AllowLogDeliveryLegacyElbAccount"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = [local.load_balancer_log_objects]

    principals {
      type        = "AWS"
      identifiers = [data.aws_elb_service_account.current.arn]
    }
  }

  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.load_balancer_logs.arn,
      "${aws_s3_bucket.load_balancer_logs.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}
