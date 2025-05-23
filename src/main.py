from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QLabel, QComboBox, QTextEdit
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils.file_handler import open_ics_file, save_csv_file
from utils.ics_parser import parse_ics
from utils.csv_writer import write_csv
import os
import fitz  # PyMuPDF
from subprocess import run, CalledProcessError
import pandas as pd
import sys
from PyQt6.QtWidgets import QCheckBox, QGroupBox


class MainWindow(QMainWindow):
    def __init__(self):
        print("Initializing MainWindow...")  # Debug statement
        super().__init__()
        self.setWindowTitle("ICS to CSV Converter")
        self.setGeometry(100, 100, 1200, 600)  # Increased width for PDF preview

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)  # Use horizontal layout for side-by-side previews

        self.file_path = ""
        self.salary_per_hour = 160

        # Initialize class variables
        self.entries = []  # To store all parsed entries
        self.filtered_entries = []  # To store filtered entries
        print("MainWindow initialized.")  # Debug statement
        self.init_ui()

    def init_ui(self):
        # Left-side layout for controls
        left_layout = QVBoxLayout()

        self.file_button = QPushButton("Select ICS File")
        self.file_button.clicked.connect(self.select_file)
        left_layout.addWidget(self.file_button)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search entries...")
        self.search_bar.textChanged.connect(self.filter_entries)
        left_layout.addWidget(self.search_bar)

        # Add Month Selector with Checkboxes
        self.month_group = QGroupBox("Select Months")
        self.month_layout = QVBoxLayout()

        self.select_all_checkbox = QCheckBox("All Months")
        self.select_all_checkbox.setChecked(True)  # Set "All Months" checkbox to checked initially
        self.select_all_checkbox.clicked.connect(self.toggle_month_checkboxes)
        self.month_layout.addWidget(self.select_all_checkbox)

        self.month_checkboxes = {}
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        for month in months:
            checkbox = QCheckBox(month)
            checkbox.setEnabled(False)  # Disable individual month checkboxes initially
            checkbox.stateChanged.connect(self.filter_entries)
            self.month_checkboxes[month] = checkbox
            self.month_layout.addWidget(checkbox)

        self.month_group.setLayout(self.month_layout)
        left_layout.addWidget(self.month_group)

        # Add Salary Per Hour text entry
        self.salary_input = QLineEdit()
        self.salary_input.setPlaceholderText("Enter Salary Per Hour")
        self.salary_input.setText(str(self.salary_per_hour))  # Set default value
        self.salary_input.textChanged.connect(self.update_salary_per_hour)
        left_layout.addWidget(self.salary_input)

        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        left_layout.addWidget(self.preview_area)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_files)  # Save files when clicked
        left_layout.addWidget(self.save_button)

        # Add left layout to the main layout
        self.layout.addLayout(left_layout)

        # Right-side layout for LaTeX and PDF previews
        right_layout = QVBoxLayout()

        # Horizontal layout for LaTeX and PDF previews
        preview_layout = QHBoxLayout()

        self.latex_preview_area = QTextEdit()
        self.latex_preview_area.setReadOnly(True)
        preview_layout.addWidget(self.latex_preview_area)

        self.pdf_preview_label = QLabel("PDF Preview will appear here.")
        self.pdf_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.pdf_preview_label)

        # Add the horizontal preview layout to the right layout
        right_layout.addLayout(preview_layout)

        self.layout.addLayout(right_layout)
        print("UI initialized.")  # Debug statement

    def toggle_month_checkboxes(self, state):
        """Enable or disable individual month checkboxes based on the 'All Months' checkbox."""
        print(f"DEBUG: State value: {state}")  # Debug statement
        if state:
            print("All Months selected: Disabling individual month checkboxes.")
            # Disable individual month checkboxes when "All Months" is checked
            for checkbox in self.month_checkboxes.values():
                checkbox.setEnabled(False)
        else:
            print("All Months deselected: Enabling individual month checkboxes.")
            # Enable individual month checkboxes when "All Months" is unchecked
            for checkbox in self.month_checkboxes.values():
                checkbox.setEnabled(True)

        # Trigger filtering when toggling "All Months"
        self.filter_entries()

    def update_salary_per_hour(self):
        try:
            self.salary_per_hour = float(self.salary_input.text())
            print(f"Updated Salary Per Hour: {self.salary_per_hour}")  # Debug statement
        except ValueError:
            self.salary_per_hour = 0  # Default to 0 if input is invalid
            print("Invalid Salary Per Hour input. Defaulting to 0.")

    def select_file(self):
        self.file_path, _ = QFileDialog.getOpenFileName(self, "Open ICS File", "", "ICS Files (*.ics)")
        if self.file_path:
            self.load_entries()

    def calculate_entry_salaries(self):
        """Calculate the salary for each entry based on the start and end times."""
        for entry in self.entries:
            hours_worked = (entry['end_time'].hour - entry['start_time'].hour) + \
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
            entry['entry_salary'] = hours_worked * self.salary_per_hour
            print(f"Calculated entry_salary for {entry['summary']}: {entry['entry_salary']}")  # Debug statement

    def load_entries(self):
        try:
            self.entries = parse_ics(self.file_path)  # Store parsed entries in the class variable
            print(f"DEBUG: Entries returned by parse_ics: {self.entries}")  # Debug statement
            self.calculate_entry_salaries()  # Calculate salaries for each entry
            self.filter_entries()  # Filter entries based on current search and month
        except Exception as e:
            self.preview_area.setText(f"Error loading ICS file: {e}")

    def update_csv_preview(self):
        csv_data = write_csv(self.filtered_entries, self.salary_per_hour)
        self.preview_area.setText(csv_data)

    def update_latex_preview(self):
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) +
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)
        latex_table = self.generate_latex_table(self.filtered_entries, total_salary, total_hours, self.salary_per_hour)
        self.latex_preview_area.setText(latex_table)

    def update_pdf_preview(self):
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) +
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)
        latex_table = self.generate_latex_table(self.filtered_entries, total_salary, total_hours, self.salary_per_hour)
        self.compile_latex_to_pdf(latex_table)

    def filter_entries(self, *args):
        """Filter entries based on search text and selected months."""
        if not isinstance(self.entries, list):
            self.preview_area.setText("Error: Invalid data format. Expected a list.")
            return

        valid_entries = [entry for entry in self.entries if isinstance(entry, dict)]
        search_text = self.search_bar.text().lower()

        # Determine selected months
        selected_months = []
        if self.select_all_checkbox.isChecked():
            selected_months = list(range(1, 13))  # All months
        else:
            for i, month in enumerate(self.month_checkboxes.keys(), start=1):
                if self.month_checkboxes[month].isChecked():
                    selected_months.append(i)

        # If no months are selected, filter out all entries
        if not selected_months:
            self.filtered_entries = []
        else:
            # Filter entries based on search text and selected months
            self.filtered_entries = [
                entry for entry in valid_entries
                if (search_text in entry.get('summary', '').lower() or search_text in entry.get('description', '').lower()) and
                (entry['date'].month in selected_months)
            ]

        # Update previews in real time
        self.update_csv_preview()
        self.update_latex_preview()
        self.update_pdf_preview()

    def convert_to_csv_and_latex(self):
        # Calculate total salary and total hours
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) + 
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)

        # Convert to CSV
        csv_data = write_csv(self.filtered_entries, self.salary_per_hour)
        csv_data += f"\nTotal Hours,,,{total_hours:.2f},Salary Per Hour,,,{self.salary_per_hour},Total Salary,,,{total_salary}"  # Add total hours, salary per hour, and total salary at the bottom
        save_csv_file(csv_data)

        # Convert to LaTeX
        latex_table = self.generate_latex_table(self.filtered_entries, total_salary, total_hours, self.salary_per_hour)
        self.latex_preview_area.setText(latex_table)

        # Compile LaTeX to PDF and display it
        self.compile_latex_to_pdf(latex_table)

    def generate_latex_table(self, entries, total_salary, total_hours, salary_per_hour):
        # Define reusable variables for LaTeX document structure
        header = (
            "\\documentclass{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage{geometry}\n"
            "\\geometry{a4paper, margin=1in}\n"
            "\\begin{document}\n"
        )
        footer = "\\end{document}"
        address = (
            "\\begin{minipage}[t]{0.45\\textwidth}\n"
            "{John Doe}\\\\\n"
            "123 Main Street\\\\\n"
            "Cityville, 12345\\\\\n"
            "Country\\\\\n"
            "\\end{minipage}\n"
        )
        banking_details = (
            "\\begin{minipage}[t]{0.45\\textwidth}\n"
            "Bank Name\\\\\n"
            "Clearing number: 0000-0\\\\\n"
            "Account number: 000 000 000-0\\\\\n"
            "IBAN: XX00 0000 0000 0000 0000 0000\\\\\n"
            "BIC: BANKCODE\\\\\n"
            "\\end{minipage}\n"
        )
        table_header = (
            "\\begin{table}[h!]\n"
            "\\centering\n"
            "\\begin{tabular}{|l|l|l|l|l|}\n"
            "\\hline\n"
            "\\textbf{Summary} & \\textbf{Date} & \\textbf{Start Time} & \\textbf{End Time} & \\textbf{Salary} \\\\\n"
            "\\hline\n"
        )
        empty_table = (
            "\\multicolumn{5}{|c|}{No entries available} \\\\\n"
            "\\hline\n"
        )
        table_footer = "\\end{tabular}\n\\caption{Invoice Details}\n\\end{table}\n"

        if not entries:
            return (
            header
            + "\\begin{center}{\\LARGE \\textbf{Salary Invoice}}\\end{center}\n"
            + "\\vspace{0.5cm}\n"
            + "\\noindent\n"
            + address
            + "\\hfill\n"
            + banking_details
            + "\\vspace{1cm}\n"
            + table_header
            + empty_table
            + table_footer
            + footer
            )

        # Group entries by month
        grouped_entries = {}
        for entry in entries:
            month = entry['date'].strftime("%B")
            grouped_entries.setdefault(month, []).append(entry)

        latex = (
            header
            + "\\begin{center}{\\LARGE \\textbf{Salary Invoice}}\\end{center}\n"
            + "\\vspace{0.5cm}\n"
            + "\\noindent\n"
            + address
            + "\\hfill\n"
            + banking_details
            + "\\vspace{1cm}\n"
            + table_header
        )

        for month, month_entries in grouped_entries.items():
            latex += f"\\multicolumn{{5}}{{|c|}}{{\\textbf{{{month}}}}} \\\\\\\\\n\\hline\n"
            month_total_salary = 0
            month_total_hours = 0

            for entry in month_entries:
                hours_worked = (entry['end_time'].hour - entry['start_time'].hour) + \
                               (entry['end_time'].minute - entry['start_time'].minute) / 60
                month_total_hours += hours_worked
                month_total_salary += entry['entry_salary']
                latex += f"{entry['summary']} & {entry['date']} & {entry['start_time']} & {entry['end_time']} & {entry['entry_salary']:.2f} \\\\\n"

            latex += (
            f"\\hline\n\\multicolumn{{3}}{{|r|}}{{\\textbf{{Total for {month}:}}}} & "
            f"\\textbf{{{month_total_hours:.2f} hours}} & \\textbf{{{month_total_salary:.2f}}} \\\\\\\\\n"
            "\\hline\n"
            )

        latex += (
            f"\\hline\n\\multicolumn{{2}}{{|r|}}{{\\textbf{{Total Hours:}} {total_hours:.2f}}} & "
            f"\\multicolumn{{1}}{{r|}}{{\\textbf{{Salary Per Hour:}} {salary_per_hour:.2f}}} & "
            f"\\multicolumn{{2}}{{r|}}{{\\textbf{{Total Salary:}} {total_salary:.2f}}} \\\\\n"
            "\\hline\n"
            + table_footer
            + footer
        )

        return latex

    def compile_latex_to_pdf(self, latex_code):
        # Save LaTeX code to a temporary file
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        tex_file = os.path.join(temp_dir, "output.tex")
        pdf_file = os.path.join(temp_dir, "output.pdf")

        with open(tex_file, "w") as file:
            file.write(latex_code)

        # Compile LaTeX to PDF using pdflatex
        try:
            run(["pdflatex", "-output-directory", temp_dir, tex_file], check=True)
            self.display_pdf(pdf_file)
        except CalledProcessError as e:
            self.latex_preview_area.setText(f"Error compiling LaTeX: {e}")

    def display_pdf(self, pdf_path):
        # Render the first page of the PDF as an image
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap()
        image_path = pdf_path.replace(".pdf", ".png")
        pix.save(image_path)

        # Display the image in the QLabel
        pixmap = QPixmap(image_path)
        self.pdf_preview_label.setPixmap(pixmap)

    def save_files(self):
        # Save CSV
        csv_data = write_csv(self.filtered_entries, self.salary_per_hour)
        save_csv_file(csv_data)

        # Save LaTeX
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) +
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)
        latex_table = self.generate_latex_table(self.filtered_entries, total_salary, total_hours, self.salary_per_hour)
        with open("output.tex", "w") as file:
            file.write(latex_table)

        # Save PDF
        self.compile_latex_to_pdf(latex_table)
        print("Files saved successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())