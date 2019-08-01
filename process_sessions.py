import sys
import json
import mistune
import re
import os
import click
import hashlib
import click
from unicodedata import normalize
from openpyxl import load_workbook
from unicodedata import normalize
from jinja2 import Template
from functools import partial
from openpyxl import load_workbook
from datetime import timedelta


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


if __name__ == "__main__":
    cli()
