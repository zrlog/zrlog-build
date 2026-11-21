#!/usr/bin/env bash
set -euo pipefail

if ! version=$(./mvnw -B -q help:evaluate -Dexpression=project.version -DforceStdout); then
  printf '%s\n' "$version" >&2
  exit 1
fi
: "${version:?Unable to determine the Maven project version}"
buildNumber="$(git rev-list --all --count)"
buildId="$(git rev-parse --short=7 HEAD)"

printf '%s\n' \
  'server.port=9090' \
  "version=${version%-SNAPSHOT}" \
  'pluginJvmArgs=-Dfile.encoding=UTF-8 -Xms4m -Xmx32m' \
  "buildId=${buildId}" \
  "buildTime=${Date:-}" \
  "buildNumber=${buildNumber}" > src/main/resources/conf.properties
