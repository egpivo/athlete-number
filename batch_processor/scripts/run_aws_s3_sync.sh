#!/bin/bash

aws s3 sync s3://pc8tw.public/WEBDATA/778592_3169/ s3://athlete-number-detection/images/2025-02-26/778592_3169 --delete --region us-east-1 >> logs/778592_3169.log 2>&1 &
aws s3 sync s3://pc8tw.public/WEBDATA/778592_3456/ s3://athlete-number-detection/images/2025-02-26/778592_3456 --delete --region us-east-1 >> logs/778592_3456.log 2>&1 &
aws s3 sync s3://pc8tw.public/WEBDATA/778592_3952/ s3://athlete-number-detection/images/2025-02-26/778592_3952 --delete --region us-east-1 >> logs/778592_3952.log 2>&1 &
aws s3 sync s3://pc8tw.public/WEBDATA/778592_3286/ s3://athlete-number-detection/images/2025-02-26/778592_3286 --delete --region us-east-1 >> logs/778592_3286.log 2>&1 &
wait
