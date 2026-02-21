import os
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Center
from textual.widgets import Header, Footer, ListView, ListItem, Label, Input, Static
import mysql.connector
import asyncio
from textual.widgets import DataTable
import subprocess


#TODO:
'''
Eidt table
Dark/Light Theme Toggle: Let users switch between UI themes.
Connection Profiles: Save and switch between multiple database connection settings.
Error Logging: Show detailed error logs and allow users to review past errors.'''

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 3306)),
}


def get_schemas():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES;")
    schemas = sorted([row[0] for row in cursor.fetchall()], key=str.lower)
    cursor.close()
    conn.close()
    return schemas


def get_tables(schema):
    conn = mysql.connector.connect(**DB_CONFIG, database=schema)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = sorted([row[0] for row in cursor.fetchall()], key=str.lower)
    cursor.close()
    conn.close()
    return tables

def get_columns(schema, table):
    conn = mysql.connector.connect(**DB_CONFIG, database=schema)
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
    columns = [row[0] for row in cursor.fetchall()]  # preserves order
    cursor.close()
    conn.close()
    return columns

def get_rows(schema, table):
    conn = mysql.connector.connect(**DB_CONFIG, database=schema)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM `{table}`;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


#Options
def create_table(schema=None, tableName=None, self=None):
    if self.selected_screen != 0:
        conn = mysql.connector.connect(**DB_CONFIG, database=schema)
        cursor = conn.cursor()
        cursor.execute(f"CREATE TABLE `{tableName}` (id INT PRIMARY KEY AUTO_INCREMENT);")
        conn.commit()
        cursor.close()
        conn.close()

def create_database(schemaName, self=None):
    if self.selected_screen == 0:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE {schemaName};")
        conn.commit()
        cursor.close()
        conn.close()

async def change_schema(self):
    if self.selected_screen != 0:
        self.selected_screen = 0
        self.table_list.clear()
        self.table_list.display = False
        self.schema_list.display = True
        if hasattr(self, "data_table"):
            self.data_table.display = False
        self.refresh_schemas()
    else:
        await self.show_warning("Already in main screen")

async def change_table(self):
    if self.selected_screen == 2:
        self.selected_screen = 1
        self.table_list.clear()
        self.table_list.display = True
        self.schema_list.display = False
        if hasattr(self, "data_table"):
            self.data_table.display = False
        self.refresh_tables()
    elif self.selected_screen == 1:
        await self.show_warning("Already in table selection screen")
    else:
        await self.show_warning("Select a schema first")

async def open_query_editor(self):
    if hasattr(self, "query_editor_box"):
        self.query_editor_box.remove()
    if hasattr(self, "query_result_box"):
        self.query_result_box.remove()
    
    self.query_editor_box = Center(
        Input(placeholder="Enter SQL query...", id="query_input")
    )
    self.mount(self.query_editor_box)
    self.query_one("#query_input", Input).focus()

    async def handle_query_submit(event):
        sql = event.value
        self.query_editor_box.remove()
        try:
            conn = mysql.connector.connect(**DB_CONFIG, database=self.selected_schema)
            cursor = conn.cursor()
            cursor.execute(sql)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                data_table = DataTable()
                for col in columns:
                    data_table.add_column(col)
                for row in rows:
                    data_table.add_row(*row)
                self.query_result_box = Center(data_table)
            else:
                conn.commit()
                self.query_result_box = Center(Static("[green]Query executed successfully [/green]"))
            cursor.close()
            conn.close()
        except Exception as e:
            self.query_result_box = Center(Static(f"[red]Error: {e}[/red]"))
        self.mount(self.query_result_box)


#drop truncate tables
def delete_table(schema, table, self=None):
    conn = mysql.connector.connect(**DB_CONFIG, database=schema)
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE `{table}`;")
    conn.commit()
    cursor.close()
    conn.close()

    
def truncate_table(schema, table, self=None):
    conn = mysql.connector.connect(**DB_CONFIG, database=schema)
    cursor = conn.cursor()
    cursor.execute(f"TRUNCATE TABLE `{table}`;")
    conn.commit()
    cursor.close()
    conn.close()


