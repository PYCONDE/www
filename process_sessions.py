import hashlib
import json
import os
import re
import codecs
import shutil
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
    if not accepted_only:
        submissions = get_all_data_from_pretalx(url)
    else:
        submissions = get_all_data_from_pretalx(url, params={'state': 'accepted'})
        submissions.extend(get_all_data_from_pretalx(url, params={'state': 'confirmed'}))
    # add custom data
    for submission in submissions:
        spkrs = ' '.join([x.get('name') for x in submission['speakers']])
        slug = slugify(f"{submission.get('track', {}).get('en', 'pycon-pydata')}-{submission['code']}-{submission['title']}-{spkrs}")
        submission['slug'] = slug

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
            # normalize twitter
            if _id == 115:
                speaker[qa_map[_id]] = qa.get('answer').split('/')[-1].replace('@', '')
                speaker['twitter'] = f"https://twitter.com/{speaker[qa_map[_id]]})"
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


def gen_gravatar(email):
    h = hashlib.md5(email.encode("utf-8")).hexdigest()
    return "https://www.gravatar.com/avatar/{}".format(h)


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
               'speakers', 'state', 'submission_type', 'title', 'track', 'slug']
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
            take_on = ['affiliation', 'homepage', '@twitter', 'twitter', 'github', 'biography']
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
    program_path = 'pyconde/content/program/'
    session_path = Path(program_path)
    session_path.mkdir(exist_ok=True)
    in_place_submissions = [x.name for x in session_path.glob('*')]
    in_place_submissions.remove('contents.lr')  # only dirs
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
python_skill: {python_skill}
---
domain_expertise: {domain_expertise}
---
meta_title: {meta_title}
---
categories: {categories_list}
---
body: {body}

"""
    all_categories = {}  # collect categories automatically add newly discovered ones
    redirects = {}  # simple url with talk code redirecting to full url, used for auto urls from other systems

    for submission in cleaned_submissions:

        # filter keynotes or other types
        if 'Talk' in submission['submission_type']:
            pass
        elif 'Tutorial' in submission['submission_type']:
            pass
        else:
            continue

        biography = []
        for x in submission['speakers']:
            biography.append(f"#### {x.get('name')}")
            if x.get('affiliation'):
                biography.append(f'Affiliation: {x["affiliation"]}')
            biography.append(f'')
            biography.append(f"{x['biography']}")
            social = []
            if x.get('twitter'):
                social.append(f"[Twitter]({x['twitter']})")
            if x.get('github'):
                social.append(f"[Github]({x['github']})")
            if x.get('homepage'):
                social.append(f"[Homepage]({x['homepage']})")
            if social:
                biography.append(' • '. join(social))
        biography = '\n\n'.join(biography)

        speaker_twitters = ' '.join([x.get('@twitter') for x in submission['speakers'] if x.get('@twitter')])
        meta_title = f"{submission['title']} {speaker_twitters} #PyConDE #PyDataBerlin #PyData"

        # easier to handle on website as full text
        python_skill = f"Python Skill Level {submission['python_skill']}"
        domain_expertise = f"Domain Expertise {submission['domain_expertise']}"

        domains = submission['domains']

        categories = [submission['track'], python_skill, domain_expertise] + [submission['submission_type'].split(' ')[0]] + domains.split(', ')
        slugified_categories = [slugify(x) for x in categories]
        categories_list = ', '.join(slugified_categories)
        all_categories.update({slugify(x): x for x in categories})

        redirects[submission['code']] = submission['slug']
        redir_dirname = session_path / submission['code']
        if submission['code'] in in_place_submissions:
            in_place_submissions.remove(submission['code'])
        create_redirect(redir_dirname, submission['slug'])

        dirname = session_path / submission['slug']
        if dirname.name in in_place_submissions:
            # print("slug hasn't changed")
            in_place_submissions.remove(dirname.name)

        dirname.mkdir(exist_ok=True)
        with open(dirname / "contents.lr", "w") as f:
            f.write(tpl.format(
                title=submission['title'],
                short_decription=submission['short_description'],
                code=submission['code'],
                body=submission['description'],
                domains=domains,
                track=submission['track'],
                submission_type=submission['submission_type'].split(' ')[0],
                speakers=', '.join([x['name'] for x in submission['speakers']]),
                biography=biography,
                affiliation=', '.join([x['affiliation'] for x in submission['speakers']]),
                twitter_image=f"/static/media/twitter/{submission['code']}.jpg",
                meta_title=meta_title,
                categories=categories,
                categories_list=categories_list,
                python_skill=python_skill,
                domain_expertise=domain_expertise,
            ))
    if in_place_submissions:  # leftover dirs
        for zombie in in_place_submissions:
            # TODO could try to redirect zombies via code
            zpath = Path('pyconde/content/program/') / zombie
            shutil.rmtree(zpath)

    for category in all_categories:
        cpath = Path('pyconde/content/program-categories') / category
        if not cpath.exists():
            cpath.mkdir()
            with open(cpath / 'contents.lr', 'w') as f:
                f.write("""name: {0}
---
title: {0} Session List
---
description: All {0} sessions at the PyConDE & Pydata Berlin 2019 conference
---""".format(all_categories[category]))


def create_redirect(redir_dirname, slug):
    redir_dirname.mkdir(exist_ok=True)
    with open(redir_dirname / "contents.lr", "w") as f:
        f.write("""_model: redirect
---
target: /program/{}
---
_discoverable: no""".format(slug))


if __name__ == "__main__":
    # load_speakers()
    # update_session_pages(use_cache=True)
    update_session_pages(use_cache=False)
    # save_csv_for_banners()
    # rename_tmp_banners()
    generate_session_pages()
