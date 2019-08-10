import hashlib
import json
import os
import re
import codecs
from datetime import timedelta
from functools import partial
from unicodedata import normalize
from pathlib import Path

import click
import requests
import pandas as pd
from openpyxl import load_workbook

TOKEN = open('_private/TOKEN.txt').read()

base_url = 'https://pretalx.com'
event = 'pyconde-pydata-berlin-2019'
headers = {'Accept': 'application/json, text/javascript', 'Authorization': f'Token {TOKEN}'}

submissions_path = Path('_private/submissions.json')
speakers_path = Path('_private/speakers.json')
clean_submissions_f = "pyconde/databags/submissions"  # filepath w/o extention
clean_speakers_f = "pyconde/databags/speakers"  # filepath w/o extention


def get_from_pretalx_api(url, params=None):
    """
    Helper function to get data from Pretalx API
    :param url:
    :param params: optional filters
    :return: results and next url (if any)
    """
    if not params:
        params = {}
    # print(f'getting more reviews: {url}')
    res = requests.get(url, headers=headers, params=params)
    resj = res.json()
    return resj['results'], resj['next']


def get_all_data_from_pretalx(url, params=None):
    """
    Helper to get paginated data from Pretalx API
    :param url: url to start from
    :param params: optional filters

    """
    api_result = []
    while url:
        chunk, url = get_from_pretalx_api(url, params=params)
        api_result.extend(chunk)
    return api_result


def load_submissions(accepted_only=True):
    url = f'{base_url}/api/events/{event}/submissions/'
    if accepted_only:
        # duplicate param 'state' cannot be passed via params dict
        url = f'{url}?q=&state=accepted&state=confirmed'
    submissions = get_all_data_from_pretalx(url)
    with open(submissions_path, 'w') as f:
        json.dump(submissions, f, indent=4)


def load_speakers():
    url = f'{base_url}/api/events/{event}/speakers'
    speakers = get_all_data_from_pretalx(url)

    qa_map = {
        112: 'affiliation',
        113: 'position',
        114: 'homepage',
        115: '@twitter',
        124: 'residence',
        117: 'github',
    }

    the_speakers = []
    for s in speakers:
        speaker = {k: s[k] for k in ['name', 'biography', 'email', 'code']}
        for qa in s['answers']:
            _id = qa.get('question', {}).get('id')
            if _id not in qa_map:
                continue
            speaker[qa_map[_id]] = qa.get('answer')
        the_speakers.append(speaker)
    with open(speakers_path, 'w') as f:
        json.dump(the_speakers, f, indent=4)


def slugify(text, delim="-"):
    """Generates an slightly worse ASCII-only slug."""

    _punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
    _regex = re.compile("[^a-z0-9]")
    # First parameter is the replacement, second parameter is your input string

    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize("NFKD", word).encode("ascii", "ignore")
        word = word.decode("ascii")
        word = _regex.sub("", word)
        if word:
            result.append(word)
    return str(delim.join(result))


def date2identifier(dt):
    if dt.second == 59:
        dt += timedelta(seconds=1)
    return dt.strftime("%a-%H:%M").lower()


def format_date(dt):
    if dt.second == 59:
        dt += timedelta(seconds=1)
    return dt.strftime("%A %H:%M").lower()


def get_talk_identifier(s):
    return s.split(" ", 1)[0]


def gen_schedule_talks(data):
    tpl = """_model: talk 
---
code: {}
"""
    for e in data.values():
        dirname = "pyconde/content/schedule/talks/{}".format(e["slug"])
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(os.path.join(dirname, "contents.lr"), "w") as f:
            f.write(tpl.format(e["slot_code"]))
    return data


def gen_gravatar(email):
    h = hashlib.md5(email.encode("utf-8")).hexdigest()
    return "https://www.gravatar.com/avatar/{}".format(h)


def fix_data(data):
    for talk in data:
        for speaker in talk.get("the_speakers", []):
            speaker["gravatar"] = gen_gravatar(speaker["email"])
            if "homepage" in speaker and not speaker["homepage"].strip().startswith(
                    "http:"
            ):
                speaker["homepage"] = "http://{}".format(speaker["homepage"].strip())
    return data


def load_talks_metadata(data, filename=None):
    return json.load(open(filename))


def merge_schedule(data, schedule=None):
    accepted_talks = {}

    for talk in schedule:
        for d in data:
            if talk["talk_code"] == d["code"]:
                d["slot_time"] = talk["slot_time"]
                d["slot_date"] = talk["slot_date"]
                d["slot_code"] = "{}-{}".format(talk["slot_time"], talk["room"])
                d["room"] = talk["room"]
                d["slug"] = slugify(d["title"])
                accepted_talks[d["slot_code"]] = d
    return accepted_talks


