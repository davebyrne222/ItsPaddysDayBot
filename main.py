from dataclasses import dataclass
from datetime import datetime
import re

import praw
import prawcore
from rich.console import Console

from secret import Configuration

# https://github.com/acini/praw-antiabuse-functions TODO: Use this!

console = Console()

@dataclass
class Responses:
    blacklistSub = "Thank you. * has been blacklisted and I will no longer reply in this subreddit."
    whitelistSub = "Thank you, I will be glad to start replying in *"
    blacklistUser = "Thank you. You have been blacklisted and I will no longer reply to your posts or comments"
    whitelistUser = "Thank you, I will be glad to start replying to your posts and comments"
    suggestion = "Thank you for your suggestion. I have logged it for review."
    invalidSubreddit = "Thank you for your message however, the subreddit you mentioned (*) does not appear to be a" \
                       " valid subreddit"
    invalidSubject = "I am a bot and unfortunately could not decipher your subject. Please see ?? for a guide on how " \
                     "to message me"
    unauthorised = "I understood your request however, it does not appear you are a moderator of *"


class ItsPaddysDayDB:

    subsTemp = {

    }

    @staticmethod
    def add_sub(sub: praw.models.Subreddit):
        """Todo: get data from database"""
        return True

    @staticmethod
    def get_sub(sub: str):
        """Todo: get data from database"""
        return True

    @staticmethod
    def blacklist_sub(sub: str):
        return True

    @staticmethod
    def whitelist_sub(sub: str):
        return True

    @staticmethod
    def blacklist_user(sub: str):
        return True

    @staticmethod
    def is_user_blacklisted(userId: str):
        return True


