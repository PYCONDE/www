import hashlib
import json
import subprocess
import codecs
import shutil
from datetime import timedelta
from pathlib import Path

import requests
import pandas as pd

from schedule.schedule_from_google_sheet import update_schedule_from_sheet, slugify

project_root = Path(__file__).resolve().parents[1]
tokenpath = project_root / '_private/TOKEN.txt'
TOKEN = tokenpath.open().read()

base_url = 'https://pretalx.com'
event = 'pyconde-pydata-berlin-2019'
headers = {'Accept': 'application/json, text/javascript', 'Authorization': f'Token {TOKEN}'}

submissions_path = project_root / Path('_private/submissions.json')
speakers_path = project_root / Path('_private/speakers.json')
clean_submissions_f = project_root / Path("website/databags/submissions.json")  # filepath
schedule__path = project_root / Path("website/databags/schedule_databag.json")  # may be added later


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

    with submissions_path.open('w') as f:
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
                speaker['twitter'] = ""
                handle = qa.get('answer').split('/')[-1].replace('@', '').strip()
                speaker[qa_map[_id]] = handle
                if handle:
                    speaker['twitter'] = f"https://twitter.com/{speaker[qa_map[_id]]}"
                else:
                    pass
            if _id == 117:
                if qa.get('answer').strip() and 'github.com' not in qa.get('answer', ""):
                    speaker['github'] = f"https://github.com/{qa.get('answer').strip()}"
            if _id == 114:
                if qa.get('answer').strip() and 'http' not in qa.get('answer', ""):
                    speaker['homepage'] = f"http://{qa.get('answer').strip()}"

        the_speakers.append(speaker)
    with speakers_path.open('w') as f:
        json.dump(the_speakers, f, indent=4)


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


def load_schedule():
    the_schedule = {}
    if not schedule__path.exists():
        return
    schedule = json.load(schedule__path.open())
    for d in schedule['dates']:
        for r in d['rooms']:
            for s in r['sessions']:
                if s.get('code'):
                    the_schedule[s['code']] = {
                        'time': d['day'].split(',')[0].lower() + "-" + s['time'],
                        'day': d['day'].split(',')[0].lower(),
                        'room': r['room_name'],
                        'start_time': s['time']
                    }
    return the_schedule


def update_session_pages(use_cache=False):
    """
    Refactored for 2019 setup
    - mangle submission data from API
    - make avaibale in databags
    """
    if not use_cache:
        load_submissions()
        load_speakers()
    submissions = json.load(submissions_path.open())
    speakers = json.load(speakers_path.open())
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
    json.dump(cleaned_submissions, clean_submissions_f.open('w'), indent=4)


def save_csv_for_banners():
    """
    CSV with banner info only, saved as UTF-16 for useage in Illustrator for auto banner generation
    :return:
    """
    cleaned_submissions = json.load(clean_submissions_f.open())
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
    df.to_csv(clean_submissions_f.with_suffix('.csv'), sep='\t', encoding='utf-8', index=False)
    with codecs.open(clean_submissions_f.with_suffix('.txt'), "w", "UTF-16") as f:  #
        f.write('\t'.join(csv) + '\n')
        for line in csv_submissions:
            f.write('\t'.join([line[k] for k in csv]) + '\n')


def rename_tmp_banners():
    """
    banners are created in the same order as in the clean_submissions_f.txt file
    :return:
    """
    df = pd.read_csv(clean_submissions_f.with_suffix('.txt'), sep='\t', encoding='utf-16')
    for i in range(0, df.shape[0]):
        src = df.iloc[i]['banner_name']
        if i == 0:
            src = src.replace('1', '')
        src = Path('_private/tmp_banners') / Path(src)
        dst = Path('_private/tmp_banners') / Path(df.iloc[i]['code']).with_suffix(src.suffix)
        src.rename(dst)


