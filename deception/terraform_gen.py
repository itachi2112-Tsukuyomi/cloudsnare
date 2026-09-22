"""
CLOUDSNARE Deception Engine — Terraform generator.

We describe decoys as Infrastructure as Code (Terraform): reproducible,
reviewable, and removable with a single `terraform destroy`.

Each decoy is:
  - a public S3 bucket (looks like a misconfiguration)
  - a REAL but powerless IAM user (deny-all policy) + access key
    -> this is the honeytoken. It can't touch anything, but AWS logs
       any attempt to USE it, giving a high-confidence breach signal.
  - a credentials.txt object inside the bucket containing that real key

Why a real key? AWS only logs the use of keys that actually exist in the
account. A random fake string would be invisible to CloudTrail. A real
deny-all key is harmless yet fully detectable — the canary-token pattern.
"""

import os


def _bucket_block(idx, bucket_name, token_id):
    b = f"decoy_{idx}"
    return f'''
# ============ Decoy {idx}: {bucket_name} ============

# --- The public bucket (the visible bait) ---
resource "aws_s3_bucket" "{b}" {{
  bucket        = "{bucket_name}"
  force_destroy = true
  tags = {{
    Name      = "{bucket_name}"
    cloudsnare = "decoy"
    token_id  = "{token_id}"
  }}
}}

resource "aws_s3_bucket_public_access_block" "{b}" {{
  bucket                  = aws_s3_bucket.{b}.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}}

resource "aws_s3_bucket_policy" "{b}" {{
  bucket     = aws_s3_bucket.{b}.id
  depends_on = [aws_s3_bucket_public_access_block.{b}]
  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${{aws_s3_bucket.{b}.arn}}/*"
    }}]
  }})
}}

# --- The honeytoken: a REAL but powerless IAM user + key ---
resource "aws_iam_user" "{b}" {{
  name          = "{bucket_name}"
  force_destroy = true
  tags = {{
    cloudsnare = "honeytoken"
    token_id  = "{token_id}"
  }}
}}

resource "aws_iam_user_policy" "{b}" {{
  name = "deny-all"
  user = aws_iam_user.{b}.name
  policy = jsonencode({{
    Version   = "2012-10-17"
    Statement = [{{ Effect = "Deny", Action = "*", Resource = "*" }}]
  }})
}}

resource "aws_iam_access_key" "{b}" {{
  user = aws_iam_user.{b}.name
}}

# --- The planted credentials file (contains the real deny-all key) ---
resource "aws_s3_object" "{b}_token" {{
  bucket  = aws_s3_bucket.{b}.id
  key     = "credentials.txt"
  content = <<-EOT
    # Production credentials - DO NOT SHARE
    aws_access_key_id = ${{aws_iam_access_key.{b}.id}}
    aws_secret_access_key = ${{aws_iam_access_key.{b}.secret}}
    # ref: {token_id}
  EOT
}}

# --- Output the real key id so CLOUDSNARE can watch CloudTrail for it ---
output "honeytoken_{idx}" {{
  value = {{
    bucket        = "{bucket_name}"
    token_id      = "{token_id}"
    access_key_id = aws_iam_access_key.{b}.id
  }}
}}
'''


def write_terraform(deception_dir, region, decoys):
    """
    decoys: list of {"bucket": name, "token": {"token_id": ...}}
    Returns path to decoys.tf.
    """
    os.makedirs(deception_dir, exist_ok=True)

    header = f'''terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{region}"
}}
'''

    blocks = [
        _bucket_block(i + 1, d["bucket"], d["token"]["token_id"])
        for i, d in enumerate(decoys)
    ]

    path = os.path.join(deception_dir, "decoys.tf")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(blocks))
    return path
