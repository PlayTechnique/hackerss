#!/usr/bin/env python3
import atexit
import fnmatch
import glob
import hashlib
import json
import os
import sys
import textwrap
import time

import urllib.request
import logging

import socketserver


def fetch_from_url(api_url: str) -> any:
    logger = logging.getLogger('hackerss')

    num_cache_files = len(fnmatch.filter(os.listdir('.'), '*.cache'))

    if (num_cache_files >= 100):
        cleanup_cache(logger)

    # The URL contains slashes, which messes around with `open()`'s attempt to create a file handle.
    # We could work out a way to parse the string and remove the unpleasant characters, or we can
    # just convert the string to some other format. I picked a hash of the string.
    # The cache is just so I don't end up spamming upstream too much. Poor upstream...
    cache_file = hashlib.md5(f"{api_url}".encode()).hexdigest() + ".cache"
    ten_minutes = 60 * 10
    body = None

    if os.path.isfile(cache_file) and (time.time() - os.path.getmtime(cache_file) < ten_minutes):
        logger.debug(f"Found cached file <{cache_file}> for <{api_url}>")
        with open(cache_file) as cache:
            body = cache.read()
    else:
        logger.debug(f"No cache file <{cache_file}> for <{api_url}>. Creating...")
        contents = urllib.request.urlopen(api_url)

        body = contents.read().decode('utf-8')

        with open(cache_file, "w") as cache:
            cache.write(body)

    json_content = json.loads(body)

    return json_content


def cleanup_cache(logger):
    logger.debug("Cleaning cache files")
    cache_files = glob.glob('*.cache')

    for file in cache_files:
        os.remove(file)


class RssFeedElements:
    ''' Taking the elements from https://www.rssboard.org/rss-profile#elements
    Mandatory header
    This header Must contain one, and only one, channel element
        The channel element is REQUIRED and MUST contain three child elements: description, link and title.
    The channel also MAY contain zero or more item elements. The order of elements within the channel MUST NOT be treated as significant.
    This class is mostly a namespace for a collection of methods; there's no constructor.
'''

    def _channel_header_body(self) -> str:
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

    def _channel_closer(self) -> str:
        return '</channel>\n'

    def _generate_item(self, story) -> str:
        buffer = list()

        # These two attributes aren't always in the data from upstream.
        try:
            # The leading newline makes the output xml much tidier to inspect
            buffer.append(f"\n<item>")
            buffer.append(f"<title>{story.get('title', 'no title provided')}</title>")
            buffer.append(f"<link>{story.get('url', 'no url provided')}</link>")
            # buffer.append(f"<source>https://hacker-news.firebaseio.com/</source>")
            buffer.append(f"</item>")
            return "\n".join(buffer)
        except Exception as e:
            logger.debug(e)
            pass

    def _rss_header(self) -> str:
        return '<rss version="2.0">\n'

    def _rss_closer(self) -> str:
        return '</rss>'

    def generate_rss_feed(self, stories: list):
        ''' Stories is a list of stories from the hacker-news api'''

        buff = list()
        buff.append(self._rss_header())
        buff.append(self._channel_header_body())

        for story in stories:
            buff.append(self._generate_item(story))

        buff.append(self._channel_closer())
        buff.append(self._rss_closer())

        return ''.join(buff)


class RssHandler(socketserver.BaseRequestHandler):
    def handle(self):
        logger.debug("DEBUG: Serving request...")
        # This creates a dependency on the server having an rss_feed method. This is fine for this sort of toy,
        # though I hope nobody who employs me ever looks at this and notices that there's no tests here and I'm just
        # passing attributes around as though they're a real protocol.
        rss_feed = self.server.rss_feed

        http_header = "HTTP/1.1 200"
        http_blank = "\n"

        # magical 3. I _think_ it's tracking the blank lines, but I got it from an error message in curl
        http_content_length_header = f"content-length: {len(rss_content.encode()) + 3}"

        data = []
        data.append(http_header)
        data.append(http_content_length_header)
        data.append(http_blank)  # http standard says to have a blank line after you've sent your metadata i.e. headers
        data.append(rss_feed)
        data.append(http_blank)

        encoded_data = '\n'.join(data).encode()

        self.request.send(encoded_data)


if __name__ == '__main__':

    if "--help" in sys.argv:
        help = textwrap.dedent('''
        Usage: execute this script and the hackernews API will be consumed and an RSS feed generated from it on a TCP socket.
        The TCP socket will be bound to 0.0.0.0
        
        Env Vars:
        RSS_FEED_PORT - defaults to 11223
        STORIES_LIMIT - defaults to 1 story; you probably want this set much higher
        ''')

        print(help)
        sys.exit(0)

    fetch = True

    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger('hackerss')
    logger.setLevel(logging.DEBUG)

    rss_feed_generator = RssFeedElements()

    serving_address = '0.0.0.0'
    serving_port = os.environ.get('RSS_FEED_PORT', '11223')
    serving_port = int(serving_port)

    logger.debug(f"Starting on {serving_address}:{serving_port}")

    hacker_news_newstories_url = "https://hacker-news.firebaseio.com/v0/newstories.json"

    if fetch:
        # Fetching newstories returns a list of page IDs.
        # https://github.com/HackerNews/API#new-top-and-best-stories
        logger.debug(f"fetching from {hacker_news_newstories_url}")
        post_ids = fetch_from_url(hacker_news_newstories_url)
        stories = list()

        # Arbitrary limit for number of stories we're interested in.
        stories_limit = os.environ.get('STORIES_LIMIT', '1')
        stories_limit = int(stories_limit)

        post_ids = post_ids[0:stories_limit]

        for post_id in post_ids:
            # Each item fetched is going to be of "story".
            # We can verify this with the 'type' attribute.
            # https://github.com/HackerNews/API#items
            post_url = f"https://hacker-news.firebaseio.com/v0/item/{post_id}.json"

            logger.debug(f"fetching {post_url}")
            post = fetch_from_url(post_url)

            if post.get('type', False) == "story":
                stories.append(post)
            else:
                logger.debug(f"ERR: {post_id} does not have attribute type story in \n{post}")

    rss_content = rss_feed_generator.generate_rss_feed(stories)
    atexit.register(cleanup_cache, logger)

    # Oof. To hand data in to the handle() method, the "best" solution I could come up with was writing a custom TCP
    # server, and the second best was to hand the data on a custom data attribute.
    with socketserver.TCPServer((serving_address, serving_port), RssHandler) as server:
        server.rss_feed = rss_content
        server.serve_forever()
