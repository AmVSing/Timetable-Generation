"""Tkinter widgets and views for the timetable application."""

import tkinter as tk
from datetime import datetime
from tkinter import Menu, ttk
from typing import Callable, List

from config import (
    DEFAULT_BUTTON_BG_COLOUR,
    DEFAULT_BUTTON_TEXT_COLOUR,
    DEFAULT_BUTTON_TEXT_HOVER_COLOUR,
    DEFAULT_FONT_SIZE,
    DEFAULT_LOG_BG_COLOUR,
    DEFAULT_LOG_RESIZER_COLOUR,
    DEFAULT_LOG_TEXT_BG_COLOUR,
    DEFAULT_LOG_TEXT_FG_COLOUR,
    DEFAULT_SIDEBAR_BG_COLOUR,
    GA_SOFT_CONSTRAINTS,
)
from database import Database_module

default_font_size = DEFAULT_FONT_SIZE
ga_soft_constraints = GA_SOFT_CONSTRAINTS
current_open_database_view = None

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
            self.log.log_frame.lift()
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
