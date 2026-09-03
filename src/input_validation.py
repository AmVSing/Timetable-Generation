"""Validation for imported timetable source data."""

from typing import List

import pandas as pd

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
