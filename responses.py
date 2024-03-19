class Responses:

    def __init__(self):
        self.blacklistSub = "Thank you. * has been blacklisted and I will no longer reply in this subreddit."
        self.whitelistSub = "Thank you, I will be glad to start replying in *"
        self.blacklistUser = "Thank you. You have been blacklisted and I will no longer reply to your posts or comments"
        self.whitelistUser = "Thank you, I will be glad to start replying to your posts and comments"
        self.suggestion = "Thank you for your suggestion. I have logged it for review."
        self.invalidSubreddit = "Thank you for your message however, the subreddit you mentioned (*) does not appear to be a valid subreddit"
        self.invalidCommand = "I am a bot and unfortunately could not decipher your subject. Please see my profile for a guide on how to message me"
        self.unauthorised = "I understood your request however, it does not appear you are a moderator of *"
        self.correction = self.load_correction_text()

    @staticmethod
    def load_correction_text():
        with open("correction_text.md", "r") as file:
            return file.read()
