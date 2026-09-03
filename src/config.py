"""shared constants for timetable configuration"""


# constants for default UI element colours
DEFAULT_BUTTON_BG_COLOUR = "#484752"
DEFAULT_BUTTON_TEXT_COLOUR = "#FFFFFF"
DEFAULT_BUTTON_TEXT_HOVER_COLOUR = "#FFD700"
DEFAULT_SIDEBAR_BG_COLOUR = "#2b2b2d"
DEFAULT_LOG_BG_COLOUR = "#FFFFFF"
DEFAULT_LOG_TEXT_BG_COLOUR = "#FFFFFF"
DEFAULT_LOG_TEXT_FG_COLOUR = "#000000"
DEFAULT_LOG_RESIZER_COLOUR = "dark grey"

# default font size
DEFAULT_FONT_SIZE = 9

# schema required for database input
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
    "choices": ["student_id", "subject_code", "is_backup"],
}

# output timetable schema
TIMETABLE_SCHEMA = {
    "timetables": [
        "timetable_id", "class_id", "subject_code", "teacher_id",
        "room_code", "timeslot",
    ],
    "timetable_students": ["timetable_id", "student_id"],
}

# expected columns in input .csv
EXPECTED_COLUMNS = [
    "entity_type", "full_name", "preferred_class_1", "preferred_class_2",
    "preferred_class_3", "preferred_class_4", "backup_preference",
    "subject_specialities", "availability", "room_code", "capacity",
    "taught_subjects", "block_name", "block_code", "nearby_blocks",
    "subject_code", "subject_name",
]

# constants for required and desired lessons for timetable generation
REQUIRED_LESSONS = 4
DESIRED_LESSONS = 5

# soft constraints for timetabling (can be violated)
GA_SOFT_CONSTRAINTS = {
    "teacher_penalty": 6,
    "room_penalty": 60,
    "student_penalty": 5,
}
