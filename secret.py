import os
from dataclasses import dataclass


@dataclass
class Configuration(object):
    def __init__(self):
        self.reddit_user_name = "None"
        self.reddit_password = "None"
        self.reddit_secret = "None"
        self.reddit_client_id = "None"
        self.reddit_user_agent = "None"

