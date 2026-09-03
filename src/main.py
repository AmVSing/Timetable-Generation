"""Application entry point and dependency wiring for Timetable Generation."""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, List

import gui as gui_module
from database import Database_module
from file_io import (
    backup_database as backup_database_file,
    export_to_csv,
    import_database as import_database_file,
    import_input_file as import_input_file_data,
)
from genetic_algorithm import (
    assign_backups,
    check_lessons_per_subject,
    create_balanced_classes,
    create_subjects_to_students_map,
    force_backup_option,
    get_teachers_per_subject,
    get_unassigned_teachers,
    run_genetic_algorithm,
    validate_chromosome_subject_schedules,
)
from gui import (
    Database_view,
    Log_window,
    Parameters_submenu,
    Settings_submenu,
    Sidebar_menu,
    Timetable_submenu,
)
from timetable_database import (
    create_timetable_tables,
    delete_timetable_tables,
    insert_timetable,
    load_data,
)


db_path = ""
current_open_submenu = None
current_left_padding = 200

root = None
log = None
db_view = None
sidebar = None


def import_input_file():
    """Run the CSV import flow and retain the selected database path."""
    global db_path
    new_db_path = import_input_file_data(log, db_view)
    if new_db_path:
        db_path = new_db_path


def import_database():
    """Run the database import flow and retain the selected path."""
    global db_path
    new_db_path = import_database_file(log, db_view)
    if new_db_path:
        db_path = new_db_path


def backup_database():
    """Back up the database currently selected by the application."""
    backup_database_file(db_path, log)


def toggle_submenu(
    root_window: tk.Widget,
    button_names: List[str],
    button_commands: List[Callable],
    submenu_name: str,
) -> None:
    """Open or close a sidebar or one of the full-width submenu views."""
    global current_open_submenu

    database_view = gui_module.current_open_database_view
    if submenu_name in {"Timetables", "Settings", "Parameters"} and database_view is not None:
        database_view.destroy()
        gui_module.current_open_database_view = None
        database_view = None

    if (
        current_open_submenu is not None
        and getattr(current_open_submenu, "submenu_name", None) == submenu_name
    ):
        if database_view:
            log.add_message("Close database view before opening other submenus")
            return
        if hasattr(current_open_submenu, "sidebar"):
            current_open_submenu.sidebar.destroy()
        elif hasattr(current_open_submenu, "frame"):
            current_open_submenu.frame.destroy()
        current_open_submenu = None
        calculate_log_width()
        log.log_frame.lift()
        sidebar.sidebar.lift()
        return

    if current_open_submenu:
        if hasattr(current_open_submenu, "sidebar"):
            current_open_submenu.sidebar.destroy()
        elif hasattr(current_open_submenu, "frame"):
            current_open_submenu.frame.destroy()
        current_open_submenu = None

    if submenu_name == "Timetables":
        if not db_path:
            log.add_message("No database loaded for viewing.", "warning")
            return
        current_open_submenu = Timetable_submenu(
            root_window, Database_module(db_path), log
        )
        return
    if submenu_name == "Settings":
        current_open_submenu = Settings_submenu(root_window, log)
        calculate_log_width()
        log.log_frame.lift()
        return
    if submenu_name == "Parameters":
        current_open_submenu = Parameters_submenu(root_window, log)
        calculate_log_width()
        log.log_frame.lift()
        return
    if not button_names and not button_commands:
        calculate_log_width()
        log.log_frame.lift()
        sidebar.sidebar.lift()
        return

    current_open_submenu = Sidebar_menu(
        root_window, [200, 1080], button_names, button_commands
    )
    current_open_submenu.submenu_name = submenu_name

    database_view = gui_module.current_open_database_view
    if database_view and hasattr(current_open_submenu, "sidebar"):
        current_open_submenu.sidebar.pack_forget()
        current_open_submenu.sidebar.pack(
            side=tk.LEFT, fill=tk.Y, before=database_view
        )

    calculate_log_width()
    log.log_frame.lift()
    sidebar.sidebar.lift()


