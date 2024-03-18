import json
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime

import praw
import prawcore

from secret import Configuration


@dataclass
class TmpDataDict:
    blacklistedSubs: list = field(default_factory=lambda: [])
    whitelistedSubs: list = field(default_factory=lambda: [])
    blacklistedUsers: list = field(default_factory=lambda: [])
    respondedPosts: list = field(default_factory=lambda: [])

    def asdict(self):
        return asdict(self)


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


class DB:

    @staticmethod
    def add_sub(sub: praw.models.Subreddit):
        """Todo: get data from database"""
        return True

    @staticmethod
    def get_sub(sub: praw.models.Subreddit):
        """Todo: get data from database"""
        return True

    @staticmethod
    def blacklist_sub(sub: praw.models.Subreddit):
        if sub.display_name not in tmpDataDict.blacklistedSubs:
            tmpDataDict.blacklistedSubs.append(sub.display_name)

    @staticmethod
    def whitelist_sub(sub: praw.models.Subreddit):
        if sub.display_name not in tmpDataDict.whitelistedSubs:
            tmpDataDict.whitelistedSubs.append(sub.display_name)

    @staticmethod
    def blacklist_user(user: praw.models.Redditor):
        if user.id not in tmpDataDict.blacklistedUsers:
            tmpDataDict.blacklistedUsers.append(user.id)

    @staticmethod
    def is_user_blacklisted(userId: str):
        return userId in tmpDataDict.blacklistedUsers


class _Bot:
    @staticmethod
    def _manage_monitored_subs(action: str, message: praw.models.Message, sub: praw.models.Subreddit):

        if not isinstance(sub, praw.models.Subreddit):
            response = Responses.invalidSubreddit

        elif not ItsPaddysDaySync._is_author_mod(message.author, sub):
            response = Responses.unauthorised

        elif action == "whitelist":
            DB.whitelist_sub(sub)
            response = Responses.whitelistSub

        elif action == "blacklist":
            DB.blacklist_sub(sub)
            response = Responses.blacklistSub

        else:
            raise ValueError(f"Invalid value for action ('{action}'). Valid options are 'whitelist' or 'blacklist")

        return response.replace("*", sub.display_name)

    @staticmethod
    def _handle_blacklist(message: praw.models.Message, sub: praw.models.Subreddit):
        ItsPaddysDaySync._manage_monitored_subs("blacklist", message, sub)

    @staticmethod
    def _handle_whitelist(message: praw.models.Message, sub: praw.models.Subreddit):
        ItsPaddysDaySync._manage_monitored_subs("whitelist", message, sub)

    @staticmethod
    def _handle_suggestion(message: praw.models.Message, sub: praw.models.Subreddit):
        # TODO: send message to LevelIntro?
        return Responses.suggestion

    @staticmethod
    def _handle_ignoreme(message: praw.models.Message, sub: praw.models.Subreddit):
        DB.blacklist_user(message.author.id)
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
            DB.whitelist_sub(message.subreddit)
            response = Responses.whitelistSub.replace("*", sub)

            if not conf.dryrun:
                tmpDataDict.respondedPosts.append(message.id)

            # get parent comment and send to _process_submission
            parent = message.parent()
            ItsPaddysDaySync._process_submission(parent)

            # get parent replies and send to _process_submission
            for comment in parent.comments:
                ItsPaddysDaySync._process_submission(comment)

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

    @staticmethod
    def _process_submission(submission):

        logger.info(
            f"{submission.subreddit_name_prefixed}, {datetime.fromtimestamp(submission.created_utc)}, {submission.id}, https://www.reddit.com{submission.permalink}")

        if submission.id in tmpDataDict.respondedPosts:
            return

        searchStr = ""
        for attr in ["title", "body", "selftext"]:
            searchStr += getattr(submission, attr, "").lower() + " "

        if not ItsPaddysDaySync._contains_patty(searchStr):
            return

        logger.info(f"--> MATCH: {searchStr}")

        if conf.dryrun:
            return

        submission.reply(Responses.correction)
        tmpDataDict.respondedPosts.append(submission.id)


class ItsPaddysDaySync(_Bot):

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

    def process_subreddit_posts(self, subreddit: str) -> None:
        logger.info(f"------------------------------")
        logger.info(f"Checking posts in {subreddit}:")
        logger.info(f"------------------------------")


        subr = self.reddit.subreddit(subreddit)

        for submission in subr.new():
            ItsPaddysDaySync._process_submission(submission)

    def process_subreddit_comments(self, subreddit: str) -> None:
        logger.info(f"------------------------------")
        logger.info(f"Checking comments in {subreddit}:")
        logger.info(f"------------------------------")


        subr = self.reddit.subreddit(subreddit)

        for submission in subr.comments(limit=None):
            ItsPaddysDaySync._process_submission(submission)


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

    return

    # check posts
    bot.process_subreddit_posts("+".join(tmpDataDict.whitelistedSubs))

    # check comments
    bot.process_subreddit_comments("+".join(tmpDataDict.whitelistedSubs))


def loadData():
    with open("data.json", "r") as fi:
        data = json.load(fi)

    tmpDataDict.blacklistedSubs = data.get("blacklistedSubs")
    tmpDataDict.whitelistedSubs = data.get("whitelistedSubs")
    tmpDataDict.blacklistedUsers = data.get("blacklistedUsers")
    tmpDataDict.respondedPosts = data.get("respondedPosts")


def dumpData():
    dataDict = tmpDataDict.asdict()

    with open("data.json", "w") as fo:
        json.dump(dataDict, fo)


if __name__ == "__main__":

    conf = Configuration()

    logger = conf.setup_logging()
    logger.debug(f"Starting")

    try:
        with open("correction_text.md", "r") as file:
            Responses.correction = file.read()

        tmpDataDict = TmpDataDict()

        loadData()

        run_bot()

    except praw.exceptions.RedditAPIException as e:
        logger.exception("API Exception (rate?):")

    except Exception as e:
        logger.exception("Unhandled Exception occurred:")

    else:
        logger.debug(f"Finished Successfully")

    finally:
        dumpData()
        logger.debug(f"Data written to file")

