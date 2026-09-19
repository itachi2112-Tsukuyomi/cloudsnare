"""
VEILGUARD Deception Engine — honeytoken generator.

A honeytoken is a FAKE credential that looks real but grants no access.
We plant one inside each decoy bucket (in a file like `credentials.txt`).
It has no legitimate use, so if it is ever seen being used, that is an
unambiguous breach signal.

IMPORTANT: these are NOT real AWS keys. They are random strings shaped
like AWS keys purely so an attacker believes they found something real.
The actual tripwire detection is built in Part 4 (Capture). Here we just
generate and record them, each with a unique token id so we know exactly
WHICH decoy was compromised if one is ever used.
"""

import secrets
import string
import uuid


def _rand(alphabet, n):
    return "".join(secrets.choice(alphabet) for _ in range(n))


def generate_honeytoken(decoy_name):
    """
    Create a fake credential bundle for one decoy.

    Returns a dict with a unique token_id (our tracking handle) and the
    fake key material we'll drop into the decoy.
    """
    token_id = uuid.uuid4().hex[:12]

    # Shaped like an AWS key ("AKIA" + 16 uppercase/digits) but random & fake.
    fake_access_key = "AKIA" + _rand(string.ascii_uppercase + string.digits, 16)
    fake_secret_key = _rand(string.ascii_letters + string.digits + "+/", 40)

    # The text file contents an attacker would find inside the decoy bucket.
    file_body = (
        "# Production credentials - DO NOT SHARE\n"
        f"aws_access_key_id = {fake_access_key}\n"
        f"aws_secret_access_key = {fake_secret_key}\n"
        f"# ref: {token_id}\n"
    )

    return {
        "token_id": token_id,
        "decoy": decoy_name,
        "fake_access_key": fake_access_key,
        "file_name": "credentials.txt",
        "file_body": file_body,
    }
