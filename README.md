# Timetable Generation System

A Python desktop application for automatically generating school timetables using a genetic algorithm. 
The system allocates students to classes based on their subject choices, assigns teachers, and schedules lessons across available rooms and timeslots while accounting for hard and soft constraints.

Developed as my A-level Computer Science NEA (2024–2025), in consultation with school staff responsible for timetabling. The aim was to provide a simpler alternative to manual timetabling, with configurable scheduling preferences and an integrated interface for managing and viewing data.

## Features

- Automatic class allocation based on subject preferences, backup choices, teacher availability anda class sizes.
- Genetic algorithm implemented from scratch, using tournament selection, crossover, mutation, conflict repair and elitism.
- Configurable penalties for room suitability, consecutive teaching periods and travel between lessons.
- SQLite database for storing student, teacher, subject, room and timetable data.
- Tkinter interface for viewing individual student and teacher timetables, searching and sorting database records, and executing custom SQL queries.
- Validated CSV input, database import and backup, and automatic CSV export of generated timetables.

## Timetabling algorithm

School timetabling is a combinatorial optimisation problem: the number of possible schedules grows rapidly as the number of classes, rooms and timeslots increases. This project uses a genetic algorithm to search for feasible schedules without exhaustively exploring the solution space.

The problem is divided into two stages:

### 1. Class allocation

Students are grouped according to their subject choices. The algorithm balances class sizes, assigns teachers and uses students' backup subject choices where necessary to accommodate limited teaching capacity.

### 2. Lesson scheduling

Each candidate timetable is represented as a chromosome: a list of lessons, with each gene containing a class, timeslot and room. An initial population is constructed using randomised assignments, taking teacher availability and existing bookings into account.

The population is evolved through:

1. **Fitness evaluation** – reject candidates violating hard constraints and penalise undesirable scheduling decisions.
2. **Tournament selection** – select fitter individuals as parents.
3. **Crossover and mutation** – combine parts of parent timetables and alter individual lesson assignments to explore alternative schedules.
4. **Conflict repair** – attempt to resolve hard-constraint violations introduced during crossover.
5. **Elitism** – retain high-fitness individuals across generations.

The mutation rate increases when fitness stagnates, and the search terminates early if no improvement is made over several generations.

### Constraints

| Hard constraints (rejected by the fitness function) | Soft constraints (fitness penalties) |
| --- | --- |
| No overlapping lessons for a student or teacher | Prefer teachers qualified for the subject |
| No double-booked rooms | Prefer rooms suitable for the subject |
| Room capacity must accommodate the class | Minimise travel between consecutive student lessons |
| Every scheduled class must have a teacher | Avoid three consecutive teaching periods |
| At least four lessons per scheduled student–subject pair | Prefer five lessons per subject |

Teacher availability is also considered when constructing the initial population. The default schedule consists of five weekdays with six periods each. The algorithm is heuristic: a successful result is not guaranteed for every input, and the global optimum is not guaranteed.

## Getting started

### Requirements

- Python 3 with Tkinter support
- `pandas` and `sqlparse` (listed in `requirements.txt`)

SQLite is included in the Python standard library. On some Linux distributions, Tkinter must be installed separately (e.g. `python3-tk` on Ubuntu/Debian).

### Installation and usage

```bash
git clone https://github.com/AmVSing/Timetable-Generation.git
cd Timetable-Generation
python -m pip install -r requirements.txt
python src/main.py
```

1. Open **File → Import .csv File** to load school data, or **Import Database** to restore an existing compatible SQLite database.
2. Use **Databases** to inspect the imported records.
3. Optionally adjust the scheduling penalties under **Parameters**.
4. Select **Generate Timetables** to run the algorithm.
5. Open **Timetables** to inspect student or teacher schedules. Generated results are stored in the database and exported to a timestamped CSV in the working directory.

Example and validation datasets are included in [`test-inputs/`](test-inputs/). For a first run, save the data worksheet from `Test F12.xlsx` as a CSV, preserving the original column headers and order. The expected CSV schema is defined in [`src/config.py`](src/config.py). Use synthetic or anonymised data for testing.

## Project structure

```text
Timetable-Generation/
├── src/
│   ├── main.py                 # Application entry point
│   ├── genetic_algorithm.py    # Class allocation and scheduling
│   ├── database.py             # SQLite database operations
│   ├── timetable_database.py   # Timetable persistence and data loading
│   ├── gui.py                  # Tkinter interface
│   ├── file_io.py              # Import, export and backup
│   ├── input_validation.py     # Input schema and record validation
│   ├── data_structures.py      # Supporting data structures
│   ├── sorting.py              # Sorting algorithms
│   └── config.py               # Schemas, constants and penalty settings
├── test-inputs/                # Development and validation datasets
└── requirements.txt
```
