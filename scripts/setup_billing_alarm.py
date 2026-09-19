"""
VEILGUARD — Billing safety alarm.

Run this ONCE right after AWS setup. It creates:
  1. An SNS topic that emails you.
  2. A CloudWatch alarm that triggers if estimated charges
     exceed BILLING_ALARM_THRESHOLD_USD.

This is your seatbelt: honeypot projects can attract real traffic,
and you never want a surprise bill.

NOTE: Billing metrics only exist in us-east-1, regardless of where
your resources live. This script handles that automatically.

Usage:
    python scripts/setup_billing_alarm.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from config import BILLING_ALARM_THRESHOLD_USD, ALERT_EMAIL


def main():
    if ALERT_EMAIL == "YOUR_EMAIL@example.com":
        print("[!] Set ALERT_EMAIL in config.py to your real email first.")
        sys.exit(1)

    # Billing metrics live ONLY in us-east-1.
    cw = boto3.client("cloudwatch", region_name="us-east-1")
    sns = boto3.client("sns", region_name="us-east-1")

    # 1. SNS topic + email subscription
    topic_arn = sns.create_topic(Name="veilguard-billing-alerts")["TopicArn"]
    sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=ALERT_EMAIL)
    print(f"[+] SNS topic ready: {topic_arn}")
    print(f"[!] Check {ALERT_EMAIL} and CONFIRM the subscription email.")

    # 2. CloudWatch billing alarm
    cw.put_metric_alarm(
        AlarmName="veilguard-estimated-charges",
        AlarmDescription="Fires if VEILGUARD-related AWS charges get too high.",
        Namespace="AWS/Billing",
        MetricName="EstimatedCharges",
        Dimensions=[{"Name": "Currency", "Value": "USD"}],
        Statistic="Maximum",
        Period=21600,  # 6 hours
        EvaluationPeriods=1,
        Threshold=float(BILLING_ALARM_THRESHOLD_USD),
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[topic_arn],
    )
    print(f"[+] Billing alarm set at ${BILLING_ALARM_THRESHOLD_USD}. You're protected.")


if __name__ == "__main__":
    main()
