#!/usr/bin/env bash
set -euo pipefail

artifactRoot=${1:?artifact root is required}
prefix=${2:?artifact prefix is required}
bucket=${ARTIFACT_BUCKET:?ARTIFACT_BUCKET is required}
endpoint=${ARTIFACT_ENDPOINT:?ARTIFACT_ENDPOINT is required}
scriptDir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
artifactDir="$artifactRoot/$prefix"

bash "$scriptDir/generate-md5sum.sh" "$artifactDir"
aws s3 cp "$artifactDir" "s3://$bucket/$prefix/" --recursive \
  --checksum-algorithm CRC32 --endpoint-url "$endpoint" --region auto --output json
