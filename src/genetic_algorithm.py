"""Legacy genetic timetable solver and class-construction helpers."""

import math
import random
import time
from collections import defaultdict

from config import DESIRED_LESSONS, GA_SOFT_CONSTRAINTS, REQUIRED_LESSONS
from sorting import merge_sort

ga_soft_constraints = GA_SOFT_CONSTRAINTS


def _add_log(log, message, priority="info"):
    """write to the UI log when the solver is being run by the GUI."""
    if log is not None:
        log.add_message(message, priority)

def create_subjects_to_students_map(data: dict) -> dict:
    """Split students up into classes based on max class size, returns lists of classes"""
    subject_code_to_student_map = defaultdict(list)# maps subject to list of students that want to do it
    for student_id in data["student_ids"]:
        for subject in data["student_choices"][student_id]["preferred"]: 
            subject_code_to_student_map[subject].append(student_id)  # maps a subject code to all the students that have that subject as a preferred class
    return subject_code_to_student_map

def get_teachers_per_subject(data: dict) -> dict:
    """map subject code to list of teachers"""
    subject_teacher_map = defaultdict(list)# maps subject to list of students that can teach it

    for teacher_id in data["teacher_ids"]: # iterate through each teacher
        teachers_subjects = data["teacher_subject"][teacher_id] 
        for subject in teachers_subjects: # iterate through each subject teacher can teach
            subject_teacher_map[subject].append(teacher_id) # add teacher id to subject- teacher map
    return subject_teacher_map

def force_backup_option(subject_code_to_student_map, subject_teacher_map, max_class_size = 24): 
    """assign backup classes if not enough teachers to teach all potential students"""
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
    """assign student to backup option by updating subject_code_to_student_map"""
    for student_id, removed_subject in pushed_to_backup:
        backup_subject = data["student_choices"][student_id]["backup"] # only one backup option
        subject_code_to_student_map[backup_subject].append(student_id) # add to backup option
        if student_id in subject_code_to_student_map[removed_subject]:
            subject_code_to_student_map[removed_subject].remove(student_id) # remove from original option
    return subject_code_to_student_map

def create_balanced_classes(subject_code_to_student_map, subject_teacher_map, max_class_size = 24):
    """create the actual final classes, using the helper even spread function"""

    classes = [] # list of classes
    class_id_counter = 1 # to uniquely identify each class

    for subject_code, student_list in subject_code_to_student_map.items(): # iterate through each subject and list of students

        teachers = subject_teacher_map[subject_code] # get teachers that can teach the suject
        num_students = len(student_list) # get num of students 
        num_teachers = len(teachers) # get num of teachers

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

def validate_classes_against_choices(final_classes, data, log=None):
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
                _add_log(log, f"Mismatch: Student {student_name} is in subject '{subject_code}' but it's neither their preferred nor backup subject.", "error")
            elif subject_code in data["student_choices"][student_id]["backup"]:
                student_name = data["student_names"][student_id]
                _add_log(log, f"Student {student_name} was forced to take their backup option ", "warning")
                backup_count +=1

    if mismatch_count == 0: # no mismatches, all correct
        _add_log(log, f"Validation: All students are in subjects they actually chose. Number of backups: {backup_count}", "info")
    else:
        _add_log(log, f"Validation: Found {mismatch_count} total mismatches.", "info") # add messages to log to say mismatches found

def validate_student_class_counts(final_classes, data, min_classes=3, max_classes=4, log=None):
    '''Checks how many classes each student appears in. If less than min or more than max, error printed '''

    assigned_count = defaultdict(int) # map student to no. of lessons they have
    for c in final_classes:
        for student_id in c["students"]:
            assigned_count[student_id] += 1 
    issues = 0 # store class separation violations as issues

    for student_id in data["student_ids"]:
        count = assigned_count[student_id]  # number of classes student is in
        student_name = data["student_names"][student_id]
        if count < min_classes: # if student is in too few classes
            _add_log(log, f"Student {student_name} only has {count} classes, less than min classes of {min_classes}", "error")
            issues += 1
        elif count > max_classes: # if student is in too many classes
            _add_log(log, f"Student {student_name} has {count} classes more than max of {max_classes})", "error")
            issues+=1
    _add_log(log, f"The number of students with an incorrect number of classes is {issues}", "info")

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

def run_genetic_algorithm(data: dict, final_classes: list, population_size: int = 250, generations:int = 25, k:int=4, num_parents:int = 250, base_mutation_rate: float = 0.05, log=None):
    """Runs the genetic algorithm and evolves solutions"""
    start_time = time.time() # record time
    initial_population = []
    for i in range (0,20): # try 20 times to generate initial population
        if initial_population ==[]:
            initial_population = generate_initial_population(data, final_classes, population_size=population_size)
        else:
            break
    if initial_population == []:
        _add_log(log, "Could not generate a timetable. Please try again. If errors persist, the constraints are too harsh", "error")
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
            _add_log(log, f"Stagnation occured, increased mutation rate to {mutation_rate}")
        elif no_improvement_generations == 0:
            mutation_rate = base_mutation_rate # reset mutation
        if no_improvement_generations >=7:
            _add_log(log, "No improvement for 7 generations, stopping algorithm")
            break # if no improvement, then break


        time_taken = time.time() - start_time # record time taken
        _add_log(log, f"Gen: {generation}, best fitness: {last_gen_best_fitness}, time: {time_taken:.2f}") # print time taken to log
    return best_solution

def validate_chromosome_subject_schedules(chromosome, data, log=None):
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
                _add_log(log, f"Error: Student {student_name} is missing subject '{subj}', which they wanted (preferred).") # print when student doesn't get a lesson they should have
                mismatch_found = True

    if not mismatch_found:
        _add_log(log, "Validation Passed: All students' subject schedules match their preferences.") # if any mismatches found, inform user

def check_lessons_per_subject(chromosome, data, log=None):
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
                _add_log(log, f"Student {student_name} has {count} lessons for subject '{subj}', below the minimum of  {REQUIRED_LESSONS}", "error")
                mismatch_found = True
            if count < DESIRED_LESSONS and count !=0:
                student_name = data["student_names"][student_id]
                _add_log(log, f"Student {student_name} has {count} lessons for subject '{subj}', but should ideally have:{DESIRED_LESSONS} lessons")
                
    if not mismatch_found:
        _add_log(log, f"All students have at least the minimum number of required lessons per subject ({REQUIRED_LESSONS})") # inform the user if any errors occur