#columns
def add_column(schema, table, self=None):
    # Prompt for column definition with a clear input
    if hasattr(self, "input_prompt"):
        self.input_prompt.remove()
    self.current_action = "Add Column"
    self.pending_table = (schema, table)
    self.input_prompt = Center(
        Input(placeholder="Column definition (e.g., age INT)", id="add_col_def")
    )
    self.mount(self.input_prompt)
    self.query_one("#add_col_def", Input).focus()

def rename_column(schema, table, self=None):
    self.pending_table = (schema, table)
    self.input_prompt = Center(
        Input(placeholder="Column to rename", id="rename_col_old")
    )
    self.mount(self.input_prompt)
    self.query_one("#rename_col_old", Input).focus()

def delete_column(schema, table, self=None):
    self.pending_table = (schema, table)
    self.input_prompt = Center(
        Input(placeholder="Column to delete", id="delete_col_name")
    )
    self.mount(self.input_prompt)
    self.query_one("#delete_col_name", Input).focus()

def refresh(self):
    if self.selected_screen == 0:
        self.refresh_schemas()
    elif self.selected_screen == 1:
        self.refresh_tables()
    elif self.selected_screen == 2:
        self.refresh_columns()


def insert_row(schema, table, self=None):
    columns = get_columns(schema, table)
    self.pending_table = (schema, table)
    self.insert_columns = columns
    self.input_prompt = Center(
        Input(placeholder=f"Enter values for {', '.join(columns)} separated by commas", id="insert_row_values")
    )
    self.mount(self.input_prompt)
    self.query_one("#insert_row_values", Input).focus()

def delete_row(schema, table, self=None):
    self.pending_table = (schema, table)
    self.input_prompt = Center(
        Input(placeholder="Enter row # to delete", id="delete_row_num")
    )
    self.mount(self.input_prompt)
    self.query_one("#delete_row_num", Input).focus()

def export_database(self=None):
    self.input_prompt = Center(
        Input(placeholder="Enter database name to export", id="export_db_name")
    )
    self.mount(self.input_prompt)
    self.query_one("#export_db_name", Input).focus()
    
def import_database(self=None):
    self.input_prompt = Center(
        Input(placeholder="Enter database name to import into", id="import_db_name")
    )
    self.mount(self.input_prompt)
    self.query_one("#import_db_name", Input).focus()

ACTIONS = {
    "Create Schema"   : create_database,
    "Change Schema"     : change_schema,
    " " : lambda *args, **kwargs: None,
    "Change Table"      : change_table,
    "Create Table"      : create_table,
    "Delete Table"      : delete_table,
    "Truncate Table"    : truncate_table,
    "  " : lambda *args, **kwargs: None,
    "Add Column"        : add_column,
    "Rename Column"     : rename_column,
    "Delete Column"     : delete_column,
    "   " : lambda *args, **kwargs: None,
    "Insert Row"        : insert_row,
    "Delete Row"        : delete_row,
    "    " : lambda *args, **kwargs: None,
    "Export Schema"     : export_database,
    "Import Schema"     : import_database,
    "     " : lambda *args, **kwargs: None,
    "Query Editor"      : open_query_editor,
    "Refresh"           : refresh
}

