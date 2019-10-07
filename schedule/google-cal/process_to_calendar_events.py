from hashlib import md5
import json
import datetime
import string

DATABAG_TALKS = '/Users/hendorf/Documents/code/PyConDE-www/website/databags/schedule_databag.json'

with open(DATABAG_TALKS, 'r') as f:
    data = json.load(f)

events = []
keys = set()
for _date in data['dates']:
    _datum = _date['datum']
    for room in _date['rooms']:
        room_name = room['room_name']
        for session in room['sessions']:
            if session['type'].lower() not in ("talk", "tutorial", "community", 'keynote'):
                continue

            starttime = f"{_datum}T{session['start']}:00+02:00"
            starttime = datetime.datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%S+02:00")  # validation
            endtime = f"{_datum}T{session['end']}:00+02:00"
            try:
                if 'ibm party' in session['title'].lower():
                    endtime = starttime + datetime.timedelta(hours=6)
                else:
                    endtime = datetime.datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%S+02:00")  # validation
            except Exception as e:
                if session['title'] in ('Keynote Q&A', 'Keynote Q&A Session'):
                    endtime = starttime + datetime.timedelta(minutes=45)
                elif session['title'] == 'Morning Announcements':
                    endtime = starttime + datetime.timedelta(minutes=10)
                elif 'panel' in session['title'].lower() :
                    endtime = starttime + datetime.timedelta(minutes=60)
                else:
                    continue

            if session['code']:
                _id = session['code']
            else:
                _id = f"{''.join([x.lower() for x in session['title'] + _datum + session['end'] if x in string.ascii_letters + string.digits])}"
            _id = md5(_id.encode()).hexdigest()

            if _id in keys:
                continue  # avoid duplicates with same session name
            keys.add(_id)

            events.append(
                {
                    'summary': f"{session['title']}" + (f"({session['speaker_names']})" if session['speaker_names'] else ""),
                    'location': room_name,
                    'description': session['description'],
                    'start': {
                        'dateTime': starttime.strftime("%Y-%m-%dT%H:%M:%S+02:00"),
                        'timeZone': 'Europe/Berlin',
                    },
                    'end': {
                        'dateTime': endtime.strftime("%Y-%m-%dT%H:%M:%S+02:00"),
                        'timeZone': 'Europe/Berlin',
                    },
                    'source': {
                        'url': f"http://pycon.de/program/{session['slug']}",
                        'title': 'PyConDE & PyData Berlin Schedule'
                    },
                    'reminders': {'useDefault': False, 'overrides': []},
                    'transparency': 'transparent',
                    'visibility': 'public',
                    'id': _id
                }
            )

with open('events.json', 'w') as f:
    json.dump(events, f, indent=4)
