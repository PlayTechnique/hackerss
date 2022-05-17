#!/usr/bin/env python3

import json
import sys

import urllib.request
import logging

import socketserver
import http.server


def fetch_from_url(api_url) -> any:
    contents = urllib.request.urlopen(api_url)

    body = contents.read()
    ids = body.decode('utf-8')
    json_content = json.loads(ids)

    return json_content


class RssFeedElements:
    ''' Taking the elements from https://www.rssboard.org/rss-profile#elements
    Mandatory header
    This header Must contain one, and only one, channel element
        The channel element is REQUIRED and MUST contain three child elements: description, link and title.
    The channel also MAY contain zero or more item elements. The order of elements within the channel MUST NOT be treated as significant.
'''

    @classmethod
    def _channel_header_body(cls) -> str:
        # The description element holds character data that provides a human-readable characterization or summary of the feed (REQUIRED).
        description = "Gwyn's Rss Channel for Hacker-News"
        # The link element identifies the URL of the web site associated with the feed (REQUIRED).
        link = "https://news.ycombinator.com"
        # The title element holds character data that provides the name of the feed (REQUIRED).
        title = description

        channel = f'''<channel>
        <description>{description}</description>
        <link>{link}</link>
        <title>{title}</title>
        '''

        return channel

    @classmethod
    def _channel_closer(cls) -> str:
        return '</channel>\n'

    @classmethod
    def _rss_header(cls) -> str:
        return '<rss version="2.0">\n'

    @classmethod
    def rss_feed(cls) -> str:
        buff = list()
        buff.append(cls._rss_header())
        buff.append(cls._channel_header_body())
        buff.append(cls._channel_closer())

        return ''.join(buff)


class RssHandler(socketserver.BaseRequestHandler):
    def handle(self):
        '''check out this unenumerated dependency 😎'''

        rss_content = RssFeedElements.rss_feed()

        http_header = "HTTP/1.1 200"
        http_blank = "\n"

        # magical 3. I _think_ it's tracking the blank lines, but I got it from an error message in curl
        http_content_length_header = f"content-length: {len(rss_content.encode()) + 3}"

        data = []
        data.append(http_header)
        data.append(http_content_length_header)
        data.append(http_blank) #http standard says to have a blank line after you've sent your metadata i.e. headers
        data.append(rss_feed)
        data.append(http_blank)

        encoded_data = '\n'.join(data).encode()

        self.request.send(encoded_data)


if __name__ == '__main__':
    fetch = False

    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger('hackerss')
    rss_feed = RssFeedElements.rss_feed()

    serving_address = '127.0.0.1'
    serving_port = 8943

    logger.setLevel(logging.DEBUG)

    hacker_news_newstories_url = "https://hacker-news.firebaseio.com/v0/newstories.json"

    if fetch:
        # Fetching newstories returns a list of page IDs.
        # https://github.com/HackerNews/API#new-top-and-best-stories
        logger.debug(f"fetching from {hacker_news_newstories_url}")
        post_ids = fetch_from_url(hacker_news_newstories_url)
        stories = list()

        # Arbitrary limit for number of stories we're interested in.
        limit = 20

        post_ids = post_ids[0:limit]

        for post_id in post_ids:
            # Each item fetched is going to be of "story".
            # We can verify this with the 'type' attribute.
            # https://github.com/HackerNews/API#items
            post_url = f"https://hacker-news.firebaseio.com/v0/item/{post_id}.json"

            logger.debug(f"fetching {post_url}")
            post = fetch_from_url(post_url)

            if post["type"] == "story":
                stories.append(post)
            else:
                sys.stderr(f"ERR: {post_id} does not have attribute type story in \n{post}")

    with socketserver.TCPServer((serving_address, serving_port), RssHandler) as httpd:
        logger.debug(f"serving on {serving_address}:{serving_port}")
        httpd.serve_forever()
