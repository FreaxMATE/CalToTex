from PyQt6.QtWidgets import QFileDialog

def open_ics_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def save_csv_file(csv_data):
    file_path, _ = QFileDialog.getSaveFileName(None, "Save CSV File", "", "CSV Files (*.csv)")
    if file_path:
        with open(file_path, 'w') as file:
            file.write(csv_data)