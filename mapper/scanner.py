"""
CLOUDSNARE Mapper — scanner.

Each function inspects ONE AWS service and returns a list of
"findings" — resources that are exposed to the internet.

Every finding is a dict with a stable shape so the rest of the
system (diffing, dashboard, intelligence) can rely on it:

    {
        "id":       unique, stable identifier for this resource,
        "service":  which AWS service it belongs to,
        "type":     kind of exposure,
        "resource": human-readable name,
        "detail":   what exactly is exposed,
        "risk":     "HIGH" | "MEDIUM" | "LOW"
    }

Design choice: each scanner is wrapped so that if one service errors
(e.g. a permission is missing), the whole scan doesn't crash — it
records the error and moves on. A partial map is better than none.
"""

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError


# --- helper -----------------------------------------------------------------

def _client(service, region):
    return boto3.client(service, region_name=region)


def _safe(scan_fn, service_name, findings, errors, region):
    """Run one scanner, catching failures so the scan continues."""
    try:
        findings.extend(scan_fn(region))
    except (ClientError, EndpointConnectionError) as e:
        errors.append({"service": service_name, "error": str(e)})
    except Exception as e:  # noqa: BLE001 - never let one service kill the scan
        errors.append({"service": service_name, "error": f"unexpected: {e}"})


# --- S3: public buckets -----------------------------------------------------

def scan_s3(region):
    """Find S3 buckets that are publicly accessible."""
    s3 = _client("s3", region)
    out = []
    buckets = s3.list_buckets().get("Buckets", [])
    for b in buckets:
        name = b["Name"]
        public = False
        reason = []

        # 1. Public Access Block — the master switch. If fully on, it's private.
        try:
            pab = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
            fully_blocked = all([
                pab.get("BlockPublicAcls", False),
                pab.get("IgnorePublicAcls", False),
                pab.get("BlockPublicPolicy", False),
                pab.get("RestrictPublicBuckets", False),
            ])
        except ClientError:
            fully_blocked = False  # no PAB configured = not blocked

        # 2. Policy status — AWS directly tells us if the policy makes it public.
        try:
            status = s3.get_bucket_policy_status(Bucket=name)["PolicyStatus"]
            if status.get("IsPublic"):
                public = True
                reason.append("bucket policy is public")
        except ClientError:
            pass  # no policy = fine

        if public and not fully_blocked:
            out.append({
                "id": f"s3:{name}",
                "service": "S3",
                "type": "public_bucket",
                "resource": name,
                "detail": "; ".join(reason) or "publicly accessible",
                "risk": "HIGH",
            })
    return out


# --- EC2 security groups: ports open to the world ---------------------------

def scan_security_groups(region):
    """Find security group rules open to 0.0.0.0/0 or ::/0."""
    ec2 = _client("ec2", region)
    out = []
    sgs = ec2.describe_security_groups().get("SecurityGroups", [])
    for sg in sgs:
        for perm in sg.get("IpPermissions", []):
            open_v4 = any(r.get("CidrIp") == "0.0.0.0/0"
                          for r in perm.get("IpRanges", []))
            open_v6 = any(r.get("CidrIpv6") == "::/0"
                          for r in perm.get("Ipv6Ranges", []))
            if not (open_v4 or open_v6):
                continue

            proto = perm.get("IpProtocol", "-1")
            if proto == "-1":
                port = "ALL"
            else:
                frm = perm.get("FromPort", "?")
                to = perm.get("ToPort", "?")
                port = f"{frm}" if frm == to else f"{frm}-{to}"

            # SSH (22) and RDP (3389) open to the world are the classic red flags.
            risk = "HIGH" if port in ("22", "3389", "ALL") else "MEDIUM"

            out.append({
                "id": f"sg:{sg['GroupId']}:{proto}:{port}",
                "service": "EC2-SG",
                "type": "open_port",
                "resource": f"{sg['GroupId']} ({sg.get('GroupName','')})",
                "detail": f"port {port}/{proto} open to the internet",
                "risk": risk,
            })
    return out


# --- EC2 instances with public IPs ------------------------------------------

def scan_ec2_instances(region):
    """Find running EC2 instances that have a public IP."""
    ec2 = _client("ec2", region)
    out = []
    reservations = ec2.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running", "pending"]}]
    ).get("Reservations", [])
    for res in reservations:
        for inst in res.get("Instances", []):
            pub_ip = inst.get("PublicIpAddress")
            if not pub_ip:
                continue
            iid = inst["InstanceId"]
            name = next((t["Value"] for t in inst.get("Tags", [])
                         if t["Key"] == "Name"), iid)
            out.append({
                "id": f"ec2:{iid}",
                "service": "EC2",
                "type": "public_instance",
                "resource": f"{name} ({iid})",
                "detail": f"public IP {pub_ip}",
                "risk": "MEDIUM",
            })
    return out


# --- RDS databases that are publicly accessible -----------------------------

def scan_rds(region):
    """Find RDS database instances marked publicly accessible."""
    rds = _client("rds", region)
    out = []
    dbs = rds.describe_db_instances().get("DBInstances", [])
    for db in dbs:
        if db.get("PubliclyAccessible"):
            out.append({
                "id": f"rds:{db['DBInstanceIdentifier']}",
                "service": "RDS",
                "type": "public_database",
                "resource": db["DBInstanceIdentifier"],
                "detail": f"{db.get('Engine','db')} publicly accessible",
                "risk": "HIGH",
            })
    return out


# --- Lambda functions exposed via public function URLs ----------------------

def scan_lambda(region):
    """Find Lambda functions with a public (unauthenticated) function URL."""
    lam = _client("lambda", region)
    out = []
    paginator = lam.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page.get("Functions", []):
            name = fn["FunctionName"]
            try:
                url_cfg = lam.get_function_url_config(FunctionName=name)
                if url_cfg.get("AuthType") == "NONE":
                    out.append({
                        "id": f"lambda:{name}",
                        "service": "Lambda",
                        "type": "public_function_url",
                        "resource": name,
                        "detail": "function URL open with no auth",
                        "risk": "HIGH",
                    })
            except ClientError:
                pass  # no function URL = fine
    return out


# --- Internet-facing load balancers -----------------------------------------

def scan_load_balancers(region):
    """Find internet-facing Elastic Load Balancers (v2)."""
    elb = _client("elbv2", region)
    out = []
    lbs = elb.describe_load_balancers().get("LoadBalancers", [])
    for lb in lbs:
        if lb.get("Scheme") == "internet-facing":
            out.append({
                "id": f"elb:{lb['LoadBalancerName']}",
                "service": "ELB",
                "type": "internet_facing_lb",
                "resource": lb["LoadBalancerName"],
                "detail": f"{lb.get('Type','lb')} exposed to the internet",
                "risk": "LOW",
            })
    return out


# --- orchestrator -----------------------------------------------------------

def scan_all(region):
    """
    Run every scanner and return the full attack surface.

    Returns: (findings, errors)
    """
    findings, errors = [], []
    _safe(scan_s3, "S3", findings, errors, region)
    _safe(scan_security_groups, "EC2-SG", findings, errors, region)
    _safe(scan_ec2_instances, "EC2", findings, errors, region)
    _safe(scan_rds, "RDS", findings, errors, region)
    _safe(scan_lambda, "Lambda", findings, errors, region)
    _safe(scan_load_balancers, "ELB", findings, errors, region)
    # stable ordering makes diffs clean and output predictable
    findings.sort(key=lambda f: f["id"])
    return findings, errors
