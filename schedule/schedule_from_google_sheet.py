# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.2.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# ## Add Schedule from Google Sheet
#
# Requires Google API access and credentials stored in **google_credentials.json**.

import json
import re
from pprint import pprint
from datetime import datetime
from unicodedata import normalize
import pandas as pd

from typing import List, Union, Sequence
from pathlib import Path
from itertools import cycle

from schedule.google_download import download_sheet

project_root = Path(__file__).resolve().parents[1]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '1uQcyxmWUuc8H1dpB8rN3FU3AF6Sy0BtKzokLXe7W9N0'
RANGE_NAME = 'Schedule Layout'  # get all of the the sheet

DATABAG_PATH = project_root / 'website/databags/schedule_databag.json'
# path to json with submission for data verifications
SUBMISSIONS_PATH = project_root / 'website/databags/submissions.json'
PROGRAM_BASE_URL = '/program'


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


class ScheduleFromGSheet:

    def __init__(self, spreadsheet_id: str, range_name: str, databag_path='databag.json'):
        """

        :param spreadsheet_id: Google spreadsheet id - can be copied from url in browser.
        :param range_name: name of the sheet (tab) here, the whole sheet is to be read in.
        """
        self.sheet: pd.DataFrame = None
        self.spreadsheet_id = spreadsheet_id
        self.range_name = range_name

        self.rooms: pd.Series = None
        self.locations: pd.Series = None
        self.use: pd.Series = None

        self.daystore = {}
        self.databag = []
        self.databag_path = Path(databag_path)

        self.submissions = {}

        self.scheduled_codes = {}  # keep track of scheduled codes to warn about dupes
        self.scheduled_bag = {}  # keep track anything schedule to reduce noise

    def save_to_json(self):
        with open(self.databag_path, 'w') as f:
            json.dump(self.databag, f, indent=4)

    def load_submissions(self, path: str):
        with open(path, 'r') as f:
            submissions = json.load(f)
            self.submissions = {x['code']: x for x in submissions}

    def set_rooms(self, row_label: Union[str, int], col_labels: Union[str, List[str]]):
        """
        By convention the room names are the same for all coumns in an instance.
        In case the room names are diiffernt, make multiple instances of this class and join later.
        :param row_label:
        :param col_labels:
        :return:
        """
        self.rooms = self.colum_indexed_line(row_label, col_labels)

    def set_locations(self, row_label: Union[str, int], col_labels: Union[str, List[str]]):
        """ like set_rooms """
        self.locations = self.colum_indexed_line(row_label, col_labels)

    def set_use(self, row_label: Union[str, int], col_labels: Union[str, List[str]]):
        """ like set_rooms """
        self.use = self.colum_indexed_line(row_label, col_labels)

    def colum_indexed_line(self, row_label: Union[str, int], col_labels: Union[str, List[str]]):
        if not isinstance(row_label, str):
            row_label = str(row_label)
        return self.get_from_sheet(row_label, col_labels)

    def read_online_sheet(self):
        """
        _sheet_data is a list of lists, these lists have different sizes.
        Data type alls str to avoid unexpected datatype conversions
        :return:
        """
        _sheet_data = download_sheet(SPREADSHEET_ID, RANGE_NAME)
        #
        #
        self.sheet = pd.DataFrame(_sheet_data, dtype=str)
        # rename to Excel column names
        self.sheet.columns = [x for x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:len(self.sheet.columns)]]
        # rename to Excel row numbers, make row labels str
        self.sheet.index = [str(x) for x in range(1, self.sheet.index.shape[0] + 1)]
        self.sheet.fillna('', inplace=True)

    def get_day_from_schedule(
            self,
            day_start_row: Union[str, int],
            day_end_row: Union[str, int],
            time_colum_name: str,
            rooms_filter: Union[List[str], str] = None,
            datum: datetime = None,
            **kwargs
    ):
        """
        Read the data for a day and return all cell contents aligned with times:
        - A day ranges from row number day_start_row to day_end_row  (Excel 1-indexed)
        - The time is in column time_colum_name
        - if there is no room set in rooms for the column, the column is skipped
        - closure: rooms
        """
        day_str = datum.strftime('%A, %B %d')
        datum = datum.date().isoformat()
        if not self.daystore.get(datum):
            self.daystore[datum] = {
                'day': day_str,
                'datum': datum,
                'rooms': []
            }

        time_talks = self.get_from_sheet(f'{day_start_row}:{day_end_row}', time_colum_name)
        # allign room, program and time
        day_sessions = self.get_sessions_for_rooms(day_end_row, day_start_row, rooms_filter, time_talks, datum)
        self.daystore[datum]['rooms'].extend(day_sessions)
        self.update_databag()

    def update_databag(self):
        """ bookkeeping, databag is the export format"""
        self.databag = {'dates': [v for k, v in self.daystore.items()]}
        # self.databag = self.daystore

    def get_from_sheet(self,
                       row_labels: Union[str, List[str]],
                       col_labels: Union[str, List[str]]
                       ):
        """
        returns a section from the Dataframe
        DataFrame index and column names must be unique for slicing
        :param: row_labels: label, list or :-range of labels
        :param: col_labels: label, list or :-range of labels
        """
        if isinstance(row_labels, int):
            row_labels = str(row_labels)
        if isinstance(row_labels, str) and ':' in row_labels:
            df_idx = list(self.sheet.index)
            # print(df_idx)
            row_from, row_to = row_labels.split(':')
            row_labels = df_idx[df_idx.index(row_from): df_idx.index(row_to) + 1]
        if isinstance(col_labels, str) and ':' in col_labels:
            df_cols = list(self.sheet.columns)
            col_from, col_to = col_labels.split(':')
            col_labels = df_cols[df_cols.index(col_from): df_cols.index(col_to) + 1]
        return self.sheet.loc[row_labels, col_labels]

    def get_sessions_for_rooms(self,
                               day_end_row: Union[str, int],
                               day_start_row: Union[str, int],
                               rooms_filter: pd.Series,
                               time_talks: Sequence[str],
                               datum: str
                               ):
        # make list of columns to series from rooms, label and roon name are required
        if not isinstance(rooms_filter, pd.Series):
            rooms_filter = self.rooms[rooms_filter]

        day_sessions = []
        for room_name, label in list(zip(rooms_filter, rooms_filter.index)):
            if not room_name:
                continue
            program = {
                'room_name': room_name,
                'location': self.locations[label],
                'use': self.use[label],
                'data_tab': slugify(f"{datum} {room_name}")
            }
            sessions = self.get_room_sessions(day_end_row, day_start_row, label, time_talks)
            program['sessions'] = sessions
            day_sessions.append(program)
        return day_sessions

    def get_room_sessions(self,
                          day_end_row: Union[str, int],
                          day_start_row: Union[str, int],
                          label: str,
                          time_talks: Sequence[str],
                          ):
        """
        To create a data dictionary, the start time and the sessions need to be aligned.
        The sessions are store in columns by row. Each ro is aligned to a room.
        :param day_end_row: label from index
        :param day_start_row: label from index
        :param label: Excel column name (A, B,…)
        :param time_talks: sequence with start times
        :return:
        """
        sessions = self.get_from_sheet(f'{day_start_row}:{day_end_row}', label)
        sessions = [x for x in list(zip(time_talks, sessions)) if x[0]]
        sessions = [self.handle_session(x) for x in sessions]
        return sessions

    def handle_session(self, session_tuple):
        """
        custom handling of contents, e. g.:
        - check for patterns as talk ids
        :param session_tuple: (time, session text)
        :return:
        """
        time, contents_str = session_tuple
        if '@' in contents_str:
            contents_str, time = contents_str.split('@')
        contents = contents_str.split()

        session_keys = [
            # same keys as in submissions
            'code', 'name', 'track', 'duration', 'description', 'short_description', 'python_skill', 'domain_expertise', 'domains', 'slug',
            'title',
            # custom keys for databag
            'speaker_names', 'type', 'url', 'plenary', 'add_to_class', 'clipcard_icon',
        ]
        session_details = dict(zip(session_keys, cycle([""])))  # init
        session_details['time'] = time

        # extra handling of tracks
        if contents and time == 'sessionname':
            session_details['title'] = contents_str
            session_details['type'] = "sessionname"

        # identify code from pretalx by pattern, submissions have to be loaded
        elif contents and self.submissions.get(contents[0]):
            # take on all matching keys from submissions
            session = self.submissions.get(contents[0])
            session_details.update({k: v for k, v in session.items() if k in session_keys})
            session_details['type'] = self.classify_session_type(session.get('submission_type'))
            session_details['speaker_names'] = ', '.join([
                f"{x.get('name', '')} {'(' + x.get('affiliation', '') + ')' if x.get('affiliation', '') else ''}".strip()
                for x in session.get('speakers')])
            session_details['url'] = f"{PROGRAM_BASE_URL}/{session['slug']}"

            # bookkeeping
            if contents[0] in self.scheduled_codes:
                print(f"WARNING: {contents[0]} is scheduled already!")
            else:
                self.scheduled_codes[contents[0]] = session_details['time']

        # customized handling of text from sheet
        elif contents and 'registration' in contents_str.lower():
            session_details['title'] = "Registration & Coffee"
            session_details['type'] = "Break"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Pick up your badge and network."
            session_details['clipcard_icon'] = "fa-ticket"
        elif contents and 'coffee' in contents_str.lower():
            session_details['title'] = "Coffee Break"
            session_details['type'] = "Break"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Break for coffee and refreshments."
            session_details['clipcard_icon'] = "fa-coffee"
        elif contents and 'lunch' == contents_str.lower():
            session_details['title'] = "Lunch"
            session_details['type'] = "Break"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Light lunch and refreshments."
            session_details['clipcard_icon'] = "fa-cutlery"
        elif contents and 'keynote:' in contents[0].lower():
            session_details['title'] = "Keynote"
            session_details['type'] = "Plenary"
            session_details['plenary'] = True
            session_details['duration'] = "00:45"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "To be announced soon."
            session_details['clipcard_icon'] = "fa-key"
        elif contents and 'open space' in contents_str.lower():
            session_details['title'] = "Open Space"
            session_details['type'] = "Community"
            session_details['duration'] = "00:30"
            session_details['track'] = "pycon-pydata"
            session_details['short_description'] = "Free, open space, please sign up at the registration."
            session_details['url'] = f"/open-space"  # convention
            session_details['clipcard_icon'] = "fa-sticky-note"
        elif contents and 'lighting talks' in contents_str.lower():
            session_details['title'] = "Lighting Talks"
            session_details['type'] = "Community"
            session_details['plenary'] = True
            session_details['duration'] = "00:45"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Five minutes to present almost anything, please sign up at the registration."
            session_details['url'] = f"/lightning-talks"  # convention
            session_details['clipcard_icon'] = "fa-bolt"
        elif contents and 'opening session' in contents_str.lower():
            session_details['title'] = "Opening Session"
            session_details['type'] = "Community"
            session_details['plenary'] = True
            session_details['duration'] = "00:15"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "The opening of the conference - a big, cheerful gathering."
            session_details['url'] = f"/opening-session"  # convention
            session_details['clipcard_icon'] = "fa-rocket"
        elif contents and 'community space' in contents_str.lower():
            session_details['title'] = "Community Space"
            session_details['type'] = "Community"
            session_details['plenary'] = True
            session_details['duration'] = "00:10"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Community announcements and presentations just before the keynote."
            session_details['url'] = f"/community-space"  # convention
            session_details['clipcard_icon'] = "fa-users"
        elif contents and 'closing session' in contents_str.lower():
            session_details['title'] = "Closing Session"
            session_details['type'] = "Community"
            session_details['plenary'] = True
            session_details['duration'] = "00:30"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Time to say goodbye and appreciate the volunteers!"
            session_details['url'] = f"/closing-session"  # convention
            session_details['clipcard_icon'] = "fa-rocket"
        elif contents and 'sprint orientation' in contents_str.lower():
            session_details['title'] = "Sprint Orientation"
            session_details['type'] = "Community"
            session_details['plenary'] = True
            session_details['duration'] = "00:15"
            session_details['track'] = "pycon-pydata"
            session_details['add_to_class'] = "color--primary"
            session_details['short_description'] = "Presentation of the sprint projects."
            session_details['url'] = f"/sprints"  # convention
            session_details['clipcard_icon'] = "fa-rocket"
        elif contents and 'psv' in contents_str.lower():
            session_details['title'] = "PSV Mitgliederversammung"
            session_details['type'] = "PSV"
            session_details['duration'] = "01:30"
            session_details['track'] = "pyconde"
            session_details['short_description'] = "The annual meeting of the Python Softwareverband e.V. (Germany Python associaltion), " \
                                                   "you must be a member of the PSV to attend."
            session_details['url'] = 'https://python-verband.org/verband'
            session_details['clipcard_icon'] = "fa-user-secret"
        elif contents and 'pyladies lunch' in contents_str.lower():
            session_details['title'] = contents_str
            session_details['duration'] = "01:00"
            session_details['url'] = 'blog/pyladies-lunch/'
            session_details['clipcard_icon'] = "fa-users"
            session_details['track'] = "pycon-pydata"
            session_details['type'] = "Community"
            session_details['domains'] = "Diversity"
            session_details['speaker_names'] = "PyLadies"
        elif contents and 'end' == contents_str.lower():
            session_details['title'] = "End of the day"
            session_details['track'] = "pyconde"
            session_details['short_description'] = "End of the day"
            session_details['clipcard_icon'] = "fa-hand-spock-o"
        elif contents:
            session_details['title'] = contents_str
            session_details['type'] = "Community"
            session_details['track'] = "pycon-pydata"
            session_details['short_description'] = "Community session."
            session_details['clipcard_icon'] = "fa-users"
        else:
            session_details['title'] = ''
            session_details['clipcard_icon'] = ""

        # bookkeeping
        if contents and not self.submissions.get(contents[0]) and contents_str not in self.scheduled_bag and time != 'sessionname':
            print(f"CHECK: not a session with code:  {contents_str}")
            self.scheduled_bag[contents_str] = time

        return session_details

    @classmethod
    def classify_session_type(cls, session_type: str):
        session_type = session_type.lower()
        for keyword in ['Talk', 'Tutorial', 'Keynote', 'Panel']:
            if keyword.lower() in session_type:
                return keyword
        return ''


