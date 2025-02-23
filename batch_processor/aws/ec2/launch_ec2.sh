#!/bin/bash

# AWS Config
INSTANCE_ID="i-xxxxxxxxxxxxxxxxx"  # Replace with your EC2 instance ID
AWS_REGION="us-east-1"

# Start EC2 instance
echo "🚀 Triggering EC2 Instance: $INSTANCE_ID"
aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"

echo "✅ EC2 Instance Started."
