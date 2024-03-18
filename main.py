import praw

from bot import ItsPaddysDaySync
from logger import logger
from secret import Configuration


def run_bot() -> None:
    bot = ItsPaddysDaySync(
        conf.reddit_user_name,
        conf.reddit_password,
        conf.reddit_client_id,
        conf.reddit_secret,
        conf.reddit_user_agent,
        conf.praw_rate_timeout,
        conf.dryrun
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
        run_bot()

    except praw.exceptions.RedditAPIException as e:
        logger.exception("API Exception (rate?):")

    except Exception as e:
        logger.exception("Unhandled Exception occurred:")

    else:
        logger.debug(f"Finished Successfully")

