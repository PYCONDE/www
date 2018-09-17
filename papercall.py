import sys
import json
import mistune
from jinja2 import Template
import re
from unicodedata import normalize
import os
from openpyxl import load_workbook
import click


TALKS_INFO_PATH = '../pycon/talks/'

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
_regex = re.compile('[^a-z0-9]')


# First parameter is the replacement, second parameter is your input string


def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        word = word.decode('ascii')
        word = _regex.sub('', word)
        if word:
            result.append(word)
    return str(delim.join(result))


def enrich(entry):
    entry["slug"] = slugify(entry["title"])
    entry["tags_str"] = " ".join(entry["tags"][:10])
    return entry





def get_talk(speaker):
    speaker = speaker.replace(',  PhD', '')
    for d in data:
        if d["name"] == speaker.replace(', ', ','):  # pdh = workaround/hotfix
            return d
    return


tpl = """_model: page_markdown
---
title: {{title}}
---
head_extra:

<meta name="twitter:card" content="summary" />
<meta name="twitter:site" content="@pyconde" />
<meta name="twitter:title" content="{{name|escape}}: {{title|escape}}" />
<meta name="twitter:description" content="{{abstract|escape}}" />
<meta name="twitter:image" content="https://de.pycon.org/files/logo.png" />
---
body:

# {{title}}
<div class="avatar">
![]({{avatar}})
**[{{name}}]({{url}})** {% if twitter %}([@{{twitter}}](http://twitter.com/{{twitter}})){% endif %}


{{bio}}
</div>
## Abstract
{%if tags_str %}
*Tags:* {{tags_str}}{%endif%}

{{abstract}}


## Description
{{description}}

"""

tpl_index = """_model: page_markdown
---
title: {{kind|capitalize}}
---
body:

{% for entry in data %}
# [{{entry.title}}](./{{entry.slug}}/)
**{{entry.name}}**

{{entry.abstract}}

{% endfor %}
"""

template = Template(tpl)
template_index = Template(tpl_index)

tutorials = ['practical-data-cleaning-101',
             'machine-learning-as-a-service',
             'machine-learning-as-a-service',
             'metaclasses-when-to-use-and-when-not-to-use',
             'network-analysis-using-python',
             'topic-modelling-and-a-lot-more-with-nlp-framework-gensim',
             'how-to-fund-your-company',
             'playing-with-google-ml-apis-and-websockets',
             ]


def dump(entry, kind='tutorials'):
    dirname = 'pyconde/content/schedule/{}/{}/'.format(kind, entry['slug'])
    print(dirname)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    with open(os.path.join(dirname, 'contents.lr'), 'w') as f:
        f.write(template.render(entry))


def gen():
    d = filter(lambda entry: entry["slug"] in tutorials, data)
    with open('pyconde/content/schedule/tutorials/contents.lr', 'w') as f:
        f.write(template_index.render(kind="tutorials", data=d))

    d = filter(lambda entry: entry["slug"] not in tutorials, data)
    with open('pyconde/content/schedule/talks/contents.lr', 'w') as f:
        f.write(template_index.render(kind="talks", data=d))

    for entry in filter(lambda entry: entry["slug"] in tutorials, data):
        dump(entry)
        # print(template.render(entry))
    for entry in filter(lambda entry: entry["slug"] not in tutorials, data):
        dump(entry, kind='talks')




def parse(s):
    if "available" in s:
        return {}
    first, speaker = s.split("[[")
    speaker = speaker.rstrip("]").replace(',', ', ')  # , seperates multiple speakers
    tags = first.rsplit('(', 1)[1].rstrip(")")
    tags = [x.strip() for x in tags.split("|") if x.strip() and x.strip() != "Other"]
    tags = [t.replace('Business Track', 'Business') for t in tags]
    if 'Data Science' in tags:
        tags.insert(0, 'PyData')

    talk = get_talk(speaker)

    if talk is None:
        print(speaker)
        talk = {"title": "FIXME", "slug": "FIXME"}
    return {"speaker": speaker, "tags": tags, "title": talk["title"], "slug": talk["slug"]}


def gen_schedule_databag():
    wb = load_workbook(os.path.join(TALKS_INFO_PATH, 'schedule.xlsx'))
    sheet = wb['Sheet1']

    d1 = [2, 3, 5, 6, 8, 9]
    d2 = [11, 12, 13, 15, 16, 18, 19]
    d3 = [21, 22, 23, 25, 26]
    talks = {}
    for day, rows in enumerate([d1, d2, d3]):
        for row_nr, row in enumerate(rows):
            try:
                key = "THEATRE_{}_{}".format(day + 1, row_nr + 1)
                value = sheet["C{}".format(row)].value
                talks[key] = parse(value)

                key = "LECTURE_{}_{}".format(day + 1, row_nr + 1)
                value = sheet["E{}".format(row)].value
                talks[key] = parse(value)

                key = "FLOOR_{}_{}".format(day + 1, row_nr + 1)
                value = sheet["B{}".format(row)].value
                talks[key] = parse(value)
            except Exception as e:
                pass  # just for debugging

    json.dump(talks, open("pyconde/databags/talks.json", "w"), indent=4)

    tutorials = {}
    for day, rows in enumerate([[2, 5, 8], [11, 15, 18], [21, 25]]):
        for row_nr, row in enumerate(rows):
            key = "MUSEUM_{}_{}".format(day + 1, row_nr + 1)
            value = sheet["D{}".format(row)].value
            tutorials[key] = parse(value)
    json.dump(tutorials, open("pyconde/databags/tutorials.json", "w"), indent=4)


import click

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
import hashlib
def gen_gravatar(email):
    h = hashlib.md5(email.encode("utf-8")).hexdigest()
    return "https://www.gravatar.com/avatar/{}".format(h)


def fix_data():
    data = json.load(open("pyconde/databags/talks.json"))
    for talk in data.values():
        for speaker in talk["the_speakers"]:
            speaker["gravatar"] = gen_gravatar(speaker["email"])
            if "homepage" in speaker and not speaker["homepage"].strip().startswith("http:"):
                speaker["homepage"] = "http://{}".format(speaker["homepage"].strip())
    json.dump(data, open("pyconde/databags/talks.json", "w"), indent=4)


@click.command()
@click.option('--schedule_dir', envvar="SCHEDULE_DIR", default="", help='The directory with the schedule and the speaker json')
def cli(schedule_dir):
    """Simple program that greets NAME for a total of COUNT times."""

    xsl_file = os.path.join(schedule_dir, "pyconde18-pydata-ka-schedule.xlsx")
    json_file = os.path.join(schedule_dir, "pyconde18-pydata-ka-all_submissions.json")

    #gen()
    # bada()
    #gen_schedule_databag()

    #data = json.load(open("pyconde/databags/talks.json"))
    #gen_schedule_talks(data)

    fix_data()

if __name__ == '__main__':
    cli()