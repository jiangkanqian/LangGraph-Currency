#!/usr/bin/env bash
set -euo pipefail
: "${IMAGE_REPO:?Set registry/project/langgraph-currency}"
GIT_COMMIT="$(git rev-parse HEAD)"
export GIT_COMMIT
IMAGE="${IMAGE_REPO}:${GIT_COMMIT}"
docker build --label "org.opencontainers.image.revision=${GIT_COMMIT}" -t "$IMAGE" .
docker push "$IMAGE"
mkdir -p reports
printf '%s\n' "$IMAGE" > reports/image.txt
