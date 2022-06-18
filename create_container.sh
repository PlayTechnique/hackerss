#!/bin/bash -e

# Script for creating a container from the hackerss image.
source hackerss.env.sh
docker rm hackerss || true
docker create -p ${RSS_FEED_PORT}:${RSS_FEED_PORT} --expose ${RSS_FEED_PORT} --name hackerss -e STORIES_LIMIT=25 docker.io/jamandbees/hackerss:0.0.4
