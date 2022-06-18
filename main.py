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


def fetch_from_url(api_url: str, cache_results: bool = True) -> any:
    '''Fetches the contents of a url, and caches the result temporarily to reduce load.

    api_url: string, the url to fetch data from.
    cache_results: boolean, whether to cache the results of this fetch. This is needed because we create the cache based
    upon the URL that we are fetching from. If the URL is unique then caching that result is useful; if the URL is not
    unique (such as with the "https://hacker-news.firebaseio.com/v0/newstories.json" api endpoint) then we'd only ever
    update the content when the cache gets busted.
    '''
    logger = logging.getLogger('hackerss')

    num_cache_files = len(fnmatch.filter(os.listdir('.'), '*.cache'))

    # Keeping the cache size manageable and the calculation simple
    if (num_cache_files >= 1000):
        cleanup_cache(logger)

    # The cache is maintained as files on disk, with uniqueness provided by appending an md5
    # of the URL to the file name
    # The cache is just so I don't end up spamming upstream too much. Poor upstream...
    cache_file = hashlib.md5(f"{api_url}".encode()).hexdigest() + ".cache"
    body = None

    if os.path.isfile(cache_file):
        logger.debug(f"Found cached file <{cache_file}> for <{api_url}>")
        with open(cache_file) as cache:
            body = cache.read()
    else:
        contents = urllib.request.urlopen(api_url)
        body = contents.read().decode('utf-8')

        if cache_results:
            logger.debug(f"Creating cache file <{cache_file}> for <{api_url}>.")
            with open(cache_file, "w") as cache:
                cache.write(body)
        else:
            logger.debug(f"Skipping cache file <{cache_file}> for <{api_url}>.")

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
        description = "Hackerss-News"
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

    def rss_feed_data(self):
        rss_feed_generator = RssFeedElements()

        stories = fetch_stories_from_api()
        rss_content = rss_feed_generator.generate_rss_feed(stories)

        return rss_content

    def handle(self):
        logger.debug("DEBUG: Serving request...")

        rss_feed = self.rss_feed_data()

        http_header = "HTTP/1.1 200"
        http_blank = "\n"

        # magical 3. I _think_ it's tracking the blank lines, but I got it from an error message in curl
        http_content_length_header = f"content-length: {len(rss_feed.encode()) + 3}"

        data = []
        data.append(http_header)
        data.append(http_content_length_header)
        data.append(http_blank)  # http standard says to have a blank line after you've sent your metadata i.e. headers
        data.append(rss_feed)
        data.append(http_blank)

        encoded_data = '\n'.join(data).encode()

        self.request.send(encoded_data)


def fetch_stories_from_api():
    # Fetching newstories returns a list of page IDs.
    # https://github.com/HackerNews/API#new-top-and-best-stories
    hacker_news_posts_ids_endpoint = "https://hacker-news.firebaseio.com/v0/topstories.json"

    logger.debug(f"fetching from {hacker_news_posts_ids_endpoint}")
    post_ids = fetch_from_url(hacker_news_posts_ids_endpoint, cache_results=False)

    stories = list()

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

    return stories


if __name__ == '__main__':

    if "--help" in sys.argv:
        help = textwrap.dedent('''
        Usage: execute this script and the hackernews API will be consumed and an RSS feed generated from it on a TCP socket.
        The TCP socket will be bound to 0.0.0.0
        
        Env Vars:
        RSS_FEED_PORT - defaults to 11223
        STORIES_LIMIT - defaults to 1 story; you probably want this set much higher.
        ''')

        print(help)
        sys.exit(0)

    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger('hackerss')
    logger.setLevel(logging.DEBUG)

    # Keep things tidy
    atexit.register(cleanup_cache, logger)

    serving_address = '0.0.0.0'
    serving_port = os.environ.get('RSS_FEED_PORT', '11223')
    serving_port = int(serving_port)

    logger.debug(f"Starting on {serving_address}:{serving_port}")

    # Oof. To hand data in to the handle() method, the "best" solution I could come up with was writing a custom TCP
    # server, and the second best was to hand the data on a custom data attribute.
    with socketserver.TCPServer((serving_address, serving_port), RssHandler) as server:
        server.serve_forever()
