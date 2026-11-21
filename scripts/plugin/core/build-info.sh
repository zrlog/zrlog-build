#!/usr/bin/env bash
set -euo pipefail

version=$(printf 'VER\t${project.version}' | ./mvnw help:evaluate | grep '^VER' | cut -f2)
buildNumber="$(git rev-list --all --count)"
buildId="$(git rev-parse --short=7 HEAD)"

printf '%s\n' \
  'server.port=9090' \
  "version=${version%-SNAPSHOT}" \
  'pluginJvmArgs=-Dfile.encoding=UTF-8 -Xms4m -Xmx32m' \
  "buildId=${buildId}" \
  "buildTime=${Date:-}" \
  "buildNumber=${buildNumber}" > src/main/resources/conf.properties
