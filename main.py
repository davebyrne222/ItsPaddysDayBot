import praw

from bot import ItsPaddysDay
from logger import logger
from config import Configuration


def run_bot() -> None:

    logger.debug(f"Starting")

    try:
        bot = ItsPaddysDay(
            conf.reddit_user_name,
            conf.reddit_password,
            conf.reddit_client_id,
            conf.reddit_secret,
            conf.reddit_user_agent,
            conf.praw_rate_timeout,
            conf.dryrun
        )

        bot.syncronise()

    except praw.exceptions.RedditAPIException as e:
        logger.exception("API Exception (rate?):")

    except Exception as e:
        logger.exception("Unhandled Exception occurred:")

    else:
        logger.debug(f"Finished Successfully")


if __name__ == "__main__":

    conf = Configuration()

    run_bot()

