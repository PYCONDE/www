import json
from pprint import pprint
import tweepy
from config import consumer_key, consumer_secret, access_token, access_token_secret

speakersf = "../_private/speakers.json"
submissionsf = "../_private/submissions.json"

with open(speakersf, "r") as f:
    all_speakers = json.load(f)

with open(submissionsf, "r") as f:
    all_submissions = json.load(f)

all_speakers = {x['code']: x for x in all_speakers}
accepted_submissions = [x for x in all_submissions if x['state'] in ("accepted", "confirmed")]
accepted_speakers = []
_ = [[accepted_speakers.extend([y['code'] for y in x['speakers']]) for x in accepted_submissions]]
accepted_speakers = set(accepted_speakers)


def cleanhandle(handle):
    if "/" in handle:
        return handle.lower().strip().split('/')[-1]
    else:
        return handle.lower().strip().replace('@', '')


handles = set([cleanhandle(all_speakers[code]['@twitter']) for code in accepted_speakers
           if all_speakers.get(code, {}).get('@twitter')])
# pprint(handles)
print(len(handles))

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

public_tweets = api.home_timeline()
for tweet in public_tweets:
    print(tweet.text)

lists = api.lists_all()
for _list in lists:
    print(_list.id, _list.name)

CURRRENT_ID = '1160256308303601665'


the_list = api.list_members(list_id=CURRRENT_ID, count=5000)
# print(the_list)
users_added = {u.screen_name.strip().lower() for u in the_list}
print(users_added)
# exit(0)

not_added = []
for handle in (handles - users_added):
    if handle in users_added:
        continue
    print("adding", handle)
    try:
        user = api.get_user(handle)
        print(user.id, user.name)
        added = api.add_list_member(list_id=CURRRENT_ID, user_id=user.id)
        # print(added)
    except:
        not_added.append(handle)

print("not added", not_added)

for handle in (users_added - handles):
    if handle in handles:
        continue
    print("removing", handle)
    try:
        user = api.get_user(handle)
        print(user.id, user.name)
        removed = api.remove_list_member(list_id=CURRRENT_ID, user_id=user.id)
        # print(removed)
    except:
        print("not removed", handle)

