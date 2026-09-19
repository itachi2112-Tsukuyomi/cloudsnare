"""
VEILGUARD Capture — CloudTrail reader.

We use CloudTrail's Event History (the lookup_events API), which is on by
default in every AWS account, records management events, and costs nothing
to query. Crucially, when someone USES an IAM access key, that call is a
management event — so honeytoken use shows up here without us having to
configure a trail or pay for data events.

Honest caveat: Event History is not instant. Events typically appear within
a few minutes (often ~5-15). VEILGUARD polls, so detection lands within that
window rather than the same second. For a live demo, run the attacker a few
minutes before the reveal, or let the watch loop pick it up.
"""

import boto3
from datetime import datetime, timedelta, timezone


def fetch_recent_events(region, lookback_minutes):
    """
    Return CloudTrail events from the last `lookback_minutes`.

    Each event is a dict with at least: EventName, EventTime, Username,
    and CloudTrailEvent (a JSON string with full detail incl. accessKeyId
    and sourceIPAddress).
    """
    ct = boto3.client("cloudtrail", region_name=region)
    start = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)

    events = []
    paginator = ct.get_paginator("lookup_events")
    for page in paginator.paginate(StartTime=start,
                                   EndTime=datetime.now(timezone.utc)):
        events.extend(page.get("Events", []))
    return events
