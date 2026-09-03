"""class wrapper for database operations"""

import sqlite3
from typing import Any, Dict, List, Tuple, Union

import pandas as pd
import sqlparse

from data_structures import Hash_table

class Database_module:
    def __init__(self, db_name: str) -> None:
        """connect to db"""
        self.conn=sqlite3.connect(db_name) # connect to db
        self.cursor=self.conn.cursor() # cursor to modify db

        # create hash tables
        self.student_hash_table = Hash_table(100) 
        self.teacher_hash_table = Hash_table(50)
        self.subject_hash_table = Hash_table(20)
        self.block_hash_table = Hash_table(10)
        
        
        self.create_tables() # create database tables

    def delete_tables(self) -> None:
        # used to reset tables on code rerun (mainly for testing)
        tables = ["students", "subjects", "teachers", "teacher_subject", "teacher_availability", "rooms", "room_subject", "blocks", "nearby_blocks", "choices"]
        for table in tables:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.commit()
    
    def create_tables(self) -> None:
        """create all the necessary tables (before timetabling) in the database"""

        # create students table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS students(
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name VARCHAR NOT NULL
                            );
        """)

        # create subjects table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
        subject_code VARCHAR PRIMARY KEY,
        subject_name VARCHAR NOT NULL
                            );
        """)

        # create teachers table
        self.cursor.execute("""
         CREATE TABLE IF NOT EXISTS teachers 
            (
            teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name VARCHAR NOT NULL
                        );              
                        
        """)
        # create teacher_availability teacher
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_availability (
        teacher_id INTEGER NOT NULL,
        day VARCHAR NOT NULL,
        PRIMARY KEY (teacher_id, day),
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        );""")
        # create teacher_subject linking subject (links teacher with the subjects they teach)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subject (
        teacher_id INTEGER NOT NULL,
        subject_code VARCHAR NOT NULL,
        PRIMARY KEY (teacher_id, subject_code),
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
        FOREIGN KEY (subject_code) REFERENCES subjects(subject_code)
                            );
        """)
        

        # create rooms table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_code VARCHAR PRIMARY KEY NOT NULL,
            capacity INTEGER,
            block_code VARCHAR,
            FOREIGN KEY (block_code) REFERENCES blocks(block_code)
        );
        """)



        # create table to link rooms to subjects
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_subject (
        room_code VARCHAR,
        subject_code VARCHAR,
        PRIMARY KEY (room_code, subject_code),
        FOREIGN KEY (room_code) REFERENCES rooms(room_code),
        FOREIGN KEY (subject_code) REFERENCES subjects(subject_code)
                            
                            
                            
                            
                            
                            )
        """)
        # create blocks table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
        block_code VARCHAR PRIMARY KEY NOT NULL,
        block_name VARCHAR NOT NULL
                            );
        """)
        # create nearby_blocks table (since the previous approach i used with lists violates 3NF)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS block_list (
        block_code VARCHAR NOT NULL,
        nearby_block_code VARCHAR NOT NULL,
        PRIMARY KEY (block_code, nearby_block_code),
        FOREIGN KEY (block_code) REFERENCES blocks(block_code),
        FOREIGN KEY (nearby_block_code) REFERENCES blocks(block_code)
                            );""")

        # create choices table (linking table that links students to chosen subjects)
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
        """insert student data into student table, and insert preferred subjects (and backup) into subject table"""
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
        """insert a student's preferred subject into the choices table"""
        self.cursor.execute("INSERT OR IGNORE INTO choices (student_id, subject_code, is_backup) VALUES (?, ?, ?);",
                            (data["student_id"], data["subject_code"], data["is_backup"]))


    def insert_teacher(self, data: Dict[str, Union[str, int]]) -> None:
        """insert teacher data, teacher's subject specialities and teacher's availability into respective tables"""
        self.cursor.execute("INSERT OR IGNORE INTO teachers (full_name) VALUES (?);", 
                            (data["full_name"],))
        teacher_id = self.cursor.lastrowid # get the last inserted teachers teacher id

        # insert records into teacher_availability. If availability is empty, empty string is inserted
        days_available = data.get("availablity", "").strip("[]").split(",")
        if not any(day.strip() for day in days_available): # if there's not a single non blank string 
            days_available = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"] # days teacher can teach

        for day in days_available:
            if day.strip():
                # insert teacher availability
                self.cursor.execute("INSERT OR IGNORE INTO teacher_availability (teacher_id, day) VALUES (?, ?);", (teacher_id, day.strip())) 
        # insert records into teacher_subject table:
        subject_specialities = data.get("subject_specialities").strip("[]").split(",") # get subjects teacher can teach
        for subject in subject_specialities:
            if subject.strip():
                # insert teacher subject specialities
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
        """insert data (from columns on room entity) into room_subject linking table"""
        self.cursor.execute("INSERT OR IGNORE INTO room_subject (room_code, subject_code) VALUES (?, ?);", (data["room_code"], data["subject_code"],))

    
    def insert_block(self, data: Dict[str, Union[str, int]]) -> None:
        """insert block row into block table"""
        self.cursor.execute("INSERT OR IGNORE INTO blocks (block_code, block_name) VALUES (?, ?);", (data["block_code"], data["block_name"]))
        
        nearby_blocks = data.get("nearby_blocks").strip("[]").split(",")
        for block in nearby_blocks:
            if block.strip():
                self.cursor.execute("INSERT OR IGNORE INTO block_list (block_code, nearby_block_code) VALUES (?, ?);", (data["block_code"], block.strip()))


    def insert_subject(self, data: Dict[str, Union[str, int]]) -> None:
        """insert row into subject table"""
        self.cursor.execute("INSERT OR IGNORE INTO subjects (subject_code, subject_name) VALUES (?,?)", (data["subject_code"], data["subject_name"]))

    
    def query_table(self, table: str = "", query: str = "") -> Union[List[Tuple[Any, Any]], str]:
        """run an SQL query and return the associated data"""
        query = query.strip() # user/ GUI query
        table = table.strip() # table being queried

        if not query: 
            if table:
                query = f"SELECT * FROM {table}" # default query
            else:
                 return "Error: no query or table provided" # error if no query or table provided
        parsed_statements = sqlparse.parse(query) # parse the query with sqlparse
        if len(parsed_statements) > 1 or not parsed_statements: # reject if more or less than one statement
            return "Error: Only one SQL statement is allowed at once"
        if parsed_statements[0].get_type() != "SELECT":
            return "Error: Only DQL commands (i.e. SELECT queries) are allowed"

        try: # try doing the query, if any errors, return them instead
            self.cursor.execute(query)
            rows = self.cursor.fetchall() # get resultant data
            columns = [] # stores field names
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
