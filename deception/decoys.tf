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

# ============ Decoy 1: cloudsnare-prod-db-backup-65443114 ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "decoy_1" {
  bucket        = "cloudsnare-prod-db-backup-65443114"
  force_destroy = true
  tags = {
    Name      = "cloudsnare-prod-db-backup-65443114"
    cloudsnare = "decoy"
    token_id  = "2e3b7de822de"
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
  name          = "cloudsnare-prod-db-backup-65443114"
  force_destroy = true
  tags = {
    cloudsnare = "honeytoken"
    token_id  = "2e3b7de822de"
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
    # ref: 2e3b7de822de
  EOT
}

# --- Output the real key id so CLOUDSNARE can watch CloudTrail for it ---
output "honeytoken_1" {
  value = {
    bucket        = "cloudsnare-prod-db-backup-65443114"
    token_id      = "2e3b7de822de"
    access_key_id = aws_iam_access_key.decoy_1.id
  }
}


# ============ Decoy 2: cloudsnare-admin-credentials-cb497859 ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "decoy_2" {
  bucket        = "cloudsnare-admin-credentials-cb497859"
  force_destroy = true
  tags = {
    Name      = "cloudsnare-admin-credentials-cb497859"
    cloudsnare = "decoy"
    token_id  = "28bcebe15d71"
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
  name          = "cloudsnare-admin-credentials-cb497859"
  force_destroy = true
  tags = {
    cloudsnare = "honeytoken"
    token_id  = "28bcebe15d71"
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
    # ref: 28bcebe15d71
  EOT
}

# --- Output the real key id so CLOUDSNARE can watch CloudTrail for it ---
output "honeytoken_2" {
  value = {
    bucket        = "cloudsnare-admin-credentials-cb497859"
    token_id      = "28bcebe15d71"
    access_key_id = aws_iam_access_key.decoy_2.id
  }
}


# ============ Decoy 3: cloudsnare-internal-api-keys-21a27ce4 ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "decoy_3" {
  bucket        = "cloudsnare-internal-api-keys-21a27ce4"
  force_destroy = true
  tags = {
    Name      = "cloudsnare-internal-api-keys-21a27ce4"
    cloudsnare = "decoy"
    token_id  = "9eb3adc893bd"
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
  name          = "cloudsnare-internal-api-keys-21a27ce4"
  force_destroy = true
  tags = {
    cloudsnare = "honeytoken"
    token_id  = "9eb3adc893bd"
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
    # ref: 9eb3adc893bd
  EOT
}

# --- Output the real key id so CLOUDSNARE can watch CloudTrail for it ---
output "honeytoken_3" {
  value = {
    bucket        = "cloudsnare-internal-api-keys-21a27ce4"
    token_id      = "9eb3adc893bd"
    access_key_id = aws_iam_access_key.decoy_3.id
  }
}
