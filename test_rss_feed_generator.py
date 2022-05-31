import unittest
import json
from main import RssFeedElements

class TestApiInteractor(unittest.TestCase):
    def setUp(self) -> None:
        self.rssFeed = RssFeedElements()

    def test_generate_item_with_fully_populated_story(self):
        story = {'title': "roflcopter", 'url': 'http://hippololamus'}
        expected = '''
<item>
<title>roflcopter</title>
<link>http://hippololamus</link>
</item>'''

        self.assertEqual(self.rssFeed._generate_item(story), expected)

    def test_generate_item_with_partly_populated_story(self):
        story = {'url': 'http://hippololamus'}
        expected = '''
<item>
<title>no title provided</title>
<link>http://hippololamus</link>
</item>'''

        self.assertEqual(self.rssFeed._generate_item(story), expected)
