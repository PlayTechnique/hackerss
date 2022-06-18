## What is Hackerss?
I like my rss feed reader, and I wanted to learn about writing an RSS feed, so I wrote a little python script that 
scrapes the [hacker-news API](https://github.com/HackerNews/API) and generates an RSS feed from it.

It can be run as a standalone script (it only uses standard library calls, so no dependencies) with Python3, or as a container. There's a docker image uploaded to docker hub, so you can run
the container directly. See the run_latest_hackerss.sh script for details; note this script is mostly there to help me 
as I was developing this thing, so be kind to it.

## Developing Hackerss
I tried to keep everything in one file, as this is a small application.
The script runs standalone perfectly well, so just run `main.py` if you want to see how it runs; if you want to run it 
kubernetes or something else, there's a container on docker hub in `docker.io/jamandbees/hackerss:<tag>`.


## Installing and Running Hackerss as a Systemd Service

1. create the hackerss container on the system you would like to run it on. You can either
run check create_container.sh for the command I use.
2. Install the hackerss.service unit file into the directory returned by `pkg-config systemd --variable=systemdsystemunitdir`
, or a different directory if that's how your OS is configured.
