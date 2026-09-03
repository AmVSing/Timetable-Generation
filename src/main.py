"""
Changes:
- Added timetable view functionality
- Added ability to change parameters
- Added timetable viewing attributes to database search
- Added timetables menu to view timetables
"""




# Import necessary modules
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
from typing import List, Callable, Optional, Dict, Tuple, Union, Any
import pandas as pd
from pandas import DataFrame
from datetime import datetime
import time
import shutil
import sqlite3
import sqlparse
import random
import math
from collections import defaultdict





#----Default values for variables and constants----
# Colours (constants) for GUI elements
DEFAULT_BUTTON_BG_COLOUR = "#484752"  # Colour of buttons, set to grey
DEFAULT_BUTTON_TEXT_COLOUR = "#FFFFFF"  # Colour of text in buttons, set to white
DEFAULT_BUTTON_TEXT_HOVER_COLOUR = "#FFD700"  # Colour of buttons when hovering, set to gold
DEFAULT_SIDEBAR_BG_COLOUR = "#2b2b2d"  # Colour of sidebar, set to dark grey
DEFAULT_LOG_BG_COLOUR = "#FFFFFF" # Colour of log (part where text appears), set to white
DEFAULT_LOG_TEXT_BG_COLOUR = "#FFFFFF" # Colour of the frame around the log, set to white
DEFAULT_LOG_TEXT_FG_COLOUR = "#000000" # Colour of text in the log, set to black
DEFAULT_LOG_RESIZER_COLOUR = "dark grey" # Colour of frame above log that allows user to resize it, set to dark grey
default_font_size = 9 # This value is a variable: it can be changed in the font size setter in settings 
db_path = "" # stores the path of the current database
# Database schema for validating imported database
REQUIRED_SCHEMA = {
    "students": ["student_id", "full_name"],
    "subjects": ["subject_code", "subject_name"],
    "teachers": ["teacher_id", "full_name"],
    "teacher_subject": ["teacher_id", "subject_code"],
    "teacher_availability": ["teacher_id", "day"],
    "rooms": ["room_code", "capacity", "block_code"],
    "room_subject": ["room_code", "subject_code"],
    "blocks": ["block_code", "block_name"],
    "block_list": ["block_code", "nearby_block_code"],
    "choices": ["student_id", "subject_code", "is_backup"]
}
# These tables may or may not be present in the database depending on whether timetabling was done before saving
TIMETABLE_SCHEMA = {
    "timetables": ["timetable_id", "class_id", "subject_code", "teacher_id", "room_code", "timeslot"],
    "timetable_students": ["timetable_id", "student_id"]
}
# Columns expected in input file
EXPECTED_COLUMNS = [

     "entity_type", "full_name", "preferred_class_1", "preferred_class_2",
    "preferred_class_3", "preferred_class_4", "backup_preference",
    "subject_specialities", "availability", "room_code", "capacity",
    "taught_subjects", "block_name", "block_code", "nearby_blocks", "subject_code", "subject_name"
]
REQUIRED_LESSONS = 4
DESIRED_LESSONS = 5




# Default genetic algorithm penalties (can be changed by user in parameters)
ga_soft_constraints = {
    "teacher_penalty": 6, 
    "room_penalty": 60,
    "student_penalty": 5
}



# Other global variable initialisation, used by various objects and functions
imported_dataframe: Optional[DataFrame] = None # Global variable to check whether dataframe has been imported or not
current_open_submenu: Optional["Sidebar_menu"] = None # Used to check whether submenu is open
current_open_database_view: Optional[tk.Widget]= None # Global variable to indicate which (if any) database views are open
current_left_padding: int = 200 # Global variable to track left padding to dynamically calculate log width





#----Input validation functions----
def validate_input(df: pd.DataFrame, expected_columns: List[str]) -> List[str]:
    """
    Checks that input dataframe is valid based on defined rules:
    """
    errors =[] # List of all errors caught
    # Validate errors, add any errors to errors list
    header_errors = validate_header(df,expected_columns)
    if header_errors:
        return header_errors # If any header errors, immediately stop checking if input is valid and return output (prevents syntax errors from incorrect headers)
    
    errors.extend(check_duplicates(df)) # Add any duplicate rows to the errors list
    # Map each entity type to the type of validation 
    entity_to_validation_map = {
        "Student": validate_student_row,
        "Teacher": validate_teacher_row,
        "Room": validate_room_row,
        "Block": validate_block_row,
        "Subject": validate_subject_row,
    } # Maps entity type to validation function
    
    # Iterate through every row in the df
    for i, row in df.iterrows():
        entity_type=row.get("entity_type", None) # Get entity type from row
        
        # Check entity type is not missing/invalid
        if pd.isna(entity_type) or entity_type not in entity_to_validation_map:
            errors.append(f"Row number {i+2} has invalid or missing entity type of: {entity_type}")
            continue # To break to next iteration to prevent trying to map things incorrectly
        
        validation_function = entity_to_validation_map[entity_type]
        row_errors = validation_function(row)
        formatted_errors = [] # List of errors formatted to show row number
        for error in row_errors:
            formatted_errors.append(f"Row {i+2}: {error}") # allows user to find wher errors are in input data
        errors.extend(formatted_errors)
    return errors  

def validate_header(df: pd.DataFrame, expected_columns: List[str]):
    """Validate the header (first row) of the input file"""
    errors = []
    
    # Check if number of columns don't match
    df_columns = list(df.columns)
    if len(df_columns) != len(expected_columns):
        errors.append(f"Column number error. Expected {len(expected_columns)}, input had {len(df_columns)}")
        return errors
    # Check if names of columns don't match
    for i in range(len(expected_columns)):
        if df_columns[i] != expected_columns[i]:
            errors.append(f"Column name error in {i+1} column. Expected {expected_columns[i]}, got {df_columns[i]}")
    return(errors)

def validate_student_row(row:pd.Series) -> List[str]:
    """
    Check if each student row is valid

    """
    errors = [] # List of errors in row
    # Fields required in each row
    required_fields = [
        "full_name", "preferred_class_1", "preferred_class_2",
        "preferred_class_3", "backup_preference"
    ]
    # Fields that MUST be empty in each row
    empty_fields = ["subject_specialities", "availability", "room_code", "capacity", "taught_subjects", 
                    "block_code", "block_name", "nearby_blocks", "subject_code", "subject_name"]

    errors.extend(entity_validator_function(row, required_fields, empty_fields, "student")) # Add errors to errors list

    class_fields = ["preferred_class_1",
        "preferred_class_2",
        "preferred_class_3",
        "preferred_class_4",
        "backup_preference"
    ] # List of all class fields
    chosen_classes = [] # List of all classes chosen by student
    for field in class_fields:
        if pd.notna(row[field]): # If the field is not empty
            chosen_classes.append(row[field]) # Add the class to the list of chosen classes
    if len(chosen_classes) != len(set(chosen_classes)): # sets do not store duplicates, hence if the lengths are not the same, there is a duplicate
        errors.append(f"Duplicate class found in student preferences in row")
    return errors

def validate_teacher_row(row:pd.Series) -> List[str]:
    """
    Check if each teacher row is valid
    """
    # Fields required in each row
    required_fields = ["full_name", "subject_specialities", "availability"]
    # Fields that MUST be empty in each row
    empty_fields = ["preferred_class_1", "preferred_class_2", "preferred_class_3", "preferred_class_4", "backup_preference", 
                    "room_code", "capacity", "taught_subjects", "block_code", "block_name", "nearby_blocks", "subject_code", 
                    "subject_name"]

    return entity_validator_function(row, required_fields, empty_fields, "teacher") # Return errors
    
def validate_room_row(row: pd.Series) -> List[str]:
    """
    Check if each room row is valid

    
    """
    # Fields required in each row
    required_fields = ["room_code", "capacity", "taught_subjects", "block_code"]

    # Fields that MUST be empty in each row
    empty_fields = ["full_name", "preferred_class_1", "preferred_class_2", "preferred_class_3", "preferred_class_4", "backup_preference", 
                    "subject_specialities", "availability", "block_name", "nearby_blocks", "subject_code", "subject_name"]
    return entity_validator_function(row, required_fields, empty_fields, "room") # Return errors

def validate_block_row(row: pd.Series) -> List[str]:
    """
    Check if each block row is valid
    
    """
    # Fields required in each row
    required_fields=["block_code", "nearby_blocks", "block_name"]

    # Fields that MUST be empty in each row
    empty_fields = ["full_name", "preferred_class_1", "preferred_class_2", "preferred_class_3", "preferred_class_4", "backup_preference", 
                    "subject_specialities", "availability", "room_code", "capacity", "taught_subjects", "subject_code", "subject_name"]

    return entity_validator_function(row,required_fields,empty_fields, "block") # Return errors
        
def validate_subject_row(row: pd.Series) -> List[str]:
    """
    Check if each subject row is valid
    
    """
        # Fields required in each row
    required_fields= ["subject_code", "subject_name"]
    # Fields that MUST be empty in each row
    empty_fields = ["full_name", "preferred_class_1", "preferred_class_2", "preferred_class_3", "preferred_class_4", "backup_preference", 
                    "subject_specialities", "availability", "room_code", "capacity", "taught_subjects", "block_code", "block_name", 
                    "nearby_blocks"]
    return entity_validator_function(row,required_fields,empty_fields, "subject") # Return errors

def entity_validator_function(row: pd.Series, required_fields: List[str], empty_fields: List[str], entity_type: str) -> List[str]:
    
    """
    Checks that all the required fields are present and all the disallowed fields are not
    """
    errors=[]
    # Iterate through fields and check if any required fields missing
    for field in required_fields:
        if pd.isna(row.get(field,None)):
            errors.append(f"Missing required field: {field} for {entity_type}")
    # Iterate through fields and check if any disallowed fields are present
    for field in empty_fields:
        if not pd.isna(row.get(field,None)):
            errors.append(f"Data should not present for field: {field} for {entity_type}")
    return errors

def check_duplicates(df: pd.DataFrame) -> List[str]:
    """Checks for duplicate rows in the input data"""
    errors =[] # List of duplicate rows
    duplicate_rows = df[df.duplicated()] # get list of duplicate rows
    if not duplicate_rows.empty: # If there are duplicate rows
        for row in duplicate_rows.index:
            errors.append(f"Duplicate row found at row number {row+2}")
    return errors








#----Database classes----
class Linked_list_node:
    # Node in a linked list that stores the position of next node, the hash and the value associated with the hash
    def __init__(self, data: str, primary_key: int, next_item: Optional["Linked_list_node"] = None) -> None:
        self.data = data # secondary key
        self.primary_key = primary_key # primary key related to the secondary key
        self.next_item = next_item # Pointer to next node in linked list

class Hash_table:
    
    def __init__(self, size: int) -> None:
        """Create a hash table of fixed size"""
        self.size = size # Number of buckets in hash table

        self.table = [None]* self.size # Creates a list (to represent hash table) of values initially all set to none
    
    def hash_function(self, data: str) -> int:
        # Using the djdb2 algorithm to hash a given key into a hash value, then storing in a bucket based on the remainder
        hash_value = 5381 # From my research, the number 5381 seems to result in the fewest collisions

        for char in data:
            # This carries out 5 binary left shifts then adds the hash value (equivalent to 33*hash_value), then adds the ascii for the character 
            hash_value = ((hash_value<<5) + hash_value) + ord(char) 
                
        bucket = hash_value % self.size # Place where the hash value will be stored
        return bucket

    def insert(self, primary_key: int, data: str) -> None:
        # Inserts a key into table alongside its associated hash 
        index = self.hash_function(data) # Place where the data will be stored
        new_node = Linked_list_node(data, primary_key, self.table[index]) # Create new node
        self.table[index] = new_node # Prepend new node into bucket



    def search(self, data: str):
        # Identifies which bucket the data is stored in by recalculating hash. 
        index = self.hash_function(data) # Place where the data is stored
        current_node = self.table[index] # First node in linked list

        primary_keys = [] # store primary keys returned in a list
        # If a linked list is already stored at the location, traverse through until the correct node is found, then return corresponding primary key
        while current_node != None:
            if current_node.data == data:
                primary_keys.append(current_node.primary_key)
            current_node = current_node.next_item # go to next node in linked list

        print(f"DEBUG: Hash Table Search for '{data}': {primary_keys}")
        return primary_keys # If there is a None type at the search location, return None

