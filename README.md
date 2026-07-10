# Player Sorter - Tournament Management System

**A professional, feature-rich free[^1] tournament management application for chess and e-sports competitions.**\
***Download link: https://github.com/OBielskyi/player_sorter/releases/latest/***

![Screenshot 1](https://github.com/OBielskyi/player_sorter/blob/main/screenshots/1.png)
![Screenshot 2](https://github.com/OBielskyi/player_sorter/blob/main/screenshots/2.png)
![Screenshot 3](https://github.com/OBielskyi/player_sorter/blob/main/screenshots/3.png)
![Screenshot 4](https://github.com/OBielskyi/player_sorter/blob/main/screenshots/4.png)
[More screenshots?](https://github.com/OBielskyi/player_sorter/blob/main/screenshots/)

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

### Chess-Specific Enhancements

**Tiebreak Methods:**
Swiss and Round-Robin tournaments support a choice of tiebreak method, selected when the tournament is configured:
- Buchholz (sum of opponents' scores)
- Sonneborn-Berger (opponents' scores weighted by result)
- Direct Encounter (head-to-head result between tied players)
- Schmuljan (opponents' scores, with wins adding and losses subtracting)
- None (fall back to rating)

**FIDE-Compliant Colour Balancing:**
Swiss, Round-Robin, Knockout, and Scheveningen tournaments automatically balance White/Black assignments, modelled on FIDE's own colour-allocation rules (Handbook C.04.1/C.04.3). This includes preventing three same-colour games in a row, honouring absolute vs. soft colour preferences, and falling back to alternation, rating, or a coin flip when no other criterion applies. Byes and half-byes are treated as colourless and don't affect the balance.

**Optional FIDE Player Details:**
Chess players can optionally be given a title (GM, IM, WGM, FM, WIM, CM, WFM, WCM), FIDE ID, federation code, sex, and birth date. None of this is required for normal use — it only matters if you plan to export the tournament as a TRF16 file for official FIDE rating submission.

**Configurable ELO Range:**
When setting up a chess tournament, you can optionally restrict player ratings to a minimum and/or maximum ELO.

### Export & Tournament Management

- **Export to CSV** — quick, spreadsheet-friendly standings/results export.
- **Export to HTML** — a shareable, browser-viewable tournament report.
- **Export to TRF16** — generates a FIDE-standard Tournament Report File suitable for actual FIDE rating submission, prompting for tournament name, city, federation, chief/deputy arbiter(s), time control, and start/end dates. (Not recommended for Knockout tournaments, since TRF16 assumes scores accumulate across all rounds the way they do in Swiss/Round-Robin — the app will warn you if you try.)
- **Saved Tournament Manager** — browse every saved tournament (finished or still in progress), resume an unfinished one from where you left off, delete old ones, or export any of them (CSV/HTML/TRF16) without having to reopen it first.

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
- **Update notifications** - Checks GitHub in the background on startup for a newer release and lets you know (non-intrusively, and only once per version — dismissing a version's notice keeps it from reappearing)

### Get Started

#### For *Windows* and *Linux*
Download and run the executable[^2] for your OS.

#### For *MacOS*
**Please note that I'm not planning to add an executable for MacOS because of lacking a device running MacOS needed to compile the executable[^3], so you'll have to run the Cross-Platform version (the .py file).**
1. Make sure Python is installed and properly configured.
2. Simply run `python player_sorter.py` and select your theme to begin organizing professional tournaments in minutes!

### Building

*[Nuitka](https://nuitka.net/)* is used for the generation of binary executables.
#### For *Windows*

The command used for building the Windows executables from the *[source code](https://github.com/OBielskyi/player_sorter/blob/main/source.py)* is as follows: 
`python -m nuitka --jobs=8 --lto=yes --python-flag=no_asserts --standalone --windows-company-name="Oleksandr Bielskyi" --windows-product-name="Player Sorter" --windows-product-version=X.X.X --windows-file-version=X.X.X --windows-file-description="Professional tournament management software" --enable-plugin=tk-inter --windows-console-mode=disable --windows-icon-from-ico=logo.ico --output-filename="PlayerSorter-vX.X.X-Windows" source.py`

#### For *Linux*

`python -m nuitka --jobs=8 --lto=yes --python-flag=no_asserts --standalone --onefile --enable-plugin=tk-inter --linux-icon=logo.png --output-filename="PlayerSorter-vX-X-X-Linux" source.py`

### Contributing

See *[CONTRIBUTING.md](https://github.com/OBielskyi/player_sorter/blob/main/CONTRIBUTING.md)*.

[^1]: "Free" as in speech. See [LICENSE](https://github.com/OBielskyi/player_sorter/blob/main/LICENSE)
[^2]: The executables before version 1.2.0 are generated with *Pyinstaller* (V1.2.0 introduced faster and smaller *Nuitka*-compiled executables). If you don't like the binaries or something doesn't work, you can run the Python file directly or create the executable binaries yourself.
[^3]: It's also possible (and not too difficult) to create your own executable binary for your OS. [Good first read](https://github.com/oop7/Py-to-EXE-Guide)
***
Copyright (C) 2026 Oleksandr Bielskyi
