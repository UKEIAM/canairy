#! /bin/zsh
set -e
REPO="canairy_downloader"
TAG="latest"


docker run -d --rm \
	-v ${1}:/data \
	-v /app/.venv \
	${REPO}:${TAG} \
	/data