class ItsPaddysDay:

    def __init__(self, reddit: praw.Reddit):
        self.reddit = reddit

    # TODO: add decorator to check author is mod?
    @staticmethod
    def _handle_blacklist(message: praw.models.Message, sub: praw.models.Subreddit):

        if not isinstance(sub, praw.models.Subreddit):
            response = Responses.invalidSubreddit

        elif not ItsPaddysDay._is_author_mod(message.author, sub):
            response = Responses.unauthorised

        else:
            ItsPaddysDayDB.blacklist_sub(sub)
            response = Responses.blacklistSub

        return response.replace("*", sub.display_name)

    # TODO: add decorator to check author is mod?
    @staticmethod
    def _handle_whitelist(message: praw.models.Message, sub: praw.models.Subreddit):

        if not isinstance(sub, praw.models.Subreddit):
            response = Responses.invalidSubreddit

        elif not ItsPaddysDay._is_author_mod(message.author, sub):
            response = Responses.unauthorised

        else:
            ItsPaddysDayDB.whitelist_sub(sub)
            response = Responses.whitelistSub

        return response.replace("*", sub.display_name)

    @staticmethod
    def _handle_suggestion(message: praw.models.Message, sub: praw.models.Subreddit):
        # TODO: send message to LevelIntro?
        return Responses.suggestion

    @staticmethod
    def _handle_ignoreme(message: praw.models.Message, sub: praw.models.Subreddit):
        ItsPaddysDayDB.blacklist_user(message.author.id)
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
    def _parse_subject(subject: str) -> tuple[str | None, str | None]:
        action, subreddit = None, None

        match = re.search(r'\B!([a-zA-Z:]+)\b', subject)

        if not match:
            pass

        elif ":" in match.group():
            action, subreddit = match.group().split(":")

        else:
            action = match.group()

        return action, subreddit

    def _process_actions(self, message: praw.models.Message, action: str, sub: str) -> str:

        if action.lower() not in self.actionMap:
            response = Responses.invalidSubject

        else:
            subr = self.reddit.subreddit(sub) if self._is_valid_sub(sub) else None
            if actionMethod := ItsPaddysDay.actionMap.get(action):
                response = actionMethod(message=message, sub=subr)
            else:
                response = Responses.invalidSubject

        return response

    def _process_mentions(self, message: praw.models.Message) -> None:
        """Performs action based on mention"""
        sub = message.subreddit.display_name
        body = message.body
        author = message.author

        if (knownSub := ItsPaddysDayDB.get_sub(sub)):
            pass
            # if knownSub.isBlacklisted:
            #     pass

        console.log(f"\nMention in: {sub} \nAction:")

    def _process_direct_message(self, message: praw.models.Message) -> None:

        action, sub = self._parse_subject(message.subject)

        if not action:
            response = Responses.invalidSubject

        else:
            response = self._process_actions(message, action, sub)

        console.log(f"subject: {message.subject} \nResponse: {response}\n")

        # message.reply(response)

        # message.mark_read()

    def process_unread_messages(self) -> None:
        """ Checks messages for mentions to control which subreddits are searched for comments

        To do:
        - Check mentions:
            - Check if mention is in a new subreddit, if so, add it to whitelist (use keyword in mention?)
            - Check if mention contains keywords to blacklist subreddit and is posted by moderator
            - check if mention contains keywords to un-blacklist subreddit and is posted by moderator
        - Check direct messages:
            - Check if message contains keywords to blacklist subreddit and is posted by moderator
            - check if message contains keywords to un-blacklist subreddit and is posted by moderator
        """
        console.log("Processing Unread Messages:")
        processedMessages = 0

        for message in self.reddit.inbox.unread():

            if message.was_comment:
                self._process_mentions(message)

            else:
                self._process_direct_message(message)

            processedMessages += 1

        if processedMessages == 0:
            console.log("No unread messages")

    def process_subreddit_posts(self, subreddit: str) -> None:
        console.print("----------------")
        console.print(f"Checking posts in {subreddit}:")

        subr = self.reddit.subreddit(subreddit)

        for submission in subr.new():
            console.print(
                f"\t - [{submission.id}, {datetime.fromtimestamp(submission.created_utc)}] {submission.title}")

            if "What am I" in submission.title:
                console.print("///////////////////////")
                console.print("found!")
                for comment in submission.comments.list():
                    console.print(
                        f"\t - [{comment.id}, {datetime.fromtimestamp(comment.created_utc)}] {comment.body}")

                console.print("///////////////////////")

    def process_subreddit_comments(self, subreddit: str) -> None:
        """ Checks whitelisted subreddits for comments and responds if a comment contains an erroneous pronunciations of
        St. Patricks Day etc.

        To do:
        - check if comments contain some version of 'pattys day'
        - respond if not previously responded to?
        - add message identifier to database (AWS?) to prevent responding again
        - use praw-antiabuse-functions?
        """

        subr = self.reddit.subreddit(subreddit)

        for comment in subr.comments():
            console.print("----------------")
            console.print(comment.selftext)
            console.print(comment.selftext)

            try:
                if "bot" in comment.data:
                    comment.reply("hello world...")
            except praw.exceptions.APIException:
                print("probably a rate limit...")


def get_subreddits():
    """TBD: get subreddits from DB"""
    for subreddit in ["testingground4bots"]:
        yield subreddit


def run_bot() -> None:
    r = praw.Reddit(
        username=conf.reddit_user_name,
        password=conf.reddit_password,
        client_id=conf.reddit_client_id,
        client_secret=conf.reddit_secret,
        user_agent=conf.reddit_user_agent
    )

    try:
        r.user.me()
    except prawcore.exceptions.ResponseException as e:
        console.log(f"Invalid user")
        raise e

    bot = ItsPaddysDay(r)

    # check messages
    bot.process_unread_messages()

    # check subreddits
    # for subreddit in get_subreddits():
    #     # check posts
    #     bot.process_subreddit_posts(subreddit)
    #
    #     # check comments
    #     bot.process_subreddit_comments(subreddit)


if __name__ == "__main__":
    conf = Configuration()

    run_bot()
