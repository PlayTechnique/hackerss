#!/usr/bin/env bash
set -ex

THIS_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${THIS_SCRIPT_DIR}"

source hackerss.env.sh

PUSH=false
RSS_FEED_PORT=${RSS_FEED_PORT:-"8943"}
STORIES_LIMIT=${STORIES_LIMIT:-"25"}

docker build --no-cache --tag jamandbees/hackerss:latest \
--build-arg rss_feed_port=${RSS_FEED_PORT} --build-arg stories_limit=${STORIES_LIMIT} \
.

if [[ "${PUSH}" = "true" ]]; then
  docker image push jamandbees/hackerss:latest
fi