class Database_module:
    def __init__(self, db_name: str) -> None:
        """Start database conection"""
        self.conn=sqlite3.connect(db_name) # connect to db
        self.cursor=self.conn.cursor() # cursor to modify db

        # Create hash tables:
        self.student_hash_table = Hash_table(100) 
        self.teacher_hash_table = Hash_table(50)
        self.subject_hash_table = Hash_table(20)
        self.block_hash_table = Hash_table(10)
        
        
        self.create_tables() # Create the tables

    def delete_tables(self) -> None:
        # Used to reset tables every time code is run (just for testing purposes)
        tables = ["students", "subjects", "teachers", "teacher_subject", "teacher_availability", "rooms", "room_subject", "blocks", "nearby_blocks", "choices"]
        for table in tables:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.commit()
    
    def create_tables(self) -> None:
        """Create all the necessary tables (before timetabling) in the database"""

        # Create students table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS students(
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name VARCHAR NOT NULL
                            );
        """)

        # Create subjects table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
        subject_code VARCHAR PRIMARY KEY,
        subject_name VARCHAR NOT NULL
                            );
        """)

        # Create teachers table
        self.cursor.execute("""
         CREATE TABLE IF NOT EXISTS teachers 
            (
            teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name VARCHAR NOT NULL
                        );              
                        
        """)
        # Create teacher_availability teacher
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_availability (
        teacher_id INTEGER NOT NULL,
        day VARCHAR NOT NULL,
        PRIMARY KEY (teacher_id, day),
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        );""")
        # Create teacher_subject linking subject (links teacher with the subjects they teach)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subject (
        teacher_id INTEGER NOT NULL,
        subject_code VARCHAR NOT NULL,
        PRIMARY KEY (teacher_id, subject_code),
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
        FOREIGN KEY (subject_code) REFERENCES subjects(subject_code)
                            );
        """)
        

        # Create rooms table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_code VARCHAR PRIMARY KEY NOT NULL,
            capacity INTEGER,
            block_code VARCHAR,
            FOREIGN KEY (block_code) REFERENCES blocks(block_code)
        );
        """)



        # Create table to link rooms to subjects
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_subject (
        room_code VARCHAR,
        subject_code VARCHAR,
        PRIMARY KEY (room_code, subject_code),
        FOREIGN KEY (room_code) REFERENCES rooms(room_code),
        FOREIGN KEY (subject_code) REFERENCES subjects(subject_code)
                            
                            
                            
                            
                            
                            )
        """)
        # Create blocks table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
        block_code VARCHAR PRIMARY KEY NOT NULL,
        block_name VARCHAR NOT NULL
                            );
        """)
        # Create nearby_blocks table (since the previous approach i used with lists violates 3NF)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS block_list (
        block_code VARCHAR NOT NULL,
        nearby_block_code VARCHAR NOT NULL,
        PRIMARY KEY (block_code, nearby_block_code),
        FOREIGN KEY (block_code) REFERENCES blocks(block_code),
        FOREIGN KEY (nearby_block_code) REFERENCES blocks(block_code)
                            );""")

        # Create choices table (linking table that links students to chosen subjects)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS choices (
        student_id INTEGER,
        subject_code VARCHAR,
        is_backup BOOLEAN,
        PRIMARY KEY (student_id, subject_code),
        FOREIGN KEY (student_id) REFERENCES students(student_id),
        FOREIGN KEY (subject_code) REFERENCES subjects(subject_code)
                            );
        """)



        self.conn.commit()
    
    def insert_student(self, data: Dict[str, Union[str, int]]) -> None: 
        """Insert student data into student table, and insert preferred subjects (and backup) into subject table"""
        self.cursor.execute("INSERT OR IGNORE INTO students (full_name) VALUES (?);", (data["full_name"],))
        student_id = self.cursor.lastrowid # get student_id of the last row so that the correct foreign key is inserted into choices
        for i in range(1,5):
            preferred_class = data.get(f"preferred_class_{i}")
            if preferred_class:
                self.insert_choice({"student_id": student_id,
                                    "subject_code": preferred_class,
                                    "is_backup": 0})
        backup_preference = data.get("backup_preference")
        self.insert_choice({"student_id": student_id,
                                "subject_code": backup_preference,
                                "is_backup": 1})


    def insert_choice(self, data: Dict[str, Union[str, int]]) -> None:
        """Insert a student's preferred subject into the choices table"""
        self.cursor.execute("INSERT OR IGNORE INTO choices (student_id, subject_code, is_backup) VALUES (?, ?, ?);",
                            (data["student_id"], data["subject_code"], data["is_backup"]))


    def insert_teacher(self, data: Dict[str, Union[str, int]]) -> None:
        """Insert teacher data, teacher's subject specialities and teacher's availability into respective tables"""
        self.cursor.execute("INSERT OR IGNORE INTO teachers (full_name) VALUES (?);", 
                            (data["full_name"],))
        teacher_id = self.cursor.lastrowid # Get the last inserted teachers teacher id

        # Insert records into teacher_availability. If availability is empty, empty string is inserted
        days_available = data.get("availablity", "").strip("[]").split(",")
        if not any(day.strip() for day in days_available): # If there's not a single non blank string 
            days_available = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"] # Days teacher can teach

        for day in days_available:
            if day.strip():
                # Insert teacher availability
                self.cursor.execute("INSERT OR IGNORE INTO teacher_availability (teacher_id, day) VALUES (?, ?);", (teacher_id, day.strip())) 
        # Insert records into teacher_subject table:
        subject_specialities = data.get("subject_specialities").strip("[]").split(",") # get subjects teacher can teach
        for subject in subject_specialities:
            if subject.strip():
                # Insert teacher subject specialities
                self.cursor.execute("INSERT OR IGNORE INTO teacher_subject (teacher_id, subject_code) VALUES (?, ?);", (teacher_id, subject.strip()))
        
    def insert_room(self, data: Dict[str, Union[str, int]]) -> None:

        self.cursor.execute("INSERT OR IGNORE INTO rooms (room_code, capacity, block_code) VALUES (?, ?, ?);",
                            (data["room_code"], data["capacity"], data["block_code"]))
        
        taught_subjects = data.get("taught_subjects").strip("[]").split(",")
        for s in taught_subjects:
            if s.strip() != "":
                self.insert_room_subject({"room_code": data["room_code"],
                                          "subject_code": s.strip()
                                          })

                
    def insert_room_subject(self, data: Dict[str, Union[str, int]]) -> None:
        """Insert data (from columns on room entity) into room_subject linking table"""
        self.cursor.execute("INSERT OR IGNORE INTO room_subject (room_code, subject_code) VALUES (?, ?);", (data["room_code"], data["subject_code"],))

    
    def insert_block(self, data: Dict[str, Union[str, int]]) -> None:
        """Insert block row into block table"""
        self.cursor.execute("INSERT OR IGNORE INTO blocks (block_code, block_name) VALUES (?, ?);", (data["block_code"], data["block_name"]))
        
        nearby_blocks = data.get("nearby_blocks").strip("[]").split(",")
        for block in nearby_blocks:
            if block.strip():
                self.cursor.execute("INSERT OR IGNORE INTO block_list (block_code, nearby_block_code) VALUES (?, ?);", (data["block_code"], block.strip()))


    def insert_subject(self, data: Dict[str, Union[str, int]]) -> None:
        """Insert row into subject table"""
        self.cursor.execute("INSERT OR IGNORE INTO subjects (subject_code, subject_name) VALUES (?,?)", (data["subject_code"], data["subject_name"]))

    
    def query_table(self, table: str = "", query: str = "") -> Union[List[Tuple[Any, Any]], str]:
        """Run an SQL query and return the associated data"""
        query = query.strip() # User/ GUI query
        table = table.strip() # Table being queried

        if not query: 
            if table:
                query = f"SELECT * FROM {table}" # Default query
            else:
                 return "Error: no query or table provided" # Error if no query or table provided
        parsed_statements = sqlparse.parse(query) # Parse the query with sqlparse
        if len(parsed_statements) > 1 or not parsed_statements: # Reject if more or less than one statement
            return "Error: Only one SQL statement is allowed at once"
        if parsed_statements[0].get_type() != "SELECT":
            return "Error: Only DQL commands (i.e. SELECT queries) are allowed"

        try: # Try doing the query, if any errors, return them instead
            self.cursor.execute(query)
            rows = self.cursor.fetchall() # Get resultant data
            columns = [] # Stores field names
            for col in self.cursor.description:
                columns.append(col[0])
            return (rows, columns)
        except Exception as e:
            return f"Error fetching data: {e}"





    def insert_data(self, valid_df: pd.DataFrame) -> None:
        """Calls other insertion functions based on entity type to insert validated dataframe into database"""


        # Dictionary to map entity type to insertion function
        entity_insertion_map = {
            "Student" : self.insert_student,
            "Teacher": self.insert_teacher,
            "Room": self.insert_room,
            "Block": self.insert_block,
            "Subject": self.insert_subject
        }
        for i, row in valid_df.iterrows():
            insertion_function = entity_insertion_map[row.get("entity_type")]

            data_dictionary = row.to_dict() # Using the pandas dataframe to dictionary function
            try:
                insertion_function(data_dictionary)
            except Exception as e:
                print(f"Following error occured when trying to insert data into row {i+1}: {e}")
                return
        self.conn.commit()
    
    def search_record(self, entity: str, search_query: str, field: str, exact_only = False) -> List:
        """
        Searches for search_query in specified field:
        1) 
        - If exact_only is False, just do a SELECT...LIKE query. Otherwise...
        - If exact only is True:
            - If the field being searched is a SIMPLE primary key, do a direct query. Else...
            - If the entity/field being searched has been hashed try to get an exact match (if none, nothing stored in list)
        2)
        - Return the results
        """

        entity_hash_map = {
            "students": self.student_hash_table,
            "teachers": self.teacher_hash_table,
            "subjects": self.subject_hash_table,
            "blocks" : self.block_hash_table
        } # Maps entity type to correct hash map

        if not exact_only:
            self.cursor.execute(f"SELECT * FROM {entity} WHERE {field} LIKE ? COLLATE NOCASE", (f"%{search_query}%",))
            partial_matches = (self.cursor.fetchall()) # List of partial matches
            return partial_matches
        else:
            exact_matches = [] # List of exact matches
            if (field.endswith("_id") or field.endswith("_code")): # A field is a primary key if and only if it ends in either _id or _code
                self.cursor.execute(f"SELECT * FROM {entity} WHERE {field} = ?", (search_query,))
                exact_matches=self.cursor.fetchall()
                print("Search carried out with primary key") # Debug to ensure that query uses this logic
            else:
                if entity in entity_hash_map and entity_hash_map[entity].search(search_query) != []: # Otherwise, search with hash logic if field is hashed
                    primary_keys =  entity_hash_map[entity].search(search_query)
                    for primary_key in primary_keys:
                        query = f"SELECT * FROM {entity} WHERE {entity[:-1]}_id = ?"
                        self.cursor.execute(query, (primary_key,))
                        exact_matches.append(self.cursor.fetchone())
            return exact_matches
 

    def get_tables(self) -> List:
        """Returns list of all tables (excluding sqlite sequence table)"""
        self.cursor.execute("""
        SELECT name
        FROM sqlite_master 
        WHERE type='table' 
          AND name NOT LIKE 'sqlite_%';
        """)
        rows = self.cursor.fetchall() # returned table names
        table_names = []
        for row in rows:
            table_names.append(row[0]) # add each table name to list
        return table_names
    

    def get_fields(self, table_name: str) -> List:
        """Get all fields in a table"""
        self.cursor.execute(f"PRAGMA table_info({table_name});") # get fields
        rows = self.cursor.fetchall()
        field_names = []
        for row in rows:
            field_names.append(row[1]) # add each field name to list
        return field_names
    
    def reload_hash_table(self) -> None:
        """Recreates hash tables when restarting"""
        
        # Students hash table:
        self.cursor.execute("SELECT student_id, full_name FROM students;")
        for row in self.cursor.fetchall():
            student_id, full_name = row # tuple of fields
            if student_id is not None and full_name:
                self.student_hash_table.insert(student_id, full_name)
        # Teachers
        self.cursor.execute("SELECT teacher_id, full_name FROM teachers;")
        for row in self.cursor.fetchall():
            teacher_id, full_name = row# tuple of fields
            if teacher_id is not None and full_name:
                self.teacher_hash_table.insert(teacher_id, full_name)
        # Blocks
        self.cursor.execute("SELECT block_code, block_name FROM blocks;")
        for row in self.cursor.fetchall():
            block_code, block_name = row# tuple of fields
            if block_code and block_name:
                self.block_hash_table.insert(block_code, block_name)
        # Subject code
        self.cursor.execute("SELECT subject_code, subject_name FROM subjects;")
        for row in self.cursor.fetchall():
            subject_code, subject_name = row# tuple of fields
            if subject_code and subject_name:
                self.subject_hash_table.insert(subject_code, subject_name)


        print("Reloaded hash tables from existing tables")
    def get_all_teachers(self) -> list:
        '''Returns a list of all teachers in the form teacher_id, full_name'''
        self.cursor.execute("SELECT teacher_id, full_name FROM teachers;")
        return self.cursor.fetchall()

    def get_all_students(self) -> list:
        '''Returns a list of all teachers in the form student_id, full_name'''
        self.cursor.execute("SELECT student_id, full_name FROM students;")
        return self.cursor.fetchall()
    def get_teacher_timetable(self, teacher_id: int) -> list:
        '''Get timetable for a teacher'''
        sql = """
        SELECT 
            timetables.subject_code AS subject,             
            timetables.class_id AS class_id,          
            teachers.full_name AS teacher,
            timetables.room_code AS room,
            timetables.timeslot
        FROM timetables
        JOIN teachers ON timetables.teacher_id = teachers.teacher_id
        WHERE teachers.teacher_id = ? 
        ORDER BY timetables.timeslot
        """
        self.cursor.execute(sql, (teacher_id,))
        return self.cursor.fetchall()

    def get_student_timetable(self, student_id: int) -> list:
        '''Get timetable for a student'''
        sql = """
        SELECT 
            timetables.subject_code AS subject,             
            timetables.class_id AS class_id,          
            teachers.full_name AS teacher,
            timetables.room_code AS room,
            timetables.timeslot
        FROM timetables
        JOIN teachers ON timetables.teacher_id = teachers.teacher_id
        JOIN timetable_students ON timetables.timetable_id = timetable_students.timetable_id
        WHERE timetable_students.student_id = ?
        ORDER BY timetables.timeslot
        """
        self.cursor.execute(sql, (student_id,))
        return self.cursor.fetchall()


