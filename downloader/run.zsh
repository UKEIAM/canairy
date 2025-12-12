#! /bin/zsh
set -e
PROJECT_PATH=$(git rev-parse --show-toplevel)
PROJECT_NAME=${PROJECT_PATH:t}
REPO="${PROJECT_NAME}_downloader"
TAG="latest"


docker run -d --rm \
	-v ${1}:/data \
	-v /app/.venv \
	${REPO}:${TAG} \
	/data
