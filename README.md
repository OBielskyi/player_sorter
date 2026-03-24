# Player Sorter - Tournament Management System

**A professional, feature-rich tournament management application for chess and e-sports competitions.**

## Description

Player Sorter is a comprehensive desktop application designed to organize and manage tournaments with ease. Built with Python and tkinter, it requires no external dependencies and runs seamlessly on Windows, macOS, and Linux.

### Key Features

**Tournament Formats:**
- Swiss System with intelligent pairing and tiebreak methods
- Round-Robin for complete round-based competition
- Single-elimination Knockout brackets
- Scheveningen team-vs-team format

**Game Support:**
- Chess tournaments with automatic ELO rating calculations (OTB and Correspondence modes)
- E-Sports leagues with trophy-based ranking systems

**Player Management:**
- Comprehensive name system (first name, last name, nickname)
- Automatic save/load functionality with separate databases for chess and e-sports
- Support for player withdrawals and half-byes
- Fair ranking system that properly handles withdrawn players

**Professional UI:**
- 7 beautiful themes (Simple Light/Dark, Catppuccin, Nord, Rose Pine, Dracula, Solarized)
- Maximized interface optimized for desktop use
- Large, readable fonts and generous spacing
- Complete visual coherence with no white spaces

**Additional Modes:**
- Dual mode for quick paired competitions
- Battle Royale elimination format
- Balanced team creation and management

### Perfect For

- Chess club directors managing weekly tournaments
- E-sports event organizers running gaming competitions
- School chess coaches tracking student progress
- Gaming cafe managers hosting tournaments
- Anyone organizing competitive events

### Technical Details

- **No installation required** - Single executable or Python file
- **Zero dependencies** - Uses built-in tkinter library
- **Cross-platform** - Works on Windows, macOS, and Linux
- **Lightweight** - Runs efficiently on any modern computer
- **Data persistence** - Automatically saves players and preferences

### Get Started

#### For *Windows* and *Linux*
Download and run the executable[^1] for your OS.

#### For *MacOS*

[!NOTE]
I'm not planning to add an executable for MacOS because of lacking a device running MacOS needed to compile the executable, so you'll have to run the .py file directly. [^2]

1. Make sure Python is installed and properly configured.
2. Simply run `python player_sorter.py` and select your theme to begin organizing professional tournaments in minutes!

[^1]: The executables before version 1.2.0 are generated with *Pyinstaller* (V1.2.0 introduced faster and smaller *Nuitka*-compiled executables). If you don't like the binaries or something doesn't work, you can run the Python file directly or create the executable binaries yourself.
[^2]: It's also possible (and not too difficult) to create your own executable binary for your OS. [Good first read](https://github.com/oop7/Py-to-EXE-Guide)
