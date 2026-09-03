"""file operations including importing, exporting/backup, schema validation, 
and .csv export operations"""

import shutil
import sqlite3
from datetime import datetime
from typing import Any, Optional
from tkinter import filedialog, messagebox

import pandas as pd

from config import EXPECTED_COLUMNS, REQUIRED_SCHEMA, TIMETABLE_SCHEMA
from database import Database_module
from input_validation import validate_input

def import_input_file(log: Any, db_view: Any) -> Optional[str]:
    """import a CSV file, validate it, and return the created database path."""
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")]) # allow user to import csv file
    if file_path:
        if not (file_path.endswith(".csv")): # check it is a csv file
            messagebox.showerror("File Error", "The selected file is not a .csv file.")
            log.add_message("File Error: The selected file is not a .csv file.", "error")
            return None
        else:
            try:
                imported_dataframe = pd.read_csv(file_path) # read file to csv
            except Exception as e:
                messagebox.showerror("File Error", f"The following error occurred: '{e}'")
                log.add_message(f"File Error: The following error has occured: '{e}'", "error")
                return None
            else:
                log.add_message(f"File imported successfully from: {file_path}")
                input_errors= validate_input(imported_dataframe, EXPECTED_COLUMNS) # validate file

                if input_errors != []: # if there are errors, errors are printed to log
                    messagebox.showerror("File Error", "Input file is in incorrect format")
                    log.add_message(f"Input file has incorrect format, errors include the following:", "error")
                    for error in input_errors:
                        log.add_message(f"{error}", "error")
                else:
                    log.add_message(f"Input file matches necessary format", "info") 
                    log.add_message(f"File is being converted into a database")
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") 
                    db_path = f"Timetabling_database_{timestamp}.db" # update db path to not be blank
                    db = Database_module(db_path) # create database module 
                    log.add_message(f"Database created with file name {db_path}", "info")
                    db.insert_data(imported_dataframe)
                    log.add_message(f"Input data inserted into database", "info")
                    
                    db_view.db = db
                    db_view.db.reload_hash_table()
                    log.add_message("Database data can be viewed in 'Databases' submenu")
                    return db_path

                    
                
    else:
        messagebox.showinfo("No File Selected", "No file was selected.")
        log.add_message("File Info: No file was selected.", "warning")
        return None
    

def backup_database(db_path: str, log: Any) -> None:
    """creates backup of database to a location specified by user"""
    if db_path != "": # check that database actually exists (presence check)
        try:
            #allow user to choose save path
            save_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite Database", "*.db")], title = "Save database backup as")
            if not save_path: # presence check on save path
                log.add_message("No backup location selected: backup cancelled", "warning")
                return
            shutil.copy2(db_path, save_path)#create copy of db
            log.add_message(f"Database backed up to: {save_path}", "info")
            messagebox.showinfo("Backup successful", f"Database successfully backed up to: {save_path}")
        except Exception as e:
            log.add_message(f"Database backup failed due to the following error: {e}", "error")
            messagebox.showerror("Backup failed", f"Failed to backup due to error: {e}")
    else:
        log.add_message(f"No database created", "warning") # tell user no database present
def validate_db_schema(conn: sqlite3.Connection, log: Any = None) -> bool:
    """checks if input data has correct schema"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='timetables'") # check if timetables table is present
        timetables_table_present = True if cursor.fetchone() else False # if it is present, set this to true, otherwise set to false
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='timetable_students'")# check if timetable_student table is present
        timetables_student_table_present = True if cursor.fetchone() else False # if it is present, set this to true, otherwise set to false
        schema_to_check_against = REQUIRED_SCHEMA.copy()

        if timetables_table_present or timetables_student_table_present: # if either of the timetable tables are present, validate against timetable schema
            schema_to_check_against.update(TIMETABLE_SCHEMA)
            
        # validate the tables
        for table, expected_columns in schema_to_check_against.items():
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone(): # check all tables are present
                if log:
                    log.add_message(f"Imported database has invalid schema: Required table: {table} is not present", "error")
                return False
            
            # check that tables have correct fields
            cursor.execute(f"PRAGMA table_info({table})")
            results = cursor.fetchall()
            input_columns = []
            for row in results:
                input_columns.append(row[1])
            missing_columns = set(expected_columns) - set(input_columns)
            if missing_columns:
                if log:
                    log.add_message(f"Imported database has invalid schema: Table {table} is missing columns {missing_columns}", "error")
                return False
        if log:
            log.add_message("Input database has correct schema", "info")
        return True
    except Exception as e:
        if log:
            log.add_message(f"An error occured when validating the input database: {e}")
        return False

def import_database(log: Any, db_view: Any) -> Optional[str]:
    """allow the user to select a database and return its path when valid."""
    import_path = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db")],title="Select Database to Import") # allow user to input database

    if not import_path: # presence check
        log.add_message("No database selected to import", "warning")
        return
    try:
        with sqlite3.connect(import_path) as conn:
            if not validate_db_schema(conn, log): # make sure schema matches
                messagebox.showerror("Invalid Database", "Input database did not match the necessary schema")
                log.add_message("Database import failed due to invalid schema", "error")
                return None
        db_path = import_path # update global database path variable
        db_view.db = Database_module(db_path) # create new database module
        db_view.db.reload_hash_table() # reload hash tables for searching

        log.add_message(f"Database successfully imported from {import_path}", "info")
        messagebox.showinfo("Import successful", f"Database successfully imported from location {import_path}")
        return db_path

    except Exception as e: # catch any errors and print them
        log.add_message(f"Database import failed due to error: {e}", "error")
        messagebox.showerror("Import Failed", f"Failed to import database due to error: {e}")

def export_to_csv(chromosome, data, filepath=None, log: Any = None):
    """export timetables to csv"""
    try:
        if filepath is None: # default filepath
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = f"Output_timetable_{timestamp}.csv"

        # turn teacher ids to teacher names
        teacher_names_map = data.get("teacher_names")
        student_names_map = data.get("student_names")


        rows = [] # rows of data
        for lesson, timeslot, room in chromosome: # add each class to list of data
            teacher_id = lesson["teacher"]
            teacher_name = teacher_names_map[teacher_id]
            
            student_list = []
            for student_id in lesson["students"]:
                student_name = student_names_map.get(student_id)
                student_list.append(student_name)
            rows.append({
                "Subject": lesson["subject"],
                "Teacher": teacher_name,
                "Students": ", ".join(student_list),
                "Timeslot": timeslot,
                "Room": room
            })

        df = pd.DataFrame(rows) # convert to DataFrame
        df.to_csv(filepath, index = False) # save as CSV
        return f"Timetable exported successfully to file location {filepath}"
    except Exception as e:
        if log:
            log.add_message(f"Error exporting timetable: {e}")
        return None
