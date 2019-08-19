import json
from datetime import datetime
import tweepy
from random import choice
from config import consumer_key, consumer_secret, access_token, access_token_secret

submissionsf = "../website/databags/submissions.json"
tweeted_already = "../website/databags/tweeted_talks.txt"

site = "https://de.pycon.org/program/"

with open(submissionsf, "r") as f:
    all_submissions = json.load(f)

accepted_submissions = [x for x in all_submissions if x['state'] in ("accepted", "confirmed")]

with open(tweeted_already) as f:
    tweeted_codes = set(f.readlines())

accepted_submissions_for_twitter = [x for x in accepted_submissions
                                    if any([y.get('@twitter') for y in x['speakers']])
                                    and x['code'] not in tweeted_codes
                                    ]

chosen = choice(accepted_submissions_for_twitter)

the_text = chosen['short_description']
the_link = f"{site}{chosen['slug']}"
the_handles = ' '.join([f"@{x.get('@twitter')}" for x in chosen['speakers']])

tweet_len = len(f"{the_text} {the_handles} at #PyConDE #PyDataBerlin")
if tweet_len > 200:
    # shorten text if needed
    the_text = the_text[:200-tweet_len+200] + "…"

the_tweet = f"{the_text} {the_handles} at #PyConDE #PyDataBerlin\n{the_link}"


auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

tweet = api.update_status(status=the_tweet)
try:
    if tweet.id:
        with open(tweeted_already, 'a') as f:
            f.write(f"{chosen['code']}\n")
except:
    exit(1)
