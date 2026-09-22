"""
CLOUDSNARE Agent — the tool layer.

These are the ONLY actions the agent can perform. The LLM never touches AWS;
it can only request one of these pre-written functions. Each "create" action
is secure by construction — it is not possible to call it in a way that
produces an insecure resource.

Split into:
  READ tools  (list_*)   - safe, no confirmation needed
  WRITE tools (create_*) - change state, always go through the confirmation gate

Adding a dangerous capability (make-public, delete, open-port) would mean
writing a function for it here. We simply don't - so the agent cannot do it.
"""

import boto3
from botocore.exceptions import ClientError


# ---------------------------------------------------------------- READ tools

def list_buckets(region, **_):
    s3 = boto3.client("s3", region_name=region)
    names = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    return {"ok": True, "buckets": names,
            "summary": f"{len(names)} bucket(s): " + (", ".join(names) or "none")}


def list_instances(region, **_):
    ec2 = boto3.client("ec2", region_name=region)
    out = []
    for res in ec2.describe_instances().get("Reservations", []):
        for inst in res.get("Instances", []):
            state = inst.get("State", {}).get("Name")
            if state in ("terminated", "shutting-down"):
                continue
            name = next((t["Value"] for t in inst.get("Tags", [])
                         if t["Key"] == "Name"), inst["InstanceId"])
            out.append({"id": inst["InstanceId"], "name": name,
                        "type": inst.get("InstanceType"), "state": state,
                        "public_ip": inst.get("PublicIpAddress")})
    return {"ok": True, "instances": out,
            "summary": f"{len(out)} running/stopped instance(s)."}


# --------------------------------------------------------------- WRITE tools

def create_secure_bucket(region, name, **_):
    """
    Create an S3 bucket that is PRIVATE, ENCRYPTED, and VERSIONED by default.
    There is no parameter to make it public - security is not optional here.
    """
    if str(name).startswith("cloudsnare"):
        return {"ok": False, "error": "Name can't start with 'cloudsnare' (reserved for decoys)."}

    s3 = boto3.client("s3", region_name=region)
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=name)
        else:
            s3.create_bucket(Bucket=name,
                             CreateBucketConfiguration={"LocationConstraint": region})

        # secure-by-default settings, always applied:
        s3.put_public_access_block(
            Bucket=name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
        s3.put_bucket_encryption(
            Bucket=name,
            ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault":
                           {"SSEAlgorithm": "AES256"}}]})
        s3.put_bucket_versioning(
            Bucket=name, VersioningConfiguration={"Status": "Enabled"})

        return {"ok": True,
                "summary": f"Bucket '{name}' created - private, encrypted (AES256), "
                           f"versioned, public access fully blocked."}
    except ClientError as e:
        return {"ok": False, "error": str(e)}


def create_secure_ec2(region, name, instance_type="t2.micro", **_):
    """
    Launch an EC2 instance with a LOCKED-DOWN security group (no inbound from
    the internet) and no public IP. Defaults to Free-Tier t2.micro.
    """
    ec2 = boto3.client("ec2", region_name=region)
    try:
        # 1. A dedicated, locked-down security group: NO inbound rules at all.
        sg_name = f"cloudsnare-agent-sg-{name}"
        try:
            sg = ec2.create_security_group(
                GroupName=sg_name,
                Description="CLOUDSNARE agent - locked down, no internet inbound")
            sg_id = sg["GroupId"]
        except ClientError as e:
            if "InvalidGroup.Duplicate" in str(e):
                sg_id = ec2.describe_security_groups(
                    GroupNames=[sg_name])["SecurityGroups"][0]["GroupId"]
            else:
                raise
        # NOTE: we deliberately add NO ingress rules -> nothing open to 0.0.0.0/0.

        # 2. Latest Amazon Linux 2023 AMI via SSM public parameter.
        ssm = boto3.client("ssm", region_name=region)
        ami = ssm.get_parameter(
            Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
        )["Parameter"]["Value"]

        # 3. Launch: no public IP, smallest safe type, tagged.
        r = ec2.run_instances(
            ImageId=ami, InstanceType=instance_type,
            MinCount=1, MaxCount=1,
            NetworkInterfaces=[{
                "DeviceIndex": 0, "AssociatePublicIpAddress": False,
                "Groups": [sg_id]}],
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": name},
                         {"Key": "created_by", "Value": "cloudsnare-agent"}]}])
        iid = r["Instances"][0]["InstanceId"]
        return {"ok": True,
                "summary": f"Instance '{name}' ({iid}, {instance_type}) launched with a "
                           f"locked-down security group (no internet inbound) and no "
                           f"public IP. Remember to terminate it when done - it costs money."}
    except ClientError as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------------------------------- registry

# auto=False means "read-only, safe, no confirmation".
# auto=True  means "changes state -> must pass the confirmation gate".
TOOLS = {
    "list_buckets":         {"fn": list_buckets,        "writes": False},
    "list_instances":       {"fn": list_instances,      "writes": False},
    "create_secure_bucket": {"fn": create_secure_bucket,"writes": True},
    "create_secure_ec2":    {"fn": create_secure_ec2,   "writes": True},
}
