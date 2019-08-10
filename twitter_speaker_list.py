import json
from pprint import pprint
import tweepy

speakersf = "_private/speakers.json"
submissionsf = "_private/submissions.json"

with open(speakersf, "r") as f:
    all_speakers = json.load(f)

with open(submissionsf, "r") as f:
    all_submissions = json.load(f)

speakers_of_accepted_submissions = [x for x in all_submissions if x['state'] in ("accepted", "confirmed")]


def cleanhandle(pers):
    if "/" in pers.get('@twitter'):
        return pers.get('@twitter').lower().strip().split('/')[-1]
    else:
        return pers.get('twitter').lower().strip().replace('@', '')


handles = {cleanhandle(pers) for pers in data if pers.get('twitter') and pers.get('status', '') == 'accepted'}
# pprint(handles)
print(len(handles))

consumer_key = "JNQs10WBnjPJUdNGzUW3YS5Qp"
consumer_secret = "Tydo9iCitovqcwX7sc6LTYCQBQyRQidwTdQhX6ZxFJiS7lk5IL"
access_token = "15324940-NbhYfPgM5QLtfpsQgN9aZwiuZ3D4jCU7iXMYkLLgo"
access_token_secret = "Xgy424MFZrnbwMS2Ug725lQKF2KTVMc9uUaIHdWwEWDZ0"

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

public_tweets = api.home_timeline()
for tweet in public_tweets:
    print(tweet.text)

lists = api.lists_all()
for _list in lists:
    print(_list.id, _list.name)

CURRRENT_ID = '1002813052767670272'


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
        print(added)
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
        print(removed)
    except:
        print("not removed", handle)

