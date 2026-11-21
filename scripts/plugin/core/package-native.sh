#!/usr/bin/env bash
set -e

outputDir=${1:?native output directory is required}
shift
scriptDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

nativeMavenArgs=("$@" "-Dsqlite-scope=provided")
nativeProfiles="native"
if [[ "${ZRLOG_PACKAGE_TYPE:-native}" != "faas" ]]; then
  nativeProfiles="${nativeProfiles},native-sqlite"
fi

agentMavenArgs=()
for arg in "${nativeMavenArgs[@]}"; do
  if [[ "${arg}" != "-Dmysql-scope=provided" ]]; then
    agentMavenArgs+=("${arg}")
  fi
done

java -version
bash "${scriptDir}/build-info.sh"
./mvnw "${nativeMavenArgs[@]}" -U -PnodeBuild clean package
./mvnw "${agentMavenArgs[@]}" -P"${nativeProfiles}" -Dagent exec:exec@java-agent -U
./mvnw "${nativeMavenArgs[@]}" -P"${nativeProfiles}" -DskipNativeTests package

version="$(sed -n 's/^version=//p' src/main/resources/conf.properties)"
exec bash "${scriptDir}/../stage-native.sh" plugin-core "${outputDir}" "${version}"