def generate_session_pages():
    cleaned_submissions = json.load(clean_submissions_f.open())
    # book keeping
    session_path = project_root / 'website/content/program/'
    session_path.mkdir(exist_ok=True)
    in_place_submissions = [x.name for x in session_path.glob('*') if x.name[0] != '.']
    in_place_submissions.remove('contents.lr')  # only dirs
    tpl = """_model: session 
---
code: {code}
---
title: {title}
---
description: {short_description}
---
short_description: {short_description}
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
room: {room}
---
start_time: {start_time}
---
day: {day}
---
meta_title: {meta_title}
---
meta_twitter_title: {meta_twitter_title}
---
categories: {categories_list}
---
slugified_slot_links: {slugified_slot_links}
---
body: {body}

"""
    all_categories = {}  # collect categories automatically add newly discovered ones
    redirects = {}  # simple url with talk code redirecting to full url, used for auto urls from other systems

    the_schedule = load_schedule()

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
            biography.append(f"{x['biography'] if x['biography'] else ''}")
            social = []
            if x.get('twitter'):
                social.append(f"[Twitter]({x['twitter']})")
            if x.get('github'):
                social.append(f"[Github]({x['github']})")
            if x.get('homepage'):
                social.append(f"[Homepage]({x['homepage']})")
            if social:
                biography.append('visit the speaker at: ' + ' • '.join(social))
        biography = '\n\n'.join(biography)

        speakers = ', '.join([x['name'] for x in submission['speakers']])
        speaker_twitters = ' '.join([x.get('@twitter') for x in submission['speakers'] if x.get('@twitter')])
        meta_title = f"{submission['title']} {speakers.replace(',', '')} PyConDE & PyDataBerlin 2019 conference "
        meta_twitter_title = f"{submission['title']} @{speaker_twitters} #PyConDE #PyDataBerlin #PyData"

        # easier to handle on website as full text
        python_skill = f"Python Skill Level {submission['python_skill']}"
        domain_expertise = f"Domain Expertise {submission['domain_expertise']}"

        domains = submission['domains']

        categories = [submission['track'], python_skill, domain_expertise] + [submission['submission_type'].split(' ')[0]] + domains.split(
            ', ')

        # add date and session start time for navidgation
        slot_links = []
        start_time, room, day = None, None, None
        if submission.get('code') and the_schedule.get(submission.get('code')):
            start_time, room = the_schedule[submission['code']]['start_time'], the_schedule[submission['code']]['room']
            day = the_schedule[submission['code']]['day']
            slot_links = [day, the_schedule[submission['code']]['time']]
        categories = categories + slot_links
        slugified_categories = [slugify(x) for x in categories]
        slugified_slot_links = ', '.join([slugify(x) for x in slot_links])
        categories_list = ', '.join(slugified_categories)
        all_categories.update({slugify(x).replace('---', '-').replace('--', '-'): x for x in categories})

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
                short_description=submission['short_description'],
                short_description_html=submission['short_description'],
                code=submission['code'],
                body=submission['description'],
                domains=domains,
                track=submission['track'],
                submission_type=submission['submission_type'].split(' ')[0],
                speakers=speakers,
                biography=biography,
                affiliation=', '.join([x['affiliation'] for x in submission['speakers']]),
                twitter_image=f"/static/media/twitter/{submission['code']}.jpg",
                meta_title=meta_title,
                meta_twitter_title=meta_twitter_title,
                categories=categories,
                categories_list=categories_list,
                python_skill=python_skill,
                domain_expertise=domain_expertise,
                slugified_slot_links=slugified_slot_links,
                start_time=start_time,
                room=room,
                day=day,
            ))
    if in_place_submissions:  # leftover dirs
        for zombie in in_place_submissions:
            # TODO could try to redirect zombies via code
            zpath = project_root / Path('website/content/program/') / zombie
            try:
                code = zombie.split('-')[1].upper()
                if redirects.get(code):
                    create_redirect(zpath, slug=redirects.get(code))
            except Exception as e:
                shutil.rmtree(zpath)

    for category in all_categories:
        cpath = project_root / Path('website/content/program-categories') / category
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


def run_lekor_update():
    command = "cd website && lektor build --output-path ../www"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    proc_stdout = process.communicate()[0].strip()
    for line in proc_stdout.decode('utf-8').split('\n'):
        print(line)


if __name__ == "__main__":
    # update_session_pages(use_cache=False)
    # update_schedule_from_sheet()
    # update_session_pages(use_cache=True)
    # generate_session_pages()
    run_lekor_update()
