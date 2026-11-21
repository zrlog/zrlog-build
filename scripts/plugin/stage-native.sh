#!/usr/bin/env bash
set -euo pipefail

binaryName=${1:?binary name is required}
artifactDir=${2:?artifact directory is required}
version=${3:?artifact version is required}

sourceFile="target/$binaryName"
extension=bin
if [[ -f "$sourceFile.exe" ]]; then
  sourceFile="$sourceFile.exe"
  architecture="Windows-$(uname -m)"
  extension=exe
else
  operatingSystem=$(uname -s)
  if [[ "$operatingSystem" == Linux ]]; then
    architecture="Linux-$(dpkg --print-architecture)"
  else
    architecture="$operatingSystem-$(uname -m)"
  fi
fi

mkdir -p -- "$artifactDir"
artifactFile="$artifactDir/$binaryName-$architecture.$extension"
mv -- "$sourceFile" "$artifactFile"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    printf 'artifact_file=%s\n' "$artifactFile"
    printf 'artifact_name=%s\n' "$binaryName"
    printf 'artifact_version=%s\n' "$version"
    printf 'artifact_architecture=%s\n' "$architecture"
  } >> "$GITHUB_OUTPUT"
fi
