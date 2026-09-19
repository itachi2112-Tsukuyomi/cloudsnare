terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

# ============ Decoy 1: veilguard-prod-db-backup-8f70aa57 ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "decoy_1" {
  bucket        = "veilguard-prod-db-backup-8f70aa57"
  force_destroy = true
  tags = {
    Name      = "veilguard-prod-db-backup-8f70aa57"
    veilguard = "decoy"
    token_id  = "9545eeb75411"
  }
}

resource "aws_s3_bucket_public_access_block" "decoy_1" {
  bucket                  = aws_s3_bucket.decoy_1.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "decoy_1" {
  bucket     = aws_s3_bucket.decoy_1.id
  depends_on = [aws_s3_bucket_public_access_block.decoy_1]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.decoy_1.arn}/*"
    }]
  })
}

# --- The honeytoken: a REAL but powerless IAM user + key ---
resource "aws_iam_user" "decoy_1" {
  name          = "veilguard-prod-db-backup-8f70aa57"
  force_destroy = true
  tags = {
    veilguard = "honeytoken"
    token_id  = "9545eeb75411"
  }
}

resource "aws_iam_user_policy" "decoy_1" {
  name = "deny-all"
  user = aws_iam_user.decoy_1.name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Deny", Action = "*", Resource = "*" }]
  })
}

resource "aws_iam_access_key" "decoy_1" {
  user = aws_iam_user.decoy_1.name
}

# --- The planted credentials file (contains the real deny-all key) ---
resource "aws_s3_object" "decoy_1_token" {
  bucket  = aws_s3_bucket.decoy_1.id
  key     = "credentials.txt"
  content = <<-EOT
    # Production credentials - DO NOT SHARE
    aws_access_key_id = ${aws_iam_access_key.decoy_1.id}
    aws_secret_access_key = ${aws_iam_access_key.decoy_1.secret}
    # ref: 9545eeb75411
  EOT
}

# --- Output the real key id so VEILGUARD can watch CloudTrail for it ---
output "honeytoken_1" {
  value = {
    bucket        = "veilguard-prod-db-backup-8f70aa57"
    token_id      = "9545eeb75411"
    access_key_id = aws_iam_access_key.decoy_1.id
  }
}


# ============ Decoy 2: veilguard-admin-credentials-35002bf6 ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "decoy_2" {
  bucket        = "veilguard-admin-credentials-35002bf6"
  force_destroy = true
  tags = {
    Name      = "veilguard-admin-credentials-35002bf6"
    veilguard = "decoy"
    token_id  = "4b4a9d1e37ce"
  }
}

resource "aws_s3_bucket_public_access_block" "decoy_2" {
  bucket                  = aws_s3_bucket.decoy_2.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "decoy_2" {
  bucket     = aws_s3_bucket.decoy_2.id
  depends_on = [aws_s3_bucket_public_access_block.decoy_2]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.decoy_2.arn}/*"
    }]
  })
}

# --- The honeytoken: a REAL but powerless IAM user + key ---
resource "aws_iam_user" "decoy_2" {
  name          = "veilguard-admin-credentials-35002bf6"
  force_destroy = true
  tags = {
    veilguard = "honeytoken"
    token_id  = "4b4a9d1e37ce"
  }
}

resource "aws_iam_user_policy" "decoy_2" {
  name = "deny-all"
  user = aws_iam_user.decoy_2.name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Deny", Action = "*", Resource = "*" }]
  })
}

resource "aws_iam_access_key" "decoy_2" {
  user = aws_iam_user.decoy_2.name
}

# --- The planted credentials file (contains the real deny-all key) ---
resource "aws_s3_object" "decoy_2_token" {
  bucket  = aws_s3_bucket.decoy_2.id
  key     = "credentials.txt"
  content = <<-EOT
    # Production credentials - DO NOT SHARE
    aws_access_key_id = ${aws_iam_access_key.decoy_2.id}
    aws_secret_access_key = ${aws_iam_access_key.decoy_2.secret}
    # ref: 4b4a9d1e37ce
  EOT
}

# --- Output the real key id so VEILGUARD can watch CloudTrail for it ---
output "honeytoken_2" {
  value = {
    bucket        = "veilguard-admin-credentials-35002bf6"
    token_id      = "4b4a9d1e37ce"
    access_key_id = aws_iam_access_key.decoy_2.id
  }
}


# ============ Decoy 3: veilguard-internal-api-keys-1380fada ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "decoy_3" {
  bucket        = "veilguard-internal-api-keys-1380fada"
  force_destroy = true
  tags = {
    Name      = "veilguard-internal-api-keys-1380fada"
    veilguard = "decoy"
    token_id  = "6eea4612a0c7"
  }
}

resource "aws_s3_bucket_public_access_block" "decoy_3" {
  bucket                  = aws_s3_bucket.decoy_3.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "decoy_3" {
  bucket     = aws_s3_bucket.decoy_3.id
  depends_on = [aws_s3_bucket_public_access_block.decoy_3]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.decoy_3.arn}/*"
    }]
  })
}

# --- The honeytoken: a REAL but powerless IAM user + key ---
resource "aws_iam_user" "decoy_3" {
  name          = "veilguard-internal-api-keys-1380fada"
  force_destroy = true
  tags = {
    veilguard = "honeytoken"
    token_id  = "6eea4612a0c7"
  }
}

resource "aws_iam_user_policy" "decoy_3" {
  name = "deny-all"
  user = aws_iam_user.decoy_3.name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Deny", Action = "*", Resource = "*" }]
  })
}

resource "aws_iam_access_key" "decoy_3" {
  user = aws_iam_user.decoy_3.name
}

# --- The planted credentials file (contains the real deny-all key) ---
resource "aws_s3_object" "decoy_3_token" {
  bucket  = aws_s3_bucket.decoy_3.id
  key     = "credentials.txt"
  content = <<-EOT
    # Production credentials - DO NOT SHARE
    aws_access_key_id = ${aws_iam_access_key.decoy_3.id}
    aws_secret_access_key = ${aws_iam_access_key.decoy_3.secret}
    # ref: 6eea4612a0c7
  EOT
}

# --- Output the real key id so VEILGUARD can watch CloudTrail for it ---
output "honeytoken_3" {
  value = {
    bucket        = "veilguard-internal-api-keys-1380fada"
    token_id      = "6eea4612a0c7"
    access_key_id = aws_iam_access_key.decoy_3.id
  }
}
