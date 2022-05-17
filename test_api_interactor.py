import unittest
import json
from main import ApiInteractor

class TestApiInteractor(unittest.TestCase):
    def setUp(self) -> None:
        self.apiGetter = ApiInteractor("https://hacker-news.firebaseio.com/v0/newstories.json")

    def test_get_post_ids(self):
        # is this the laziest test I've ever written? Not even close.
        self.assertTrue(type(self.apiGetter._fetch_post_ids()) is list)
