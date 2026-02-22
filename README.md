# TUImysqlworkbench

A terminal-based MySQL Workbench built with Python and [Textual](https://github.com/Textualize/textual). This TUI app allows you to manage MySQL databases, tables, and data interactively from your terminal.

## Features
- List, create, and delete schemas (databases)
- List, create, rename, truncate, and delete tables
- View and edit table data
- Add, rename, and delete columns
- Insert and delete rows
- Export/import tables to/from Excel files
- Export/import entire schemas (databases) via SQL files
- Query editor for running custom SQL queries
- Keyboard navigation and input cancellation (Escape/Ctrl+C)

## Requirements
- Python 3.8+
- MySQL server
- [Textual](https://github.com/Textualize/textual)
- pandas
- openpyxl
- mysql-connector-python

## Installation
1. Clone the repository:
	```bash
	git clone https://github.com/Franciszek821/TUImysqlworkbench.git
	cd TUImysqlworkbench
	```
2. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
	Or install manually:
	```bash
	pip install textual pandas openpyxl mysql-connector-python
	```

## Usage
1. Configure your MySQL connection in `terminal.py` (edit the `DB_CONFIG` dictionary).
2. Run the app:
	```bash
	python terminal.py
	```
3. Use the keyboard to navigate and perform actions. Use Escape or Ctrl+C to cancel input prompts.

## Key Bindings
- `Escape`: Cancel input or go back
- `Ctrl+C`: Cancel input
- Arrow keys: Navigate lists
- Tab: Navigate tabs
- Enter: Select/confirm


## Notes
- Excel import creates a new table with all columns as VARCHAR(255).
- Export/import of schemas uses `mysqldump` and `mysql` commands (ensure they are installed and in your PATH).

## License
MIT License