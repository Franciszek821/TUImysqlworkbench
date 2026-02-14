from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label
import mysql.connector
import os
from dotenv import load_dotenv

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
    schemas = [row[0] for row in cursor.fetchall()]
    cursor.close
    conn.close()
    return schemas

class SchemaApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        self.list_view = ListView()
        yield self.list_view
        yield Footer()

    def on_mount(self) -> None:
        try:
            schemas = get_schemas()
            for schema in schemas:
                self.list_view.append(
                    ListItem(Label(schema))
                )
        except Exception as e:
            self.list_view.append(
                ListItem(Label(f"Error: {e}"))
            )

if __name__ == "__main__":
    SchemaApp().run()