#----GUI general classes below----
# Button class
class Sidebar_button:
    
    def __init__(
        self, 
        root: tk.Widget, 
        button_text: str, 
        command: Callable, 
        button_size: List[int] = [20, 2],
        button_bg_colour: str = DEFAULT_BUTTON_BG_COLOUR,
        text_colour: str = DEFAULT_BUTTON_TEXT_COLOUR,
        hover_colour: str = DEFAULT_BUTTON_TEXT_HOVER_COLOUR
    ) -> None:
        """ Initialise button with command, size, colour, text and hover effects"""
        self.button_bg_colour = button_bg_colour
        self.text_colour = text_colour
        self.hover_colour = hover_colour

        # Create button
        self.button = tk.Button(
            root,
            text=button_text,
            command=command,
            bg=self.button_bg_colour,
            fg=self.text_colour,
            width=button_size[0],
            height=button_size[1]
        )

        # Bind hover events
        self.button.bind("<Enter>", self.onhover)
        self.button.bind("<Leave>", self.ondehover)
        self.button.pack(fill=tk.X, pady=5, padx=10)  # Pack button, pad button to look nicer

    def onhover(self, event: tk.Event) -> None:
        """Change colour when hovering over button"""
        self.button.config(fg=self.hover_colour)

    def ondehover(self, event: tk.Event) -> None:
        """Revert colour when stopped hovering"""
        self.button.config(fg=self.text_colour)

# Sidebar Menu class
class Sidebar_menu:
    def __init__(
        self, 
        root: tk.Widget, 
        menu_size: List[int], 
        button_names: List[str], 
        button_commands: List[Callable],
        sidebar_bg_colour: str = DEFAULT_SIDEBAR_BG_COLOUR
    ) -> None:
        """Initialises sidebar with all buttons"""

        # Updated to prevent splitting of sidebar using height
        self.sidebar = tk.Frame(root, bg=sidebar_bg_colour, width=menu_size[0], height = menu_size[1])
        self.sidebar.pack_propagate(False)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        for name, command in zip(button_names, button_commands):
            Sidebar_button(self.sidebar, name, command) # Create each button in its assciated sidebar with its name & command

#Log window class
class Log_window:
    def __init__(self,
                 root: tk.Tk,
                 sidebar_width: int = 200,
                 log_width: int = 0,
                 bg_colour: str = DEFAULT_LOG_BG_COLOUR,
                 text_bg_colour: str = DEFAULT_LOG_TEXT_BG_COLOUR,
                 text_fg_colour: str = DEFAULT_LOG_TEXT_FG_COLOUR,
                 resizer_colour: str = DEFAULT_LOG_RESIZER_COLOUR
                 ) -> None:
        """Initialises log window"""
        
        # Set sidebar and log width to ensure log doesn't go over the sidebar
        self.sidebar_width = sidebar_width
        self.log_width = log_width
        # Set all the colours to values of associated keyword parameters
        self.bg_colour = bg_colour
        self.text_bg_colour = text_bg_colour
        self.text_fg_colour = text_fg_colour
        self.resizer_colour = resizer_colour


        # Create frame which log is in
        self.log_frame = tk.Frame(root, bg=self.bg_colour, relief=tk.RAISED, borderwidth=2)
        # Initially place the log frame right after the main sidebar at the bottom
        self.log_frame.place(x=self.sidebar_width, rely=1.0, anchor='sw', width = self.log_width)




        # Create text box 
        self.text_box = tk.Text(self.log_frame, bg=self.text_bg_colour, fg = self.text_fg_colour, wrap=tk.WORD, height = 10, width = 50)
        self.text_box.pack(side=tk.LEFT, fill = tk.BOTH, expand = True, padx=5, pady=5)

        self.text_box.configure(state="disabled") # Prevent from typing in it

        # Create scrollbar so that it scrolls up and down
        self.scrollbar = ttk.Scrollbar(self.log_frame, command=self.text_box.yview)
        self.text_box.configure(yscrollcommand = self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.clear_button = tk.Button(self.log_frame, text = "Clear log", command = self.clear_log, bg = "red", fg = "white")
        self.clear_button.pack(pady=5, padx= 10, side = tk.BOTTOM)

        # Allow for resizing (with resizing method)
        self.resizer = tk.Frame(self.log_frame,bg=self.resizer_colour, cursor = "sb_v_double_arrow", height = 5, relief=tk.RAISED, borderwidth=2)

        self.resizer.place(relx=0,rely=0,relwidth=1.0)
        self.resizer.bind("<B1-Motion>", self.resize_log)





    # Method for resizing log
    def resize_log(self, event: tk.Event) -> None:
        """Resizes log based on clicking and dragging the resizer"""
        new_height = self.log_frame.winfo_height()-event.y+40
        self.text_box.config(height=new_height//20)


    # add message to log
    def add_message(self, message: str, priority: str = "info") -> None:
        """Writes a message to the screen"""
        # Default priority of message set to information

        # Get timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        
        # Put message into text box in log
        self.text_box.configure(state="normal") # Set to write so that you can insert the message
        self.text_box.insert(tk.END, f"[{timestamp}]: {priority.upper()} - {message}\n")
        self.text_box.tag_config(priority)
        self.text_box.see(tk.END)
        self.text_box.configure(state="disabled")
    def clear_log(self):
        '''Deletes all text in log'''
        self.text_box.configure(state="normal")  
        self.text_box.delete("1.0", tk.END)  
        self.text_box.configure(state="disabled")  

#----GUI submenu classes----
class Database_view:
    def __init__(self, root: tk.Widget,db_path: str, log: Log_window) -> None:
        """Instantiate database view with arguments and attributes to store other GUI based info"""
        global current_open_database_view
        # Set all attributes to arguments passed in
        self.root = root 
        self.log = log
        if db_path.strip():
            self.db = Database_module(db_path)
            self.db.reload_hash_table()
        else:
            self.db = None

        # Set up variables for table and field selection
        self.table_var = tk.StringVar() # table to search
        self.field_var = tk.StringVar() # field to search
        self.exact_only_var = tk.StringVar(value = "False") # exact matches only

        self.current_data = None # Used to track data to sort
        self.column_names = [] # Used to track current column names
        self.current_table = None # Used to track current opened table
        self.treeview = None # Used to track treeview
        self.custom_query_window = None # Used to track whether query window is open or not

    # Database view set up:
    def create_database_view(self, table_name: str, query: str = "") ->tk.Widget:
        """Retrieves data from database, displays info in a treeview"""
        global current_open_database_view
        if current_open_database_view: # destroy database view if it is already open
            current_open_database_view.destroy()
            current_open_database_view = None
            return
        
        if self.db is None: # otherwise, if the database is non-existent, inform user no database exists
            frame = tk.Frame(self.root, bg="lightgray")
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            label = tk.Label(frame, text="No database loaded.\nPlease import or create a database first.")
            label.pack(padx=20, pady=20)
            current_open_database_view = frame
            self.log.add_message("No database loaded for viewing.", "warning") 
            log.log_frame.lift()
            return frame

        self.current_table = table_name

        query_data = self.db.query_table(table = table_name, query= query)
        self.create_treeview(self.current_table, query_data)
        
    def create_treeview(self, table_name: str, query_data) -> None:
        """Create treeview with data from create_database_view method"""
        global current_open_database_view
        if isinstance(query_data, str): # query data only returns a string if an error of some sort occurs
            self.log.add_message(f"Database error: {query_data}", "error")
            return
        rows, self.column_names = query_data # If no errors, then get the rows and columns
        self.current_data = rows
        # Frame for the treeview to appear in
        frame = tk.Frame(self.root)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        current_open_database_view = frame

        # Frame for search bar
        search_frame = tk.Frame(frame, bg = "gray", padx = 5, pady=5)
        search_frame.pack(fill=tk.X)
        
        # Table selection dropdown menu:
        tk.Label(search_frame, text = "Table:").pack(side=tk.LEFT, padx=5)
        tables = self.db.get_tables()
        self.table_var.set(table_name)
        table_dropdown = tk.OptionMenu(search_frame, self.table_var, *tables, command=self.on_table_change)
        table_dropdown.pack(side=tk.LEFT, padx = 5)

        # Field selection dropdown:
        tk.Label(search_frame, text = "Field:").pack(side=tk.LEFT, padx = 5)
        # fields only fetched if the table is in the database. Otherwise, just set it 
        fields = self.db.get_fields(table_name) if table_name in self.db.get_tables() else self.column_names 
        self.field_var.set(fields[0] if fields else "")
        self.field_dropdown = tk.OptionMenu(search_frame, self.field_var, *fields)
        self.field_dropdown.pack(side = tk.LEFT, padx = 5)


        # Actual search bar itself:
        self.search_entry = tk.Entry(search_frame, width = "40")
        self.search_entry.pack(side=tk.LEFT, padx= 5, pady=5)

        # Allows user to only get exact matches if desired.
        tk.Label(search_frame, text="Exact matches only:").pack(side=tk.LEFT, padx=5)
        self.exact_only_dropdown = ttk.OptionMenu(search_frame, self.exact_only_var, "False", "True", "False")
        self.exact_only_dropdown.pack(side=tk.LEFT, padx=5)

        # Search button:
        search_button = tk.Button(search_frame, text = "Search", command = self.execute_search)
        search_button.pack(side=tk.LEFT, padx= 5, pady=5)

        # custom query button
        custom_query_button = tk.Button(frame, text="Custom Query", command=self.open_custom_query_window)
        custom_query_button.pack(side=tk.TOP, pady=2)
        

        # Create the treeview view of database
        self.treeview = ttk.Treeview(frame, columns =self.column_names, show = "headings")
        self.treeview.pack(fill=tk.BOTH, expand= True, side=tk.LEFT) # Pack to left


        # Write column headings
        for col in self.column_names:
            self.treeview.heading(col, text = col, anchor=tk.W)
            self.treeview.column(col, width = 100, anchor=tk.W)


        # Scrollbar down to go through records
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.treeview.yview)
        self.treeview.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # Bind header click to sorting
        self.treeview.bind("<Button-1>", self.on_header_click)

        # Insert rows into treeview
        for r in rows:
           self.treeview.insert("", "end", values = r)
        

        self.log.add_message(f"Displayed table {table_name}", "info")


        self.log.log_frame.lift() # Place log over databases

    def on_header_click(self, event: tk.Event):
        """Check if user has clicked a header. If they have, find correct column clicked"""
        region = self.treeview.identify("region", event.x, event.y) # get region of click
        if region == "heading":
            column_id = self.treeview.identify_column(event.x)
            index = int(column_id[1:]) # index of column
            field_name = self.column_names[index-1] # field clicked
            self.dropdown_menu(event, field_name) # create dropdown menu for field

    def dropdown_menu(self, event: tk.Event, field: str) -> None:
        """Create dropdown menu to sort data"""
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label = "Sort ascending", command = lambda: self.sort_column(field, ascending = True))
        menu.add_command(label = "Sort descending", command = lambda: self.sort_column(field, ascending = False))
        menu.post(event.x_root, event.y_root) # create menu at cursor
    
    def sort_column(self, field: str, ascending: bool = True) -> None:
        """Sort the data being displayed"""
        global current_open_database_view
        if field not in self.column_names: # Added to prevent sorting of non-existent columns with new system
            self.log.add_message(f"Cannot sort by field: {field}, not found in columns of current data", "error")
            return
        field_index = self.column_names.index(field) # Index of field to sort by
        try:
            self.current_data.sort(key = lambda row: row[field_index], reverse = not ascending) # sort in correct order
        except Exception as e: # to catch any errors
            self.log.add_message(f"Sorting error: {e}", "error")
            return
        # Replace existing db view with sorted data
        if current_open_database_view: 
            current_open_database_view.destroy()
            current_open_database_view = None

        sorted_query_data = (self.current_data, self.column_names)
        self.create_treeview(self.current_table, sorted_query_data)
        self.log.add_message(f"Sorted by {field} in {'ascending' if ascending else 'descending'} order", "info")

    def open_custom_query_window(self):
        """Open custom query window and execute query"""
        if self.custom_query_window is not None: # if window already open, destroy
            self.custom_query_window.destroy()
            self.custom_query_window = None
        self.custom_query_window = tk.Toplevel(self.root) # create custom query window
        self.custom_query_window.title("Enter a custom SQL query")

        # enter query
        label = tk.Label(self.custom_query_window, text = "Type an SQL SELECT statement")
        label.pack(padx=10, pady =5)

        self.query_text = tk.Text(self.custom_query_window, height = 5, width = 60) # store query_text
        self.query_text.pack(padx=10, pady = 5)
        #Button to run query 
        run_query_button = tk.Button(self.custom_query_window, text= "Run Query", command = self.run_custom_query)
        run_query_button.pack(padx = 10, pady = 5)

    def run_custom_query(self):
        """Run a user entered query"""
        global current_open_database_view
        query = self.query_text.get("1.0", tk.END).strip() # get user#s query
        if not query: # presence check
            self.log.add_message("No query entered", "warning")
            return
    
        result = self.db.query_table(query=query) # use query table logic
        if isinstance(result, str): # if errors with carrying out query
            self.log.add_message(result, "error")
            return
        if current_open_database_view: # replace db view with results
            current_open_database_view.destroy()
            current_open_database_view = None
        self.create_treeview("students", result)
        self.log.add_message("Custom query executed", "info")
    
    def on_table_change(self, selected_table):
        """Changes fields if table changes"""
        if not selected_table: # if no table set field to blank
            self.field_var.set("")
            return
        fields = self.db.get_fields(selected_table) # get fields

        self.field_dropdown["menu"].delete(0, "end") # delete all current fields in dropdown

        for field in fields: # add all new fields to dropdown
            self.field_dropdown["menu"].add_command(label = field, command = lambda c=field: self.field_var.set(c))
        
        self.field_var.set(fields[0] if fields else "") # set the selected field to the first field
    
    def execute_search(self):
        """Carry out user entered search"""
        global current_open_database_view
        table_name = self.table_var.get() # get searched field
        field_name = self.field_var.get() # get searched field name
        query_text = self.search_entry.get().strip()
        exact_only = self.exact_only_var.get() == "True"

        if not table_name: # presence check
            self.log.add_message("No table selected", "warning")
            return
        if not field_name:# presence check
            self.log.add_message("No valid field selecetd", "warning")
            return
        if not query_text:# presence check
            self.log.add_message("No query input", "warning")
            return
        
        # Get returned rows
        returned_rows = self.db.search_record(table_name,  query_text, field_name, exact_only = exact_only)

        if current_open_database_view: # destroy current database view if one exists
            current_open_database_view.destroy()
            current_open_database_view = None
        
        fields = self.db.get_fields(table_name) # update fields to be those of the new, queried table
        query_data = (returned_rows, fields) # add fields (columns) to the returned rows
        self.create_treeview(f"{table_name}", query_data) # create treeview
        self.log.add_message(f"Search for '{query_text}' in {table_name}.{field_name}", "info")