def update_schedule_from_sheet():
    s = ScheduleFromGSheet(SPREADSHEET_ID, RANGE_NAME, DATABAG_PATH)
    s.read_online_sheet()
    s.set_rooms(5, "A:L")
    s.set_locations(7, "A:L")
    s.set_use(6, "A:L")

    s.load_submissions(SUBMISSIONS_PATH)

    talks_time_colum_name = "A"
    talks_colums = ["C", "D", "E", "F", "G", "K"]

    tuts_time_colum_name = "H"
    tuts_colums = ["I", "J"]

    days = {
        'wed-talks': {
            'datum': datetime(2019, 10, 9),
            'day_start_row': 10,
            'day_end_row': 28,
            'time_colum_name': talks_time_colum_name,
            'rooms_filter': talks_colums,
        },
        'wed-tuts': {
            'datum': datetime(2019, 10, 9),
            'day_start_row': 10,
            'day_end_row': 28,
            'time_colum_name': tuts_time_colum_name,
            'rooms_filter': tuts_colums,
        },
        'thu-talks': {
            'datum': datetime(2019, 10, 10),
            'day_start_row': 36,
            'day_end_row': 57,
            'time_colum_name': talks_time_colum_name,
            'rooms_filter': talks_colums,
        },
        'thu-tuts': {
            'datum': datetime(2019, 10, 10),
            'day_start_row': 36,
            'day_end_row': 57,
            'time_colum_name': tuts_time_colum_name,
            'rooms_filter': tuts_colums,
        },
        'fri-talks': {
            'datum': datetime(2019, 10, 11),
            'day_start_row': 65,
            'day_end_row': 83,
            'time_colum_name': talks_time_colum_name,
            'rooms_filter': talks_colums,
        },
        'fri-tuts': {
            'datum': datetime(2019, 10, 11),
            'day_start_row': 65,
            'day_end_row': 83,
            'time_colum_name': tuts_time_colum_name,
            'rooms_filter': tuts_colums,
        },
    }
    for name, day in days.items():
        s.get_day_from_schedule(**day)
    s.save_to_json()
    not_scheduled = set(s.submissions) - set(s.scheduled_codes)
    for ns in not_scheduled:
        print(f"NOT SCHEDULED: {ns} {s.submissions.get(ns)['title']}")


if __name__ == '__main__':
    update_schedule_from_sheet()