class MysqlWorkbenchTUI(App):

    def show_confirmation(self, action_name, schema, table):
        if hasattr(self, "confirmation_prompt"):
            self.confirmation_prompt.remove()
        self.pending_action =  (action_name, schema, table)
        self.confirmation_prompt = Center(
            Input(placeholder=f"Type YES to confirm {action_name} '{table}'", id="confirm_input")
        )
        self.mount(self.confirmation_prompt)
        self.query_one('#confirm_input', Input).focus()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_schema = None
        self.selected_screen = 0  # 0=schema, 1=table, 2=columns
        self.current_action = None  # Ensure this attribute always exists

    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("escape", "comeback", "Comeback to screen before"),
    ]

    async def action_comeback(self):
        if hasattr(self, "query_editor_box"):
            self.query_editor_box.remove()
            if hasattr(self, "query_result_box"):
                self.query_result_box.remove()
            return
        if self.selected_screen == 2:
            await self.change_table_comeback()
        elif self.selected_screen == 1:
            await self.change_schema_comeback()
        
    async def change_table_comeback(self):
        if self.selected_screen == 2:
            self.selected_screen = 1
            self.table_list.clear()
            self.table_list.display = True
            self.schema_list.display = False
            if hasattr(self, "data_table"):
                self.data_table.display = False
            self.refresh_tables()
        elif self.selected_screen == 1:
            await self.show_warning("Already in table selection screen")
        else:
            await self.show_warning("Select a schema first")

    async def change_schema_comeback(self):
        if self.selected_screen != 0:
            self.selected_screen = 0
            self.table_list.clear()
            self.table_list.display = False
            self.schema_list.display = True
            if hasattr(self, "data_table"):
                self.data_table.display = False
            self.refresh_schemas()
        else:
            await self.show_warning("Already in main screen")

    def refresh_tables(self):
        """Clear and reload tables for the selected schema."""
        if not hasattr(self, "selected_schema"):
            return

        self.table_list.clear()
        try:
            tables = get_tables(self.selected_schema)
            for table in tables:
                self.table_list.append(
                    ListItem(Label(table), name=table)
                )
        except Exception as e:
            self.table_list.append(ListItem(Label(f"Error: {e}")))


    def refresh_columns(self):
        """Clear and reload columns for the selected table in the data_table widget."""
        if not hasattr(self, "selected_schema") or not hasattr(self, "data_table") or not self.data_table.display:
            return
        table_name = None
        if hasattr(self, "title") and ">" in self.title:
            table_name = self.title.split(" > ")[-1]
        if not table_name:
            return
        # Remove and recreate the data_table widget
        self.data_table.remove()
        self.data_table = DataTable()
        try:
            columns = get_columns(self.selected_schema, table_name)
            # Add virtual row number column
            self.data_table.add_column("#")
            for col in columns:
                self.data_table.add_column(col)
            rows = get_rows(self.selected_schema, table_name)
            for idx, row in enumerate(rows, start=1):
                self.data_table.add_row(str(idx), *row)
            self.mount(self.data_table, after=self.table_list)
            self.data_table.display = True
            self.table_list.display = False
        except Exception as e:
            self.table_list.append(ListItem(Label(f"Error: {e}")))

    def refresh_schemas(self):


        self.schema_list.clear()
        try:
            schemas = get_schemas()
            for schema in schemas:
                self.schema_list.append(
                    ListItem(Label(schema), name=schema)
                )
        except Exception as e:
            self.schema_list.append(ListItem(Label(f"Error: {e}")))

    #warning
    async def show_warning(self, message: str, duration: float =0.5):
        if hasattr(self, "warning_box"):
            self.warning_box.remove()
        
        self.warning_box = Center(Static(f"[red]{message}[/red]"))
        self.mount(self.warning_box)
    
        await asyncio.sleep(duration)
        self.warning_box.remove()

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            self.schema_list = ListView(id="schemas")
            self.table_list = ListView(id="tables")
            self.option_list = ListView(id="options")
            yield self.schema_list
            yield self.table_list
            yield self.option_list
        if self.selected_screen != 0:
            yield Footer()

    def on_mount(self) -> None:
        try:
            schemas = get_schemas()
            for schema in schemas:
                self.schema_list.append(
                    ListItem(Label(schema), name=schema)
                )
        except Exception as e:
            self.schema_list.append(
                ListItem(Label(f"Error: {e}"))
            )
        self.schema_list.display = True
        self.table_list.display = False
        self.option_list.styles.width = "30%"


        self.action_items = {}
        for name in ACTIONS.keys():
            item = ListItem(Label(name), name=name)
            self.option_list.append(item)
            self.action_items[name] = item



    def show_input(self, action_name):
        if hasattr(self, "input_prompt"):
            self.input_prompt.remove()
        self.current_action = action_name
        self.input_prompt = Center(
            Input(placeholder=f"Enter name:", id="name")
        )
        self.mount(self.input_prompt)
        self.query_one("#name", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted):
        value = event.value
        if event.input.id == "import_db_name":
            self.import_db_name = event.value.strip()
            self.input_prompt.remove()
            self.input_prompt = Center(
                Input(placeholder="Enter path of .sql file", id="import_db_file")
            )
            self.mount(self.input_prompt)
            self.query_one("#import_db_file", Input).focus()
            return
        elif event.input.id == "import_db_file":
            import_path = event.value.strip()
            db_name = self.import_db_name
            user = DB_CONFIG["user"]
            password = DB_CONFIG["password"]
            host = DB_CONFIG["host"]
            port = DB_CONFIG["port"]
            if not os.path.isfile(import_path):
                await self.show_warning("Provided path is not a file.", 10)
                self.input_prompt.remove()
                return
            try:
                cmd = [
                    "mysql",
                    f"-h{host}",
                    f"-P{port}",
                    f"-u{user}",
                    f"-p{password}",
                    db_name
                ]
                with open(import_path, "r") as f:
                    result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    await self.show_warning(f"Database imported from {import_path}", 3)
                else:
                    await self.show_warning(f"Import failed: {result.stderr}", 10)
            except Exception as e:
                await self.show_warning(f"Error: {e}", 10)
            self.input_prompt.remove()
            return
        elif event.input.id == "export_db_name":
            self.export_db_name = event.value.strip()
            self.input_prompt.remove()
            self.input_prompt = Center(
                Input(placeholder="Enter folder path to save export", id="export_db_folder")
            )
            self.mount(self.input_prompt)
            self.query_one("#export_db_folder", Input).focus()
            return

        elif event.input.id == "export_db_folder":
            folder_path = event.value.strip()
            db_name = self.export_db_name
            if not os.path.isdir(folder_path):
                await self.show_warning("Provided path is not a directory.", 10)
                self.input_prompt.remove()
                return
            export_path = os.path.join(folder_path, f"{db_name}.sql")
            user = DB_CONFIG["user"]
            password = DB_CONFIG["password"]
            host = DB_CONFIG["host"]
            port = DB_CONFIG["port"]
            try:
                cmd = [
                    "mysqldump",
                    f"-h{host}",
                    f"-P{port}",
                    f"-u{user}",
                    f"-p{password}",
                    db_name
                ]
                with open(export_path, "w") as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    await self.show_warning(f"Database exported to {export_path}", 2)
                else:
                    await self.show_warning(f"Export failed: {result.stderr}", 10)
            except Exception as e:
                await self.show_warning(f"Error: {e}", 10)
            self.input_prompt.remove()
            return
        elif event.input.id == "delete_row_num":
            row_number = int(event.value.strip())
            self.input_prompt.remove()
            schema, table = self.pending_table
            rows = get_rows(schema, table)
            if row_number < 1 or row_number > len(rows):
                await self.show_warning("Invalid row number", 10)
                return
            pk_value = rows[row_number - 1][0]
            self.confirmation_prompt = Center(
                Input(placeholder=f"Type YES to confirm deletion of row {row_number}", id="confirm_delete_row")
            )
            self.mount(self.confirmation_prompt)
            self.query_one("#confirm_delete_row", Input).focus()
            self.pending_row_pk = pk_value
            self.pending_row_number = row_number
            return
        elif event.input.id == "confirm_delete_row":
            if event.value.strip().upper() == "YES" or event.value.strip().upper() == "Y":
                schema, table = self.pending_table
                pk_value = self.pending_row_pk
                try:
                    conn = mysql.connector.connect(**DB_CONFIG, database=schema)
                    cursor = conn.cursor()
                    # Dynamically get PK column name
                    cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name = 'PRIMARY';")
                    pk_info = cursor.fetchone()
                    if pk_info:
                        pk_col = pk_info[4]  # Column_name is at index 4
                    else:
                        pk_col = 'id'  # fallback
                    cursor.execute(f"DELETE FROM `{table}` WHERE `{pk_col}` = %s;", (pk_value,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    await self.show_warning(f"Row {self.pending_row_number} deleted successfully.")
                    self.refresh_columns()
                except Exception as e:
                    await self.show_warning(f"Error: {e}", 1)
            else:
                await self.show_warning("Row deletion cancelled")
            self.confirmation_prompt.remove()
            return
        elif event.input.id == "insert_row_values":
            values = [v.strip() for v in value.split(",")]
            schema, tables = self.pending_table
            columns = self.insert_columns
            if len(values) != len(columns):
                await self.show_warning(f"Incorrect number of values", 10)
                self.input_prompt.remove()
                return
            # Check column types
            conn = mysql.connector.connect(**DB_CONFIG, database=schema)
            cursor = conn.cursor()
            cursor.execute(f"SHOW COLUMNS FROM `{tables}`;")
            col_info = cursor.fetchall()
            type_errors = []
            for idx, (col_name, col_type, _, _, _, _) in enumerate(col_info):
                val = values[idx]
                # Simple type check for INT
                if "int" in col_type.lower():
                    try:
                        int(val)
                    except ValueError:
                        type_errors.append(f"Column '{col_name}' expects INT, got '{val}'")
                # Add more type checks as needed (float, date, etc.)
            if type_errors:
                await self.show_warning("; ".join(type_errors), 10)
                self.input_prompt.remove()
                cursor.close()
                conn.close()
                return
            placeholders = ", ".join(["%s"] * len(values))
            col_names = ", ".join([f"`{col}`" for col in columns])
            try:
                cursor.execute(
                    f"Insert INTO `{tables}` ({col_names}) VALUES ({placeholders});",
                    values
                )
                conn.commit()
                cursor.close()
                conn.close()
                await self.show_warning("Row inserted")
                self.refresh_columns()
            except Exception as e:
                await self.show_warning(f"Error: {e}", 10)
            self.input_prompt.remove()
            return
        elif event.input.id == "delete_col_name":
            schema, table = self.pending_table
            columns = get_columns(schema, table)
            if len(columns) <= 1:
                col_name = event.value.strip()
                self.input_prompt.remove()
                await self.show_warning("Cannot delete the last column. Delete the table instead", 1)
                return
            col_name = event.value.strip()
            self.input_prompt.remove()

            try:
                conn = mysql.connector.connect(**DB_CONFIG, database=schema)
                cursor = conn.cursor()
                cursor.execute(f"ALTER TABLE `{table}` DROP COLUMN `{col_name}`;")
                conn.commit()
                cursor.close()
                conn.close()
                await self.show_warning("Column deleted")
                self.refresh_columns()
            except Exception as e:
                await self.show_warning(f"Error: {e}", 1)
            return
        elif event.input.id == "rename_col_old":
            self.old_col_name = event.value.strip()
            self.input_prompt.remove()
            self.input_prompt = Center(
                Input(placeholder="New column name", id="rename_col_new")
            )
            self.mount(self.input_prompt)
            self.query_one("#rename_col_new", Input).focus()
            return
        elif event.input.id == "rename_col_new":
            new_col_name = event.value.strip()
            self.input_prompt.remove()
            schema, table = self.pending_table
            try:
                conn = mysql.connector.connect(**DB_CONFIG, database=schema)
                cursor = conn.cursor()
                cursor.execute(f"ALTER TABLE `{table}` RENAME COLUMN `{self.old_col_name}` TO `{new_col_name}`;")
                conn.commit()
                cursor.close()
                conn.close()
                await self.show_warning("Column renamed")
                self.refresh_columns()
            except Exception as e:
                await self.show_warning(f"Error: {e}")
            return

        elif event.input.id == "confirm_input":
            self.confirmation_prompt.remove()
            if event.value.strip().upper() == "YES" or event.value.strip().upper() == "Y":
                action_name, schema, table = self.pending_action
                try:
                    ACTIONS[action_name](schema, table, self)
                    await self.show_warning(f"{action_name} successful")
                    if hasattr(self, "data_table"):
                        self.data_table.remove()
                    self.selected_screen = 1
                    self.table_list.display = True
                    self.refresh_tables()
                    self.title = f"{self.selected_schema}"
                except Exception as e:
                    await self.show_warning(f"Error {e}", duration=10)
            else:
                await self.show_warning("Action cancelled")
            return
        elif event.input.id == "query_input":
            if hasattr(self, "query_editor_box"):
                self.query_editor_box.remove()
            try:
                conn = mysql.connector.connect(**DB_CONFIG, database=self.selected_schema)
                cursor = conn.cursor()
                cursor.execute(value)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    data_table = DataTable()
                    for col in columns:
                        data_table.add_column(col)
                    for row in rows:
                        data_table.add_row(*row)
                    self.query_result_box = Center(data_table)
                    self.mount(self.query_result_box)
                    self.set_focus(data_table)
                else:
                    conn.commit()
                    self.query_result_box = Center(Static("[green]Query executed successfully [/green]"))
                cursor.close()
                conn.close()
            except Exception as e:
                self.query_result_box = Center(Static(f"[red]Error: {e}[/red]"))
            self.mount(self.query_result_box)
            self.refresh_tables()
            self.refresh_schemas()
            return
        
        self.input_prompt.remove()

        if self.current_action == "Add Column":
            schema, table = self.pending_table
            col_def = value.strip()  # e.g., "age INT"
            try:
                conn = mysql.connector.connect(**DB_CONFIG, database=schema)
                cursor = conn.cursor()
                cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN {col_def};")
                conn.commit()
                cursor.close()
                conn.close()
                await self.show_warning("Column added")
                self.refresh_columns()
            except Exception as e:
                await self.show_warning(f"Error: {e}")
            return
        if self.current_action in ACTIONS:
            if self.current_action == "Create Table":
                ACTIONS[self.current_action](self.selected_schema, value, self)
                self.refresh_tables()
            elif self.current_action == "Create Database":
                ACTIONS[self.current_action](value, self)
                self.refresh_schemas()



    async def on_list_view_selected(self, event: ListView.Selected):


        if event.list_view.id == "schemas":
            self.selected_schema = event.item.name
            self.table_list.clear()
            try:
                tables = get_tables(self.selected_schema)
                for table in tables:
                    self.table_list.append(ListItem(Label(table), name=table))
                self.schema_list.display = False
                self.table_list.display = True
                self.set_focus(self.table_list)
                self.selected_screen = 1
                self.title = f"{self.selected_schema}"
            except Exception as e:
                self.table_list.append(ListItem(Label(f"Error: {e}")))

        elif event.list_view.id == "tables":
            self.data_table = DataTable()
            try:
                columns = get_columns(self.selected_schema, event.item.name)
                # Add virtual row number column
                self.data_table.add_column("#")
                for col in columns:
                    self.data_table.add_column(col)
                rows = get_rows(self.selected_schema, event.item.name)
                for idx, row in enumerate(rows, start=1):
                    self.data_table.add_row(str(idx), *row)
                if rows is None or len(rows) == 0:
                    self.show_warning("Table is empty")
                self.mount(self.data_table, after=self.table_list)
                self.table_list.display = False
                self.data_table.display = True
                self.selected_screen = 2
                self.title = f"{self.selected_schema} > {event.item.name}"
            except Exception as e:
                self.table_list.append(ListItem(Label(f"Error: {e}")))



        selected_name = event.item.name
        if selected_name in ["Create Table"] and self.selected_screen == 1:
            self.show_input(selected_name)
        elif selected_name in ["Create Table"] and self.selected_screen != 1:
            await self.show_warning("Select schema first")
        elif selected_name in ["Create Database"] and self.selected_screen == 0:
            self.show_input(selected_name)
        elif selected_name in ["Create Database"] and self.selected_screen != 0:
            await self.show_warning("Go to main screen to create a database") 
        elif selected_name in ["Change Schema", "Change Table"]:
            coro = ACTIONS[selected_name](self)
            if asyncio.iscoroutine(coro):
                await coro
            else:
                coro
        elif selected_name == "Query Editor":
            coro = ACTIONS[selected_name](self)
            if asyncio.iscoroutine(coro):
                await coro
            else:
                coro
        elif selected_name in ["Delete Table", "Truncate Table"]:
            if self.selected_screen == 2 and hasattr(self, "data_table"):
                table_name = self.title.split(" > ")[-1]
                schema_name = self.selected_schema
                self.show_confirmation(selected_name, schema_name, table_name)
            else:
                await self.show_warning("Select a table first")
        elif selected_name in ["Add Column", "Rename Column", "Delete Column", "Insert Row", "Delete Row"]:
            if self.selected_screen == 2 and hasattr(self, "data_table"):
                table_name = self.title.split(" > ")[-1]
                schema_name = self.selected_schema
                ACTIONS[selected_name](schema_name , table_name, self)
            else:
                await self.show_warning("Select a table first")
        elif selected_name in ["Export Database", "Import Database"]:
            if self.selected_screen == 0:
                ACTIONS[selected_name](self)
            else:
                await self.show_warning("Go to main screen to import/export a database") 
        elif selected_name == "Refresh":
            ACTIONS[selected_name](self)

if __name__ == "__main__":
    MysqlWorkbenchTUI().run()