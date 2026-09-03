"""Timetable persistence and solver-data loading."""

import sqlite3
from collections import defaultdict
from typing import Any, Dict

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

def insert_timetable(db_path: str, chromosome: list, log: Any = None):
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
        message = f"The following error occured while inserting data into the timetable tables: {e}"
        if log:
            log.add_message(message, "error")
        return message

def delete_timetable_tables(db_path: str, log: Any = None):
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
         message = f"The following error occured while deleting the timetable tables: {e}"
         if log:
             log.add_message(message, "error")
         return message

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
    conn.close()
    return output
