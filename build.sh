#!/bin/bash -el

THIS_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${THIS_SCRIPT_DIR}"

source hackerss.env.sh

function help() {
	echo "${THIS_SCRIPT} --help - display this message"
	echo "Builds a docker build command and executes it. Has some environment variables for controlling options."
	echo "These are consumed either from 'hackerss.env.sh' in this repo, or from your environment."
	echo "Here's what you can set and the defaults:"
	echo '  IMAGE_TAG=${IMAGE_TAG:-"dev"} - the image tag'
  echo '  PUSH=${PUSH:-"false"} - controls whether to push the built image to docker hub. Set to the string "true" to push.'
  echo '  RSS_FEED_PORT=${RSS_FEED_PORT:-"8943"} - the port for python to bind to.'
  echo '  STORIES_LIMIT=${STORIES_LIMIT:-"25"} - The number of stories to fetch from upstream'
}


if [[ "$1" = "--help" ]]; then
  help
  exit 0
fi

IMAGE_TAG=${IMAGE_TAG:-"dev"}
PUSH=${PUSH:-"false"}
RSS_FEED_PORT=${RSS_FEED_PORT:-"8943"}
STORIES_LIMIT=${STORIES_LIMIT:-"25"}

docker build --tag jamandbees/hackerss:${IMAGE_TAG} \
--build-arg rss_feed_port=${RSS_FEED_PORT} --build-arg stories_limit=${STORIES_LIMIT} \
.

if [[ "${PUSH}" = "true" ]]; then
  docker image push jamandbees/hackerss:${IMAGE_TAG}
fi
