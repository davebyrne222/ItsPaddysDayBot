import json
import praw

from logger import logger


class DB:

    def __init__(self):
        self.blacklistedSubs: list = []
        self.whitelistedSubs: list = []
        self.blacklistedUsers: list = []
        self.respondedPosts: list = []

        self._tmp_load_data()

    def __del__(self):
        data = dict(
            blacklistedSubs = self.blacklistedSubs,
            whitelistedSubs = self.whitelistedSubs,
            blacklistedUsers = self.blacklistedUsers,
            respondedPosts = self.respondedPosts
        )

        with open("data.json", "w") as fo:
            json.dump(data, fo)

        logger.debug(f"Data written to file")

    def _tmp_load_data(self):
        with open("data.json", "r") as fi:
            data = json.load(fi)

        self.blacklistedSubs = data.get("blacklistedSubs")
        self.whitelistedSubs = data.get("whitelistedSubs")
        self.blacklistedUsers = data.get("blacklistedUsers")
        self.respondedPosts = data.get("respondedPosts")

        logger.debug(f"Data loaded")

    def blacklist_sub(self, sub: praw.models.Subreddit):
        if sub.display_name not in self.blacklistedSubs:
            self.blacklistedSubs.append(sub.display_name)

    def get_blacklisted_subs(self):
        return self.blacklistedSubs

    def whitelist_sub(self, sub: praw.models.Subreddit):
        if sub.display_name not in self.whitelistedSubs:
            self.whitelistedSubs.append(sub.display_name)

    def get_whitelisted_subs(self):
        return self.whitelistedSubs

    def blacklist_user(self, user: praw.models.Redditor):
        if user.id not in self.blacklistedUsers:
            self.blacklistedUsers.append(user.id)

    def add_responded_post(self, postId: str):
        if postId not in self.respondedPosts:
            self.respondedPosts.append(postId)

    def is_post_responded(self, postId: str):
        return postId in self.respondedPosts

    def is_user_blacklisted(self, userId: str):
        return userId in self.blacklistedUsers