def drop_values(data):
    for talk in data:
        for speaker in talk.get("the_speakers", []):
            pass
    return data


def load_schedule(filename=None):
    rows = [
        3,
        4,
        6,
        7,
        9,
        10,
        11,
        13,
        14,
        15,
        17,
        18,
        19,
        21,
        22,
        23,
        25,
        26,
        27,
        29,
        30,
        31,
    ]

    rooms = {"B": "cubus", "C": "media", "D": "lounge", "E": "lecture", "G": "openhub"}

    wb = load_workbook(filename)
    sheet = wb["Sheet1"]
    sheet["G9"].value = "8WXEH8 {}".format(sheet["G9"].value)
    talk_list = []
    for row in rows:
        for room, room_name in rooms.items():
            slot_time = date2identifier(sheet[f"A{row}"].value)
            slot_date = format_date(sheet[f"A{row}"].value)
            talk = sheet[f"{room}{row}"].value
            if talk is None or talk.strip() == "" or "<<< available >>>" in talk:
                continue
            talk_identifier = get_talk_identifier(talk)
            talk_list.append(
                {
                    "slot_time": slot_time,
                    "slot_date": slot_date,
                    "room": room_name,
                    "talk_code": talk_identifier,
                    "talk": talk,
                }
            )
    return talk_list


def drop_sensitive_speaker_infromation(data):
    for talk in data.values():
        for speaker in talk.get("the_speakers", []):
            for k in list(speaker.keys()):
                if not k in ["name", "biography", "homepage", "@twitter"]:
                    del speaker[k]
    return data


def load_videos(filename):
    d = {}
    for video in json.load(open(filename)):
        d[video["code"]] = video
    return d


def write_databag(data):
    json.dump(data, open("pyconde/databags/talks.json", "w"), indent=4)
    return data


def merge_video(data, videos):
    for talk in data.values():
        talk["video"] = videos.get(talk["code"], None)
    return data


def pipe(*tasks):
    data = None
    for task in tasks:
        data = task(data)
    return data


@click.command()
@click.option(
    "--schedule_dir",
    envvar="SCHEDULE_DIR",
    default="../../github_pycon_priv/2018/",
    help="The directory with the schedule and the speaker json",
)
def cli(schedule_dir):
    """generate the databag for the schedule"""

    xsl_file = os.path.join(schedule_dir, "pyconde18-pydata-ka-schedule.xlsx")
    json_file = os.path.join(schedule_dir, "pyconde18-pydata-ka-all_submissions.json")
    video_file = os.path.join(schedule_dir, "videos/video_schedule_mapping.json")

    data = pipe(
        partial(load_talks_metadata, filename=json_file),
        fix_data,
        partial(merge_schedule, schedule=load_schedule(xsl_file)),
        drop_sensitive_speaker_infromation,
        partial(merge_video, videos=load_videos(video_file)),
        write_databag,
        gen_schedule_talks,
    )


def update_session_pages(use_cache=False):
    """
    Refactored for 2019 setup
    - mangle submission data from API
    - make avaibale in databags
    """
    if not use_cache:
        load_submissions()
        load_speakers()
    submissions = json.load(open(submissions_path))
    speakers = json.load(open(speakers_path))
    speakers = {s['code']: s for s in speakers}
    # TODO: add custom sessions as Open Space
    # take on only required attributes

    eq_attr = ['abstract', 'answers', 'code', 'description', 'duration', 'is_featured',
               'speakers', 'state', 'submission_type', 'title', 'track']
    id_answers = {118: 'short_description', 111: 'python_skill', 110: 'domain_expertise', 119: 'domains'}
    cleaned_submissions = []
    for s in submissions:
        cs = {k: s[k] for k in s if k in eq_attr}
        cs['submission_type'] = cs['submission_type']['en']
        cs['track'] = cs['track']['en']
        cs['submission_type'] = cs['submission_type'].replace('Talk-', 'Talk -')
        for answer in [a for a in cs['answers'] if a['question']['id'] in id_answers]:
            val = answer['answer']
            if answer['id'] == 119:
                val = val.split(', ')
            cs[id_answers[answer['question']['id']]] = val
        del cs['answers']
        # add speaker info
        enriched_speakers = []
        for x in cs['speakers']:
            take_on = ['affiliation', 'homepage', '@twitter', 'github', 'biography']
            _add = {k: speakers[x['code']].get(k, '') for k in take_on}
            x.update(_add)
            enriched_speakers.append(x)
        cs['speakers'] = enriched_speakers
        cleaned_submissions.append(cs)
    json.dump(cleaned_submissions, open(f"{clean_submissions_f}.json", "w"), indent=4)


