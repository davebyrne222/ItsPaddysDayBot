from dataclasses import dataclass

import praw
import prawcore
from datetime import datetime
import re

from logger import logger
from db import DB


@dataclass
class Responses:
    blacklistSub = "Thank you. * has been blacklisted and I will no longer reply in this subreddit."
    whitelistSub = "Thank you, I will be glad to start replying in *"
    blacklistUser = "Thank you. You have been blacklisted and I will no longer reply to your posts or comments"
    whitelistUser = "Thank you, I will be glad to start replying to your posts and comments"
    suggestion = "Thank you for your suggestion. I have logged it for review."
    invalidSubreddit = "Thank you for your message however, the subreddit you mentioned (*) does not appear to be a" \
                       " valid subreddit"
    invalidCommand = "I am a bot and unfortunately could not decipher your subject. Please see my profile for a guide on how " \
                     "to message me"
    unauthorised = "I understood your request however, it does not appear you are a moderator of *"
    correction = ""

    def __init__(self):
        with open("correction_text.md", "r") as file:
            self.correction = file.read()


class _Bot:
    def __init__(self,
                 reddit_user_name: str,
                 reddit_password: str,
                 reddit_client_id: str,
                 reddit_secret: str,
                 reddit_user_agent: str,
                 ratelimit_seconds: int,
                 dryrun: bool
                 ):

        self.reddit = praw.Reddit(
            username=reddit_user_name,
            password=reddit_password,
            client_id=reddit_client_id,
            client_secret=reddit_secret,
            user_agent=reddit_user_agent,
            ratelimit_seconds=ratelimit_seconds
        )
        self._db = DB()
        self.dryrun = dryrun

    def _manage_monitored_subs(self, action: str, message: praw.models.Message, sub: praw.models.Subreddit):

        if not isinstance(sub, praw.models.Subreddit):
            response = Responses.invalidSubreddit

        elif not ItsPaddysDay._is_author_mod(message.author, sub):
            response = Responses.unauthorised

        elif action == "whitelist":
            self._db.whitelist_sub(sub)
            response = Responses.whitelistSub

        elif action == "blacklist":
            self._db.blacklist_sub(sub)
            response = Responses.blacklistSub

        else:
            raise ValueError(f"Invalid value for action ('{action}'). Valid options are 'whitelist' or 'blacklist")

        return response.replace("*", sub.display_name)

    def _handle_blacklist(self, message: praw.models.Message, sub: praw.models.Subreddit):
        self._manage_monitored_subs("blacklist", message, sub)

    def _handle_whitelist(self, message: praw.models.Message, sub: praw.models.Subreddit):
        self._manage_monitored_subs("whitelist", message, sub)

    @staticmethod
    def _handle_suggestion(message: praw.models.Message, sub: praw.models.Subreddit):
        # TODO: send message to LevelIntro?
        return Responses.suggestion

    def _handle_ignoreme(self, message: praw.models.Message, sub: praw.models.Subreddit):
        self._db.blacklist_user(message.author.id)
        return Responses.blacklistUser

    actionMap = {
        "!blacklist": _handle_blacklist,
        "!whitelist": _handle_whitelist,
        "!suggestion": _handle_suggestion,
        "!ignoreme": _handle_ignoreme
    }

    @staticmethod
    def _is_author_mod(author: praw.models.Redditor, subreddit: str) -> bool:
        return subreddit in [sub.display_name for sub in author.moderated()]

    def _is_valid_sub(self, subreddit: str) -> bool:
        try:
            return len(self.reddit.subreddits.search_by_name(subreddit, exact=True)) == 1
        except prawcore.exceptions.NotFound:
            return False

    @staticmethod
    def _parse_command(subject: str) -> tuple[str | None, str | None]:
        action, subreddit = None, None

        match = re.search(r'\B!([a-zA-Z:]+)\b', subject)

        if not match:
            pass

        elif ":" in match.group():
            action, subreddit = match.group().split(":")

        else:
            action = match.group()

        return action, subreddit

    def _perform_action(self, message: praw.models.Message, action: str, sub: str) -> str:

        if action.lower() not in self.actionMap:
            response = Responses.invalidCommand

        else:
            subr = self.reddit.subreddit(sub) if self._is_valid_sub(sub) else None

            if actionMethod := ItsPaddysDay.actionMap.get(action):
                response = actionMethod(message=message, sub=subr)
            else:
                response = Responses.invalidCommand

        return response

    def _process_mention(self, message: praw.models.Message) -> str:

        sub = message.subreddit.display_name
        action, _ = ItsPaddysDay._parse_command(message.body)

        if action:
            response = self._perform_action(message, action, sub)

        else:
            self._db.whitelist_sub(message.subreddit)
            response = Responses.whitelistSub.replace("*", sub)

            if not self.dryrun:
                self._db.add_responded_post(message.id)

            # get parent comment and send to _process_submission
            parent = message.parent()
            self._process_submission(parent)

            # get parent replies and send to _process_submission
            for comment in parent.comments:
                self._process_submission(comment)

        return response

    def _process_direct_message(self, message: praw.models.Message) -> str:

        action, sub = ItsPaddysDay._parse_command(message.subject)

        if not action:
            response = Responses.invalidCommand

        else:
            response = self._perform_action(message, action, sub)

        return response

    @staticmethod
    def _contains_patty(searchStr: str) -> bool:
        if any((
                "st patty" in searchStr,
                "st. patty" in searchStr,
                "saint patty" in searchStr,
        )):
            return True
        return False

    def _process_submission(self, submission):

        logger.debug(f"{submission.subreddit_name_prefixed}, {datetime.fromtimestamp(submission.created_utc)}, {submission.id}, https://www.reddit.com{submission.permalink}")

        if self._db.is_post_responded(submission.id):
            return

        searchStr = ""
        for attr in ["title", "body", "selftext"]:
            searchStr += getattr(submission, attr, "").lower() + " "

        if not ItsPaddysDay._contains_patty(searchStr):
            return

        logger.info(f"--> MATCH: {searchStr}")
        logger.info(f"{submission.subreddit_name_prefixed}, {datetime.fromtimestamp(submission.created_utc)}, {submission.id}, https://www.reddit.com{submission.permalink}")

        if self.dryrun:
            return

        submission.reply(Responses.correction)
        self._db.add_responded_post(submission.id)


