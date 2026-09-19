"""
VEILGUARD Remediation — the fix library.

Each exposure type maps to a SAFE, well-defined remediation. These are the
only actions VEILGUARD is ever allowed to take on real resources, and only
after a human approves. Each entry has:

  recommend(finding) -> human-readable description of the proposed fix
  apply(finding, region) -> performs the fix, returns a result string

Design rules:
  - Only reversible, low-blast-radius fixes are auto-applied (S3, SG, Lambda).
  - Disruptive changes (RDS, EC2 public IP, ELB) are RECOMMEND-ONLY: we
    describe the fix but never apply it automatically, because it could
    interrupt a live service. The human does those manually.
  - Decoys are never touched (filtered out before we ever get here).
"""

import boto3


# ---- S3: public bucket -> enable public access block -----------------------

def _s3_recommend(f):
    return (f"Enable S3 Block Public Access on bucket '{f['resource']}' "
            f"(overrides public policies/ACLs; reversible).")


def _s3_apply(f, region):
    name = f["resource"]
    s3 = boto3.client("s3", region_name=region)
    s3.put_public_access_block(
        Bucket=name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    return f"Block Public Access enabled on '{name}'."


# ---- EC2 security group: open port -> revoke the 0.0.0.0/0 rule ------------

def _sg_recommend(f):
    return (f"Revoke the internet-open ingress rule on {f['resource']} "
            f"({f['detail']}).")


def _sg_apply(f, region):
    # finding id looks like: sg:{GroupId}:{proto}:{port}
    parts = f["id"].split(":")
    group_id = parts[1]
    ec2 = boto3.client("ec2", region_name=region)

    sgs = ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"]
    revoked = 0
    for sg in sgs:
        for perm in sg.get("IpPermissions", []):
            open_ranges = [r for r in perm.get("IpRanges", [])
                           if r.get("CidrIp") == "0.0.0.0/0"]
            if not open_ranges:
                continue
            revoke_perm = {k: perm[k] for k in ("IpProtocol", "FromPort", "ToPort")
                           if k in perm}
            revoke_perm["IpRanges"] = [{"CidrIp": "0.0.0.0/0"}]
            ec2.revoke_security_group_ingress(
                GroupId=group_id, IpPermissions=[revoke_perm])
            revoked += 1
    return f"Revoked {revoked} internet-open rule(s) on {group_id}."


# ---- Lambda: public function URL -> delete the URL config -------------------

def _lambda_recommend(f):
    return (f"Remove the unauthenticated function URL on Lambda "
            f"'{f['resource']}'.")


def _lambda_apply(f, region):
    name = f["resource"]
    lam = boto3.client("lambda", region_name=region)
    lam.delete_function_url_config(FunctionName=name)
    return f"Public function URL removed from '{name}'."


# ---- Recommend-only (too disruptive to auto-apply) -------------------------

def _rds_recommend(f):
    return (f"[MANUAL] Set RDS '{f['resource']}' to PubliclyAccessible=false "
            f"during a maintenance window (may briefly interrupt connections).")


def _instance_recommend(f):
    return (f"[MANUAL] Review public exposure of EC2 '{f['resource']}'. "
            f"Consider moving behind a NAT/ALB instead of a public IP.")


def _elb_recommend(f):
    return (f"[MANUAL] Review internet-facing load balancer '{f['resource']}'. "
            f"Confirm it is intended to be public.")


# ---- Registry --------------------------------------------------------------
# auto=True means VEILGUARD can apply it (after approval).
# auto=False means recommend-only; the human must do it manually.

REGISTRY = {
    "public_bucket":       {"recommend": _s3_recommend,     "apply": _s3_apply,     "auto": True},
    "open_port":           {"recommend": _sg_recommend,     "apply": _sg_apply,     "auto": True},
    "public_function_url": {"recommend": _lambda_recommend, "apply": _lambda_apply, "auto": True},
    "public_database":     {"recommend": _rds_recommend,    "apply": None,          "auto": False},
    "public_instance":     {"recommend": _instance_recommend,"apply": None,         "auto": False},
    "internet_facing_lb":  {"recommend": _elb_recommend,    "apply": None,          "auto": False},
}


def handler_for(finding_type):
    return REGISTRY.get(finding_type)
