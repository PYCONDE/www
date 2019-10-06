### 1. process_to_calendar_events.py

Build Calendar events, mashup of:

transform json to consumable calendar input.
    
output: events.json

### 2. sync_events_to_calendar.py

* Sync data from events.json with Google calendar.
* required/private: API key client_secret.json
* Calendar id is static in code (PyConDE calendar)
* ids of events must be unique!