def calculate_log_width() -> None:
    """Fit the log beside the main sidebar and any open secondary sidebar."""
    global current_left_padding

    if root is None or sidebar is None or log is None:
        return
    root.update_idletasks()
    if current_open_submenu and hasattr(current_open_submenu, "sidebar"):
        current_left_padding = (
            sidebar.sidebar.winfo_width()
            + current_open_submenu.sidebar.winfo_width()
        )
    else:
        current_left_padding = sidebar.sidebar.winfo_width()

    new_width = root.winfo_width() - current_left_padding
    log.log_frame.place_configure(
        x=current_left_padding, rely=1, anchor="sw", width=new_width
    )


def generate_timetable():
    """Generate, validate, persist, and export a timetable."""
    if not db_path.strip():
        log.add_message(
            "No database generated/selected, timetable generation cannot occur",
            "warning",
        )
        return

    log.add_message("Starting timetable generation", "info")
    try:
        data = load_data(db_path)
        subject_map = create_subjects_to_students_map(data)
        teacher_map = get_teachers_per_subject(data)
        forced = force_backup_option(subject_map, teacher_map, max_class_size=24)
        subject_map = assign_backups(forced, subject_map, data)
        final_classes = create_balanced_classes(
            subject_map, teacher_map, max_class_size=24
        )

        for teacher_id in get_unassigned_teachers(
            data["teacher_ids"], final_classes
        ):
            log.add_message(
                f"{data['teacher_names'][teacher_id]} is not teaching any classes"
            )

        log.add_message("Created balanced classes for timetabling", "info")
        best_solution = run_genetic_algorithm(
            data, final_classes, log=log
        )
        if not best_solution:
            messagebox.showwarning(
                "Timetable Generation",
                "No valid solution found by the genetic algorithm.",
            )
            log.add_message("No valid timetable solution found.", "warning")
            return

        log.add_message("Genetic algorithm completed. Validating solution", "info")
        validate_chromosome_subject_schedules(best_solution, data, log=log)
        check_lessons_per_subject(best_solution, data, log=log)
        log.add_message("Solution validated. Inserting into database", "info")

        delete_timetable_tables(db_path, log=log)
        create_timetable_tables(db_path)
        insert_timetable(db_path, chromosome=best_solution, log=log)
        log.add_message("Timetable inserted into database successfully", "info")

        result_message = export_to_csv(best_solution, data, log=log)
        if result_message:
            log.add_message(result_message, "info")
            messagebox.showinfo("Timetable Generation Complete", result_message)
    except Exception as error:
        log.add_message(
            f"Error during timetable generation: {error}", "error"
        )
        messagebox.showerror(
            "Timetable Generation Error", f"An error occurred:\n{error}"
        )


def main() -> None:
    """Build and start the Tkinter application."""
    global root, log, db_view, sidebar

    root = tk.Tk()
    root.title("Timetable Generation System")
    root.geometry("1024x768")
    root.minsize(400, 300)

    log = Log_window(root, sidebar_width=199, log_width=799)
    db_view = Database_view(root, db_path, log)

    tables = [
        "students",
        "choices",
        "teachers",
        "subjects",
        "teacher_subject",
        "rooms",
        "room_subject",
        "blocks",
        "block_list",
    ]
    submenu_names = [table.capitalize() for table in tables]
    submenu_commands = [
        lambda table=table: db_view.create_database_view(table)
        for table in tables
    ]

    sidebar = Sidebar_menu(
        root,
        [200, 768],
        [
            "File",
            "Databases",
            "Timetables",
            "Parameters",
            "Settings",
            "Generate Timetables",
        ],
        [
            lambda: toggle_submenu(
                root,
                ["Import .csv File", "Import Database", "Backup Database"],
                [import_input_file, import_database, backup_database],
                "File",
            ),
            lambda: toggle_submenu(
                root, submenu_names, submenu_commands, "Databases"
            ),
            lambda: toggle_submenu(root, [], [], "Timetables"),
            lambda: toggle_submenu(root, [], [], "Parameters"),
            lambda: toggle_submenu(root, [], [], "Settings"),
            generate_timetable,
        ],
    )
    sidebar.sidebar.lift()

    root.bind("<Configure>", lambda event: calculate_log_width())
    calculate_log_width()
    root.mainloop()


if __name__ == "__main__":
    main()
