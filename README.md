# PromptBox

A modern desktop prompt library for Windows, built with Python and Tkinter.

## Features

- Organize reusable prompts by category
- Search and manage favorites
- Create, edit, and delete prompts
- Import and export prompt backups as JSON
- Light and dark appearance options
- Local SQLite storage

## Run from source

1. Install Python 3.12 or later.
2. Download or clone this repository.
3. Run `run.bat` on Windows.

## Build the Windows executable

Run `build.bat` on Windows, or use the **Build Windows EXE** workflow under the Actions tab.

The workflow creates a `PromptBox.exe` artifact that can be downloaded from its successful run. Artifacts are retained for 30 days.

## Data and privacy

PromptBox stores its database and settings locally in the current Windows user's application data directory. Prompt content is not uploaded by the application.

## Project status

Version 0.5.0 — development build. Not yet a signed installer or Microsoft Store package.
