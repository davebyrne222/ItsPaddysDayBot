import re
from dataclasses import dataclass
from datetime import datetime

import praw
import prawcore

from logger import logger
from secret import Configuration
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
    correction = "Mo Chara, I think you might be referring to St. Patricks Day, however the correct shorthand spelling is St. Paddy. \n\n I'm a bot"


class _Bot:
    def __init__(self,
                 reddit_user_name: str,
                 reddit_password: str,
                 reddit_client_id: str,
                 reddit_secret: str,
                 reddit_user_agent: str,
                 ratelimit_seconds: int
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

    def _manage_monitored_subs(self, action: str, message: praw.models.Message, sub: praw.models.Subreddit):

        if not isinstance(sub, praw.models.Subreddit):
            response = Responses.invalidSubreddit

        elif not ItsPaddysDaySync._is_author_mod(message.author, sub):
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

            if actionMethod := ItsPaddysDaySync.actionMap.get(action):
                response = actionMethod(message=message, sub=subr)
            else:
                response = Responses.invalidCommand

        return response

    def _process_mention(self, message: praw.models.Message) -> str:

        sub = message.subreddit.display_name
        action, _ = ItsPaddysDaySync._parse_command(message.body)

        if action:
            response = self._perform_action(message, action, sub)

        else:
            self._db.whitelist_sub(message.subreddit)
            response = Responses.whitelistSub.replace("*", sub)

            if not conf.dryrun:
                self._db.add_responded_post(message.id)

            # get parent comment and send to _process_submission
            parent = message.parent()
            self._process_submission(parent)

            # get parent replies and send to _process_submission
            for comment in parent.comments:
                self._process_submission(comment)

        return response

    def _process_direct_message(self, message: praw.models.Message) -> str:

        action, sub = ItsPaddysDaySync._parse_command(message.subject)

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

        if not ItsPaddysDaySync._contains_patty(searchStr):
            return

        logger.info(f"--> MATCH: {searchStr}")
        logger.info(f"{submission.subreddit_name_prefixed}, {datetime.fromtimestamp(submission.created_utc)}, {submission.id}, https://www.reddit.com{submission.permalink}")

        if conf.dryrun:
            return

        submission.reply(Responses.correction)
        self._db.add_responded_post(submission.id)


class ItsPaddysDaySync(_Bot):

    def __init__(self, *args):
        super().__init__(*args)

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

                if not conf.dryrun:
                    message.reply(response)
                    message.mark_read()

            logger.info(f"subject: {message.subject} \nResponse: {response}\n")

    def process_subreddit_posts(self) -> None:
        subreddits = "+".join(self._db.get_whitelisted_subs())

        logger.info(f"------------------------------")
        logger.info(f"Checking posts in {subreddits}:")
        logger.info(f"------------------------------")

        subr = self.reddit.subreddit(subreddits)

        for submission in subr.new():
            self._process_submission(submission)

    def process_subreddit_comments(self) -> None:
        subreddits = "+".join(self._db.get_whitelisted_subs())

        logger.info(f"------------------------------")
        logger.info(f"Checking comments in {subreddits}:")
        logger.info(f"------------------------------")

        subr = self.reddit.subreddit(subreddits)

        for submission in subr.comments(limit=None):
            self._process_submission(submission)


def run_bot() -> None:
    bot = ItsPaddysDaySync(
        conf.reddit_user_name,
        conf.reddit_password,
        conf.reddit_client_id,
        conf.reddit_secret,
        conf.reddit_user_agent,
        conf.praw_rate_timeout
    )

    # check messages
    bot.process_unread_messages()

    # check posts
    bot.process_subreddit_posts()

    # check comments
    bot.process_subreddit_comments()


if __name__ == "__main__":

    conf = Configuration()

    logger.debug(f"Starting")

    try:
        with open("correction_text.md", "r") as file:
            Responses.correction = file.read()

        run_bot()

    except praw.exceptions.RedditAPIException as e:
        logger.exception("API Exception (rate?):")

    except Exception as e:
        logger.exception("Unhandled Exception occurred:")

    else:
        logger.debug(f"Finished Successfully")