def save_csv_for_banners():
    """
    CSV with banner info only, saved as UTF-16 for useage in Illustrator for auto banner generation
    :return:
    """
    cleaned_submissions = json.load(open(f"{clean_submissions_f}.json", "r"))
    # save csv for banner generation
    csv = ['code', 'title', 'track', 'speakers', 'affiliation', 'banner_name']
    csv_submissions = []
    for i, c in enumerate(cleaned_submissions, 1):
        record = {_c: c.get(_c, '') for _c in csv}
        record['speakers'] = ', '.join([x.get('name', '') for x in c['speakers']])
        record['affiliation'] = ', '.join([x.get('affiliation', '') for x in c['speakers']])
        record['banner_name'] = f'Twitter-{i}.jpg'  # output filename from Illustrator
        csv_submissions.append(record)
    df = pd.DataFrame(csv_submissions)
    df.to_csv(f"{clean_submissions_f}.csv", sep='\t', encoding='utf-8', index=False)
    with codecs.open(f"{clean_submissions_f}.txt", "w", "UTF-16") as f:  #
        f.write('\t'.join(csv) + '\n')
        for line in csv_submissions:
            f.write('\t'.join([line[k] for k in csv]) + '\n')


def rename_tmp_banners():
    """
    banners are created in the same order as in the clean_submissions_f.txt file
    :return:
    """
    df = pd.read_csv(f'{clean_submissions_f}.txt', sep='\t', encoding='utf-16')
    for i in range(0, df.shape[0]):
        src = df.iloc[i]['banner_name']
        if i == 0:
            src = src.replace('1', '')
        src = Path('_private/tmp_banners') / Path(src)
        dst = Path('_private/tmp_banners') / Path(df.iloc[i]['code']).with_suffix(src.suffix)
        src.rename(dst)


def generate_session_pages():
    cleaned_submissions = json.load(open(f"{clean_submissions_f}.json", "r"))
    # book keeping
    session_path = Path('pyconde/content/program/')
    session_path.mkdir(exist_ok=True)
    in_place_submissions = session_path.glob('*')
    tpl = """_model: session 
---
code: {code}
---
title: {title}
---
description: {short_decription}
---
twitter_image: {twitter_image}
---
speakers: {speakers}
---
submission_type: {submission_type}
---
domains: {domains}
---
biography: {biography}
---
affiliation: {affiliation}
---
track: {track}
---
body: {body}

"""

    for submission in cleaned_submissions:
        biography = []
        for x in submission['speakers']:
            biography.append(f"#### {x.get('name')}")
            if x.get('affiliation'):
                biography.append(f'Affiliation: {x["affiliation"]}')
            biography.append(f'')
            biography.append(f"{x['biography']}")
            social = []
            if x.get('@twitter'):
                social.append(f"[Twitter](https://twitter.com/{x['@twitter'].replace('@', '')})")
            if x.get('github'):
                social.append(f"[Gthub]({x['github']})")
            if x.get('homepage'):
                social.append(f"[Homepage]({x['homepage']})")
            if social:
                biography.append(' • '. join(social))
        biography = '\n\n'.join(biography)

        domains = f"{' • '.join(submission['domains'].split(', '))}"
        expertise = f"Python Knowledge {submission['python_skill']} • Domain Expertise: {submission['domain_expertise']}"

        slug = slugify(f"{submission['track']}-{submission['code']}-{submission['title']}-{' '.join([x.get('name') for x in submission['speakers']])}")
        dirname = session_path / slug
        dirname.mkdir(exist_ok=True)
        with open(dirname / "contents.lr", "w") as f:
            f.write(tpl.format(
                title=submission['title'],
                short_decription=submission['short_description'],
                code=submission['code'],
                body=submission['description'],
                domains=domains,
                track=submission['track'],
                expertise=expertise,
                submission_type=submission['submission_type'],
                speakers=', '.join([x['name'] for x in submission['speakers']]),
                biography=biography,
                affiliation=', '.join([x['affiliation'] for x in submission['speakers']]),
                twitter_image=f"/static/media/twitter/{submission['code']}.jpg",
            ))
        # break
    # TODO redirect renames to new dir


if __name__ == "__main__":
    # load_speakers()
    # update_session_pages(use_cache=True)
    # save_csv_for_banners()
    # rename_tmp_banners()
    generate_session_pages()
