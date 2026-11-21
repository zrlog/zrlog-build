#!/usr/bin/env bash
set -euo pipefail

artifactDir=${1:?artifact directory is required}
shift
scriptDir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

mkdir -p -- "$artifactDir"
bash -e ./mvnw "$@" clean
bash "$scriptDir/build-info.sh" "$artifactDir"
bash -e ./mvnw "$@" -PnodeBuild package assembly:single "-DoutputDirectory=$artifactDir"
