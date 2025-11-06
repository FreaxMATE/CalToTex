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
import configparser


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
        
        # Load personal and banking information from config
        self.config_info = self.load_config()
        
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

        # Add save buttons in a horizontal layout
        save_buttons_layout = QHBoxLayout()
        
        self.save_csv_button = QPushButton("Save CSV")
        self.save_csv_button.clicked.connect(self.save_csv)
        save_buttons_layout.addWidget(self.save_csv_button)
        
        self.save_tex_button = QPushButton("Save TEX")
        self.save_tex_button.clicked.connect(self.save_tex)
        save_buttons_layout.addWidget(self.save_tex_button)
        
        self.save_pdf_button = QPushButton("Save PDF")
        self.save_pdf_button.clicked.connect(self.save_pdf)
        save_buttons_layout.addWidget(self.save_pdf_button)
        
        left_layout.addLayout(save_buttons_layout)
        
        self.save_all_button = QPushButton("Save All")
        self.save_all_button.clicked.connect(self.save_all)
        left_layout.addWidget(self.save_all_button)

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

    def load_config(self):
        """Load personal and banking information from config file."""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.txt')
        
        # Default values
        default_config = {
            'name': 'John Doe',
            'address_line1': 'Street Address 123',
            'address_line2': '12345 City Name',
            'address_line3': 'Country',
            'bank_name': 'Bank Name',
            'clearing_number': '1234-5',
            'account_number': '123 456 789-0',
            'iban': 'XX00 0000 0000 0000 0000 0000',
            'bic': 'XXXXXXXX'
        }
        
        try:
            config.read(config_path)
            return {
                'name': config.get('Personal Information', 'name', fallback=default_config['name']),
                'address_line1': config.get('Personal Information', 'address_line1', fallback=default_config['address_line1']),
                'address_line2': config.get('Personal Information', 'address_line2', fallback=default_config['address_line2']),
                'address_line3': config.get('Personal Information', 'address_line3', fallback=default_config['address_line3']),
                'bank_name': config.get('Banking Information', 'bank_name', fallback=default_config['bank_name']),
                'clearing_number': config.get('Banking Information', 'clearing_number', fallback=default_config['clearing_number']),
                'account_number': config.get('Banking Information', 'account_number', fallback=default_config['account_number']),
                'iban': config.get('Banking Information', 'iban', fallback=default_config['iban']),
                'bic': config.get('Banking Information', 'bic', fallback=default_config['bic'])
            }
        except Exception as e:
            print(f"Error loading config file: {e}. Using default values.")
            return default_config

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
            # Recalculate entry salaries with the new rate
            self.calculate_entry_salaries()
            # Update all previews to reflect the new calculations
            self.filter_entries()
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
            f"{{{self.config_info['name']}}}\\\\\n"
            f"{self.config_info['address_line1']}\\\\\n"
            f"{self.config_info['address_line2']}\\\\\n"
            f"{self.config_info['address_line3']}\\\\\n"
            "\\end{minipage}\n"
        )
        banking_details = (
            "\\begin{minipage}[t]{0.45\\textwidth}\n"
            f"{self.config_info['bank_name']}\\\\\n"
            f"Clearing number: {self.config_info['clearing_number']}\\\\\n"
            f"Account number: {self.config_info['account_number']}\\\\\n"
            f"IBAN: {self.config_info['iban']}\\\\\n"
            f"BIC: {self.config_info['bic']}\\\\\n"
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
            latex += f"\\multicolumn{{5}}{{|c|}}{{\\textbf{{{month}}}}} \\\\ \n\\hline\n"
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
            f"\\textbf{{{month_total_hours:.2f} hours}} & \\textbf{{{month_total_salary:.2f}}} \\\\ \n"
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

    def save_csv(self):
        """Save only the CSV file."""
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) +
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)
        csv_data = write_csv(self.filtered_entries, self.salary_per_hour)
        csv_data += f"\nTotal Hours,,,{total_hours:.2f},Salary Per Hour,,,{self.salary_per_hour},Total Salary,,,{total_salary}"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "output.csv", "CSV Files (*.csv)")
        if file_path:
            with open(file_path, 'w') as file:
                file.write(csv_data)
            print(f"CSV file saved successfully to {file_path}")

    def save_tex(self):
        """Save only the LaTeX file."""
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) +
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)
        latex_table = self.generate_latex_table(self.filtered_entries, total_salary, total_hours, self.salary_per_hour)
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save TEX File", "output.tex", "LaTeX Files (*.tex)")
        if file_path:
            with open(file_path, "w") as file:
                file.write(latex_table)
            print(f"TEX file saved successfully to {file_path}")

    def save_pdf(self):
        """Save only the PDF file."""
        total_salary = sum(entry['entry_salary'] for entry in self.filtered_entries)
        total_hours = sum((entry['end_time'].hour - entry['start_time'].hour) +
                        (entry['end_time'].minute - entry['start_time'].minute) / 60
                        for entry in self.filtered_entries)
        latex_table = self.generate_latex_table(self.filtered_entries, total_salary, total_hours, self.salary_per_hour)
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF File", "output.pdf", "PDF Files (*.pdf)")
        if file_path:
            # Save LaTeX to a temporary file
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            tex_file = os.path.join(temp_dir, "temp_output.tex")
            
            with open(tex_file, "w") as file:
                file.write(latex_table)
            
            # Compile LaTeX to PDF
            try:
                pdf_temp_file = os.path.join(temp_dir, "temp_output.pdf")
                run(["pdflatex", "-output-directory", temp_dir, tex_file], check=True)
                
                # Copy the compiled PDF to the user's chosen location
                import shutil
                shutil.copy(pdf_temp_file, file_path)
                print(f"PDF file saved successfully to {file_path}")
            except CalledProcessError as e:
                print(f"Error compiling LaTeX to PDF: {e}")

    def save_all(self):
        """Save CSV, LaTeX, and PDF files."""
        self.save_csv()
        self.save_tex()
        self.save_pdf()
        print("All files saved successfully.")

    def save_files(self):
        """Legacy method - calls save_all for backward compatibility."""
        self.save_all()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())