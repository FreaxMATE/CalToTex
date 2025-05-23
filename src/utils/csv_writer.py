import csv
from io import StringIO

def write_csv(entries, salary_per_hour):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Start Time', 'End Time', 'Salary Per Hour', 'Total Salary'])

    for entry in entries:
        writer.writerow([entry['date'], entry['start_time'], entry['end_time'], salary_per_hour, entry['entry_salary']])

    return output.getvalue()