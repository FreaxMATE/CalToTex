from icalendar import Calendar
from datetime import datetime

def parse_ics(file_path):
    entries = []
    with open(file_path, 'r') as file:
        calendar = Calendar.from_ical(file.read())
        for component in calendar.walk():
            if component.name == "VEVENT":
                start = component.get('dtstart').dt
                end = component.get('dtend')
                summary = component.get('summary', '')
                description = component.get('description', '')
                # Handle missing 'dtend' by using 'dtstart' as fallback
                if end:
                    end = end.dt
                else:
                    end = start  # Assume the event has no end time

                # Ensure 'start' and 'end' are datetime objects
                if isinstance(start, datetime) and isinstance(end, datetime):
                    entries.append({
                        'summary': summary,
                        'date': start.date(),
                        'start_time': start.time(),
                        'end_time': end.time(),
                        'description': description,
                        'entry_salary': 0  # Placeholder, calculated later
                    })

    # Sort entries by date
    entries.sort(key=lambda entry: entry['date'])
    return entries