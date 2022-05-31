FROM python:3.10.4-slim-bullseye as base
ARG rss_feed_port

ENV RSS_FEED_PORT=$rss_feed_port
EXPOSE $rss_feed_port
COPY main.py /app/
ENTRYPOINT python3 /app/main.py
