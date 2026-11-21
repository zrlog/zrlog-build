#!/usr/bin/env bash
set -e

scriptDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${scriptDir}/build-info.sh"
./mvnw -PnodeBuild clean package assembly:single "$@" -U
