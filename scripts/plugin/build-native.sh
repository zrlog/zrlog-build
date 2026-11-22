#!/usr/bin/env bash
set -euo pipefail

artifactDir=${1:?artifact directory is required}
shift
scriptDir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Bash 3.2 with nounset rejects expansion of an empty array.
nativeOptions=(-Pnative)
if [[ "${PLUGIN_NATIVE_SKIP_TESTS:-false}" == true ]]; then
  nativeOptions+=(-DskipNativeTests)
fi

java -version
./mvnw "$@" clean
bash "$scriptDir/build-info.sh" "$artifactDir"
./mvnw "$@" -PnodeBuild package
./mvnw "$@" "${nativeOptions[@]}" -Dagent exec:exec@java-agent -U
./mvnw "$@" "${nativeOptions[@]}" package

properties=target/generated-resources/plugin-info/plugin.properties
binaryName=$(sed -n 's/^shortName=//p' "$properties" | head -n 1 | tr -d '\r')
version=$(sed -n 's/^version=//p' "$properties" | head -n 1 | tr -d '\r')
bash "$scriptDir/stage-native.sh" "$binaryName" "$artifactDir" "$version"
