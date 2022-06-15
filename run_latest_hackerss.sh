#!/usr/bin/env bash

set -e

THIS_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd ${THIS_SCRIPT_DIR}

source hackerss.env.sh

CONTAINER_VERSION=${CONTAINER_VERSION:-"latest"}

echo "RSS_FEED_PORT is <${RSS_FEED_PORT}>"
docker run \
--rm \
--expose "${RSS_FEED_PORT}" \
--name hackerss \
-p ${RSS_FEED_PORT}:${RSS_FEED_PORT} \
-t \
jamandbees/hackerss:${CONTAINER_VERSION}