class Timetable_submenu:
    def __init__(self, root, db, log):
        # Initialise main attributes
        self.root = root
        self.db = db
        self.log = log
        self.submenu_name = "Timetables" # Used to track submenu 


        # Create frame
        self.frame = tk.Frame(self.root, bg = "lightgray")
        self.frame.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)


        # Create top bar (for search bar and dropdown)
        top_bar = tk.Frame(self.frame, bg = "gray")
        top_bar.pack(side = tk.TOP, fill = tk.X)

        # Dropdown to select which entity to search (teacher/ student)
        self.search_entity_var = tk.StringVar(value = "Teacher")
        entity_dropdown = ttk.OptionMenu(top_bar, self.search_entity_var, "Student", "Student", "Teacher") # Student is default value, and user can pick between student and teacher. 
        entity_dropdown.pack(side=tk.LEFT, padx=5, pady=5)

        # Search bar
        self.search_entry = tk.Entry(top_bar, width = 40)
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=5)

        # Search button
        self.search_button = tk.Button(top_bar, text="Search", command=self.execute_search)
        self.search_button.pack(side=tk.LEFT, padx=5)

        # Button to display all data related to entity
        self.show_all_button = tk.Button(top_bar, text="Display all data", command=self.show_all_data)
        self.show_all_button.pack(side=tk.LEFT, padx=5)

        # Create treeview of results
        # Frame
        self.results_frame = tk.Frame(self.frame, bg = "white")
        self.results_frame.pack(side=tk.TOP, fill = tk.BOTH, expand = True)

        # Tree
        self.tree = ttk.Treeview(self.results_frame, columns = ("ID", "Name"), show = "headings")
        self.tree.heading("ID", text ="ID")
        self.tree.heading("Name", text = "Name")
        self.tree.column("ID", width=80)
        self.tree.column("Name", width=180)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Display timetable on double click
        self.tree.bind("<Double-1>", self.display_timetable)
        self.log.log_frame.lift()

    def execute_search(self):
        '''Execute search using search record logic'''
        search_query = self.search_entry.get().strip() # Remove empty spaces
        entity_type = self.search_entity_var.get() 

        if entity_type == "Teacher":
            table = "teachers"
        else:
            table = "students"

        if not search_query:
            self.log.add_message("Search query is empty", "warning") # Show error if no search query
            return
        results = self.db.search_record(table, search_query, "full_name")

        if not results:
            self.log.add_message("No results found", "info")
            return
        formatted_results = []
        for row in results:
            formatted_results.append((row[0],row[1])) # Format so that results in the correct format for populate_results function

        self.populate_results(formatted_results) # populate tree with results if found

    def show_all_data(self):
        """Show all teacher/ student records"""
        entity_type = self.search_entity_var.get() # get entity from dropdown

        if entity_type == "Teacher":
            results = self.db.get_all_teachers() # get teachers in db
        else:
            results = self.db.get_all_students() # get student in db
        
        if not results:
            self.log.add_message("No results found", "info")
            return
        self.populate_results(results)

    def populate_results(self, records):
        """Create treeview with results"""
        self.tree.delete(*self.tree.get_children()) # Delete everything currently in tree
        for record in records:
            self.tree.insert("", "end", values = record) # Then insert new records into tree
        self.log.log_frame.lift() # Make sure log is on top

    def display_timetable(self, event):
        """Display individual's timetable in separate window"""
        try:
            selected_item = self.tree.selection() # get item user double clicked
            if not selected_item:
                return
            row_data = self.tree.item(selected_item[0], "values")
            person_id, person_name = row_data # get person's name and id
            entity_type = self.search_entity_var.get()
            if entity_type == "Teacher": # lookup check
                timetable_data = self.db.get_teacher_timetable(person_id)
            else:
                timetable_data = self.db.get_student_timetable(person_id)
            
            if not timetable_data: # presence check
                self.log.add_message(f"No timetable found for {entity_type} {person_name} (ID {person_id})", "info")
                return
            self.create_timetable_window(entity_type, person_id, person_name, timetable_data)
        except:
            self.log.add_message("Timetables have not been generated yet", "warning")
    
    def create_timetable_window(self, entity_type, person_id, person_name, timetable_data):
        window = tk.Toplevel(self.root)
        window.title(f"{entity_type} Timetable - {person_name} - id: {person_id}")
        # Rows and columns for timetable
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"] 
        periods = ["Period 1\n09:00", "Period 2\n09:55", "Period 3\n11:05", 
                   "Period 4\n12:00", "Period 5\n14:15", "Period 6\n15:10"]
        
        # Map (day, period), a tuple, to lesson details (also a tuple)
        schedule_map = {} # store a student's schedu;e
        for (subject, class_id, teacher, room, timeslot) in timetable_data:
            day_index = timeslot // 6 # get the day of the lesson
            period_index = timeslot % 6 # get period of the lesson
            schedule_map[(day_index, period_index)] = (subject, class_id, teacher, room)


        label_empty = tk.Label(window, text ="Period", bg = "lightgray", width = 20, relief = tk.RIDGE) # Label periods
        label_empty.grid(row=0, column=0, sticky = "nsew")

        for column_index, day_name in enumerate(days, start =1): # For each day, create a label
            label_day = tk.Label(window, text= day_name, bg = "lightgray",width = 20, relief = tk.RIDGE)
            label_day.grid(row = 0, column = column_index, sticky = "nsew")
        
        for period_index in range(6): # For each period, create a label
            period_label =tk.Label(window, text=periods[period_index], bg="white", width=12, relief=tk.RIDGE)
            period_label.grid(row=period_index+1, column=0, sticky="nsew")
            for day_index in range(5):
                if (day_index, period_index) in schedule_map: # Display lesson if it is there at a specific time
                    subject, class_id, teacher, room = schedule_map[(day_index, period_index)]
                    cell_text = f"{subject}\n{class_id}\n{teacher}\n{room}"
                else:
                    cell_text = ""
                cell_label = tk.Label(window, text=cell_text, bg="white", width=20, relief=tk.RIDGE)
                cell_label.grid(row=period_index+1, column=day_index+1, sticky="nsew")

        for column in range(6):
            window.columnconfigure(column, weight=1)
        for row in range(7):
            window.rowconfigure(row, weight=1)
    
class Settings_submenu:
    def __init__(self, root, log):
        """Submenu to allow user to adjust GUI settings"""
        # Initialise attributes from arguments
        self.root = root
        self.log = log
        self.submenu_name = "Settings"

        # Frame for menu where settings can be changed
        self.frame = tk.Frame(self.root, bg = "lightgray")
        self.frame.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)

        # title
        title_label = tk.Label(self.frame, text = "Settings", bg = "lightgray")
        title_label.pack(pady=10)

        # frame for changing font
        font_frame = tk.Frame(self.frame, bg = "lightgray")
        font_frame.pack(pady=10)
        # label and entry for changing font
        font_label = tk.Label(font_frame, text = "Font size:", bg = "lightgray")
        font_label.pack(side=tk.LEFT, padx = 5)
        self.font_size_entry = tk.Entry(font_frame, width = 5)
        self.font_size_entry.insert(0, str(default_font_size))
        self.font_size_entry.pack(side=tk.LEFT)
        # button for changing font
        apply_font_button = tk.Button(font_frame, text = "Apply font size", command = self.change_font_size)
        apply_font_button.pack(side=tk.LEFT, padx=5)


    def change_font_size(self):
        """Change font size to what user sets """
        global default_font_size 
        new_font_size = self.font_size_entry.get().strip() # get user entry
        if not new_font_size.isdigit(): # check it is an integer
            self.log.add_message("Invalid font size entered. Please enter a number", "error")
            return
        new_font_size = int(new_font_size)
        if new_font_size <=5: # range check
            self.log.add_message("Entered font is below minimum of 6")
            return
        elif new_font_size >=20:
            self.log.add_message("Entered font is above maximum of 19")
            return
        default_font_size = new_font_size # update global variable to account for new font
        self.root.option_add("*font", f"TkDefaultFont {new_font_size}")
        self.log.add_message(f"Font size changed to {new_font_size}")

        self.update_all_widget_fonts(self.root, ("TkDefaultFont", new_font_size))
        self.update_all_widget_fonts(self.frame, ("TkDefaultFont", new_font_size))
    
    def update_all_widget_fonts(self, widget: tk.Widget, font:tuple)-> None:
        """Recursively go through and update all widgets to have the new font size"""
        try: 
            widget.config(font=font)
        except tk.TclError: # some TKinter elements don't have the attribute font
            pass
        for child in widget.winfo_children():
            self.update_all_widget_fonts(child, font) # recursively go through and modify each child widget

class Parameters_submenu:
    def __init__(self, root: tk.Widget, log: Log_window):
        """instantiate submenu"""
        global ga_soft_constraints
        # Set attributes
        self.root = root
        self.log = log
        self.submenu_name = "Parameters" # submenu 
        # Frame for menu
        self.frame = tk.Frame(self.root, bg = "lightgray")
        self.frame.pack(side=tk.LEFT, fill = tk.BOTH, expand = True)


        # Title for menu (to show user it is the settings submenu)
        title_label = tk.Label(self.frame, text="Parameters", bg="lightgray")
        title_label.pack(pady=10)

        # Frame for modifying teacher parameter:
        teacher_param_frame = tk.Frame(self.frame, bg="lightgray")
        teacher_param_frame.pack(pady=5, fill=tk.X)
        teacher_label = tk.Label(teacher_param_frame, text="Penalty for teachers having >2 lesons back to back:", bg="lightgray")
        teacher_label.pack(side=tk.LEFT, padx=5)
        # Set entry and allow parameter to be set
        self.teacher_penalty_entry = tk.Entry(teacher_param_frame, width=5)
        self.teacher_penalty_entry.insert(0, str(ga_soft_constraints["teacher_penalty"]))
        self.teacher_penalty_entry.pack(side=tk.LEFT)
        apply_teacher_pen= tk.Button(teacher_param_frame, text="Apply", command= lambda: self.apply_penalty("teacher_penalty",self.teacher_penalty_entry))
        apply_teacher_pen.pack(side=tk.LEFT, padx=5)

        # Frame for modifying student parameter:
        student_param_frame = tk.Frame(self.frame, bg="lightgray")
        student_param_frame.pack(pady=5, fill=tk.X)
        student_label= tk.Label(student_param_frame, text="Penalty for students having lessons far apart back to back:", bg="lightgray")
        student_label.pack(side=tk.LEFT, padx=5)

        # Set entry and allow parameter to be set
        self.student_penalty_entry = tk.Entry(student_param_frame, width=5)
        self.student_penalty_entry.insert(0, str(ga_soft_constraints["student_penalty"]))
        self.student_penalty_entry.pack(side=tk.LEFT)
        apply_student_pen=tk.Button(student_param_frame, text="Apply", command= lambda: self.apply_penalty("student_penalty",self.student_penalty_entry))
        apply_student_pen.pack(side=tk.LEFT, padx=5)

        # Room wrong subject frame
        room_param_frame = tk.Frame(self.frame, bg="lightgray")
        room_param_frame.pack(pady=5, fill=tk.X)
        room_button = tk.Label(room_param_frame, text="Penalty for room not suited for teaching subject:", bg="lightgray")
        room_button.pack(side=tk.LEFT, padx=5)

        # Set entry for rooms penalty
        self.room_penalty_entry = tk.Entry(room_param_frame, width=5)
        self.room_penalty_entry.insert(0, str(ga_soft_constraints["room_penalty"]))
        self.room_penalty_entry.pack(side=tk.LEFT)
        apply_room_pen= tk.Button(room_param_frame, text="Apply", command= lambda: self.apply_penalty("room_penalty",self.room_penalty_entry))
        apply_room_pen.pack(side=tk.LEFT, padx=5)

    def apply_penalty(self, parameter: str, entry_widget: tk.Entry) -> None:

        """Apply changes to penalty when button pressed"""
        global ga_soft_constraints
        # Get input
        input_value = entry_widget.get().strip()

        if not input_value.isdigit(): # check it is a number
            self.log.add_message("Inputted penalty should be an integer", "error")
            return
        penalty_value = int(input_value)
        if penalty_value <0: # check it is not negative
            self.log.add_message("Penalty value must be a positive integer")
            return
        elif penalty_value > 100: # check it is not too high
            self.log.add_message("Penalty value must be less than or equal to 100")
            return
        ga_soft_constraints[parameter] = penalty_value
        self.log.add_message(f"Successfully set {parameter} parameter to {penalty_value}", "info")



