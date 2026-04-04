# AIAxiom Project

A Python-based tool for automated task management and AI-assisted development.

## Project Structure

```
AIAxiom/
|-- src/                    # Source code
|   |-- core/              # Core functionality modules
|   |   |-- auto_agent/    # Auto agent implementations
|   |   |-- function/      # Function management
|   |   |-- json/          # JSON utilities
|   |   |-- log_mgr/       # Logging management
|   |   |-- model/         # Data models
|   |-- tools/             # Tool implementations
|   |   |-- skill_loader/  # Skill loading utilities
|   |   |-- task_mgr/      # Task management
|   |   |-- todo_mgr.py    # Todo management
|   |   |-- tools.py       # Main tools module
|   |-- main.py            # Main application entry point
|-- greet.py               # Example greeting module
|-- requirements.txt       # Python dependencies
|-- README.md             # This file
```

## Setup Instructions

1. Ensure Python 3.7+ is installed
2. Install dependencies: `pip install -r requirements.txt`
3. Run the main application: `python src/main.py`

## Dependencies

See `requirements.txt` for the complete list of required packages.

## Usage

The project provides tools for task management, AI-assisted development workflows, and automated testing.

## Development

- Source code is organized in the `src/` directory
- Core modules are in `src/core/`
- Tool implementations are in `src/tools/`
- Tests should be written in a separate `tests/` directory