class ItsPaddysDay(_Bot):

    def __init__(self, *args, nPostsLimit=100, nCommentsLimit=None):
        super().__init__(*args)

        self.nPostsLimit = nPostsLimit
        self.nCommentsLimit = nCommentsLimit

    def process_unread_messages(self) -> None:
        logger.info(f"------------------------------")
        logger.info("Processing Unread Messages")
        logger.info(f"------------------------------")

        for message in self.reddit.inbox.unread():
            logger.debug(f"subject: {message.subject}")

            if message.was_comment:
                response = self._process_mention(message)

            else:
                response = self._process_direct_message(message)

                if not self.dryrun:
                    message.reply(response)
                    message.mark_read()

            logger.info(f"subject: {message.subject} \nResponse: {response}\n")

    def process_subreddit_posts(self, subreddit: str) -> None:
        logger.info(f"------------------------------")
        logger.info(f"Checking posts in {subreddit}:")
        logger.info(f"------------------------------")

        subr = self.reddit.subreddit(subreddit)

        for submission in subr.new(limit=self.nPostsLimit):
            self._process_submission(submission)

    def process_subreddit_comments(self, subreddit: str) -> None:
        logger.info(f"------------------------------")
        logger.info(f"Checking comments in {subreddit}:")
        logger.info(f"------------------------------")

        subr = self.reddit.subreddit(subreddit)

        for submission in subr.comments(limit=self.nCommentsLimit):
            self._process_submission(submission)

    def syncronise(self):
        """Process unread messages and reviews subreddits (n-posts and n-comments set by nPostsLimit, nCommentsLimit)"""
        # check messages
        self.process_unread_messages()

        # check subreddits
        subreddits = "+".join(self._db.get_whitelisted_subs())
        self.process_subreddit_posts(subreddits)
        self.process_subreddit_comments(subreddits)