#----File submenu functions (links to input validation)----
def import_input_file() -> DataFrame:
    """Imports a CSV file, returns a dataframe. Also manages minor errors in actually importing the file"""
    global imported_dataframe
    global db_path
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
                    db.create_tables() # create database with timestamp
                    log.add_message(f"Database created with file name {db_path}", "info")
                    db.insert_data(imported_dataframe)
                    log.add_message(f"Input data inserted into database", "info")
                    
                    db_view.db = db
                    db_view.db.reload_hash_table()
                    log.add_message("Database data can be viewed in 'Databases' submenu")

                    
                
    else:
        messagebox.showinfo("No File Selected", "No file was selected.")
        log.add_message("File Info: No file was selected.", "warning")
        return None
    

def backup_database():
    """Creates backup of database to a location specified by user"""
    global db_path
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
def validate_db_schema(conn: sqlite3.Connection) -> bool:
    """Checks if input data has correct schema"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='timetables'") # check if timetables table is present
        timetables_table_present = True if cursor.fetchone() else False # if it is present, set this to true, otherwise set to false
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='timetable_students'")# check if timetable_student table is present
        timetables_student_table_present = True if cursor.fetchone() else False # if it is present, set this to true, otherwise set to false
        schema_to_check_against = REQUIRED_SCHEMA.copy()

        if timetables_table_present or timetables_student_table_present: # if either of the timetable tables are present, validate against timetable schema
            schema_to_check_against.update(TIMETABLE_SCHEMA)
            
        # Validate the tables
        for table, expected_columns in schema_to_check_against.items():
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone(): # Check all tables are present
                log.add_message(f"Imported database has invalid schema: Required table: {table} is not present", "error")
                return False
            
            # Check that tables have correct fields
            cursor.execute(f"PRAGMA table_info({table})")
            results = cursor.fetchall()
            input_columns = []
            for row in results:
                input_columns.append(row[1])
            missing_columns = set(expected_columns) - set(input_columns)
            if missing_columns:
                log.add_message(f"Imported database has invalid schema: Table {table} is missing columns {missing_columns}", "error")
                return False
        log.add_message("Input database has correct schema", "info")
        return True
    except Exception as e:
        log.add_message(f"An error occured when validating the input database: {e}")
        return False

def import_database():
    """Allow user to input a database"""
    global db_path, db_view
    import_path = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db")],title="Select Database to Import") # allow user to input database

    if not import_path: # presence check
        log.add_message("No database selected to import", "warning")
        return
    try:
        conn = sqlite3.connect(import_path) # connect
        if not validate_db_schema(conn): # make sure schema matches
            messagebox.showerror("Invalid Database", "Input database did not match the necessary schema")
            log.add_message("Database import failed due to invalid schema", "error")
            conn.close()
            return
        db_path = import_path # update global database path variable
        db_view.db = Database_module(db_path) # create new database module
        db_view.db.reload_hash_table() # reload hash tables for searching

        log.add_message(f"Database successfully imported from {import_path}", "info")
        messagebox.showinfo("Import successful", f"Database successfully imported from location {import_path}")

    except Exception as e: # catch any errors and print them
        log.add_message(f"Database import failed due to error: {e}", "error")
        messagebox.showerror("Import Failed", f"Failed to import database due to error: {e}")
    finally:
        conn.close() # close connection regardless of what happens

# ----GUI functions----
# Toggle submenu function
def toggle_submenu(
    root_window: tk.Widget,
    button_names: List[str],
    button_commands: List[Callable],
    submenu_name: str
) -> None:
    '''Toggles submenu open and close. Also opens/closes sidebar if necessary (i.e. if there are any buttons), and adjusts log width as necessary'''
    global current_open_submenu, current_open_database_view, log, sidebar, current_left_padding

    # fprce user to close db view before opening timetables/ settings menu
    if ((submenu_name == "Timetables") or (submenu_name == "Settings") or (submenu_name == "Parameters")) and current_open_database_view is not None:
        current_open_database_view.destroy()
        current_open_database_view = None

    # Closes the current submenu if a) the submenu is open and b) the submenu button clicked is the same as the open submenu, then exit function
    if current_open_submenu is not None and getattr(current_open_submenu, "submenu_name", None) == submenu_name:
        if current_open_database_view:
            log.add_message("Close database view before opening other submenus")
            return
        if hasattr(current_open_submenu, "sidebar"): # For submenus with buttons
            current_open_submenu.sidebar.destroy()
        elif hasattr(current_open_submenu, "frame"): # For submenus without buttons
            current_open_submenu.frame.destroy()
        current_open_submenu= None
        calculate_log_width()
        log.log_frame.lift() # Place the log above all other screen elements
        sidebar.sidebar.lift() # Place the sidebar over everything else including the log
        return 



    if current_open_submenu: # Close any other open sidebar if present
        if hasattr(current_open_submenu, "sidebar"):
            current_open_submenu.sidebar.destroy()
        elif hasattr(current_open_submenu, "frame"):
            current_open_submenu.frame.destroy()
        current_open_submenu = None
    
    if submenu_name == "Timetables": # Create timetable menu instead of sidebar if it is clicked
        db = Database_module(db_path)
        current_open_submenu = Timetable_submenu(root_window, db, log)
        return
    elif submenu_name == "Settings":
        current_open_submenu = Settings_submenu(root_window, log)
        calculate_log_width()
        log.log_frame.lift()
        return
    elif submenu_name == "Parameters":
        current_open_submenu = Parameters_submenu(root_window, log)
        calculate_log_width()
        log.log_frame.lift()
        return
    elif button_names == [] and button_commands == []:
        current_open_submenu = None
        calculate_log_width()
        log.log_frame.lift()
        sidebar.sidebar.lift()
        return

    # Otherwise, create a new submenu with a sidebar     
    current_open_submenu = Sidebar_menu(root_window, [200, 1080], button_names, button_commands)
    current_open_submenu.submenu_name = submenu_name


    # If database view is open, open the submenu first
    if current_open_database_view and hasattr(current_open_submenu, "sidebar"):
        current_open_submenu.sidebar.pack_forget()
        current_open_submenu.sidebar.pack(side=tk.LEFT, fill=tk.Y, before=current_open_database_view)

        
    calculate_log_width()
    log.log_frame.lift()
    sidebar.sidebar.lift()


def calculate_log_width() -> None:
    """Adjusts the log frame width so that it matches the window size, sidebar and open submenus"""
    global current_left_padding, log, sidebar, root, current_open_submenu
    root.update_idletasks()

    if current_open_submenu and hasattr(current_open_submenu, "sidebar"): # Only add padding if a submenu is open, and it is not the timetables submenu
        current_left_padding = sidebar.sidebar.winfo_width() + current_open_submenu.sidebar.winfo_width()
    else:
        current_left_padding = sidebar.sidebar.winfo_width()

    new_width = root.winfo_width()-current_left_padding

    log.log_frame.place_configure(x=current_left_padding,rely=1, anchor = 'sw', width=new_width)

#----Timetabling database code----
def create_timetable_tables(db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create main timetable table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetables (
            timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            subject_code VARCHAR NOT NULL,
            teacher_id INTEGER NOT NULL,
            room_code VARCHAR NOT NULL,
            timeslot INTEGER NOT NULL,
            FOREIGN KEY(subject_code) REFERENCES subjects(subject_code),
            FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id),
            FOREIGN KEY(room_code) REFERENCES rooms(room_code),
            UNIQUE(subject_code, teacher_id, room_code, timeslot)
        );
        """)

        # Create junction table to link each student to lesson
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_students (
            timetable_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            PRIMARY KEY (timetable_id, student_id),
            FOREIGN KEY(timetable_id) REFERENCES Timetables(timetable_id),
            FOREIGN KEY(student_id) REFERENCES students(student_id),
            UNIQUE(timetable_id, student_id)
        );
        """)

        conn.commit() # commit changes
        conn.close() # end db connection


    except Exception as e: # If any error occurs return it
        return f"The following error occured while creating the timetable tables: {e}"

def insert_timetable(db_path: str, chromosome: list):
    """Insert timetabling data into database"""
    try:
        conn = sqlite3.connect(db_path) # connect
        cursor = conn.cursor() # cursor to modify

        for lesson, timeslot, room_code in chromosome: 
            # get lesson information
            subject_code = lesson["subject"]
            teacher_id = lesson["teacher"]
            student_ids = lesson["students"]
            class_id = lesson["class_id"]

            # Insert info into database
            cursor.execute("""
                INSERT INTO timetables(class_id, subject_code, teacher_id, room_code, timeslot) 
                VALUES (?, ?, ?, ?, ?);
            """, (class_id, subject_code, teacher_id, room_code, timeslot))

            timetable_id = cursor.lastrowid # get id of last timetable inserted

            for student_id in student_ids: # Insert into junction table timetable_students
                
                cursor.execute("""
                    INSERT OR IGNORE INTO timetable_students(timetable_id, student_id)
                    VALUES (?, ?);
                """, (timetable_id, student_id))
        conn.commit() # save changes
        conn.close() # close db
    except Exception as e: # catch errors
        log.add_message(f"The following error occured while inserting data into the timetable tables: {e}", "error")

def delete_timetable_tables(db_path: str):
    '''Deletes relevant timetable tables'''
    try:
        conn = sqlite3.connect(db_path) # connect
        cursor = conn.cursor()
        # drop timetabling tables
        cursor.execute("DROP TABLE IF EXISTS timetables;")
        cursor.execute("DROP TABLE IF EXISTS timetable_students;")

        conn.commit() # commit
        conn.close() # close
        return True # so that program knows there are no errors
    except Exception as e: # if error occurs, it's returned
         log.add_message(f"The following error occured while deleting the timetable tables: {e}", "error")

#----Timetable to csv code---
def export_to_csv(chromosome, data, filepath = None):
    """Export timetables to csv"""
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
        log.add_message(f"Error exporting timetable: {e}") # return errors

#----Merge sort----
def merge_sort(items, reverse = False):
    """Recursive merge with multiprocessing to speed up sorting
        Multiprocessing removed due to issues with importing files."""
    if isinstance(items, set):
        items = list(items) # sets are inherently unordered, so i'm converting the set to list
    if len(items) <=1: # base case
        return items
    mid = len(items)//2 # split list by middle
    left = items[:mid]
    right = items[mid:]
    # if multiprocessing.current_process().name == "MainProcess": # This prevents daemonic processes having child processes
    #     with multiprocessing.Pool(3) as pool:
    #         left, right = pool.map(merge_sort, [left, right])
    # else:
    #     left = merge_sort(left)
    #     right = merge_sort(right) 
    left = merge_sort(left) # recursively break down left sub-list
    right = merge_sort(right) # recursively break down right sub-list
    sorted_items = merge(left, right) # sort

    if not reverse:
        return sorted_items
    else:
        return sorted_items[::-1] # reverse if required

def merge(left, right):
    """Merge helper function to merge sub-lists into one list"""
    index1 = 0 # set index for left sublist
    index2 = 0 # "" for right sublust
    final_list = []

    list_is_2D = isinstance(left[0], list) and len(left[0]) > 1 # Checks if list is 2D: if first item in left list is itself a list of length >1
    while index1 < len(left) and index2 < len(right):
        if list_is_2D: # if 2D, then sort by second item in each list
            left_value = left[index1][1]
            right_value = right[index2][1]
        else: # otherwise, just sort by the item
            left_value = left[index1]
            right_value = right[index2]

        if left_value > right_value: # if left item greater
            final_list.append(right[index2]) # add the right value
            index2 += 1
        else: # else right value is greater or elements are equal
            final_list.append(left[index1])
            index1 +=1
    final_list.extend(left[index1:]) # add all items remaining in left list
    final_list.extend(right[index2:]) # add all items remaining in right list
    return final_list

#----Load data code----
def load_data(db_path: str) -> Dict:
    """Loads database, stores data associated with each entity in a dictionary, then stores each of these dictionaries in another dictionary"""


    conn = sqlite3.connect(db_path) # Establish connection to database
    cursor = conn.cursor()

    # Mapping teacher id to teacher name
    teacher_names = {}
    cursor.execute("SELECT teacher_id, full_name FROM teachers;")
    for teacher_id, teacher_name in cursor.fetchall():
        teacher_names[teacher_id] = teacher_name
    # Mapping student id to student name
    student_names = {}
    cursor.execute("SELECT student_id, full_name FROM students;")
    for student_id, student_name in cursor.fetchall():
        student_names[student_id] = student_name


    # Retrieving teacher related info
    # Teacher id
    cursor.execute("SELECT teacher_id FROM teachers;")
    rows = cursor.fetchall()
    teacher_ids = set() # Using a set to prevent any duplicates 
    for row in rows:
        teacher_ids.add(row[0])


    # Teacher availability

    teacher_availability = defaultdict(set) # defaultdict is used to automatically create an empty set if teacher_id has not been added yet
    # A set is used because a) each teacher can teach on multiple days, b) it prevents any duplicates and c) it allows for faster lookups than a list
    cursor.execute("SELECT teacher_id, day FROM teacher_availability;")
    rows = cursor.fetchall()
    for teacher_id, day in rows:
        teacher_availability[teacher_id].add(day)

    
    # Teacher subject
    teacher_subject = defaultdict(set) # automatically create empty set if teacher_id not added
    # used for same reason as it is in teacher_availability
    cursor.execute("SELECT teacher_id, subject_code FROM teacher_subject;")
    rows = cursor.fetchall()
    for teacher_id, subject_code in rows:
        teacher_subject[teacher_id].add(subject_code)
    
    # Retrieve subject info

    subject_codes = set() # Set of subject codes
    cursor.execute("SELECT subject_code FROM subjects;")
    rows = cursor.fetchall() # get all results as tuples
    for row in rows: 
        subject_codes.add(row[0]) # add each subject code to subject_codes set

    # Retrieve student info:
    student_ids = set() # set of student ids
    cursor.execute("SELECT student_id FROM students;")
    rows = cursor.fetchall()
    for row in rows:
        student_ids.add(row[0]) # add each student id to set of ids
    

    # Retrieve students choices
    student_choices = {}
    for student_id in student_ids:
        student_choices[student_id] = {"preferred": set(), "backup": ""} # Store preferred and backup classes separately. Again using sets to prevent duplicates

    cursor.execute("SELECT student_id, subject_code, is_backup FROM choices;")
    rows = cursor.fetchall()
    for student_id, subject_code, is_backup in rows:
        if is_backup:
            student_choices[student_id]["backup"] = subject_code
        else:
            student_choices[student_id]["preferred"].add(subject_code)

    # Retrieve room information (room code, capacity and block code)
    rooms = dict() # room code to capacity and block code
    cursor.execute("SELECT room_code, capacity, block_code FROM rooms;")
    rows = cursor.fetchall()
    for (room_code, capacity, block_code) in rows:
        rooms[room_code] = {"capacity": capacity, "block_code": block_code}

    room_subject = defaultdict(set)
    cursor.execute("SELECT room_code, subject_code FROM room_subject;")
    rows = cursor.fetchall()
    for room_code, subject_code in rows:
        room_subject[room_code].add(subject_code)
    
    # Retrieve block information (block code and adjacent blocks)
    blocks = set() # set of block codes
    cursor.execute("SELECT block_code FROM blocks;")
    rows = cursor.fetchall()
    for row in rows:
        blocks.add(row[0]) # add each block code to set
    
    nearby_blocks = defaultdict(set) # essentially an adjacency list
    cursor.execute("SELECT block_code, nearby_block_code FROM block_list;")
    rows = cursor.fetchall()
    for block_code, nearby_block_code in rows:
        nearby_blocks[block_code].add(nearby_block_code)
    
    output = {
              "teacher_names": teacher_names, # dictionary of ids to name
              "student_names": student_names, # dictionary of ids to name
              "teacher_ids": teacher_ids, # set of ids
              "teacher_availability": dict(teacher_availability), # teacher maps to working days
              "teacher_subject": dict(teacher_subject),
              "subject_codes": subject_codes, # set of subjects
              "student_ids": student_ids, # set of ids
              "student_choices": student_choices, # dictionary of choices
              "rooms": rooms, # dictionary with capacity and block code
              "room_subject": dict(room_subject), # dictionary mapping room to subjects taught
              "blocks": blocks, # set of block codes
              "nearby_blocks": dict(nearby_blocks) # adjacenecy list (dictionary)
              }
    return output

#----Class creation code----
def create_subjects_to_students_map(data: dict) -> dict:
    """Split students up into classes based on max class size, returns lists of classes"""
    subject_code_to_student_map = defaultdict(list)# maps subject to list of students that want to do it
    for student_id in data["student_ids"]:
        for subject in data["student_choices"][student_id]["preferred"]: 
            subject_code_to_student_map[subject].append(student_id)  # Maps a subject code to all the students that have that subject as a preferred class
    return subject_code_to_student_map

def get_teachers_per_subject(data: dict) -> dict:
    """Map subject code to list of teachers"""
    subject_teacher_map = defaultdict(list)# maps subject to list of students that can teach it

    for teacher_id in data["teacher_ids"]: # Iterate through each teacher
        teachers_subjects = data["teacher_subject"][teacher_id] 
        for subject in teachers_subjects: # Iterate through each subject teacher can teach
            subject_teacher_map[subject].append(teacher_id) # add teacher id to subject- teacher map
    return subject_teacher_map

def force_backup_option(subject_code_to_student_map, subject_teacher_map, max_class_size = 24): 
    """Assign backup classes if not enough teachers to teach all potential students"""
    pushed_to_backup = [] # students forced to take backup option

    for subject_code, student_list in subject_code_to_student_map.items():
        num_teachers = len(subject_teacher_map[subject_code]) # get number of teachers per subject
        capacity = num_teachers * max_class_size # get max students that can be taught for subject

        if len(student_list) > capacity: # if too many students
            overflow = len(student_list)- capacity
            random.shuffle(student_list) # shuffle so students removed are random
            overflow_students = student_list[-overflow:]
            del student_list[-overflow:]

            for student_id in overflow_students:
                pushed_to_backup.append((student_id, subject_code))# force overflow students to take backup
    return pushed_to_backup

def assign_backups(pushed_to_backup, subject_code_to_student_map, data):
    """Assign student to backup option by updating subject_code_to_student_map"""
    for student_id, removed_subject in pushed_to_backup:
        backup_subject = data["student_choices"][student_id]["backup"] # only one backup option
        subject_code_to_student_map[backup_subject].append(student_id) # add to backup option
        if student_id in subject_code_to_student_map[removed_subject]:
            subject_code_to_student_map[removed_subject].remove(student_id) # remove from original option
    return subject_code_to_student_map

def create_balanced_classes(subject_code_to_student_map, subject_teacher_map, max_class_size = 24):
    """Create the actual final classes, using the helper even spread function"""

    classes = [] # list of classes
    class_id_counter = 1 # to uniquely identify each class

    for subject_code, student_list in subject_code_to_student_map.items(): # Iterate through each subject and list of students

        teachers = subject_teacher_map[subject_code] # Get teachers that can teach the suject
        num_students = len(student_list) # Get num of students 
        num_teachers = len(teachers) # Get num of teachers

        # shuffle so that class generation isn't biased
        random.shuffle(student_list) 
        random.shuffle(teachers)

        
        min_classes = math.ceil(num_students/ float(max_class_size)) # Figure out min. no. of classes
        actual_classes = min(min_classes, num_teachers) # choose smallest between min classes and number of teachers
        classes_for_subject = evenly_spread_classes(student_list, actual_classes) # evenly spread classes

        for i, group in enumerate(classes_for_subject):
            assigned_teacher = teachers[i % num_teachers] # Assign teacher (at random since teachers list is shuffled)
            # create new class
            new_class = {"class_id": class_id_counter, "subject" : subject_code, "students": set(group), "teacher": assigned_teacher} 
            classes.append(new_class) # add new class 
            class_id_counter += 1 #increment counter
    return classes

def evenly_spread_classes(student_list, num_classes):
    """Evenly divide classes"""
    num_students = len(student_list) # number of students
    smallest_size = num_students// num_classes if (num_classes and num_students) else 0 #size of smalest class
    remainder = num_students % num_classes if (num_classes and num_students) else 0 # remaining students 

    resulting_classes = [] # final classes
    index = 0
    for c in range(num_classes): # iterate through for each required class
        size = smallest_size # set size to smallest size initially
        if remainder > 0:
            size +=1 # add 1 if the number doesn't divide equally
            remainder -=1 # subtract 1 from remainder to account for increased size
        chunk = student_list[index:index+size] # chunk of students that have been put into a class
        index +=size
        resulting_classes.append(chunk)
    return resulting_classes

def validate_classes_against_choices(final_classes, data):
    """
    Ensurse that classes assigned match either the preferred or backup class.
    """
    mismatch_count = 0 # not assigned backup or preferred
    backup_count = 0 # assigned backup over preferred
    for cls in final_classes: # iterate through each class
        subject_code = cls["subject"] # get subject code
        students_in_class = cls["students"] # get list of students
        for student_id in students_in_class:
            # Did student sid choose subject?
            if (subject_code not in data["student_choices"][student_id]["preferred"] 
                and subject_code != data["student_choices"][student_id]["backup"]):
                mismatch_count += 1 # not preferred or backup
                student_name = data["student_names"][student_id]
                log.add_message(f"Mismatch: Student {student_name} is in subject '{subject_code}' but it's neither their preferred nor backup subject.", "error")
            elif subject_code in data["student_choices"][student_id]["backup"]:
                student_name = data["student_names"][student_id]
                log.add_message(f"Student {student_name} was forced to take their backup option ", "warning")
                backup_count +=1

    if mismatch_count == 0: # no mismatches, all correct
        log.add_message(f"Validation: All students are in subjects they actually chose. Number of backups: {backup_count}", "info")
    else:
        log.add_message(f"Validation: Found {mismatch_count} total mismatches.", "info") # add messages to log to say mismatches found

def validate_student_class_counts(final_classes, data, min_classes=3, max_classes=4):
    '''Checks how many classes each student appears in. If less than min or more than max, error printed '''

    assigned_count = defaultdict(int) # map student to no. of lessons they have
    for c in final_classes:
        for student_id in c["students"]:
            assigned_count[student_id] += 1 
    issues = 0 # store class separation violations as issues

    for student_id in data["student_ids"]:
        count = assigned_count[student_id]  # number of classes student is in
        if count < min_classes: # if student is in too few classes
            student_name = data["student_names"][student_id]
            log.add_message(f"Student {student_name} only has {count} classes, less than min classes of {min_classes}", "error")
            issues += 1
        elif count > max_classes: # if student is in too many classes
            log.add_message(f"Student {student_name} has {count} classes more than max of {max_classes})", "error")
            issues+=1
    log.add_message(f"The number of students with an incorrect number of classes is {issues}", "info")

def get_unassigned_teachers(teachers: list, classes: list) -> list:
    """Get teachers who are not teaching a class"""
    assigned_teachers = set() # get teachers assigned to a lesson
    unassigned_teachers = [] # store teachers not assigned to lesson
    for cls in classes:
        assigned_teachers.add(cls["teacher"]) # get all assigned teachers
    for teacher in teachers: # iterate through teachers
        if teacher not in assigned_teachers: 
            unassigned_teachers.append(teacher)
    return unassigned_teachers



#----Genetic algorithm code----
def fitness_function(chromosome, data):
    """Determines the fitness of an individual chromosome"""
    score = 0
    student_schedule = defaultdict(set) # track student lessons
    teacher_schedule = defaultdict(set) # track teacher lessons
    room_schedule = defaultdict(set) # track when room is taken
    subject_lesson_counts = defaultdict(int) # track no. of lessons student has

    for lesson, timeslot, room in chromosome: # Iterate through every assigned class in the chromosome
        subject = lesson["subject"] # get class subject
        students = lesson["students"] # get class students 
        teacher = lesson["teacher"] # get class teachers


        for student in students:
            subject_lesson_counts[(student, subject)] +=1
            if timeslot in student_schedule[student]: # If timeslot already exists for student
                return -math.inf # immediately return -math.inf
            student_schedule[student].add(timeslot) # otherwise add to schedule
            # Penalty for simultaneous student lessons being far apart
            

    
            
        if timeslot in teacher_schedule[teacher]: # If current timeslot for lesson is already in teacher schedule
            #print("DEBUG: teacher timeslot already taken")
            return -math.inf # Immediately return -math.inf, as this is a hard violation and should never happen
        teacher_schedule[teacher].add(timeslot) # otherwise add the timeslot to the teachers schedule



        if timeslot in room_schedule[room]:
            #print("DEBUG: room already taken")
            return -math.inf # Immediately return -math.inf if timeslot already in rooms schedule
        
        room_schedule[room].add(timeslot)

        if len(students) > data["rooms"][room]["capacity"]: # Check room can handle no. of students
            #print("DEBUG: Room too small for students")
            print(len(students), "is number of students and room capacity is ", data["rooms"][room]["capacity"])
            return -math.inf
        
        # Double check that there definitely is a teacher
        if teacher is None:
            #print("DEBUG: no teacher")
            return -math.inf
        
        # Soft constraints

        if subject not in data["teacher_subject"][teacher]: # If teacher is not qualified to teach subject, penalise
            #print("DEBUG: bad teacher")
            score-=100
        
        # Ensure room is correct room to teach the subject
        if room and subject not in data["room_subject"][room]:
            #print("DEBUG: bad room")
            score -= ga_soft_constraints["room_penalty"]
    
    for (student, subject), count in subject_lesson_counts.items(): # Ensure student is in exactly 6 lessons for each subject
        if count < DESIRED_LESSONS:
            if count < REQUIRED_LESSONS:
            #print("DEBUG: Not exactly 6 lessons")
                return -math.inf
            else:
                score -= 1000
        

    for student in student_schedule: # iterate through students
        sorted_timeslots = merge_sort(student_schedule[student]) # sprt timeslots
        for timeslot1, timeslot2 in zip(sorted_timeslots, sorted_timeslots[1:]):
            if timeslot1+1 == timeslot2 and (timeslot1//6 == timeslot2//6): # If student has back to back lessons
                class1 = room1 = None # set class and room to none 
                class2 = room2 = None # ""

                for lesson, timeslot, room in chromosome:
                    if timeslot == timeslot1 and student in lesson["students"]: # linear search for lesson
                        class1 = lesson
                        room1 = room
                        break

                for lesson, timeslot, room in chromosome: # linear search for next lesson
                    if timeslot == timeslot2 and student in lesson["students"]:
                        class2 = lesson
                        room2 = room
                        break
                
                if class1 and class2 and room1 and room2: 
                    block1 = data["rooms"][room1]["block_code"]
                    block2 = data["rooms"][room2]["block_code"]

                    if block2 != block1 and block2 not in data["nearby_blocks"][block1]:
                        score -= ga_soft_constraints["student_penalty"] # apply penalty if rooms are not in same block
    for teacher in teacher_schedule: # iterate through each teacher
        sorted_timeslots = merge_sort(teacher_schedule[teacher]) # sort timeslots
        for timeslot1, timeslot2, timeslot3 in zip(sorted_timeslots, sorted_timeslots[1:], sorted_timeslots[2:]):
            if timeslot1 + 1 == timeslot2 and timeslot2 + 1 == timeslot3: 
                # make sure lessons are on the same day (i.e. not like p6 on monday and p1 on tuesday)
                day1 = timeslot1//6 
                day2 = timeslot2//6
                day3 = timeslot3//6
                if day1 == day2 == day3:
                    #print(f"DEBUG: Teacher {teacher} has three consecutive lessons at timeslots {timeslot1}, {timeslot2}, {timeslot3}")
                    score -= ga_soft_constraints["teacher_penalty"]
    return score

def generate_initial_population(data, final_classes, population_size=1000):
    """
    Generates an initial population of potential timetables. Tries for each class to have 5 timeslots,
    if that fails, and the student already has 3 classes, thens skip the class. Otherwise, if there are
    not 5 timeslots, and the student does not already have 3 classes, assign 1 or 2 timeslots for the lesson
    to the student
    """

    timeslots_to_days = {
        0: "Monday", 6: "Tuesday", 12: "Wednesday", 18: "Thursday", 24: "Friday"
    }

    population = []

    for _ in range(population_size):
        chromosome = []
        student_schedule = defaultdict(set)   # student maps to set of timeslots
        teacher_schedule = defaultdict(set)   # teacher maps to set of timeslots
        room_schedule = defaultdict(set)      # room maps to set of timeslots
        student_class_count = defaultdict(int)  # Track how many classes each student is in (student maps to no. of classes)

        # Attempt to assign required timeslots at least (desired timeslots at best)
        for c in final_classes:
            class_teacher = c["teacher"]
            class_teacher_availability = data["teacher_availability"][class_teacher]
            students_in_class = c["students"]
            subject = c["subject"]

            # Check all students have >= 3 subjects
            all_students_have_3 = all(student_class_count[s] >= 3 for s in students_in_class)

            # Try to get required timeslots timeslots
            chosen_timeslots = []
            available_timeslots = list(range(30))
            random.shuffle(available_timeslots)
            attempts = 0

            while len(chosen_timeslots) < REQUIRED_LESSONS and attempts < 60:
                if not available_timeslots:
                    # a fallback - just pick a random timeslot if none other available
                    timeslot = random.randint(0, 29)
                else:
                    timeslot = available_timeslots.pop(0)
                attempts += 1

                day = timeslots_to_days[timeslot // 6 * 6]
                # Check teacher
                if day not in class_teacher_availability:
                    continue
                if timeslot in teacher_schedule[class_teacher]:
                    continue

                # Check student conflicts
                conflict = any(timeslot in student_schedule[s] for s in students_in_class)
                if conflict:
                    continue

                # if no conflicts, choose it
                chosen_timeslots.append(timeslot)

            if len(chosen_timeslots) < REQUIRED_LESSONS: # if not enough lessons per subject
                if all_students_have_3: # if students already have 3 subjects
                    continue
                else: # worst case, choose 1 or 2 timeslots for the subject
                    if not chosen_timeslots:
                        # pick 1 random timeslot as fallback
                        chosen_timeslots = [random.randint(0, 29)]
                    else:
                        # keep just 1 or 2 lessons (worst case scenario)
                        chosen_timeslots = chosen_timeslots[: random.randint(1, 2)]

            # choose room
            possible_rooms = [
                r for r in data["rooms"]
                if subject in data["room_subject"][r]
            ]
            if not possible_rooms:
                # as a fallback, pick any room at random
                possible_rooms = list(data["rooms"].keys())

            for timeslot in chosen_timeslots:
                random.shuffle(possible_rooms)
                # find a free room if possible
                free_rooms = [r for r in possible_rooms if timeslot not in room_schedule[r]]
                if free_rooms:
                    room = free_rooms[0]
                else:
                    # otherwise just pick a random room
                    room = random.choice(possible_rooms)

                # update the student teacher and room schedules
                teacher_schedule[class_teacher].add(timeslot) 
                room_schedule[room].add(timeslot)
                for student in students_in_class:
                    student_schedule[student].add(timeslot)

                chromosome.append((c, timeslot, room)) # add lesson to chromosome

            for student in students_in_class: # track no. of classes each student takes
                student_class_count[student] += 1

        if fitness_function(chromosome, data) > -math.inf: # make sure chromosome is valid
            population.append(chromosome)

    return population

def tournament_selection(population, data, k= 4, num_parents = None):
    '''Selects the most fit individuals for next generation'''
    if num_parents is None: 
        num_parents = len(population) # default to no. of parents being same as last gen

    fitness_scores = []
    for chromosome in population: # Add all chromosomes and fitness scores to list
        fitness_scores.append([chromosome, fitness_function(chromosome, data)])
    valid_chromosomes = []

    for chromosome_fitness in fitness_scores: 
        if chromosome_fitness[1] > -math.inf: # Add all chromosomes with fitness > -math.inf to valid chromosomes list
            valid_chromosomes.append(chromosome_fitness)
    if valid_chromosomes == []: # If no valid chromosomes, use the last generation
        return []
    sorted_valid_chromosomes = merge_sort(valid_chromosomes, reverse = True) # sort in descending order
    if len(sorted_valid_chromosomes) < 4:
        k = 1
    

    parents = []
    for i in range(num_parents):
        tournament_candidates = random.sample(sorted_valid_chromosomes, k) # Pick k random chromosomes
        fitness_values = []
        for candidate in tournament_candidates:
            fitness_values.append(candidate[1]) # Create list of fitness values
        best_candidate_index = fitness_values.index(max(fitness_values)) # Get index of best score
        tournament_winner = tournament_candidates[best_candidate_index][0] # Get candidate with best score
        parents.append(tournament_winner) # Add to new population
    return parents

def repair_conflicts(chromosome, original_parent, data):
    '''Tries to fix chromosome not meeting hard constraints while keeping gene changes'''
    repaired = []
    # track room teacher and student schedules
    room_schedules = defaultdict(set)
    teacher_schedules = defaultdict(set)
    student_schedules = defaultdict(set)
    
    # Add all room teacher and student lessons 
    for lesson, timeslot, room in chromosome:
        teacher_schedules[lesson["teacher"]].add(timeslot)
        room_schedules[room].add(timeslot)
        for student in lesson["students"]:
            student_schedules[student].add(timeslot)
    
    for i, (lesson, timeslot, room) in enumerate(chromosome): # iterate through each lesson, numbered
        original_lesson, original_timeslot, original_room = original_parent[i] # get parent for chromosome
        
        
        if lesson != original_lesson: # dont try a new assignemnt if the child chromosome is different from parent
            attempt_new_schedule = False
            
            # If current setup is invalid (violates any hard constraints), set a flag to try a new one
            if (timeslot in teacher_schedules[lesson["teacher"]] or
                timeslot in room_schedules[room] or
                any(timeslot in student_schedules[s] for s in lesson["students"])):
                attempt_new_schedule = True
            
            if attempt_new_schedule:
                # find new setup for lesson by choosing new timeslot and room
                valid_timeslots = []
                for timeslot in range(30):
                    if timeslot not in teacher_schedules[lesson["teacher"]] and all(timeslot not in student_schedules[s] for s in lesson["students"]):
                        valid_timeslots.append(timeslot) # get valid timeslots
                
                if valid_timeslots:
                    new_timeslot = random.choice(valid_timeslots) # choose random timeslot 
                    valid_rooms = []
                    for room in data["rooms"]: 
                        if new_timeslot not in room_schedules[room] and lesson["subject"] in data["room_subject"][room] and len(lesson["students"]) <= data["rooms"][room]["capacity"]:
                            valid_rooms.append(room) # get valid rooms
                    
                    if valid_rooms: # randomly choose room and update teacher, room and student schedules.
                        new_room = random.choice(valid_rooms) 
                        teacher_schedules[lesson["teacher"]].add(new_timeslot)
                        room_schedules[new_room].add(new_timeslot)
                        for student in lesson["students"]:
                            student_schedules[student].add(new_timeslot)
                        repaired.append((lesson, new_timeslot, new_room))
                        continue
            # Keep original parent gene if repair failed, and add this to the schedules. 
            repaired.append(original_parent[i])
            teacher_schedules[original_lesson["teacher"]].add(original_timeslot)
            room_schedules[original_room].add(original_timeslot)
            for student in original_lesson["students"]:
                student_schedules[student].add(original_timeslot)
        else:
            repaired.append((lesson, timeslot, room)) # if lesson is the same as original, don't change anything
    
    return repaired

def find_swap_segment(parent_a, parent_b, min_length=1):
    """
    Find a segment where parents differ. If none exists of the minimum length, return none
    """
    # Use the minimum length of the two parents to avoid index errors.
    common_length = min(len(parent_a), len(parent_b))
    differing_indices = [i for i in range(common_length) if parent_a[i] != parent_b[i]] # get places where the chromsomes are different
    if len(differing_indices) < min_length:
        return None # if parents are identical, return none
    start = random.choice(differing_indices)
    end = start + 1
    while end < common_length and parent_a[end] != parent_b[end] and (end - start) < (min_length + 3):
        end += 1 # find end of swap segment
    return (start, end)

def mutate_gene(gene, data, original=None, attempts = 5):
    '''
    Mutate gene by picking new timeslot and room. Attempt 10 times to make valid change, otherwise make random change
    '''
    lesson, timeslot, room = gene
    # Pick new timeslot
    for attempt in range(attempts):
        new_timeslot = random.randint(0, 29) # Pick random timeslot

        # Pick room
        possible_rooms = []
        for room in data["rooms"]:
            if len(lesson["students"]) <= data["rooms"][room]["capacity"]:
                possible_rooms.append(room) # Get list of potential rooms
        
        if possible_rooms:
            new_room = random.choice(possible_rooms) # Pick random room with enough capacity 
        else:
            new_room = room # if no available rooms, pick a room at random

        day = timeslot // 6
        if day not in data["teacher_availability"][lesson["teacher"]]:
            continue # If teacher is not available on that day, skip attempt
        if timeslot == new_timeslot and room == new_room:
            new_timeslot = (new_timeslot+1) % 30# if origianl and final genes are the same, force a change
         
    return (lesson, new_timeslot, new_room)

def crossover(parent1, parent2, data, max_attempts=20):
    '''
    Swaps a gene segment from parents. Repair done if genetically identical children. Mutation done if repair doesn't cause change.
    '''
    for attempt in range(max_attempts): # attempt multiple times (20 by default)
        segment = find_swap_segment(parent1, parent2) # find swap segment with function
        if segment:  # if segment exists, perform regular crossover
            start, end = segment
            child1 = parent1[:start] + parent2[start:end] + parent1[end:]
            child2 = parent2[:start] + parent1[start:end] + parent2[end:]
        else:
            # If no segments, just swap randomly
            differing_indices = [i for i in range(len(parent1)) if parent1[i] != parent2[i]] # get differing indices
            child1 = parent1[:]
            child2 = parent2[:]
            if differing_indices:
                num_swaps = random.randint(1, len(differing_indices)) # swap them
                indices_to_swap = random.sample(differing_indices, num_swaps)
                for i in indices_to_swap:
                    child1[i], child2[i] = parent2[i], parent1[i]
            else:
                # If parents are identical, force a change with mutation
                child1 = parent1[:] # passed by value
                child2 = parent2[:]
                swap_index = random.randint(0, len(parent1)-1) # choose place to swap
                child1[swap_index] = mutate_gene(child1[swap_index], data, original=parent1[swap_index]) #mutate the swap index gene
                child2[swap_index] = mutate_gene(child2[swap_index], data, original=parent2[swap_index])

        # Repair conflicts (ensure not genetically identical)
        child1_repaired = repair_conflicts(child1, parent1, data)
        child2_repaired = repair_conflicts(child2, parent2, data)

        # find no. of differences in genes of children and parents
        diff1 = count_differences(child1_repaired, parent1)
        diff2 = count_differences(child2_repaired, parent2)

        # If no differences, force a mutation
        if diff1 == 0: # if no differences for one child, force a mutation to get a change
            index = random.randint(0, len(child1_repaired) - 1)
            child1_repaired[index] = mutate_gene(child1_repaired[index], data, original=parent1[index])
            child1_repaired = repair_conflicts(child1_repaired, parent1, data)
            diff1 = count_differences(child1_repaired, parent1)
        if diff2 == 0: # same for child 2 
            index = random.randint(0, len(child2_repaired) - 1)
            child2_repaired[index] = mutate_gene(child2_repaired[index], data, original=parent2[index])
            child2_repaired = repair_conflicts(child2_repaired, parent2, data)
            diff2 = count_differences(child2_repaired, parent2)

        if diff1 > 0 and diff2 > 0: # if there are genetic differences, return the children
            valid1 = fitness_function(child1_repaired, data) > -math.inf
            valid2 = fitness_function(child2_repaired, data) > -math.inf
            if valid1 and valid2:
                return child1_repaired, child2_repaired
            elif valid1:
                return child1_repaired, parent2[:]
            elif valid2:
                return parent1[:], child2_repaired

    # If no crossover points selected, just mutate parents
    mutated_parent1 = parent1[:]
    mutated_parent2 = parent2[:]
    index = random.randint(0, len(parent1) - 1)
    mutated_parent1[index] = mutate_gene(mutated_parent1[index], data, original=parent1[index])
    index = random.randint(0, len(parent2) - 1)
    mutated_parent2[index] = mutate_gene(mutated_parent2[index], data, original=parent2[index])
    return mutated_parent1, mutated_parent2

def count_differences(chrom1, chrom2):
    """Checks number of differences in parent and child chromosomes"""
    return sum(1 for gene1, gene2 in zip(chrom1, chrom2) if gene1 != gene2)

def replace_population(old_population, children, data, new_population_size, elitism = 20):
    """Replaces old population with new, better population"""
    last_gen_fitnesses = []
    for chromosome in old_population:
        last_gen_fitnesses.append([chromosome, fitness_function(chromosome, data)]) # Get last gens fitness
    sorted_fitness_of_last_gen = merge_sort(last_gen_fitnesses, reverse = True) # sort last gen fitness
    elites = sorted_fitness_of_last_gen[:elitism] # get best solutions from last gen

    fitness_of_children = []
    for chromosome in children:
        fitness_of_children.append([chromosome, fitness_function(chromosome, data)])
    sorted_fitness_of_children = merge_sort(fitness_of_children, reverse = True) # get children sorted by fitness

    required_children = new_population_size - elitism # find number of children required
    if required_children < 0:
        required_children = 0 # prevent list slicing errors
    
    surviving_children = sorted_fitness_of_children[:required_children]
    next_generation = elites + surviving_children
    return [chromosome for (chromosome, fitness) in next_generation] # retur list of chromosomes (without their fitnesses)

def mutate_chromosome(chromosome, data, mutation_rate = 0.025):
    """Has a chance to mutate a chromosome, by replacing a gene with a mutated gene"""
    new_chromosome = []
    for gene in chromosome: # iterate through evert gene
        if random.random() < mutation_rate: # mutate gene
            new_chromosome.append(mutate_gene(gene, data))
        else:
            new_chromosome.append(gene) # keep regular gene
    return new_chromosome

def run_genetic_algorithm(data: dict, final_classes: list, population_size: int = 250, generations:int = 25, k:int=4, num_parents:int = 250, base_mutation_rate: float = 0.05):
    """Runs the genetic algorithm and evolves solutions"""
    start_time = time.time() # record time
    initial_population = []
    for i in range (0,20): # try 20 times to generate initial population
        if initial_population ==[]:
            initial_population = generate_initial_population(data, final_classes, population_size=population_size)
        else:
            break
    if initial_population == []:
        log.add_message("Could not generate a timetable. Please try again. If errors persist, the constraints are too harsh", "error")
        return
    


    last_gen_best_fitness = None # To check if fitness is getting better
    no_improvement_generations = 0 # Track how many generations without improvement

    best_solution = None # Track best solution


    population = initial_population # set initial population
    mutation_rate = base_mutation_rate 
    
    for generation in range(generations): # Evolution loop
        parents = tournament_selection(population, data, k=k, num_parents=num_parents) # Select parents

        children = []

        for i in range(0, len(parents), 2): # iterate through parents (step set to 2)
            if i+1 < len(parents): # Choose parents to crossover
                parent1 = parents[i]
                if i+1 < len(parents):
                    parent2 = parents[i+1]
                else:
                    random_integer = random.randint(0, len(parents)-1)
                    parent2 = parents[random_integer]

            child1, child2 = crossover(parent1, parent2, data) # Crossover parents to get children
            
            child1 = mutate_chromosome(child1, data, mutation_rate = mutation_rate) # Mutate children
            child2 = mutate_chromosome(child2, data, mutation_rate = mutation_rate)

            children.append(child1)
            children.append(child2)

        population = replace_population(population, children, data, new_population_size=population_size) # replace previous population


        current_best_solution = max(population, key = lambda x: fitness_function(x, data)) # Get best solution
        current_best_solution_fitness = fitness_function(current_best_solution, data)

        if last_gen_best_fitness is None or current_best_solution_fitness > last_gen_best_fitness: # update best soluion if better one
            best_solution = current_best_solution
            last_gen_best_fitness = current_best_solution_fitness
            no_improvement_generations = 0
        elif last_gen_best_fitness <= current_best_solution_fitness: # otherwise, increment no imporvement generations
            no_improvement_generations +=1


        if no_improvement_generations == 3: 
            mutation_rate *= 1.6 # increase mutation to prevent stagnation
            log.add_message(f"Stagnation occured, increased mutation rate to {mutation_rate}")
        elif no_improvement_generations == 0:
            mutation_rate = base_mutation_rate # reset mutation
        if no_improvement_generations >=7:
            log.add_message("No improvement for 7 generations, stopping algorithm")
            break # if no improvement, then break


        time_taken = time.time() - start_time # record time taken
        log.add_message(f"Gen: {generation}, best fitness: {last_gen_best_fitness}, time: {time_taken:.2f}") # print time taken to log
    return best_solution

def validate_chromosome_subject_schedules(chromosome, data):
    """Checks whether students get all the subject they want."""

    # student maps to lessons they are assigned
    assigned_subjects_by_student = defaultdict(set)

    for (lesson, timeslot, room) in chromosome: # iterate through lessons
        subject = lesson["subject"]
        students = lesson["students"]
        
        for student_id in students:
            assigned_subjects_by_student[student_id].add(subject) # update student schedules

    
    mismatch_found = False
    for student_id in data["student_ids"]:
        desired_subjects = set(data["student_choices"][student_id]["preferred"]) # get desired subjects

        assigned_subjects = assigned_subjects_by_student[student_id] # get subjects the student is actually assigned

        # check each student is assigned their desired subjects
        for subj in desired_subjects:
            if subj not in assigned_subjects:
                student_name = data["student_names"][student_id] 
                log.add_message(f"Error: Student {student_name} is missing subject '{subj}', which they wanted (preferred).") # print when student doesn't get a lesson they should have
                mismatch_found = True

    if not mismatch_found:
        log.add_message("Validation Passed: All students' subject schedules match their preferences.") # if any mismatches found, inform user

def check_lessons_per_subject(chromosome, data):
    """Checks number of lessons student has for each subject"""

    
    subject_lesson_counts = defaultdict(int)

    # Count how many times each student, subject pair appears in the chromosome
    for (lesson, timeslot, room) in chromosome:
        subject = lesson["subject"]
        students = lesson["students"]
        for student in students:
            subject_lesson_counts[(student, subject)] += 1

    # Flag to track if any errors are found
    mismatch_found = False

    
    for student_id in data["student_ids"]: # iterate through each student
        # get student preference and backup subjects
        chosen_subjects = set(data["student_choices"][student_id]["preferred"])
        backup_subj = data["student_choices"][student_id]["backup"]
        if backup_subj:
            chosen_subjects.add(backup_subj) 

        # For each subject the student wants, check if they have desired, required or less no. of lessons
        for subj in chosen_subjects:
            count = subject_lesson_counts.get((student_id, subj), 0)
            if count < REQUIRED_LESSONS and count != 0:
                student_name = data["student_names"][student_id]
                log.add_message(f"Student {student_name} has {count} lessons for subject '{subj}', below the minimum of  {REQUIRED_LESSONS}", "error")
                mismatch_found = True
            if count < DESIRED_LESSONS and count !=0:
                student_name = data["student_names"][student_id]
                log.add_message(f"Student {student_name} has {count} lessons for subject '{subj}', but should ideally have:{DESIRED_LESSONS} lessons")
                
    if not mismatch_found:
        log.add_message(f"All students have at least the minimum number of required lessons per subject ({REQUIRED_LESSONS})") # inform the user if any errors occur

def generate_timetable():
    """Main procedure that runs the genetic algorithm and develops and outputs timetable. Generate timetable button will be binded to this"""
    global db_path
    if not db_path.strip(): 
        log.add_message("No database generated/selected, timetable generation cannot occur", "warning") # warning message if no database 
        return
    log.add_message("Starting timetable generation", "info")
    try:
        data = load_data(db_path) # Load data from the database

        subject_map = create_subjects_to_students_map(data) # get students per subject
        teacher_map = get_teachers_per_subject(data) # get teachers per subject
        forced = force_backup_option(subject_map, teacher_map, max_class_size=24) # decide students to revert to backup options
        subject_map = assign_backups(forced, subject_map, data) # assign backup to necessary students

        final_classes = create_balanced_classes(subject_map, teacher_map, max_class_size=24) # Create classes
        unassigned_teacher_ids = get_unassigned_teachers(data["teacher_ids"], final_classes)
        for id in unassigned_teacher_ids: # get each teacher's id
            teacher = data["teacher_names"][id]
            log.add_message(f"{teacher} is not teaching any classes")
        
        log.add_message("Created balanced classes for timetabling", "info")

        best_solution = run_genetic_algorithm(data, final_classes) # create best solution
        if not best_solution: # if no solution, tell the user
            messagebox.showwarning("Timetable Generation", "No valid solution found by the genetic algorithm.")
            log.add_message("No valid timetable solution found.", "warning")
            return

        log.add_message("Genetic algorithm completed. Validating solution", "info")

        # check validity of solution
        validate_chromosome_subject_schedules(best_solution, data)
        check_lessons_per_subject(best_solution, data)
        log.add_message("Solution validated. Inserting into database", "info")

        # insert timetable into database
        delete_timetable_tables(db_path)
        create_timetable_tables(db_path)
        insert_timetable(db_path, chromosome=best_solution)
        log.add_message("Timetable inserted into database successfully", "info")

        # export timetables as a .csv
        result_message = export_to_csv(best_solution, data)
        log.add_message(result_message, "info")
        messagebox.showinfo("Timetable Generation Complete", result_message)

    except Exception as e: 
        log.add_message(f"Error during timetable generation: {e}", "error")
        messagebox.showerror("Timetable Generation Error", f"An error occurred:\n{e}")




# Running main program
root = tk.Tk()
root.title("Timetable Generation System")
root.geometry("1024x768")  # Default resolution
root.minsize(400, 300)  # Minimum window size


# Log window:

log = Log_window(
    root,
    sidebar_width=199,
    log_width=799
)

# Instantiate database view:
db_view = Database_view(root, db_path, log)

# List of all tables to display in database view
tables = ["students", "choices", "teachers", "subjects", "teacher_subject", "rooms", "room_subject", "blocks", "block_list"]
submenu_names = []
for table in tables:
    submenu_names.append(table.capitalize())
submenu_commands = []
for table in tables:
    submenu_commands.append(lambda table = table: db_view.create_database_view(table))


# Main sidebar
sidebar = Sidebar_menu(
    root, 
    [200, 768], 
    ["File", "Databases", "Timetables", "Parameters", "Settings", "Generate Timetables"],
    [
        lambda: toggle_submenu(root, ["Import .csv File", "Import Database", "Backup Database"], [import_input_file, import_database, backup_database], "File"),
        lambda: toggle_submenu(root, submenu_names, submenu_commands, "Databases"),
        lambda: toggle_submenu(root, [], [], "Timetables"),
        lambda: toggle_submenu(root, [], [], "Parameters"),
        lambda: toggle_submenu(root, [], [], "Settings"),
        lambda: generate_timetable()
    ]
)

sidebar.sidebar.lift()

root.bind('<Configure>', lambda event: calculate_log_width()) # Triggered when window is resized, or when anything else is resized or moved

calculate_log_width()
root.mainloop()
