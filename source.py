#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Oleksandr Bielskyi
"""
Player Sorter - A simple GUI application for creating and sorting player tables
Supports Chess (ELO) and E-sports (Trophies) with three modes:
- Dual: Pair players based on rating with randomness
- Battle Royale: Sort by win rate
- Teams: Create balanced teams
"""

import csv
import datetime
import filecmp
import html
import json
import os
import pathlib
import random
import re
import shutil
import threading
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import filedialog, messagebox, ttk
from typing import List

# ── Version / update-check constants ──────────────────────────────────────────
# Bump this on every release. Used solely to compare against the latest GitHub
# release tag to power the startup "Update available" check below.
__version__ = "2.5.0"

# owner/repo slug for the GitHub API's "latest release" endpoint. That endpoint
# already resolves to the newest non-draft, non-prerelease release, so no
# extra prerelease-filtering logic is needed on our end.
_GITHUB_REPO = "OBielskyi/player_sorter"
_GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"
_GITHUB_LATEST_RELEASE_URL = f"https://github.com/{_GITHUB_REPO}/releases/latest/"

# JSON file that persists the "Don't show this again" update-notification choice
_UPDATE_SETTINGS_FILE = "player_sorter_update_settings.json"


def _parse_version(version_str: str) -> tuple:
    """Parse a version string like "v2.3.0" or "2.3.0" into a tuple of ints,
    e.g. (2, 3, 0), for numeric comparison (so "2.10.0" correctly sorts after
    "2.9.0" instead of being compared as strings).

    Non-numeric/unparseable segments are ignored; an entirely unparseable or
    empty string returns an empty tuple, which _is_version_newer() treats as
    "older than everything" - matching the requirement that a missing/unknown
    current version should be treated as obviously out of date.
    """
    if not version_str:
        return ()
    cleaned = version_str.strip().lstrip("vV")
    parts = []
    for segment in cleaned.split("."):
        digits = "".join(ch for ch in segment if ch.isdigit())
        if digits == "":
            break
        parts.append(int(digits))
    return tuple(parts)


def _is_version_newer(latest_str: str, current_str: str) -> bool:
    """Return True if latest_str is a newer version than current_str.

    An unparseable/missing current_str is always treated as out of date
    (returns True, as long as latest_str parses to something at all).
    """
    latest = _parse_version(latest_str)
    current = _parse_version(current_str)
    if not latest:
        return False  # Couldn't parse the remote version; don't claim an update exists.
    if not current:
        return True  # No usable local version - assume outdated, per design.
    # Pad the shorter tuple with zeros so (2, 4) vs (2, 4, 0) compares equal.
    length = max(len(latest), len(current))
    latest_padded = latest + (0,) * (length - len(latest))
    current_padded = current + (0,) * (length - len(current))
    return latest_padded > current_padded


# Theme definitions
THEMES = {
    "Simple Light": {
        "bg": "#FFFFFF",
        "fg": "#000000",
        "select_bg": "#0078D7",
        "select_fg": "#FFFFFF",
        "button_bg": "#E1E1E1",
        "button_fg": "#000000",
        "accent_button_bg": "#0078D7",  # Vibrant blue for important buttons
        "accent_button_fg": "#FFFFFF",
        "entry_bg": "#FFFFFF",
        "entry_fg": "#000000",
        "highlight": "#0078D7",
        "border": "#CCCCCC",
        "title_fg": "#0078D7",  # Blue titles
        "subtitle_fg": "#666666",  # Gray subtitles
    },
    "Simple Dark": {
        "bg": "#1E1E1E",
        "fg": "#E0E0E0",
        "select_bg": "#0E639C",
        "select_fg": "#FFFFFF",
        "button_bg": "#2D2D30",
        "button_fg": "#E0E0E0",
        "accent_button_bg": "#007ACC",  # Vibrant blue
        "accent_button_fg": "#FFFFFF",
        "entry_bg": "#3E3E42",
        "entry_fg": "#E0E0E0",
        "highlight": "#007ACC",
        "border": "#3E3E42",
        "title_fg": "#E0E0E0",
        "subtitle_fg": "#A0A0A0",
    },
    "Catppuccin": {
        "bg": "#1E1E2E",
        "fg": "#CDD6F4",
        "select_bg": "#89B4FA",
        "select_fg": "#1E1E2E",
        "button_bg": "#89B4FA",  # Sky blue buttons
        "button_fg": "#1E1E2E",
        "accent_button_bg": "#F5C2E7",  # Pink for important buttons
        "accent_button_fg": "#1E1E2E",
        "entry_bg": "#313244",
        "entry_fg": "#CDD6F4",
        "highlight": "#F5C2E7",
        "border": "#45475A",
        "title_fg": "#F5C2E7",  # Pink titles
        "subtitle_fg": "#89B4FA",  # Blue subtitles
    },
    "Nord": {
        "bg": "#2E3440",
        "fg": "#ECEFF4",
        "select_bg": "#88C0D0",
        "select_fg": "#2E3440",
        "button_bg": "#88C0D0",  # Frost blue buttons
        "button_fg": "#2E3440",
        "accent_button_bg": "#81A1C1",  # Aurora green for important
        "accent_button_fg": "#2E3440",
        "entry_bg": "#3B4252",
        "entry_fg": "#ECEFF4",
        "highlight": "#81A1C1",
        "border": "#4C566A",
        "title_fg": "#88C0D0",  # Frost blue titles
        "subtitle_fg": "#81A1C1",  # Aurora subtitles
    },
    "Rose Pine": {
        "bg": "#191724",
        "fg": "#E0DEF4",
        "select_bg": "#9CCFD8",
        "select_fg": "#191724",
        "button_bg": "#9CCFD8",  # Pine teal buttons
        "button_fg": "#191724",
        "accent_button_bg": "#F6C177",  # Gold for important
        "accent_button_fg": "#191724",
        "entry_bg": "#26233A",
        "entry_fg": "#E0DEF4",
        "highlight": "#F6C177",
        "border": "#403D52",
        "title_fg": "#F6C177",  # Gold titles
        "subtitle_fg": "#9CCFD8",  # Teal subtitles
    },
    "Dracula": {
        "bg": "#282A36",
        "fg": "#F8F8F2",
        "select_bg": "#BD93F9",
        "select_fg": "#282A36",
        "button_bg": "#BD93F9",  # Purple buttons
        "button_fg": "#282A36",
        "accent_button_bg": "#FF79C6",  # Pink for important
        "accent_button_fg": "#282A36",
        "entry_bg": "#44475A",
        "entry_fg": "#F8F8F2",
        "highlight": "#FF79C6",
        "border": "#6272A4",
        "title_fg": "#FF79C6",  # Pink titles
        "subtitle_fg": "#BD93F9",  # Purple subtitles
    },
    "Solarized": {
        "bg": "#002B36",
        "fg": "#839496",
        "select_bg": "#268BD2",
        "select_fg": "#FDF6E3",
        "button_bg": "#268BD2",  # Blue buttons
        "button_fg": "#FDF6E3",
        "accent_button_bg": "#2AA198",  # Cyan for important
        "accent_button_fg": "#FDF6E3",
        "entry_bg": "#073642",
        "entry_fg": "#93A1A1",
        "highlight": "#2AA198",
        "border": "#586E75",
        "title_fg": "#268BD2",  # Blue titles
        "subtitle_fg": "#2AA198",  # Cyan subtitles
    },
}


# ── Display / scaling constants ───────────────────────────────────────────────
# Supported UI scale percentages
SCALE_OPTIONS = [25, 50, 75, 100, 125, 150, 175, 200]

# JSON file that persists the chosen scale between sessions
_DISPLAY_SETTINGS_FILE = "player_sorter_display_settings.json"

# Name of the dedicated folder for saved tournament files
_TOURNAMENTS_DIR_NAME = "Tournaments"


def _tournaments_candidates() -> list[pathlib.Path]:
    """Return the ordered list of candidate paths for the Tournaments directory.
    No directories are created or modified; callers decide what to do with them.

    Fallback chain:
      1. <user's Documents folder>/Tournaments
      2. <user's home directory>/Tournaments
      3. <app's current working directory>/Tournaments
    """
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []
    docs = home / "Documents"
    if docs.is_dir():
        candidates.append(docs / _TOURNAMENTS_DIR_NAME)
    candidates.append(home / _TOURNAMENTS_DIR_NAME)
    candidates.append(pathlib.Path.cwd() / _TOURNAMENTS_DIR_NAME)
    return candidates


def _get_tournaments_dir() -> pathlib.Path:
    """Return the Tournaments save directory, creating it on demand.

    Selection logic:
      1. If any candidate already exists and is writable, use the first such
         directory.  This keeps the chosen location stable across launches and
         ensures _get_tournaments_dir() always agrees with
         _find_existing_tournaments_dir().
      2. If no candidate exists yet, create (and write-probe) the first one
         in the fallback chain that the OS will allow.

    Raises RuntimeError (with a user-readable message) if every candidate
    fails — callers are expected to catch this and show it via messagebox.
    """
    candidates = _tournaments_candidates()

    # Pass 1 — prefer an already-existing directory.
    for candidate in candidates:
        if candidate.is_dir():
            try:
                probe = candidate / ".write_probe"
                probe.touch()
                probe.unlink()
                return candidate
            except OSError:
                continue  # Exists but not writable; try the next one.

    # Pass 2 — nothing exists yet; create the first writable location.
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.touch()
            probe.unlink()
            return candidate
        except OSError:
            continue

    attempted = "\n".join(f"  • {p}" for p in candidates)
    raise RuntimeError(
        "Could not create a writable Tournaments folder in any of the "
        "following locations:\n\n"
        f"{attempted}\n\n"
        "Check your filesystem permissions and try again."
    )


def _find_existing_tournaments_dir() -> pathlib.Path | None:
    """Return the first candidate Tournaments directory that already exists
    AND is writable, without creating anything new.  Returns None if no
    suitable directory is found.  Used by the load screen so it never creates
    a folder just by being opened.

    The writability check mirrors _get_tournaments_dir() Pass 1 exactly,
    guaranteeing that both functions always agree on which directory is
    authoritative — including the edge case where an existing Tournaments
    directory is read-only (in which case both functions skip it and look
    at the next candidate).
    """
    for candidate in _tournaments_candidates():
        if candidate.is_dir():
            try:
                probe = candidate / ".write_probe"
                probe.touch()
                probe.unlink()
                return candidate
            except OSError:
                continue  # Exists but not writable — skip, same as _get_tournaments_dir.
    return None


def _unique_discarded_path(dest_dir: pathlib.Path, original_name: str) -> pathlib.Path:
    """Return a path of the form <dest_dir>/discarded_<original_name> that does
    not yet exist, appending a numeric suffix (_1, _2, …) if necessary to
    avoid silently overwriting a previously discarded file.
    """
    candidate = dest_dir / f"discarded_{original_name}"
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        candidate = dest_dir / f"discarded_{counter}_{original_name}"
        if not candidate.exists():
            return candidate
        counter += 1


def _migrate_cwd_tournaments() -> None:
    """Move any tournament JSON files sitting in the app's CWD into the
    dedicated Tournaments directory.

    Conflict resolution when a file with the same name already exists in the
    destination:
      - Identical content  → remove the CWD copy (it's a true duplicate).
      - Different content  → move the CWD copy to the Tournaments directory
                             under a unique name of the form
                             discarded_<original_name> (or
                             discarded_<n>_<original_name> if that name is
                             already taken), so nothing is lost but the load
                             screen won't pick it up automatically.

    Only called after confirming CWD files exist, so the Tournaments directory
    is never created needlessly on startup.
    """
    cwd = pathlib.Path.cwd()
    old_files = list(cwd.glob("tournament_*_*.json"))
    if not old_files:
        return  # Nothing to migrate — Tournaments dir is never touched.

    try:
        dest_dir = _get_tournaments_dir()
    except RuntimeError as exc:
        messagebox.showerror(
            "Migration Error",
            "Found tournament files in the app folder that need to be "
            "moved, but no writable Tournaments folder could be created:\n\n"
            f"{exc}\n\n"
            "The files have been left in place.",
        )
        return

    for src in old_files:
        try:
            dest = dest_dir / src.name
            if dest.exists():
                if filecmp.cmp(str(src), str(dest), shallow=False):
                    # True duplicate — just remove the CWD copy.
                    src.unlink()
                else:
                    # Different content — preserve it under a renamed path so
                    # the user can inspect it, but keep it out of normal loading.
                    renamed = _unique_discarded_path(dest_dir, src.name)
                    shutil.move(str(src), str(renamed))
            else:
                shutil.move(str(src), str(dest))
        except OSError:
            pass  # Skip any individual file that cannot be moved.
# ──────────────────────────────────────────────────────────────────────────────


def _normalize_name_casing(name: str) -> str:
    """Convert a first/last name to standard title-case formatting,
    regardless of how the user typed it ("mcdonald", "MCDONALD",
    "mcDonald" all become "McDonald"). Collapses repeated internal
    whitespace too. Only intended for first_name/last_name - nicknames
    are left exactly as typed, since stylized capitalization is often
    intentional there.
    """
    name = " ".join(name.split())
    if not name:
        return name
    name = name.title()
    # str.title() lowercases the letter right after "Mc", e.g.
    # "mcdonald" -> "Mcdonald". Fix that common case specifically,
    # since guessing at other prefixes (e.g. "Mac") risks getting
    # unrelated names (Macy, Macon) wrong.
    name = re.sub(r"\bMc([a-z])", lambda m: "Mc" + m.group(1).upper(), name)
    return name


def _player_display_name_key(player: "Player") -> str:
    """Case-insensitive key for comparing two players' display names."""
    return player.name.strip().casefold()


class Player:
    """Represents a player with their stats"""

    def __init__(
        self,
        first_name: str = "",
        last_name: str = "",
        nickname: str = "",
        rating: int = 0,
        wins: int = 0,
        losses: int = 0,
        draws: int = 0,
        byes: int = 0,
        half_byes: int = 0,
    ):
        self.first_name = first_name
        self.last_name = last_name
        self.nickname = nickname
        self.rating = rating
        self.wins = wins
        self.losses = losses
        self.draws = draws
        self.byes = byes
        self.half_byes = half_byes
        self.eliminated = False
        self.withdrawn = False  # Track if player has withdrawn
        self.withdrawal_round = None  # Round when player withdrew
        self.opponents = []  # Track who they've played against
        # Per-opponent result for each entry in `opponents`, kept in the
        # same order/length: "win", "loss", or "draw". Needed for
        # Sonneborn-Berger and Direct Encounter, which (unlike Buchholz)
        # depend on the OUTCOME of each game, not just who was played.
        # Always the same length as `opponents`; old save files won't
        # have this, so it defaults to [] and tiebreaks that need it
        # degrade gracefully (treat unknown results as contributing 0)
        # rather than raising.
        self.results_vs_opponents = []
        # Colour played in each REAL game (never for byes/half-byes, which
        # FIDE treats as colourless), parallel to `opponents` /
        # `results_vs_opponents`: "white" or "black" per entry. Used to
        # compute colour balance/streak for Chess Colour Balancing. Old
        # saves won't have this - defaults to [] and every consumer below
        # degrades gracefully (treats a player with no colour history as
        # having no preference yet) rather than crashing.
        self.colors = []
        self.requested_half_bye = False  # For current round

        # ===== FIDE / TRF16 fields (all optional, chess-only) =====
        # None of these are required to use the app - they only matter if
        # the director wants a TRF16 export usable for actual FIDE rating
        # submission (as opposed to just pairing/tiebreak interop, which
        # works fine without them). Old saves won't have any of these;
        # every consumer treats a missing/None value as "unknown, leave
        # blank in the export" rather than raising.
        self.sex = None  # "m" or "w" (FIDE's own two-letter convention)
        self.title = None  # One of: GM, IM, WGM, FM, WIM, CM, WFM, WCM
        self.fide_federation = None  # 3-letter FIDE federation code
        self.fide_id = None  # FIDE ID number, as a string
        self.birth_date = None  # "YYYY/MM/DD" (partial dates not supported by TRF16)
        # Snapshot of `rating` at the moment THIS tournament started, used
        # for TRF starting-rank assignment (by descending rating "at
        # start") and for the TRF FIDE-Rating column - both of which
        # should reflect the rating a player entered the event with, not
        # a rating this app's automatic ELO mode may have since adjusted
        # mid-event. None until a tournament actually starts.
        self.initial_rating = None

    @property
    def name(self):
        """Get display name based on what's available"""
        if self.nickname and (self.first_name or self.last_name):
            # Has nickname and name: show both
            full_name = f"{self.first_name} {self.last_name}".strip()
            if full_name:
                return f"{full_name} ({self.nickname})"
            else:
                return self.nickname
        elif self.nickname:
            # Only nickname
            return self.nickname
        else:
            # Only real name
            return f"{self.first_name} {self.last_name}".strip()

    @property
    def total_games(self):
        return self.wins + self.losses + self.draws + self.byes + self.half_byes

    @property
    def points(self):
        """Calculate points: win=1, draw=0.5, loss=0, bye=1, half-bye=0.5"""
        return (
            self.wins * 1.0 + self.draws * 0.5 + self.byes * 1.0 + self.half_byes * 0.5
        )

    @property
    def win_rate(self):
        """Calculate win rate as percentage"""
        if self.total_games == 0:
            return 0.0
        return (self.points / self.total_games) * 100

    @property
    def score_rate(self):
        """Calculate score as points per game (for withdrawn players fairness)"""
        if self.games_played == 0:
            return 0.0
        return self.points / self.games_played

    @property
    def games_played(self):
        """Games actually played (excluding byes and half-byes)"""
        return self.wins + self.losses + self.draws

    @property
    def white_games(self):
        """Number of REAL games played with White (byes are colourless)"""
        return self.colors.count("white")

    @property
    def black_games(self):
        """Number of REAL games played with Black (byes are colourless)"""
        return self.colors.count("black")

    @property
    def color_difference(self):
        """White games minus Black games (FIDE 'colour difference')"""
        return self.white_games - self.black_games


class PlayerSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Player Sorter")

        # Load theme preference
        self.current_theme = self.load_theme_preference()

        # Load scale preference early so the very first window render already
        # uses the correct scale.  We capture the system's default tk scaling
        # value here (before we change anything) so we could restore it later
        # if ever needed, but we immediately override it with the saved pct.
        self._default_tk_scaling = float(self.root.tk.call("tk", "scaling"))
        self._current_scale_pct = self._load_scale_preference()
        self._apply_scale(self._current_scale_pct)

        # Maximize window - cross-platform approach
        try:
            # Try Windows/Linux method first
            self.root.state("zoomed")
        except tk.TclError:
            try:
                # Try macOS method
                self.root.attributes("-zoomed", True)
            except Exception:
                # Fallback: maximize manually by setting geometry to screen size
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        # Allow window resizing
        self.root.resizable(True, True)

        # Fullscreen toggle: F11 and Alt+Enter
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Alt-Return>", self._toggle_fullscreen)

        self.game_type = None
        self.sort_mode = None
        self.players: List[Player] = []
        self.current_round = 0
        self.teams: List[List[Player]] = []
        self.in_game = False  # Track if we're in an active game
        self.editing_player_index = None  # Index of player being edited, or None
        self.half_bye_enabled = False  # Track if half-byes are allowed
        self.withdrawal_enabled = False  # Track if withdrawals are allowed
        self.max_rounds = None  # Maximum rounds (None = unlimited)
        self.tournament_history = []
        # List of round dicts, populated during tournament play
        self.tournament_start_time = None
        self.rating_mode = None
        """'automatic', 'manual', or 'unranked' for chess;
        'ranked' or 'unranked' for e-sports"""
        self.min_elo = 1000  # Minimum ELO for tournament (chess only)
        self.max_elo = None  # Maximum ELO for tournament (chess only, None = unlimited)

        # Apply theme before showing UI
        self.apply_theme(self.current_theme)

        # Migrate any tournament files left in the app's CWD to the dedicated
        # Tournaments directory (one-time, silent, happens before first render).
        _migrate_cwd_tournaments()

        # Non-blocking background check for a newer stable GitHub release.
        self._check_for_updates()

        self.show_theme_selection()

    def _toggle_fullscreen(self, event=None):
        """Toggle true fullscreen mode (F11 / Alt+Enter)."""
        is_fullscreen = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not is_fullscreen)

    def load_theme_preference(self):
        """Load saved theme preference"""
        try:
            if os.path.exists("player_sorter_theme.json"):
                with open("player_sorter_theme.json", "r") as f:
                    data = json.load(f)
                    # Handle old "Simple White" name
                    theme = data.get("theme", "Simple Light")
                    if theme == "Simple White":
                        theme = "Simple Light"
                    return theme
        except (OSError, json.JSONDecodeError):
            pass
        return "Simple Light"  # Default theme

    def save_theme_preference(self, theme_name):
        """Save theme preference to file"""
        try:
            with open("player_sorter_theme.json", "w") as f:
                json.dump({"theme": theme_name}, f)
        except (OSError, TypeError):
            pass

    # ── Scale / display-settings helpers ──────────────────────────────────────

    def _load_scale_preference(self) -> int:
        """Return the saved scale percentage, or 100 if none / corrupt."""
        try:
            if os.path.exists(_DISPLAY_SETTINGS_FILE):
                with open(_DISPLAY_SETTINGS_FILE, "r") as fh:
                    data = json.load(fh)
                scale = int(data.get("scale_pct", 100))
                if scale in SCALE_OPTIONS:
                    return scale
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass
        return 100  # Safe default

    def _save_scale_preference(self, scale_pct: int) -> None:
        """Persist the chosen scale percentage to disk."""
        try:
            with open(_DISPLAY_SETTINGS_FILE, "w") as fh:
                json.dump({"scale_pct": scale_pct}, fh)
        except (OSError, TypeError):
            pass  # Non-fatal — just skip saving

    # ── Update-check helpers ────────────────────────────────────────────────

    def _load_dismissed_update_version(self):
        """Return the version string the user last dismissed via "Don't show
        this again", or None if they've never dismissed one (or the pref
        file is missing/corrupt). Storing the specific version - rather than
        a permanent on/off switch - means dismissing v2.5.0 only silences
        v2.5.0; a future v2.6.0 will still trigger the notification.
        """
        try:
            if os.path.exists(_UPDATE_SETTINGS_FILE):
                with open(_UPDATE_SETTINGS_FILE, "r") as fh:
                    data = json.load(fh)
                dismissed = data.get("dismissed_version")
                return dismissed if isinstance(dismissed, str) and dismissed else None
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        return None

    def _save_dismissed_update_version(self, version: str) -> None:
        """Persist the specific version the user chose to dismiss."""
        try:
            with open(_UPDATE_SETTINGS_FILE, "w") as fh:
                json.dump({"dismissed_version": version}, fh)
        except (OSError, TypeError):
            pass  # Non-fatal - just skip saving.

    def _check_for_updates(self) -> None:
        """Kick off a background check against the GitHub API for a newer
        stable release. Entirely non-blocking: runs on a daemon thread, and
        any network failure (no internet, DNS failure, GitHub rate limit,
        timeout, malformed response, etc.) is swallowed silently - this check
        should never interrupt startup or show an error to the user.

        Always runs (even if a version was previously dismissed) since the
        only way to know whether an even-newer version has since shipped is
        to actually check; the dismissal is only compared against the result
        once it's back, inside _fetch_latest_release_and_maybe_notify().
        """
        threading.Thread(
            target=self._fetch_latest_release_and_maybe_notify, daemon=True
        ).start()

    def _fetch_latest_release_and_maybe_notify(self) -> None:
        """Runs on a background thread. Fetches the latest release tag from
        GitHub and, if it's newer than __version__ (or __version__ is
        missing/unparseable) AND isn't the specific version the user already
        dismissed, schedules the notification dialog back onto the main
        thread via root.after() - tkinter widgets must only be touched from
        the main thread.
        """
        try:
            request = urllib.request.Request(
                _GITHUB_LATEST_RELEASE_API,
                headers={
                    # GitHub's API rejects requests with no User-Agent header.
                    "User-Agent": "PlayerSorter-UpdateCheck",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            latest_tag = data.get("tag_name", "")
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ValueError,
            OSError,
        ):
            return  # No internet, GitHub unreachable/rate-limited, bad JSON, etc.

        current_version = globals().get("__version__", "")
        if not _is_version_newer(latest_tag, current_version):
            return  # Already up to date (or the response was unparseable).

        dismissed = self._load_dismissed_update_version()
        # Compare parsed version tuples, not raw strings, so "v2.5.0" (from
        # GitHub) correctly matches a dismissal saved as "2.5.0".
        if dismissed is not None and _parse_version(latest_tag) == _parse_version(dismissed):
            return  # User already dismissed exactly this version.

        latest_display = latest_tag.strip().lstrip("vV") or latest_tag
        try:
            # The user may have closed the app while this background check
            # was still waiting on the network; in that case self.root is
            # already destroyed and scheduling a callback on it raises
            # RuntimeError/TclError. That's expected in a race like this, not
            # a real error, so it's swallowed rather than left to print an
            # unhandled-exception traceback in the console on every close.
            self.root.after(0, lambda: self._show_update_notification(latest_display))
        except (RuntimeError, tk.TclError):
            pass

    def _show_update_notification(self, latest_version: str) -> None:
        """Show a popup dialog telling the user a newer stable release is
        available, with the current/latest version numbers, a copyable link
        to the GitHub releases page, and a "Don't show this again" checkbox
        (which silences only this specific version, not future ones).
        """
        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])

        dialog = tk.Toplevel(self.root)
        dialog.title("Update Available")
        dialog.configure(bg=theme["bg"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        container = tk.Frame(dialog, bg=theme["bg"], padx=24, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="A new version of Player Sorter is available!",
            font=("Segoe UI", 13, "bold"),
            bg=theme["bg"],
            fg=theme["title_fg"],
            wraplength=380,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        current_version = globals().get("__version__", "") or "unknown"
        tk.Label(
            container,
            text=f"Current version: {current_version}\nLatest version:  {latest_version}",
            font=("Segoe UI", 10),
            bg=theme["bg"],
            fg=theme["fg"],
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 10))

        tk.Label(
            container,
            text="Release link (select and copy):",
            font=("Segoe UI", 9),
            bg=theme["bg"],
            fg=theme["subtitle_fg"],
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        link_entry = tk.Entry(
            container,
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            width=48,
        )
        link_entry.insert(0, _GITHUB_LATEST_RELEASE_URL)
        link_entry.config(state="readonly")
        link_entry.pack(anchor=tk.W, pady=(2, 14), fill=tk.X)
        # Pre-select the link text so the user can copy it with one Ctrl+C.
        link_entry.selection_range(0, tk.END)

        dont_show_again_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            container,
            text="Don't show this again",
            variable=dont_show_again_var,
        ).pack(anchor=tk.W, pady=(0, 14))

        def on_close():
            if dont_show_again_var.get():
                self._save_dismissed_update_version(latest_version)
            dialog.destroy()

        ttk.Button(container, text="OK", command=on_close).pack(anchor=tk.E)
        dialog.protocol("WM_DELETE_WINDOW", on_close)

        # Center the dialog over the main window.
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _get_base_scaling(self) -> float:
        """Get the baseline scaling factor for this platform."""
        # Use the saved original system scaling, not the current (possibly modified) value
        return self._default_tk_scaling

    def _apply_scale(self, scale_pct: int) -> None:
        """Apply the requested UI scale percentage."""
        self._current_scale_pct = scale_pct
        self._scale_multiplier = scale_pct / 100.0

        # Apply to tk.scaling()
        base_scaling = self._get_base_scaling()
        new_scaling = base_scaling * self._scale_multiplier
        self.root.tk.call("tk", "scaling", new_scaling)
    
    def _sf(self, base_size: int, weight: str = "") -> tuple:
        """Scale Font helper: returns (family, scaled_size, weight) tuple."""
        scaled = int(base_size * getattr(self, '_scale_multiplier', 1.0))
        weight_value = weight if weight else "normal"
        return ("Arial", scaled, weight_value)
    
    def _sp(self, base_value: int) -> str:
        """Scale Padding helper: returns scaled padding as string.
        
        Usage: padding=self._sp(20)
        """
        scaled = int(base_value * getattr(self, '_scale_multiplier', 1.0))
        return str(scaled)

    def show_display_settings(self) -> None:
        """Open a small modal dialog for changing the UI scale."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Display Settings")
        dialog.transient(self.root)   # Keep it on top of the main window
        dialog.grab_set()             # Make it modal
        dialog.resizable(False, False)

        # Apply the current colour scheme so the dialog matches the rest of
        # the app instead of looking like a plain grey system dialog.
        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        dialog.configure(bg=theme["bg"])

        frame = ttk.Frame(dialog, padding=self._sp(40))
        frame.pack(fill=tk.BOTH, expand=True)

        # ── Title ──────────────────────────────────────────────────────────
        ttk.Label(
            frame, text="Display Settings", font=self._sf(16, "bold")
        ).pack(pady=(0, 20))

        # ── Scale row ──────────────────────────────────────────────────────
        scale_row = ttk.Frame(frame)
        scale_row.pack(fill=tk.X, pady=10)

        ttk.Label(scale_row, text="UI Scale:", font=self._sf(12)).pack(
            side=tk.LEFT, padx=(0, 15)
        )

        # Pre-select the currently active percentage in the drop-down.
        scale_var = tk.StringVar(value=f"{self._current_scale_pct}%")
        scale_combo = ttk.Combobox(
            scale_row,
            textvariable=scale_var,
            values=[f"{s}%" for s in SCALE_OPTIONS],
            state="readonly",
            width=10,
            font=self._sf(12),
        )
        scale_combo.pack(side=tk.LEFT)

        # ── Explanatory note ───────────────────────────────────────────────
        ttk.Label(
            frame,
            text=(
                "The change takes effect immediately."
            ),
            font=self._sf(10, "italic"),
            justify=tk.CENTER,
        ).pack(pady=(15, 20))

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = ttk.Frame(frame)
        btn_row.pack(pady=(0, 10))

        def _on_apply() -> None:
            val_str = scale_var.get().replace("%", "").strip()
            try:
                chosen_pct = int(val_str)
            except ValueError:
                return
            if chosen_pct not in SCALE_OPTIONS:
                return  # Shouldn't happen via the combo, but be defensive

            self._apply_scale(chosen_pct)
            self._save_scale_preference(chosen_pct)
            # Reapply the current theme so ttk.Style fonts update with new scale
            self.apply_theme(self.current_theme)
            dialog.destroy()
            # Refresh the theme-selection screen so the user immediately sees
            # the new scale on all widgets (clear_window + full rebuild).
            self.show_theme_selection()

        ttk.Button(btn_row, text="Apply", command=_on_apply, width=12).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(btn_row, text="Close", command=dialog.destroy, width=12).pack(
            side=tk.LEFT, padx=8
        )

        # ── Position dialog near top-right of main window ──────────────────
        dialog.update_idletasks()
        d_w = dialog.winfo_reqwidth()
        d_h = dialog.winfo_reqheight()
        r_x = self.root.winfo_x()
        r_y = self.root.winfo_y()
        r_w = self.root.winfo_width()

        # Screen dimensions (approximate)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Calculate position, with bounds checking
        x = r_x + r_w - d_w - 30
        y = r_y + 80

        # Clamp to screen
        x = max(0, min(x, screen_w - d_w - 10))
        y = max(0, min(y, screen_h - d_h - 10))

        dialog.geometry(f"+{x}+{y}")

    # ── End scale / display-settings helpers ──────────────────────────────────

    def apply_theme(self, theme_name):
        """Apply the selected theme to the entire application"""
        if theme_name not in THEMES:
            theme_name = "Simple Light"

        theme = THEMES[theme_name]
        self.current_theme = theme_name

        # Configure root window background
        self.root.configure(bg=theme["bg"])

        # Configure ttk styles
        style = ttk.Style()

        # Always use clam as the base ttk theme.
        # On Windows the default vista/winnative theme intercepts colour
        # properties and ignores custom styles on first paint, making Simple
        # Light look broken until a round-trip through another theme forces
        # clam to be active. Unconditionally setting clam here fixes this.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Configure all widget styles with proper backgrounds to avoid white spaces
        style.configure("TFrame", background=theme["bg"])
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        style.configure(
            "TLabelframe",
            background=theme["bg"],
            foreground=theme["fg"],
            bordercolor=theme["border"],
        )
        style.configure(
            "TLabelframe.Label", background=theme["bg"], foreground=theme["fg"]
        )

        # Canvas widgets (fix white space in scrollable areas)
        style.configure("TCanvas", background=theme["bg"])

        # Buttons with vibrant colors
        style.configure(
            "TButton",
            font=self._sf(12),
            padding=10,
            background=theme["button_bg"],
            foreground=theme["button_fg"],
            bordercolor=theme["border"],
        )
        style.map(
            "TButton",
            background=[
                ("active", theme["select_bg"]),
                ("pressed", theme["highlight"]),
            ],
            foreground=[("active", theme["select_fg"])],
        )

        # Large button style with accent colors
        style.configure(
            "Large.TButton",
            font=self._sf(14, "bold"),
            padding=15,
            background=theme["accent_button_bg"],
            foreground=theme["accent_button_fg"],
        )
        style.map(
            "Large.TButton",
            background=[
                ("active", theme["highlight"]),
                ("pressed", theme["select_bg"]),
            ],
            foreground=[("active", theme["accent_button_fg"])],
        )

        # Entry fields
        style.configure(
            "TEntry",
            fieldbackground=theme["entry_bg"],
            foreground=theme["entry_fg"],
            bordercolor=theme["border"],
        )

        # Radiobuttons with proper backgrounds
        style.configure("TRadiobutton", background=theme["bg"], foreground=theme["fg"])
        style.configure(
            "Large.TRadiobutton",
            font=self._sf(11),
            padding=5,
            background=theme["bg"],
            foreground=theme["fg"],
        )
        style.map(
            "TRadiobutton",
            background=[("active", theme["bg"])],
            foreground=[("active", theme["highlight"])],
        )

        # Checkbuttons
        style.configure("TCheckbutton", background=theme["bg"], foreground=theme["fg"])

        # Treeview (tables) with colored headings for themed look
        style.configure(
            "Treeview",
            background=theme["entry_bg"],
            foreground=theme["entry_fg"],
            fieldbackground=theme["entry_bg"],
            bordercolor=theme["border"],
        )

        # Use accent colors for table headings in colorful themes
        if theme_name in ["Catppuccin", "Nord", "Rose Pine", "Dracula", "Solarized"]:
            style.configure(
                "Treeview.Heading",
                background=theme["button_bg"],
                foreground=theme["button_fg"],
                bordercolor=theme["border"],
                font=self._sf(11, "bold"),
            )
        else:
            # Simple themes keep subdued headings
            style.configure(
                "Treeview.Heading",
                background=theme["button_bg"],
                foreground=theme.get("button_fg", theme["fg"]),
                bordercolor=theme["border"],
                font=self._sf(11, "bold"),
            )

        style.map(
            "Treeview",
            background=[("selected", theme["select_bg"])],
            foreground=[("selected", theme["select_fg"])],
        )
        style.configure("Treeview", font=self._sf(10), rowheight=25)

        # Scrollbars
        style.configure(
            "Vertical.TScrollbar",
            background=theme["button_bg"],
            troughcolor=theme["bg"],
            bordercolor=theme["border"],
            arrowcolor=theme.get("button_fg", theme["fg"]),
        )

    def show_theme_selection(self):
        """Show theme selection screen at startup"""
        self.clear_window()

        # ── Top bar: houses the "Display Settings" button flush to the right.
        # It is packed first (before the main content frame) so the geometry
        # manager places it at the very top of the window regardless of how
        # the content frame is sized below it.
        top_bar = ttk.Frame(self.root)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(10, 0))

        ttk.Button(
            top_bar,
            text="⚙ Display Settings",
            command=self.show_display_settings,
        ).pack(side=tk.RIGHT)

        # ── Main content (theme selection) ─────────────────────────────────
        frame = ttk.Frame(self.root, padding=self._sp(60))
        frame.pack(expand=True, fill=tk.BOTH)

        # Title
        title = ttk.Label(frame, text="Player Sorter", font=self._sf(32, "bold"))
        title.pack(pady=30)

        subtitle = ttk.Label(frame, text="Select Theme", font=self._sf(18))
        subtitle.pack(pady=20)

        # Theme buttons
        theme_frame = ttk.Frame(frame)
        theme_frame.pack(pady=20)

        for i, theme_name in enumerate(THEMES.keys()):
            btn = ttk.Button(
                theme_frame,
                text=theme_name,
                width=25,
                command=lambda t=theme_name: self.select_theme(t),
            )
            btn.pack(pady=8)

            # Highlight current theme
            if theme_name == self.current_theme:
                ttk.Label(
                    theme_frame, text="✓ Current", font=self._sf(9, "italic")
                ).pack()

        # Continue button
        ttk.Button(
            frame,
            text="Continue to App",
            width=25,
            style="Large.TButton",
            command=self.show_initial_selection,
        ).pack(pady=30)

    def select_theme(self, theme_name):
        """Select and apply a theme"""
        self.apply_theme(theme_name)
        self.save_theme_preference(theme_name)
        # Refresh the theme selection screen to show new theme
        self.show_theme_selection()

    def show_initial_selection(self):
        """Show initial game type and mode selection"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding=self._sp(60))
        frame.pack(expand=True, fill=tk.BOTH)

        # Title with larger font
        title = ttk.Label(frame, text="Player Sorter", font=self._sf(32, "bold"))
        title.pack(pady=50)

        # Game Type Selection
        ttk.Label(frame, text="Select Game Type:", font=self._sf(16)).pack(pady=20)

        game_frame = ttk.Frame(frame)
        game_frame.pack(pady=20)

        ttk.Button(
            game_frame,
            text="Chess (ELO)",
            width=30,
            style="Large.TButton",
            command=lambda: self.select_game_type("chess"),
        ).pack(side=tk.LEFT, padx=15)
        ttk.Button(
            game_frame,
            text="E-Sports (Trophies)",
            width=30,
            style="Large.TButton",
            command=lambda: self.select_game_type("esports"),
        ).pack(side=tk.LEFT, padx=15)

        # Load tournament button
        ttk.Button(
            frame,
            text="📂 Load a Tournament",
            width=30,
            command=self.show_load_tournament_screen,
        ).pack(pady=10)

        # Theme switcher button at bottom
        ttk.Button(
            frame, text="🎨 Change Theme", width=20, command=self.show_theme_selection
        ).pack(pady=20)

    def show_load_tournament_screen(self):
        """Scan the Tournaments directory for saved tournament files and let the
        user pick one to view (finished) or resume (unfinished)."""

        # Scan for an already-existing Tournaments directory without creating
        # one — opening the load screen should never create a folder.
        t_dir = _find_existing_tournaments_dir()
        files = [] if t_dir is None else [
            str(p) for p in sorted(t_dir.glob("tournament_*_*.json"))
        ]

        if not files:
            messagebox.showinfo(
                "No Tournaments Found",
                "No saved tournament files were found in the Tournaments folder.",
            )
            return

        # Parse each file to get metadata without loading fully
        file_entries = []
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                file_entries.append(
                    {
                        "filepath": filepath,
                        "finished": meta.get("finished", False),
                        "system": meta.get("tournament_system", "unknown"),
                        "start_time": meta.get("tournament_start_time", "unknown"),
                        "current_round": meta.get("current_round", 0),
                        "player_count": len(meta.get("players", [])),
                    }
                )
            except Exception:
                continue  # Skip unreadable files silently

        if not file_entries:
            messagebox.showerror(
                "Error", "Found tournament files but could not read any."
            )
            return

        # Sort: unfinished first, then finished — both groups newest to oldest
        unfinished = sorted(
            [e for e in file_entries if not e["finished"]],
            key=lambda e: e["start_time"],
            reverse=True,
        )
        finished = sorted(
            [e for e in file_entries if e["finished"]],
            key=lambda e: e["start_time"],
            reverse=True,
        )
        file_entries = unfinished + finished

        # If only one file, load it directly. clear_window() is deferred to
        # _open_tournament_entry's success path, so a failed load (corrupt
        # file, permission error, etc.) leaves this list screen on-screen
        # behind the error messagebox instead of stranding the user on a
        # blank window with no way back.
        if len(file_entries) == 1:
            self._open_tournament_entry(
                file_entries[0], return_to=self.show_initial_selection
            )
            return

        # Otherwise display list for user to choose from
        self.clear_window()
        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Load a Tournament", font=("Arial", 24, "bold")).pack(
            pady=20
        )
        ttk.Label(
            frame,
            text="Select a tournament to view or resume. "
            "Unfinished tournaments are listed first.",
            font=("Arial", 12),
        ).pack(pady=5)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        cols = ["status", "date_time", "system", "rounds_played", "players"]
        tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=15)
        tree.heading("status", text="Status")
        tree.heading("date_time", text="Date & Time")
        tree.heading("system", text="System")
        tree.heading("rounds_played", text="Rounds Played")
        tree.heading("players", text="Players")
        tree.column("status", width=110)
        tree.column("date_time", width=180)
        tree.column("system", width=120)
        tree.column("rounds_played", width=120)
        tree.column("players", width=70)

        system_display = {
            "swiss": "Swiss",
            "round_robin": "Round-Robin",
            "knockout": "Knockout",
            "scheveningen": "Scheveningen",
        }

        for entry in file_entries:
            status = "⚠ UNFINISHED" if not entry["finished"] else "✓ Finished"
            dt = entry["start_time"].replace("_", " ")  # Nicer display
            sys_name = system_display.get(entry["system"], entry["system"].title())
            tree.insert(
                "",
                tk.END,
                iid=entry["filepath"],  # Use filepath as row ID for easy retrieval
                values=(
                    status,
                    dt,
                    sys_name,
                    entry["current_round"],
                    entry["player_count"],
                ),
            )

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)

        def on_load():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select a tournament.")
                return
            filepath = selected[0]  # We used filepath as iid
            entry = next(e for e in file_entries if e["filepath"] == filepath)
            self._open_tournament_entry(entry)

        def on_export():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning(
                    "No Selection", "Please select a tournament to export."
                )
                return
            filepath = selected[0]
            self._export_csv_from_filepath(filepath)

        def on_export_html():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning(
                    "No Selection", "Please select a tournament to export."
                )
                return
            filepath = selected[0]
            self._export_html_from_filepath(filepath)

        def on_export_trf():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning(
                    "No Selection", "Please select a tournament to export."
                )
                return
            filepath = selected[0]
            self._export_trf_from_filepath(filepath)

        def on_delete():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning(
                    "No Selection", "Please select a tournament to delete."
                )
                return
            filepath = selected[0]
            entry = next(e for e in file_entries if e["filepath"] == filepath)
            dt_display = entry["start_time"].replace("_", " ")
            status_word = "unfinished" if not entry["finished"] else "finished"
            confirmed = messagebox.askyesno(
                "Confirm Deletion",
                f"Permanently delete this {status_word} tournament?\n\n"
                f"  Date/Time: {dt_display}\n"
                f"  System:    {entry['system'].replace('_', '-').title()}\n\n"
                "This cannot be undone.",
            )
            if not confirmed:
                return
            try:
                os.remove(filepath)
            except OSError as exc:
                messagebox.showerror("Delete Failed", f"Could not delete file:\n{exc}")
                return
            # Remove from our in-memory list and the treeview, then refresh
            file_entries[:] = [e for e in file_entries if e["filepath"] != filepath]
            tree.delete(filepath)
            # If no entries remain, go back to the main screen
            if not file_entries:
                messagebox.showinfo("All Gone", "No saved tournaments remaining.")
                self.show_initial_selection()

        ttk.Button(btn_frame, text="Back", command=self.show_initial_selection).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="Delete Selected",
            command=on_delete,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="📄 Export as CSV",
            command=on_export,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="🌐 Export as HTML",
            command=on_export_html,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="♟ Export as TRF16",
            command=on_export_trf,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="Load Selected Tournament",
            style="Large.TButton",
            command=on_load,
        ).pack(side=tk.LEFT, padx=5)

    def _open_tournament_entry(self, entry: dict, return_to=None):
        """Load a tournament file and dispatch to viewer or resumption.

        clear_window() is called here, AFTER a successful load, rather than
        by the caller before this runs. That way a failed load (corrupt
        file, permission error, etc.) leaves whatever screen the user was
        on (e.g. the Load Tournament list) visible behind the error
        messagebox, instead of leaving a blank window with no way back.

        return_to: optional override for the viewer's "Back" target. Callers
            that bypass the Load Tournament list (e.g. the single-file
            auto-load shortcut in show_load_tournament_screen) must pass an
            explicit return_to here — defaulting to show_load_tournament_screen
            would send "Back" straight into another single-file auto-load,
            reopening this same viewer in an infinite loop with no way to
            reach the main menu. Defaults to show_load_tournament_screen,
            which is correct when the user actually picked this entry from
            a visible list.
        """
        success = self.load_tournament_from_file(entry["filepath"])
        if not success:
            return

        self.clear_window()
        if entry["finished"]:
            # View-only: go straight to round-by-round viewer
            self.show_round_by_round_viewer(
                self.tournament_history,
                return_to=return_to if return_to else self.show_load_tournament_screen,
            )
        else:
            # Resume: advance to the next round
            self._resume_unfinished_tournament()

    def _resume_unfinished_tournament(self):
        """Resume an unfinished tournament from where it was saved.
        The last fully-finished round is current_round; we advance to current_round + 1.
        """
        system = self.tournament_system
        next_round = self.current_round + 1
        self.current_round = next_round

        if system == "swiss":
            self.show_swiss_round()
        elif system == "round_robin":
            self.show_round_robin_round()
        elif system == "knockout":
            self.show_knockout_round()
        elif system == "scheveningen":
            # For scheveningen, schev_round counter drives the flow
            # It was saved at the end of the last completed schev_round
            # show_scheveningen_round() increments schev_round at the top,
            # so set it back by 1
            self.schev_round = getattr(self, "schev_round", 0)
            # schev_round is already the LAST completed round in the save file,
            # and show_scheveningen_round() does schev_round += 1 before doing anything,
            # so we do NOT decrement — just call it directly
            self.show_scheveningen_round()

    def select_game_type(self, game_type: str):
        """Handle game type selection"""
        self.game_type = game_type
        self.show_mode_selection()

    def show_mode_selection(self):
        """Show sorting mode selection"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True, fill=tk.BOTH)

        # Title
        game_name = "Chess" if self.game_type == "chess" else "E-Sports"
        title = ttk.Label(
            frame, text=f"{game_name} - Select Mode", font=("Arial", 24, "bold")
        )
        title.pack(pady=30)

        # Mode Selection
        ttk.Label(frame, text="Select Sorting Mode:", font=("Arial", 14)).pack(pady=20)

        if self.game_type == "chess":
            modes = [
                (
                    "Tournament",
                    "tournament",
                    "Swiss, Round-Robin, Knockout, Scheveningen",
                ),
                ("Dual", "dual", "Pair players based on rating"),
                ("Battle Royale", "battle_royale", "Sort by win rate"),
                ("Teams", "teams", "Create balanced teams"),
            ]
        else:
            modes = [
                ("Dual", "dual", "Pair players based on rating"),
                ("Battle Royale", "battle_royale", "Sort by win rate"),
                ("Teams", "teams", "Create balanced teams"),
            ]

        # Create buttons in a centered column
        btn_container = ttk.Frame(frame)
        btn_container.pack(pady=10)

        for mode_name, mode_id, description in modes:
            btn_frame = ttk.Frame(btn_container)
            btn_frame.pack(pady=12)

            btn = ttk.Button(
                btn_frame,
                text=mode_name,
                width=25,
                command=lambda m=mode_id: self.select_mode(m),
            )
            btn.pack(side=tk.LEFT, padx=10)

            ttk.Label(btn_frame, text=f"- {description}", font=("Arial", 11)).pack(
                side=tk.LEFT, padx=10
            )

        # Back button
        ttk.Button(frame, text="← Back", command=self.show_initial_selection).pack(
            pady=30
        )

    def select_mode(self, mode: str):
        """Handle mode selection"""
        self.sort_mode = mode
        self.current_round = 0
        self.teams = []
        self.in_game = False

        if mode == "tournament":
            self.show_tournament_system_selection()
        else:
            self.tournament_system = None
            self.tiebreak_method = None
            self.half_bye_enabled = False
            self.show_player_input()

    def show_tournament_system_selection(self):
        """Show tournament system selection"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True, fill=tk.BOTH)

        # Title with larger font
        title = ttk.Label(
            frame, text="Chess - Select Tournament System", font=("Arial", 24, "bold")
        )
        title.pack(pady=30)

        # Tournament systems with larger fonts
        ttk.Label(frame, text="Select Tournament System:", font=("Arial", 14)).pack(
            pady=20
        )

        systems = [
            (
                "Swiss System",
                "swiss",
                "Players paired by score, avoid repeat opponents",
            ),
            ("Round-Robin", "round_robin", "Everyone plays everyone"),
            ("Knockout (Single Elimination)", "knockout", "Elimination bracket"),
            ("Scheveningen", "scheveningen", "Team vs team, all vs all"),
        ]

        # Create buttons in centered column
        btn_container = ttk.Frame(frame)
        btn_container.pack(pady=10)

        for sys_name, sys_id, description in systems:
            btn_frame = ttk.Frame(btn_container)
            btn_frame.pack(pady=12)

            btn = ttk.Button(
                btn_frame,
                text=sys_name,
                width=30,
                command=lambda s=sys_id: self.select_tournament_system(s),
            )
            btn.pack(side=tk.LEFT, padx=10)

            ttk.Label(btn_frame, text=f"- {description}", font=("Arial", 11)).pack(
                side=tk.LEFT, padx=10
            )

        # Back button
        ttk.Button(frame, text="← Back", command=self.show_mode_selection).pack(pady=30)

    def select_tournament_system(self, system: str):
        """Handle tournament system selection"""
        self.tournament_system = system

        if system in ["swiss", "round_robin"]:
            self.show_tiebreak_selection()
        elif system == "scheveningen":
            self.show_scheveningen_setup()
        elif system == "knockout":
            # Knockout has fixed format - show simplified settings
            self.tiebreak_method = None
            self.show_knockout_settings()
        else:
            # Fallback
            self.tiebreak_method = None
            self.half_bye_enabled = False
            self.withdrawal_enabled = False
            self.max_rounds = None
            self.show_player_input()

    def show_tiebreak_selection(self):
        """Show tiebreak method selection"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True, fill=tk.BOTH)

        system_name = (
            "Swiss System" if self.tournament_system == "swiss" else "Round-Robin"
        )
        title = ttk.Label(
            frame, text=f"{system_name} - Configuration", font=("Arial", 24, "bold")
        )
        title.pack(pady=30)

        # Tiebreak selection
        ttk.Label(frame, text="Select Tiebreak Method:", font=("Arial", 14)).pack(
            pady=20
        )

        tiebreaks = [
            ("Buchholz", "buchholz", "Sum of opponents' scores"),
            ("Sonneborn-Berger", "sonneborn_berger", "Weighted opponents' scores"),
            ("Direct Encounter", "direct_encounter", "Head-to-head result"),
            ("None (Rating)", "rating", "Use rating as tiebreak"),
        ]

        btn_container = ttk.Frame(frame)
        btn_container.pack(pady=10)

        for tb_name, tb_id, description in tiebreaks:
            btn_frame = ttk.Frame(btn_container)
            btn_frame.pack(pady=12)

            btn = ttk.Button(
                btn_frame,
                text=tb_name,
                width=25,
                command=lambda t=tb_id: self.set_tiebreak_and_continue(t),
            )
            btn.pack(side=tk.LEFT, padx=10)

            ttk.Label(btn_frame, text=f"- {description}", font=("Arial", 11)).pack(
                side=tk.LEFT, padx=10
            )

        ttk.Button(
            frame, text="← Back", command=self.show_tournament_system_selection
        ).pack(pady=30)

    def set_tiebreak_and_continue(self, tiebreak: str):
        """Set tiebreak and show half-bye option"""
        self.tiebreak_method = tiebreak
        self.show_half_bye_option()

    def show_half_bye_option(self):
        """Show tournament configuration options
        (half-byes, withdrawals, max rounds, rating mode)"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="30")
        frame.pack(expand=True, fill=tk.BOTH)

        system_name = (
            "Swiss System" if self.tournament_system == "swiss" else "Round-Robin"
        )
        title = ttk.Label(
            frame,
            text=f"{system_name} - Tournament Settings",
            font=("Arial", 22, "bold"),
        )
        title.pack(pady=20)

        # Scrollable frame for all options - larger height
        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Rating Mode Option - larger fonts
        rating_frame = ttk.LabelFrame(
            scrollable_frame,
            text="Rating Changes",
            padding="20",
            style="Large.TLabelframe",
        )
        rating_frame.pack(pady=15, padx=30, fill=tk.X)

        if self.game_type == "chess":
            ttk.Label(
                rating_frame,
                text="How should ELO ratings change after games?",
                font=("Arial", 12, "bold"),
            ).pack(pady=8)

            self.rating_mode_var = tk.StringVar(value="automatic_otb")

            ttk.Radiobutton(
                rating_frame,
                text="Automatic - Online/OTB (balanced changes, K=32)",
                variable=self.rating_mode_var,
                value="automatic_otb",
                style="Large.TRadiobutton",
            ).pack(anchor=tk.W, pady=4)
            ttk.Radiobutton(
                rating_frame,
                text="Automatic - Daily/Correspondence (harsher changes, K=48)",
                variable=self.rating_mode_var,
                value="automatic_correspondence",
                style="Large.TRadiobutton",
            ).pack(anchor=tk.W, pady=4)
            ttk.Radiobutton(
                rating_frame,
                text="Manual - Manually update ELO after each round",
                variable=self.rating_mode_var,
                value="manual",
                style="Large.TRadiobutton",
            ).pack(anchor=tk.W, pady=4)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No ELO changes",
                variable=self.rating_mode_var,
                value="unranked",
                style="Large.TRadiobutton",
            ).pack(anchor=tk.W, pady=4)
        else:  # esports
            ttk.Label(
                rating_frame,
                text="Should trophy ratings be updated?",
                font=("Arial", 12, "bold"),
            ).pack(pady=8)

            self.rating_mode_var = tk.StringVar(value="unranked")

            ttk.Radiobutton(
                rating_frame,
                text="Ranked - Manually update trophies after each round",
                variable=self.rating_mode_var,
                value="ranked",
                style="Large.TRadiobutton",
            ).pack(anchor=tk.W, pady=4)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No trophy changes",
                variable=self.rating_mode_var,
                value="unranked",
                style="Large.TRadiobutton",
            ).pack(anchor=tk.W, pady=4)

        # Half-Bye Option - larger
        hb_frame = ttk.LabelFrame(scrollable_frame, text="Half-Byes", padding="20")
        hb_frame.pack(pady=15, padx=30, fill=tk.X)

        ttk.Label(
            hb_frame,
            text="Allow players to request half-byes (0.5 points) between rounds?",
            font=("Arial", 11),
            wraplength=700,
        ).pack(pady=8)

        self.half_bye_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(
            hb_frame,
            text="Yes - Enable half-byes",
            variable=self.half_bye_var,
            value=True,
            style="Large.TRadiobutton",
        ).pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(
            hb_frame,
            text="No - Disable half-byes",
            variable=self.half_bye_var,
            value=False,
            style="Large.TRadiobutton",
        ).pack(anchor=tk.W, pady=4)

        # Withdrawal Option - larger
        wd_frame = ttk.LabelFrame(
            scrollable_frame, text="Player Withdrawals", padding="20"
        )
        wd_frame.pack(pady=15, padx=30, fill=tk.X)

        ttk.Label(
            wd_frame,
            text=(
                "Allow players to withdraw from the tournament between rounds?\n"
                "Withdrawn players keep their score but stop playing."
            ),
            font=("Arial", 11),
            wraplength=700,
        ).pack(pady=8)

        self.withdrawal_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(
            wd_frame,
            text="Yes - Allow withdrawals",
            variable=self.withdrawal_var,
            value=True,
            style="Large.TRadiobutton",
        ).pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(
            wd_frame,
            text="No - No withdrawals",
            variable=self.withdrawal_var,
            value=False,
            style="Large.TRadiobutton",
        ).pack(anchor=tk.W, pady=4)

        # Max Rounds Option - larger
        rounds_frame = ttk.LabelFrame(
            scrollable_frame, text="Maximum Rounds", padding="20"
        )
        rounds_frame.pack(pady=15, padx=30, fill=tk.X)

        ttk.Label(
            rounds_frame,
            text="Set maximum number of rounds (optional):",
            font=("Arial", 11),
        ).pack(pady=8)

        rounds_input_frame = ttk.Frame(rounds_frame)
        rounds_input_frame.pack(pady=8)

        self.max_rounds_var = tk.StringVar(value="")
        ttk.Label(rounds_input_frame, text="Rounds:", font=("Arial", 11)).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Entry(
            rounds_input_frame,
            textvariable=self.max_rounds_var,
            width=15,
            font=("Arial", 11),
        ).pack(side=tk.LEFT, padx=8)
        ttk.Label(
            rounds_input_frame,
            text="(leave empty for unlimited)",
            font=("Arial", 10, "italic"),
        ).pack(side=tk.LEFT, padx=8)

        # ELO Limits (Chess only) - larger
        if self.game_type == "chess":
            elo_frame = ttk.LabelFrame(
                scrollable_frame, text="ELO Requirements", padding="20"
            )
            elo_frame.pack(pady=15, padx=30, fill=tk.X)

            ttk.Label(
                elo_frame,
                text="Set minimum and maximum ELO for tournament participants:",
                font=("Arial", 11),
            ).pack(pady=8)

            # Minimum ELO
            min_elo_frame = ttk.Frame(elo_frame)
            min_elo_frame.pack(pady=8, fill=tk.X)

            ttk.Label(min_elo_frame, text="Minimum ELO:", font=("Arial", 11)).pack(
                side=tk.LEFT, padx=8
            )
            self.min_elo_var = tk.StringVar(value="1000")
            ttk.Entry(
                min_elo_frame,
                textvariable=self.min_elo_var,
                width=15,
                font=("Arial", 11),
            ).pack(side=tk.LEFT, padx=8)
            ttk.Label(
                min_elo_frame,
                text="(default: 1000, absolute minimum: 100)",
                font=("Arial", 10, "italic"),
            ).pack(side=tk.LEFT, padx=8)

            # Maximum ELO
            max_elo_frame = ttk.Frame(elo_frame)
            max_elo_frame.pack(pady=8, fill=tk.X)

            ttk.Label(max_elo_frame, text="Maximum ELO:", font=("Arial", 11)).pack(
                side=tk.LEFT, padx=8
            )
            self.max_elo_var = tk.StringVar(value="")
            ttk.Entry(
                max_elo_frame,
                textvariable=self.max_elo_var,
                width=15,
                font=("Arial", 11),
            ).pack(side=tk.LEFT, padx=8)
            ttk.Label(
                max_elo_frame,
                text="(leave empty for no upper limit)",
                font=("Arial", 10, "italic"),
            ).pack(side=tk.LEFT, padx=8)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons - larger
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=25)

        ttk.Button(
            btn_frame, text="← Back", width=15, command=self.show_tiebreak_selection
        ).pack(side=tk.LEFT, padx=10)
        ttk.Button(
            btn_frame,
            text="Continue to Setup",
            width=20,
            command=self.confirm_tournament_settings,
        ).pack(side=tk.LEFT, padx=10)

    def confirm_tournament_settings(self):
        """Confirm tournament settings and proceed to player input"""
        rating_mode_value = self.rating_mode_var.get()

        # Parse rating mode and sub-mode
        if rating_mode_value == "automatic_otb":
            self.rating_mode = "automatic"
            self.elo_submode = "otb"
        elif rating_mode_value == "automatic_correspondence":
            self.rating_mode = "automatic"
            self.elo_submode = "correspondence"
        else:
            self.rating_mode = rating_mode_value
            self.elo_submode = None

        self.half_bye_enabled = self.half_bye_var.get()
        self.withdrawal_enabled = self.withdrawal_var.get()

        # Parse max rounds
        max_rounds_str = self.max_rounds_var.get().strip()
        if max_rounds_str:
            try:
                self.max_rounds = int(max_rounds_str)
                if self.max_rounds < 1:
                    messagebox.showwarning(
                        "Invalid Input", "Maximum rounds must be at least 1"
                    )
                    return
            except ValueError:
                messagebox.showwarning(
                    "Invalid Input", "Maximum rounds must be a number"
                )
                return
        else:
            self.max_rounds = None

        # Parse ELO limits (Chess only)
        if self.game_type == "chess":
            # Minimum ELO
            min_elo_str = self.min_elo_var.get().strip()
            if min_elo_str:
                try:
                    self.min_elo = int(min_elo_str)
                    if self.min_elo < 100:
                        messagebox.showwarning(
                            "Invalid Input", "Minimum ELO cannot be below 100"
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Minimum ELO must be a number"
                    )
                    return
            else:
                self.min_elo = 1000  # Default

            # Maximum ELO
            max_elo_str = self.max_elo_var.get().strip()
            if max_elo_str:
                try:
                    self.max_elo = int(max_elo_str)
                    if self.max_elo < self.min_elo:
                        messagebox.showwarning(
                            "Invalid Input",
                            (
                                f"Maximum ELO ({self.max_elo}) must be greater than "
                                f"or equal to minimum ELO ({self.min_elo})"
                            ),
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Maximum ELO must be a number"
                    )
                    return
            else:
                self.max_elo = None  # No upper limit
        else:
            # E-Sports doesn't use ELO limits
            self.min_elo = None
            self.max_elo = None

        self.show_player_input()

    def show_scheveningen_setup(self):
        """Show Scheveningen system setup"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        title = ttk.Label(
            frame, text="Scheveningen System - Setup", font=("Arial", 16, "bold")
        )
        title.pack(pady=20)

        ttk.Label(
            frame, text="In Scheveningen, two teams compete.", font=("Arial", 11)
        ).pack(pady=5)
        ttk.Label(
            frame,
            text="Every player from Team A plays every player from Team B.",
            font=("Arial", 10),
        ).pack(pady=5)

        ttk.Label(frame, text="\nPlayers per team:", font=("Arial", 11, "bold")).pack(
            pady=10
        )

        self.schev_team_size_var = tk.IntVar(value=4)
        spinbox = ttk.Spinbox(
            frame, from_=2, to=10, textvariable=self.schev_team_size_var, width=10
        )
        spinbox.pack(pady=5)

        ttk.Label(frame, text="\nTiebreak method:", font=("Arial", 11, "bold")).pack(
            pady=10
        )

        self.schev_tiebreak_var = tk.StringVar(value="rating")
        tiebreaks = [
            ("Buchholz", "buchholz"),
            ("Sonneborn-Berger", "sonneborn_berger"),
            ("Direct Encounter", "direct_encounter"),
            ("Rating", "rating"),
        ]

        for tb_name, tb_id in tiebreaks:
            ttk.Radiobutton(
                frame, text=tb_name, variable=self.schev_tiebreak_var, value=tb_id
            ).pack(pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(
            btn_frame, text="← Back", command=self.show_tournament_system_selection
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Continue", command=self.confirm_scheveningen_setup
        ).pack(side=tk.LEFT, padx=5)

    def confirm_scheveningen_setup(self):
        """Confirm Scheveningen setup and proceed"""
        self.scheveningen_team_size = self.schev_team_size_var.get()
        self.tiebreak_method = self.schev_tiebreak_var.get()
        self.show_scheveningen_settings()

    def show_knockout_settings(self):
        """Show Knockout tournament settings
        (rating mode only, no half-byes/withdrawals/max rounds)"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        title = ttk.Label(
            frame, text="Knockout - Tournament Settings", font=("Arial", 16, "bold")
        )
        title.pack(pady=20)

        # Only Rating Mode for Knockout
        rating_frame = ttk.LabelFrame(frame, text="Rating Changes", padding="15")
        rating_frame.pack(pady=10, padx=40, fill=tk.X)

        if self.game_type == "chess":
            ttk.Label(
                rating_frame,
                text="How should ELO ratings change after games?",
                font=("Arial", 10, "bold"),
            ).pack(pady=5)

            self.rating_mode_var = tk.StringVar(value="automatic_otb")

            ttk.Radiobutton(
                rating_frame,
                text="Automatic - Online/OTB (balanced changes, K=32)",
                variable=self.rating_mode_var,
                value="automatic_otb",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Automatic - Daily/Correspondence (harsher changes, K=48)",
                variable=self.rating_mode_var,
                value="automatic_correspondence",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Manual - Manually update ELO after each round",
                variable=self.rating_mode_var,
                value="manual",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No ELO changes",
                variable=self.rating_mode_var,
                value="unranked",
            ).pack(anchor=tk.W, pady=2)
        else:  # esports
            ttk.Label(
                rating_frame,
                text="Should trophy ratings be updated?",
                font=("Arial", 10, "bold"),
            ).pack(pady=5)

            self.rating_mode_var = tk.StringVar(value="unranked")

            ttk.Radiobutton(
                rating_frame,
                text="Ranked - Manually update trophies after each round",
                variable=self.rating_mode_var,
                value="ranked",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No trophy changes",
                variable=self.rating_mode_var,
                value="unranked",
            ).pack(anchor=tk.W, pady=2)

        # Note about knockout features
        note_frame = ttk.LabelFrame(frame, text="Note", padding="10")
        note_frame.pack(pady=10, padx=40, fill=tk.X)
        ttk.Label(
            note_frame,
            text="Knockout tournaments have a fixed format:\n"
            "• No half-byes (players must compete)\n"
            "• No withdrawals (single elimination)\n"
            "• Natural end (continues to 1 winner)",
            font=("Arial", 9),
            justify=tk.LEFT,
        ).pack()

        # ELO Limits (Chess only)
        if self.game_type == "chess":
            elo_frame = ttk.LabelFrame(frame, text="ELO Requirements", padding="15")
            elo_frame.pack(pady=10, padx=40, fill=tk.X)

            ttk.Label(
                elo_frame,
                text="Set minimum and maximum ELO for tournament participants:",
                font=("Arial", 10),
            ).pack(pady=5)

            # Minimum ELO
            min_elo_frame = ttk.Frame(elo_frame)
            min_elo_frame.pack(pady=5, fill=tk.X)

            ttk.Label(min_elo_frame, text="Min ELO:").pack(side=tk.LEFT, padx=5)
            self.min_elo_var = tk.StringVar(value="1000")
            ttk.Entry(min_elo_frame, textvariable=self.min_elo_var, width=10).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Label(
                min_elo_frame,
                text="(default: 1000, min: 100)",
                font=("Arial", 9, "italic"),
            ).pack(side=tk.LEFT, padx=5)

            # Maximum ELO
            max_elo_frame = ttk.Frame(elo_frame)
            max_elo_frame.pack(pady=5, fill=tk.X)

            ttk.Label(max_elo_frame, text="Max ELO:").pack(side=tk.LEFT, padx=5)
            self.max_elo_var = tk.StringVar(value="")
            ttk.Entry(max_elo_frame, textvariable=self.max_elo_var, width=10).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Label(
                max_elo_frame,
                text="(leave empty for no limit)",
                font=("Arial", 9, "italic"),
            ).pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(
            btn_frame, text="← Back", command=self.show_tournament_system_selection
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Continue to Setup", command=self.confirm_knockout_settings
        ).pack(side=tk.LEFT, padx=5)

    def confirm_knockout_settings(self):
        """Confirm knockout settings"""
        rating_mode_value = self.rating_mode_var.get()

        # Parse rating mode and sub-mode
        if rating_mode_value == "automatic_otb":
            self.rating_mode = "automatic"
            self.elo_submode = "otb"
        elif rating_mode_value == "automatic_correspondence":
            self.rating_mode = "automatic"
            self.elo_submode = "correspondence"
        else:
            self.rating_mode = rating_mode_value
            self.elo_submode = None

        # Knockout doesn't support these features
        self.half_bye_enabled = False
        self.withdrawal_enabled = False
        self.max_rounds = None

        # Parse ELO limits (Chess only)
        if self.game_type == "chess":
            # Minimum ELO
            min_elo_str = self.min_elo_var.get().strip()
            if min_elo_str:
                try:
                    self.min_elo = int(min_elo_str)
                    if self.min_elo < 100:
                        messagebox.showwarning(
                            "Invalid Input", "Minimum ELO cannot be below 100"
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Minimum ELO must be a number"
                    )
                    return
            else:
                self.min_elo = 1000  # Default

            # Maximum ELO
            max_elo_str = self.max_elo_var.get().strip()
            if max_elo_str:
                try:
                    self.max_elo = int(max_elo_str)
                    if self.max_elo < self.min_elo:
                        messagebox.showwarning(
                            "Invalid Input",
                            (
                                f"Maximum ELO ({self.max_elo}) must be greater than "
                                f"or equal to minimum ELO ({self.min_elo})"
                            ),
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Maximum ELO must be a number"
                    )
                    return
            else:
                self.max_elo = None  # No upper limit
        else:
            self.min_elo = None
            self.max_elo = None

        self.show_player_input()

    def show_scheveningen_settings(self):
        """Show Scheveningen tournament settings (no max rounds - has fixed rounds)"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)

        title = ttk.Label(
            frame, text="Scheveningen - Tournament Settings", font=("Arial", 22, "bold")
        )
        title.pack(pady=20)

        # Scrollable frame
        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Rating Mode
        rating_frame = ttk.LabelFrame(
            scrollable_frame, text="Rating Changes", padding="15"
        )
        rating_frame.pack(pady=15, padx=30, fill=tk.X)

        if self.game_type == "chess":
            ttk.Label(
                rating_frame,
                text="How should ELO ratings change after games?",
                font=("Arial", 12, "bold"),
            ).pack(pady=5)

            self.rating_mode_var = tk.StringVar(value="automatic_otb")

            ttk.Radiobutton(
                rating_frame,
                text="Automatic - Online/OTB (balanced changes, K=32)",
                variable=self.rating_mode_var,
                value="automatic_otb",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Automatic - Daily/Correspondence (harsher changes, K=48)",
                variable=self.rating_mode_var,
                value="automatic_correspondence",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Manual - Manually update ELO after each round",
                variable=self.rating_mode_var,
                value="manual",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No ELO changes",
                variable=self.rating_mode_var,
                value="unranked",
            ).pack(anchor=tk.W, pady=2)
        else:  # esports
            ttk.Label(
                rating_frame,
                text="Should trophy ratings be updated?",
                font=("Arial", 12, "bold"),
            ).pack(pady=5)

            self.rating_mode_var = tk.StringVar(value="unranked")

            ttk.Radiobutton(
                rating_frame,
                text="Ranked - Manually update trophies after each round",
                variable=self.rating_mode_var,
                value="ranked",
            ).pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No trophy changes",
                variable=self.rating_mode_var,
                value="unranked",
            ).pack(anchor=tk.W, pady=2)

        # Half-Byes (Scheveningen supports this)
        hb_frame = ttk.LabelFrame(scrollable_frame, text="Half-Byes", padding="15")
        hb_frame.pack(pady=15, padx=30, fill=tk.X)

        ttk.Label(
            hb_frame,
            text="Allow players to request half-byes (0.5 points) between rounds?",
            font=("Arial", 11),
            wraplength=700,
        ).pack(pady=5)

        self.half_bye_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(
            hb_frame,
            text="Yes - Enable half-byes",
            variable=self.half_bye_var,
            value=True,
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            hb_frame,
            text="No - Disable half-byes",
            variable=self.half_bye_var,
            value=False,
        ).pack(anchor=tk.W, pady=2)

        # Withdrawals (Scheveningen supports this)
        wd_frame = ttk.LabelFrame(
            scrollable_frame, text="Player Withdrawals", padding="15"
        )
        wd_frame.pack(pady=15, padx=30, fill=tk.X)

        ttk.Label(
            wd_frame,
            text=(
                "Allow players to withdraw from the tournament between rounds?\n"
                "Withdrawn players keep their score but stop playing."
            ),
            font=("Arial", 11),
            wraplength=700,
        ).pack(pady=5)

        self.withdrawal_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(
            wd_frame,
            text="Yes - Allow withdrawals",
            variable=self.withdrawal_var,
            value=True,
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            wd_frame,
            text="No - No withdrawals",
            variable=self.withdrawal_var,
            value=False,
        ).pack(anchor=tk.W, pady=2)

        # Note about fixed rounds
        note_frame = ttk.LabelFrame(
            scrollable_frame, text="Tournament Length", padding="10"
        )
        note_frame.pack(pady=15, padx=30, fill=tk.X)
        ttk.Label(
            note_frame,
            text=(
                f"Scheveningen has fixed rounds:\n"
                f"Team size: {self.scheveningen_team_size} players per team\n"
                f"Total rounds: {self.scheveningen_team_size} "
                "(each player plays each opponent once)"
            ),
            font=("Arial", 10),
            justify=tk.LEFT,
        ).pack()

        # ELO Limits (Chess only)
        if self.game_type == "chess":
            elo_frame = ttk.LabelFrame(
                scrollable_frame, text="ELO Requirements", padding="15"
            )
            elo_frame.pack(pady=15, padx=30, fill=tk.X)

            ttk.Label(
                elo_frame,
                text="Set minimum and maximum ELO for tournament participants:",
                font=("Arial", 11),
            ).pack(pady=5)

            # Minimum ELO
            min_elo_frame = ttk.Frame(elo_frame)
            min_elo_frame.pack(pady=5, fill=tk.X)

            ttk.Label(min_elo_frame, text="Minimum ELO:").pack(side=tk.LEFT, padx=5)
            self.min_elo_var = tk.StringVar(value="1000")
            ttk.Entry(min_elo_frame, textvariable=self.min_elo_var, width=10).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Label(
                min_elo_frame,
                text="(default: 1000, absolute minimum: 100)",
                font=("Arial", 9, "italic"),
            ).pack(side=tk.LEFT, padx=5)

            # Maximum ELO
            max_elo_frame = ttk.Frame(elo_frame)
            max_elo_frame.pack(pady=5, fill=tk.X)

            ttk.Label(max_elo_frame, text="Maximum ELO:").pack(side=tk.LEFT, padx=5)
            self.max_elo_var = tk.StringVar(value="")
            ttk.Entry(max_elo_frame, textvariable=self.max_elo_var, width=10).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Label(
                max_elo_frame,
                text="(leave empty for no upper limit)",
                font=("Arial", 9, "italic"),
            ).pack(side=tk.LEFT, padx=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back", command=self.show_scheveningen_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="Continue to Setup",
            command=self.confirm_scheveningen_settings,
        ).pack(side=tk.LEFT, padx=5)

    def confirm_scheveningen_settings(self):
        """Confirm Scheveningen settings"""
        rating_mode_value = self.rating_mode_var.get()

        # Parse rating mode and sub-mode
        if rating_mode_value == "automatic_otb":
            self.rating_mode = "automatic"
            self.elo_submode = "otb"
        elif rating_mode_value == "automatic_correspondence":
            self.rating_mode = "automatic"
            self.elo_submode = "correspondence"
        else:
            self.rating_mode = rating_mode_value
            self.elo_submode = None

        self.half_bye_enabled = self.half_bye_var.get()
        self.withdrawal_enabled = self.withdrawal_var.get()

        # Scheveningen has fixed rounds based on team size
        self.max_rounds = None

        # Parse ELO limits (Chess only)
        if self.game_type == "chess":
            # Minimum ELO
            min_elo_str = self.min_elo_var.get().strip()
            if min_elo_str:
                try:
                    self.min_elo = int(min_elo_str)
                    if self.min_elo < 100:
                        messagebox.showwarning(
                            "Invalid Input", "Minimum ELO cannot be below 100"
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Minimum ELO must be a number"
                    )
                    return
            else:
                self.min_elo = 1000  # Default

            # Maximum ELO
            max_elo_str = self.max_elo_var.get().strip()
            if max_elo_str:
                try:
                    self.max_elo = int(max_elo_str)
                    if self.max_elo < self.min_elo:
                        messagebox.showwarning(
                            "Invalid Input",
                            (
                                f"Maximum ELO ({self.max_elo}) must be greater than "
                                f"or equal to minimum ELO ({self.min_elo})"
                            ),
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Maximum ELO must be a number"
                    )
                    return
            else:
                self.max_elo = None  # No upper limit
        else:
            self.min_elo = None
            self.max_elo = None

        self.show_player_input()

    def show_player_input(self, auto_load: bool = True):
        """Show player input interface.

        auto_load: if True (the default, used by every "starting fresh"
        entry point), automatically loads the saved roster from disk for
        convenience. Pass False when returning here with live, valuable
        in-memory player state that must not be overwritten — e.g.
        back_to_setup() returning from a mid-tournament screen, where
        self.players already holds real progress (scores, opponents
        played, etc.) that the saved roster file on disk knows nothing
        about. Loading over it there would silently destroy that
        progress, contradicting the "Current game progress will be kept"
        promise shown in that confirmation dialog.
        """
        self.editing_player_index = None  # Cancel any edit in progress
        self.clear_window()

        # Main container with more padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title with larger font
        game_name = "Chess" if self.game_type == "chess" else "E-Sports"
        if self.sort_mode == "tournament":
            system_names = {
                "swiss": "Swiss System",
                "round_robin": "Round-Robin",
                "knockout": "Knockout",
                "scheveningen": "Scheveningen",
            }
            mode_name = system_names.get(self.tournament_system, "Tournament")
        else:
            mode_name = self.sort_mode.replace("_", " ").title()
        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        title = ttk.Label(
            main_frame, text=f"{game_name} - {mode_name}", font=("Arial", 20, "bold")
        )
        title.pack(pady=15)

        # Input frame with larger font
        input_frame = ttk.LabelFrame(main_frame, text="Add/Edit Player", padding="15")
        input_frame.pack(fill=tk.X, padx=20, pady=10)

        # Determine which fields are required based on game type and mode
        is_tournament = self.sort_mode == "tournament"
        is_chess = self.game_type == "chess"

        # Create input fields based on requirements
        # Row 0: First Name, Last Name
        # Row 1: Nickname, Rating, Add Button

        ttk.Label(input_frame, text="First Name:", font=("Arial", 11)).grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=8
        )
        self.first_name_entry = ttk.Entry(input_frame, width=20, font=("Arial", 11))
        self.first_name_entry.grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(input_frame, text="Last Name:", font=("Arial", 11)).grid(
            row=0, column=2, sticky=tk.W, padx=10, pady=8
        )
        self.last_name_entry = ttk.Entry(input_frame, width=20, font=("Arial", 11))
        self.last_name_entry.grid(row=0, column=3, padx=10, pady=8)

        ttk.Label(input_frame, text="Nickname:", font=("Arial", 11)).grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=8
        )
        self.nickname_entry = ttk.Entry(input_frame, width=20, font=("Arial", 11))
        self.nickname_entry.grid(row=1, column=1, padx=10, pady=8)

        # Rating input
        ttk.Label(input_frame, text=f"{rating_name}:", font=("Arial", 11)).grid(
            row=1, column=2, sticky=tk.W, padx=10, pady=8
        )
        self.rating_entry = ttk.Entry(input_frame, width=15, font=("Arial", 11))
        self.rating_entry.grid(row=1, column=3, padx=10, pady=8)

        # Add/Update button
        self.add_update_btn = ttk.Button(
            input_frame, text="Add Player", command=self.add_or_update_player
        )
        self.add_update_btn.grid(row=1, column=4, padx=15, pady=8)

        # Optional FIDE info - only relevant for chess tournaments (Swiss/
        # Round-Robin/Knockout/Scheveningen), where it can be exported via
        # TRF16. Left blank, a TRF16 export still works fine for pairing/
        # tiebreak interop - these only matter for genuine FIDE rating
        # submission, so nobody is forced to fill them in.
        self.fide_fields_shown = is_chess and is_tournament
        if self.fide_fields_shown:
            fide_frame = ttk.LabelFrame(
                input_frame, text="FIDE Info (optional)", padding="8"
            )
            fide_frame.grid(row=2, column=0, columnspan=5, sticky=tk.W, pady=(5, 0))

            ttk.Label(fide_frame, text="Sex:", font=("Arial", 10)).grid(
                row=0, column=0, sticky=tk.W, padx=6, pady=4
            )
            self.sex_combo = ttk.Combobox(
                fide_frame, width=5, font=("Arial", 10),
                values=["", "m", "w"], state="readonly",
            )
            self.sex_combo.set("")
            self.sex_combo.grid(row=0, column=1, padx=6, pady=4)

            ttk.Label(fide_frame, text="Title:", font=("Arial", 10)).grid(
                row=0, column=2, sticky=tk.W, padx=6, pady=4
            )
            self.title_combo = ttk.Combobox(
                fide_frame, width=6, font=("Arial", 10),
                values=["", "GM", "IM", "WGM", "FM", "WIM", "CM", "WFM", "WCM"],
                state="readonly",
            )
            self.title_combo.set("")
            self.title_combo.grid(row=0, column=3, padx=6, pady=4)

            ttk.Label(fide_frame, text="Federation:", font=("Arial", 10)).grid(
                row=0, column=4, sticky=tk.W, padx=6, pady=4
            )
            self.federation_entry = ttk.Entry(
                fide_frame, width=6, font=("Arial", 10)
            )
            self.federation_entry.grid(row=0, column=5, padx=6, pady=4)

            ttk.Label(fide_frame, text="FIDE ID:", font=("Arial", 10)).grid(
                row=1, column=0, sticky=tk.W, padx=6, pady=4
            )
            self.fide_id_entry = ttk.Entry(fide_frame, width=12, font=("Arial", 10))
            self.fide_id_entry.grid(row=1, column=1, padx=6, pady=4)

            ttk.Label(fide_frame, text="Birth date (YYYY/MM/DD):", font=("Arial", 10)).grid(
                row=1, column=2, columnspan=2, sticky=tk.W, padx=6, pady=4
            )
            self.birth_date_entry = ttk.Entry(
                fide_frame, width=12, font=("Arial", 10)
            )
            self.birth_date_entry.grid(row=1, column=4, padx=6, pady=4)

        # Requirements label
        req_text = ""
        if is_chess and is_tournament:
            req_text = "Required: First Name + Last Name | Optional: Nickname"
        elif is_chess:
            req_text = "Required: (First + Last Name) OR Nickname | Optional: Both"
        else:  # e-sports
            req_text = "Required: Nickname | Optional: First Name + Last Name"

        req_label = ttk.Label(
            input_frame, text=req_text, font=("Arial", 9, "italic"), foreground="blue"
        )
        req_label.grid(row=3, column=0, columnspan=5, pady=5)

        # Player list with more height
        list_frame = ttk.LabelFrame(main_frame, text="Players", padding="15")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Treeview for player list - larger height and columns
        columns = [
            "name",
            "rating",
            "wins",
            "losses",
            "draws",
            "byes",
            "hbyes",
            "winrate",
        ]

        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("rating", text=rating_name)
        self.tree.heading("wins", text="Wins")
        self.tree.heading("losses", text="Losses")
        self.tree.heading("draws", text="Draws")
        self.tree.heading("byes", text="Byes")
        self.tree.heading("hbyes", text="½Bye")
        self.tree.heading("winrate", text="Win Rate %")

        # Wider columns for better readability
        self.tree.column("name", width=150)
        self.tree.column("rating", width=80)
        self.tree.column("wins", width=60)
        self.tree.column("losses", width=60)
        self.tree.column("draws", width=60)
        self.tree.column("byes", width=60)
        self.tree.column("hbyes", width=60)
        self.tree.column("winrate", width=100)

        # Configure treeview font
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_player_select)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Edit Selected", command=self.edit_player).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            button_frame, text="Remove Selected", command=self.remove_player
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_players).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Save Players", command=self.save_players).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            button_frame,
            text="Load Players",
            command=self._load_and_refresh,
        ).pack(side=tk.LEFT, padx=5)

        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(action_frame, text="← Back", command=self.show_mode_selection).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            action_frame,
            text="Start Game",
            command=self.start_game,
            style="Large.TButton",
        ).pack(side=tk.RIGHT, padx=5)

        # Bind Enter key to add player - all fields
        self.first_name_entry.bind("<Return>", lambda e: self.add_or_update_player())
        self.last_name_entry.bind("<Return>", lambda e: self.add_or_update_player())
        self.nickname_entry.bind("<Return>", lambda e: self.add_or_update_player())
        self.rating_entry.bind("<Return>", lambda e: self.add_or_update_player())

        # Focus on appropriate field based on mode
        if is_chess and is_tournament:
            self.first_name_entry.focus()  # Tournament chess: first name required
        elif not is_chess:
            self.nickname_entry.focus()  # E-sports: nickname required
        else:
            self.first_name_entry.focus()  # Non-tournament chess: start with first name

        # Auto-load players from save file (if exists) - skipped when the
        # caller has live in-memory progress to preserve (see docstring).
        if auto_load:
            self.auto_load_players()

        # Refresh player list
        self.refresh_player_list()

    def on_player_select(self, event):
        """Handle player selection in tree"""
        pass  # Just for binding, actual edit is done via button

    def edit_player(self):
        """Load selected player into input fields for editing"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a player to edit")
            return

        # The tree only shows non-eliminated players, so map the tree row index
        # to the real index inside self.players to avoid editing the wrong player.
        tree_row = self.tree.index(selected[0])
        visible_players = [p for p in self.players if not p.eliminated]
        if tree_row >= len(visible_players):
            return
        player = visible_players[tree_row]
        self.editing_player_index = self.players.index(player)

        # Load player data into entry fields
        self.first_name_entry.delete(0, tk.END)
        self.first_name_entry.insert(0, player.first_name)

        self.last_name_entry.delete(0, tk.END)
        self.last_name_entry.insert(0, player.last_name)

        self.nickname_entry.delete(0, tk.END)
        self.nickname_entry.insert(0, player.nickname)

        self.rating_entry.delete(0, tk.END)
        self.rating_entry.insert(0, str(player.rating))

        if self.fide_fields_shown:
            self.sex_combo.set(player.sex or "")
            self.title_combo.set(player.title or "")
            self.federation_entry.delete(0, tk.END)
            self.federation_entry.insert(0, player.fide_federation or "")
            self.fide_id_entry.delete(0, tk.END)
            self.fide_id_entry.insert(0, player.fide_id or "")
            self.birth_date_entry.delete(0, tk.END)
            self.birth_date_entry.insert(0, player.birth_date or "")

        # Change button text
        self.add_update_btn.config(text="Update Player")
        self.first_name_entry.focus()

    def _read_fide_fields(self):
        """Read and loosely validate the optional FIDE Info fields.
        Returns a dict of {sex, title, fide_federation, fide_id,
        birth_date} - each None if left blank - or None if something
        was filled in but doesn't look right (a warning is shown in that
        case). Every field here is optional, so an all-blank form is
        always valid."""
        if not self.fide_fields_shown:
            return {
                "sex": None, "title": None, "fide_federation": None,
                "fide_id": None, "birth_date": None,
            }

        sex = self.sex_combo.get().strip() or None
        title = self.title_combo.get().strip() or None
        federation = self.federation_entry.get().strip().upper() or None
        fide_id = self.fide_id_entry.get().strip() or None
        birth_date = self.birth_date_entry.get().strip() or None

        if federation and (len(federation) != 3 or not federation.isalpha()):
            messagebox.showwarning(
                "Invalid Federation",
                "FIDE Federation should be a 3-letter code (e.g. USA, GER), "
                "or left blank.",
            )
            return None

        if fide_id and not fide_id.isdigit():
            messagebox.showwarning(
                "Invalid FIDE ID", "FIDE ID should contain digits only, or be left blank."
            )
            return None

        if birth_date:
            if not re.match(r"^\d{4}/\d{2}/\d{2}$", birth_date):
                messagebox.showwarning(
                    "Invalid Birth Date",
                    "Birth date should be in YYYY/MM/DD format (e.g. "
                    "2005/03/17), or left blank.",
                )
                return None

        return {
            "sex": sex, "title": title, "fide_federation": federation,
            "fide_id": fide_id, "birth_date": birth_date,
        }

    def add_or_update_player(self):
        """Add a new player or update existing one with name validation"""
        first_name = _normalize_name_casing(self.first_name_entry.get().strip())
        last_name = _normalize_name_casing(self.last_name_entry.get().strip())
        nickname = self.nickname_entry.get().strip()
        rating_str = self.rating_entry.get().strip()

        is_tournament = self.sort_mode == "tournament"
        is_chess = self.game_type == "chess"

        # Validate name fields based on mode
        if is_chess and is_tournament:
            # Chess tournament: REQUIRE first + last name
            if not first_name or not last_name:
                messagebox.showwarning(
                    "Input Error",
                    "Chess tournaments require both First Name and Last Name",
                )
                return
        elif is_chess:
            # Non-tournament chess: REQUIRE (first + last) OR nickname
            if not ((first_name and last_name) or nickname):
                messagebox.showwarning(
                    "Input Error",
                    (
                        "Please enter either:\n- First Name AND Last Name\n"
                        "- OR Nickname\n- OR all three"
                    ),
                )
                return
        else:
            # E-sports: REQUIRE nickname
            if not nickname:
                messagebox.showwarning(
                    "Input Error", "E-Sports mode requires a Nickname"
                )
                return

        # Validate rating
        if not rating_str:
            messagebox.showwarning("Input Error", "Please enter a rating")
            return

        try:
            rating = int(rating_str)
        except ValueError:
            messagebox.showwarning("Input Error", "Rating must be a number")
            return

        # Validate rating constraints
        if self.game_type == "chess":
            # Absolute minimum is 100
            if rating < 100:
                messagebox.showwarning("Invalid Rating", "ELO cannot be below 100")
                return

            # Check tournament ELO limits if set
            if self.sort_mode == "tournament":
                if self.min_elo and rating < self.min_elo:
                    messagebox.showwarning(
                        "Invalid Rating",
                        f"ELO ({rating}) is below tournament minimum ({self.min_elo})",
                    )
                    return

                if self.max_elo and rating > self.max_elo:
                    messagebox.showwarning(
                        "Invalid Rating",
                        f"ELO ({rating}) is above tournament maximum ({self.max_elo})",
                    )
                    return
        else:
            # E-sports: Trophies can never be negative. This mirrors the
            # floor apply_manual_ratings already enforces during a running
            # tournament - without it here too, a player could be
            # registered with a negative Trophy count that manual updates
            # would then refuse to ever set it back to.
            if rating < 0:
                messagebox.showwarning(
                    "Invalid Rating", "Trophies cannot be below 0"
                )
                return

        fide_fields = self._read_fide_fields()
        if fide_fields is None:
            return  # a warning was already shown

        # Build the candidate name's display form the same way the real
        # Player object would, so the duplicate check below can never
        # drift out of sync with how names actually render in the UI.
        candidate = Player(
            first_name=first_name, last_name=last_name, nickname=nickname
        )
        candidate_key = _player_display_name_key(candidate)

        # Check if we are updating an existing player (edit mode)
        if self.editing_player_index is not None:
            # Look for a collision against every OTHER player (case-
            # insensitive on the full display name) before committing the
            # rename. Compare by index, not by object/name, so renaming a
            # player back to their own unchanged name never false-positives.
            for i, p in enumerate(self.players):
                if i == self.editing_player_index:
                    continue
                if _player_display_name_key(p) == candidate_key:
                    messagebox.showwarning(
                        "Duplicate Player",
                        (
                            f'A player named "{candidate.name}" already exists. '
                            "Please use a different name, or add a nickname to "
                            "tell them apart."
                        ),
                    )
                    return

            # Update the player at the remembered index — works even if
            # the user changed name fields, which is exactly what caused
            # the "mitosis" bug when matching by name.
            player = self.players[self.editing_player_index]
            player.first_name = first_name
            player.last_name = last_name
            player.nickname = nickname
            player.rating = rating
            player.sex = fide_fields["sex"]
            player.title = fide_fields["title"]
            player.fide_federation = fide_fields["fide_federation"]
            player.fide_id = fide_fields["fide_id"]
            player.birth_date = fide_fields["birth_date"]
            self.editing_player_index = None  # Clear edit mode
            self.add_update_btn.config(text="Add Player")
        else:
            # No edit in progress — check for a display-name collision
            # against every existing player (case-insensitive), since two
            # different first/last/nickname combinations can still render
            # identically (e.g. "Jo Ann" vs "Joann").
            existing_player = None
            for p in self.players:
                if _player_display_name_key(p) == candidate_key:
                    existing_player = p
                    break
            if existing_player:
                if (
                    existing_player.first_name == first_name
                    and existing_player.last_name == last_name
                    and existing_player.nickname == nickname
                ):
                    # Exact duplicate typed in manually - treat it as
                    # "update this player's rating" rather than an error,
                    # to preserve the previous convenience behavior.
                    existing_player.rating = rating
                    existing_player.sex = fide_fields["sex"]
                    existing_player.title = fide_fields["title"]
                    existing_player.fide_federation = fide_fields["fide_federation"]
                    existing_player.fide_id = fide_fields["fide_id"]
                    existing_player.birth_date = fide_fields["birth_date"]
                else:
                    messagebox.showwarning(
                        "Duplicate Player",
                        (
                            f'A player named "{candidate.name}" already exists. '
                            "Please use a different name, or add a nickname to "
                            "tell them apart."
                        ),
                    )
                    return
            else:
                # Genuinely new player
                player = candidate
                player.rating = rating
                player.sex = fide_fields["sex"]
                player.title = fide_fields["title"]
                player.fide_federation = fide_fields["fide_federation"]
                player.fide_id = fide_fields["fide_id"]
                player.birth_date = fide_fields["birth_date"]
                self.players.append(player)

        # Clear entries
        self.first_name_entry.delete(0, tk.END)
        self.last_name_entry.delete(0, tk.END)
        self.nickname_entry.delete(0, tk.END)
        self.rating_entry.delete(0, tk.END)
        if self.fide_fields_shown:
            self.sex_combo.set("")
            self.title_combo.set("")
            self.federation_entry.delete(0, tk.END)
            self.fide_id_entry.delete(0, tk.END)
            self.birth_date_entry.delete(0, tk.END)
        self.add_update_btn.config(text="Add Player")

        # Refresh list
        self.refresh_player_list()

        # Focus back on appropriate entry
        if is_chess and is_tournament:
            self.first_name_entry.focus()
        elif not is_chess:
            self.nickname_entry.focus()
        else:
            self.first_name_entry.focus()

    def remove_player(self):
        """Remove selected player"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(
                "Selection Error", "Please select a player to remove"
            )
            return

        tree_row = self.tree.index(selected[0])
        visible_players = [p for p in self.players if not p.eliminated]
        if tree_row >= len(visible_players):
            return
        player = visible_players[tree_row]
        index = self.players.index(player)
        del self.players[index]
        self.editing_player_index = None  # Cancel any pending edit
        self.add_update_btn.config(text="Add Player")
        self.refresh_player_list()

    def clear_players(self):
        """Clear all players"""
        if self.players and messagebox.askyesno("Confirm", "Clear all players?"):
            self.players.clear()
            self.editing_player_index = None  # Cancel any pending edit
            self.add_update_btn.config(text="Add Player")
            self.refresh_player_list()

    def refresh_player_list(self):
        """Refresh the player list display"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add players
        for player in self.players:
            if not player.eliminated:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        player.name,
                        player.rating,
                        player.wins,
                        player.losses,
                        player.draws,
                        player.byes,
                        player.half_byes,
                        f"{player.win_rate:.1f}",
                    ),
                )

    def get_save_filename(self):
        """Get the appropriate save filename based on game type"""
        if self.game_type == "chess":
            return "player_sorter_chess.json"
        else:  # esports
            return "player_sorter_esports.json"

    def save_players(self):
        """Save current players to file (separate for chess and e-sports)"""
        filename = self.get_save_filename()

        try:
            data = {"game_type": self.game_type, "players": []}

            for player in self.players:
                player_data = {
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "nickname": player.nickname,
                    "rating": player.rating,
                    "wins": player.wins,
                    "losses": player.losses,
                    "draws": player.draws,
                    "byes": player.byes,
                    "half_byes": player.half_byes,
                    "sex": player.sex,
                    "title": player.title,
                    "fide_federation": player.fide_federation,
                    "fide_id": player.fide_id,
                    "birth_date": player.birth_date,
                }
                data["players"].append(player_data)

            with open(filename, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save players: {str(e)}")
            return False

    def load_players(self):
        """Load players from file (separate for chess and e-sports)"""
        filename = self.get_save_filename()

        if not os.path.exists(filename):
            # No save file exists yet - this is normal for first run
            return False

        try:
            with open(filename, "r") as f:
                data = json.load(f)

            # Verify the save file matches current game type
            if data.get("game_type") != self.game_type:
                messagebox.showwarning(
                    "Wrong Game Type",
                    (
                        f"Save file is for {data.get('game_type', 'unknown')} "
                        f"but current mode is {self.game_type}"
                    ),
                )
                return False

            # Clear current players
            self.players = []

            # Load players
            for player_data in data.get("players", []):
                """Support both old format (name) and
                new format (first_name, last_name, nickname)"""
                if "first_name" in player_data or "nickname" in player_data:
                    # New format
                    player = Player(
                        first_name=player_data.get("first_name", ""),
                        last_name=player_data.get("last_name", ""),
                        nickname=player_data.get("nickname", ""),
                        rating=player_data.get("rating", 0),
                        wins=player_data.get("wins", 0),
                        losses=player_data.get("losses", 0),
                        draws=player_data.get("draws", 0),
                        byes=player_data.get("byes", 0),
                        half_byes=player_data.get("half_byes", 0),
                    )
                    player.sex = player_data.get("sex")
                    player.title = player_data.get("title")
                    player.fide_federation = player_data.get("fide_federation")
                    player.fide_id = player_data.get("fide_id")
                    player.birth_date = player_data.get("birth_date")
                else:
                    # Old format - convert 'name' to first_name + last_name
                    old_name = player_data.get("name", "")
                    name_parts = old_name.split(" ", 1)
                    first_name = name_parts[0] if len(name_parts) > 0 else ""
                    last_name = name_parts[1] if len(name_parts) > 1 else ""

                    player = Player(
                        first_name=first_name,
                        last_name=last_name,
                        nickname="",
                        rating=player_data.get("rating", 0),
                        wins=player_data.get("wins", 0),
                        losses=player_data.get("losses", 0),
                        draws=player_data.get("draws", 0),
                        byes=player_data.get("byes", 0),
                        half_byes=player_data.get("half_byes", 0),
                    )
                self.players.append(player)

            return True
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load players: {str(e)}")
            return False

    def _load_and_refresh(self):
        """Load players from file and refresh the list display."""
        if self.load_players():
            self.refresh_player_list()

    def auto_load_players(self):
        """Automatically load players when entering player input screen"""
        if self.load_players():
            self.refresh_player_list()

    def auto_save_players(self):
        """Automatically save players after game ends"""
        self.save_players()

    def save_tournament_to_file(self, finished: bool) -> str | None:
        """Serialise the current tournament to a JSON file.
        Returns the filename on success, or None on failure.

        File naming convention:
        tournament_YYYY-MM-DD_HH-MM-SS_SYSTEM_[finished|unfinished].json
        """
        # Use stored start time, or generate one now as fallback
        timestamp = getattr(self, "tournament_start_time", None)
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        system_label = getattr(self, "tournament_system", "tournament")
        status_label = "finished" if finished else "unfinished"

        try:
            t_dir = _get_tournaments_dir()
        except RuntimeError as exc:
            messagebox.showerror("Save Error", f"Could not save tournament:\n\n{exc}")
            return None
        filename = str(
            t_dir / f"tournament_{timestamp}_{system_label}_{status_label}.json"
        )

        # Build serialisable player list (full state, not just to_dict())
        players_data = []
        for player in self.players:
            players_data.append(
                {
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "nickname": player.nickname,
                    "rating": player.rating,
                    "wins": player.wins,
                    "losses": player.losses,
                    "draws": player.draws,
                    "byes": player.byes,
                    "half_byes": player.half_byes,
                    "eliminated": player.eliminated,
                    "withdrawn": player.withdrawn,
                    "withdrawal_round": player.withdrawal_round,
                    "opponents": player.opponents,
                    "results_vs_opponents": player.results_vs_opponents,
                    "colors": player.colors,
                    "requested_half_bye": player.requested_half_bye,
                    "sex": player.sex,
                    "title": player.title,
                    "fide_federation": player.fide_federation,
                    "fide_id": player.fide_id,
                    "birth_date": player.birth_date,
                    "initial_rating": player.initial_rating,
                }
            )

        # For scheveningen: also save team membership
        schev_team_a_names = [p.name for p in getattr(self, "schev_team_a", [])]
        schev_team_b_names = [p.name for p in getattr(self, "schev_team_b", [])]

        data = {
            "finished": finished,
            "tournament_system": getattr(self, "tournament_system", None),
            "tiebreak_method": getattr(self, "tiebreak_method", None),
            "half_bye_enabled": getattr(self, "half_bye_enabled", False),
            "withdrawal_enabled": getattr(self, "withdrawal_enabled", False),
            "max_rounds": getattr(self, "max_rounds", None),
            "rating_mode": getattr(self, "rating_mode", None),
            "elo_submode": getattr(self, "elo_submode", None),
            "min_elo": getattr(self, "min_elo", None),
            "max_elo": getattr(self, "max_elo", None),
            "current_round": self.current_round,
            "tournament_start_time": timestamp,
            "schev_round": getattr(self, "schev_round", None),
            "schev_total_rounds": getattr(self, "schev_total_rounds", None),
            "scheveningen_team_size": getattr(self, "scheveningen_team_size", None),
            "round_robin_total_rounds": getattr(self, "round_robin_total_rounds", 0),
            "round_robin_player_order": [
                p.name for p in getattr(self, "round_robin_player_order", [])
            ],
            "schev_team_a_names": schev_team_a_names,
            "schev_team_b_names": schev_team_b_names,
            "schev_team_a_white_first": getattr(
                self, "schev_team_a_white_first", None
            ),
            # TRF16 starting ranks are assigned once, at tournament start,
            # by descending rating-at-start - never recomputed later, so
            # they must be saved rather than derived fresh on load (by
            # then, live ratings may have moved under automatic ELO mode).
            "trf_starting_rank_names": getattr(self, "trf_starting_rank_names", None),
            "players": players_data,
            "tournament_history": getattr(self, "tournament_history", []),
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save tournament:\n{e}")
            return None

    def _save_and_exit_tournament(self):
        """Save tournament as unfinished and return to main menu."""
        # Flush any pending half-bye / withdrawal checkbox states to player
        # objects BEFORE serialising, so they survive the save/resume cycle.
        self._flush_pending_round_requests()
        filename = self.save_tournament_to_file(finished=False)
        if filename:
            messagebox.showinfo(
                "Saved",
                f"Tournament saved to:\n{filename}\n\n"
                "You can resume it later via 'Load a Tournament'.",
            )
            self.in_game = False
            self.tournament_history = []
            self.show_initial_selection()

    def _save_finished_tournament(self):
        """Save a completed tournament to file.

        After writing the finished copy, check whether a corresponding
        _unfinished save still exists (left over from a previous
        'Save & Exit').  If it does, ask the director whether to delete it —
        keeping it would let the unfinished copy appear on the Load screen
        alongside the finished one, which is confusing.
        """
        filename = self.save_tournament_to_file(finished=True)
        if not filename:
            return

        # The finished filename ends with _finished.json; the unfinished
        # counterpart (if it exists) has the same prefix with _unfinished.json.
        unfinished_path = pathlib.Path(
            filename.replace("_finished.json", "_unfinished.json")
        )
        if unfinished_path.exists():
            keep_both = messagebox.askyesno(
                "Unfinished Copy Exists",
                f"An unfinished save of this tournament still exists:\n\n"
                f"  {unfinished_path.name}\n\n"
                "Would you like to keep both files?\n\n"
                "• Yes — keep both (the unfinished copy will still appear "
                "on the Load screen)\n"
                "• No  — delete the unfinished copy (recommended)",
            )
            if not keep_both:
                try:
                    unfinished_path.unlink()
                except OSError as exc:
                    messagebox.showwarning(
                        "Cleanup Failed",
                        f"Could not delete the unfinished copy:\n{exc}\n\n"
                        "You can delete it manually from the Load screen.",
                    )

        messagebox.showinfo("Saved", f"Tournament saved to:\n{filename}")

    def _build_players_from_save_data(self, data: dict) -> list:
        """Reconstruct full Player objects from a tournament save dict's
        "players" list. Shared by load_tournament_from_file (loading a
        tournament to keep working on) and the TRF16 exporter (which
        needs full Player objects too - e.g. for apply_tiebreak - even
        when exporting straight from a file the user hasn't opened)."""
        players = []
        for pd in data.get("players", []):
            player = Player(
                first_name=pd.get("first_name", ""),
                last_name=pd.get("last_name", ""),
                nickname=pd.get("nickname", ""),
                rating=pd.get("rating", 0),
                wins=pd.get("wins", 0),
                losses=pd.get("losses", 0),
                draws=pd.get("draws", 0),
                byes=pd.get("byes", 0),
                half_byes=pd.get("half_byes", 0),
            )
            player.eliminated = pd.get("eliminated", False)
            player.withdrawn = pd.get("withdrawn", False)
            player.withdrawal_round = pd.get("withdrawal_round")
            player.opponents = pd.get("opponents", [])
            # Old saves won't have this field. If it's missing or shorter
            # than `opponents` (e.g. partially-written old data), pad with
            # "" so the two lists stay the same length - apply_tiebreak
            # treats an empty/unknown result as contributing 0, rather
            # than crashing on a zip() length mismatch.
            results_vs_opponents = pd.get("results_vs_opponents", [])
            if len(results_vs_opponents) < len(player.opponents):
                results_vs_opponents = results_vs_opponents + [""] * (
                    len(player.opponents) - len(results_vs_opponents)
                )
            player.results_vs_opponents = results_vs_opponents
            # Old saves won't have this either; pad the same way. A
            # missing/unrecognised entry is treated as "no colour info"
            # for that game by every consumer (_color_preference etc.),
            # rather than crashing or silently miscounting.
            colors = pd.get("colors", [])
            if len(colors) < len(player.opponents):
                colors = colors + [None] * (len(player.opponents) - len(colors))
            player.colors = colors
            player.requested_half_bye = pd.get("requested_half_bye", False)
            player.sex = pd.get("sex")
            player.title = pd.get("title")
            player.fide_federation = pd.get("fide_federation")
            player.fide_id = pd.get("fide_id")
            player.birth_date = pd.get("birth_date")
            player.initial_rating = pd.get("initial_rating")
            players.append(player)
        return players

    def load_tournament_from_file(self, filepath: str) -> bool:
        """Load a saved tournament file and restore all state.
        Returns True on success, False on failure."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not read file:\n{e}")
            return False

        # Restore settings
        self.tournament_system = data.get("tournament_system")
        self.tiebreak_method = data.get("tiebreak_method")
        self.half_bye_enabled = data.get("half_bye_enabled", False)
        self.withdrawal_enabled = data.get("withdrawal_enabled", False)
        self.max_rounds = data.get("max_rounds")
        self.rating_mode = data.get("rating_mode", "unranked")
        self.elo_submode = data.get("elo_submode")
        self.min_elo = data.get("min_elo")
        self.max_elo = data.get("max_elo")
        self.current_round = data.get("current_round", 1)
        self.tournament_start_time = data.get("tournament_start_time")
        self.sort_mode = "tournament"
        self.game_type = "chess"
        self.in_game = True
        self.tournament_history = data.get("tournament_history", [])

        # Restore scheveningen state
        self.schev_round = data.get("schev_round") or 0
        self.schev_total_rounds = data.get("schev_total_rounds") or 0
        self.scheveningen_team_size = data.get("scheveningen_team_size") or 0
        self.schev_team_a_white_first = data.get("schev_team_a_white_first")

        # Restore round-robin stable round count (0 means "not set / old save")
        self.round_robin_total_rounds = data.get("round_robin_total_rounds") or 0
        # The colour plan is deterministic from order + total_rounds, so it's
        # cheap and safest to just recompute it lazily rather than trust
        # anything left over in memory from a different tournament.
        self.round_robin_color_plan = None

        # TRF16 starting ranks, assigned once at tournament start by
        # descending rating-at-start (see _compute_trf_starting_ranks) -
        # restored as-is rather than recomputed, since current ratings
        # may have since moved under automatic ELO mode.
        self.trf_starting_rank_names = data.get("trf_starting_rank_names")

        # Restore players
        self.players = self._build_players_from_save_data(data)
        # name -> list of Player objects with that name, in save order. A
        # list (not a single Player) because older or hand-edited save
        # files might contain duplicate names; keeping all candidates lets
        # the team-reconstruction step below consume them one at a time
        # instead of one duplicate silently overwriting another.
        player_map = {}
        for player in self.players:
            player_map.setdefault(player.name, []).append(player)

        # Restore scheveningen teams (by matching saved names to Player
        # objects). Always initialise both lists so schev screens never
        # hit AttributeError.
        #
        # Each name is popped from its candidates list as it's used, so a
        # save file with duplicate player names can't make the same
        # Player object end up on both teams (or silently drop one of the
        # duplicates) - each saved name slot resolves to a distinct
        # player, in the order they were originally saved.
        schev_a_names = data.get("schev_team_a_names", [])
        schev_b_names = data.get("schev_team_b_names", [])
        self.schev_team_a = []
        self.schev_team_b = []
        if schev_a_names:
            for n in schev_a_names:
                candidates = player_map.get(n)
                if candidates:
                    self.schev_team_a.append(candidates.pop(0))
            for n in schev_b_names:
                candidates = player_map.get(n)
                if candidates:
                    self.schev_team_b.append(candidates.pop(0))

        # Restore the fixed round-robin rotation order (see
        # generate_round_robin_pairings for why this must stay stable
        # across rounds/half-byes/withdrawals). Old saves won't have it;
        # generate_round_robin_pairings already has a fallback for that.
        rr_order_names = data.get("round_robin_player_order", [])
        if rr_order_names:
            rr_player_map = {}
            for p in self.players:
                rr_player_map.setdefault(p.name, []).append(p)
            self.round_robin_player_order = []
            for n in rr_order_names:
                candidates = rr_player_map.get(n)
                if candidates:
                    self.round_robin_player_order.append(candidates.pop(0))

        return True

    def start_game(self):
        """Start the game based on mode"""
        if not self.players:
            messagebox.showwarning("No Players", "Please add at least one player")
            return

        # Show rating mode selection for non-tournament modes
        if self.sort_mode in ["dual", "battle_royale", "teams"]:
            self.show_simple_rating_mode_selection()
        elif self.sort_mode == "tournament":
            self.start_tournament()

    def show_simple_rating_mode_selection(self):
        """Show simplified rating mode selection for non-tournament modes"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        mode_name = self.sort_mode.replace("_", " ").title()
        title = ttk.Label(
            frame, text=f"{mode_name} - Rating Settings", font=("Arial", 16, "bold")
        )
        title.pack(pady=20)

        # Rating mode selection
        rating_frame = ttk.LabelFrame(frame, text="Rating Changes", padding="20")
        rating_frame.pack(pady=20, padx=40, fill=tk.X)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        if self.game_type == "chess":
            ttk.Label(
                rating_frame,
                text=f"How should {rating_name} ratings change after games?",
                font=("Arial", 11, "bold"),
            ).pack(pady=10)

            self.rating_mode_var = tk.StringVar(value="unranked")

            # Automatic ELO relies on the standard expected-score formula
            # comparing one player's rating directly against a specific
            # opponent's - it requires paired win/loss results. Dual mode
            # has that (each match is p1 vs p2). Battle Royale and Teams
            # only record raw win/loss/draw counts per player with no
            # "against whom", so there's no valid opponent rating to plug
            # into the formula - Automatic is intentionally unavailable
            # there, not just hidden by omission.
            if self.sort_mode == "dual":
                ttk.Radiobutton(
                    rating_frame,
                    text="Automatic - Online/OTB (balanced changes, K=32)",
                    variable=self.rating_mode_var,
                    value="automatic_otb",
                ).pack(anchor=tk.W, pady=5, padx=20)
                ttk.Radiobutton(
                    rating_frame,
                    text="Automatic - Daily/Correspondence (harsher changes, K=48)",
                    variable=self.rating_mode_var,
                    value="automatic_correspondence",
                ).pack(anchor=tk.W, pady=5, padx=20)

            ttk.Radiobutton(
                rating_frame,
                text="Manual - Manually update ELO after each round",
                variable=self.rating_mode_var,
                value="manual",
            ).pack(anchor=tk.W, pady=5, padx=20)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No ELO changes",
                variable=self.rating_mode_var,
                value="unranked",
            ).pack(anchor=tk.W, pady=5, padx=20)
        else:  # esports
            ttk.Label(
                rating_frame,
                text=f"Should {rating_name} ratings be updated?",
                font=("Arial", 11, "bold"),
            ).pack(pady=10)

            self.rating_mode_var = tk.StringVar(value="unranked")

            ttk.Radiobutton(
                rating_frame,
                text="Ranked - Manually update trophies after each round",
                variable=self.rating_mode_var,
                value="ranked",
            ).pack(anchor=tk.W, pady=5, padx=20)
            ttk.Radiobutton(
                rating_frame,
                text="Unranked - No trophy changes",
                variable=self.rating_mode_var,
                value="unranked",
            ).pack(anchor=tk.W, pady=5, padx=20)

        # Max Rounds input for Dual and Teams mode
        if self.sort_mode in ["dual", "teams"]:
            rounds_frame = ttk.LabelFrame(frame, text="Tournament Length", padding="15")
            rounds_frame.pack(pady=10, padx=40, fill=tk.X)

            ttk.Label(
                rounds_frame,
                text="Set maximum number of rounds (optional):",
                font=("Arial", 10),
            ).pack(pady=5)

            rounds_input_frame = ttk.Frame(rounds_frame)
            rounds_input_frame.pack(pady=5)

            self.max_rounds_var = tk.StringVar(value="")
            ttk.Label(rounds_input_frame, text="Rounds:").pack(side=tk.LEFT, padx=5)
            ttk.Entry(
                rounds_input_frame, textvariable=self.max_rounds_var, width=10
            ).pack(side=tk.LEFT, padx=5)
            ttk.Label(
                rounds_input_frame,
                text="(leave empty for unlimited)",
                font=("Arial", 9, "italic"),
            ).pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back", command=self.show_player_input).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame, text="Start", command=self.confirm_simple_rating_mode
        ).pack(side=tk.LEFT, padx=5)

    def confirm_simple_rating_mode(self):
        """Confirm rating mode and start the appropriate game mode"""
        rating_mode_value = self.rating_mode_var.get()

        # Parse rating mode and sub-mode
        if rating_mode_value == "automatic_otb":
            self.rating_mode = "automatic"
            self.elo_submode = "otb"
        elif rating_mode_value == "automatic_correspondence":
            self.rating_mode = "automatic"
            self.elo_submode = "correspondence"
        else:
            self.rating_mode = rating_mode_value
            self.elo_submode = None

        # Parse max rounds if available (Dual mode)
        if hasattr(self, "max_rounds_var"):
            max_rounds_str = self.max_rounds_var.get().strip()
            if max_rounds_str:
                try:
                    self.max_rounds = int(max_rounds_str)
                    if self.max_rounds < 1:
                        messagebox.showwarning(
                            "Invalid Input", "Maximum rounds must be at least 1"
                        )
                        return
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Input", "Maximum rounds must be a number"
                    )
                    return
            else:
                self.max_rounds = None
        else:
            self.max_rounds = None

        self.in_game = True
        self.current_round = 1

        if self.sort_mode == "dual":
            if len(self.players) < 2:
                messagebox.showwarning(
                    "Not Enough Players", "Need at least 2 players for dual mode"
                )
                self.in_game = False  # Roll back — no game was actually started
                return
            self._reset_players_for_new_session()
            self.show_dual_game()
        elif self.sort_mode == "battle_royale":
            if len(self.players) < 4:
                messagebox.showwarning(
                    "Not Enough Players", "Need at least 4 players for battle royale"
                )
                self.in_game = False  # Roll back — no game was actually started
                return
            self._reset_players_for_new_session()
            self.show_battle_royale_game()
        elif self.sort_mode == "teams":
            if len(self.players) < 2:
                messagebox.showwarning(
                    "Not Enough Players", "Need at least 2 players for team mode"
                )
                self.in_game = False  # Roll back — no game was actually started
                return
            self._reset_players_for_new_session()
            self.show_team_configuration()

    def show_dual_game(self):
        """Show dual mode game interface with pairings and result tracking"""
        # Sort players by rating and win rate with randomness
        active_players = [p for p in self.players if not p.eliminated]
        random.shuffle(active_players)
        # Consider both rating and win rate in sorting
        active_players.sort(
            key=lambda p: (
                (p.rating * 0.6 + p.win_rate * 10 * 0.4) + random.randint(-50, 50)
            ),
            reverse=True,
        )

        # Create pairs
        pairs = []
        while len(active_players) >= 2:
            player1 = active_players.pop(0)
            player2 = active_players.pop(0)
            pairs.append([player1, player2, None])  # [p1, p2, result]

        leftover = active_players[0] if active_players else None

        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame,
            text=f"Dual Mode - Round {self.current_round}",
            font=("Arial", 18, "bold"),
        )
        title.pack(pady=10)

        # Results frame with scrollbar
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(results_frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        # Store result variables
        self.dual_results = []

        for i, pair in enumerate(pairs):
            p1, p2 = pair[0], pair[1]
            pair_frame = ttk.LabelFrame(
                scrollable_frame, text=f"Match {i + 1}", padding="10"
            )
            pair_frame.pack(fill=tk.X, padx=5, pady=5)

            # Player 1
            p1_label = f"{p1.name} ({rating_name}: {p1.rating}, WR: {p1.win_rate:.1f}%)"
            ttk.Label(pair_frame, text=p1_label, font=("Arial", 10)).grid(
                row=0, column=0, sticky=tk.W, padx=5
            )

            # VS
            ttk.Label(pair_frame, text="vs", font=("Arial", 10, "italic")).grid(
                row=0, column=1, padx=10
            )

            # Player 2
            p2_label = f"{p2.name} ({rating_name}: {p2.rating}, WR: {p2.win_rate:.1f}%)"
            ttk.Label(pair_frame, text=p2_label, font=("Arial", 10)).grid(
                row=0, column=2, sticky=tk.W, padx=5
            )

            # Result buttons
            result_var = tk.StringVar(value="")
            self.dual_results.append((pair, result_var))

            result_frame = ttk.Frame(pair_frame)
            result_frame.grid(row=1, column=0, columnspan=3, pady=5)

            ttk.Radiobutton(
                result_frame,
                text=f"{p1.name} Wins",
                variable=result_var,
                value="p1_win",
            ).pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(
                result_frame, text="Draw", variable=result_var, value="draw"
            ).pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(
                result_frame,
                text=f"{p2.name} Wins",
                variable=result_var,
                value="p2_win",
            ).pack(side=tk.LEFT, padx=5)

        if leftover:
            leftover_frame = ttk.LabelFrame(
                scrollable_frame, text="Bye (1 point)", padding="10"
            )
            leftover_frame.pack(fill=tk.X, padx=5, pady=5)
            ttk.Label(
                leftover_frame,
                text=(
                    f"{leftover.name} ({rating_name}: {leftover.rating}, "
                    f"WR: {leftover.win_rate:.1f}%)"
                ),
                font=("Arial", 10),
            ).pack(anchor=tk.W)
            # Bye round counts as 1 full point
            self.dual_results.append(
                ([leftover, None, "bye"], tk.StringVar(value="bye"))
            )

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Finish Round", command=self.finish_dual_round).pack(
            side=tk.LEFT, padx=5
        )

    def finish_dual_round(self):
        """Process dual round results and show standings"""
        # Check all matches have results
        for pair, result_var in self.dual_results:
            if result_var.get() == "" or result_var.get() not in [
                "p1_win",
                "p2_win",
                "draw",
                "bye",
                "half_bye",
            ]:
                messagebox.showwarning(
                    "Incomplete", "Please set results for all matches"
                )
                return

        # Store results for rating calculation
        self.tournament_results = self.dual_results

        # Apply results
        for pair, result_var in self.dual_results:
            result = result_var.get()
            if result == "bye":
                pair[0].byes += 1  # Bye = 1 full point
            elif result == "p1_win":
                pair[0].wins += 1
                pair[1].losses += 1
                pair[0].opponents.append(pair[1].name)
                pair[1].opponents.append(pair[0].name)
                pair[0].results_vs_opponents.append("win")
                pair[1].results_vs_opponents.append("loss")
            elif result == "p2_win":
                pair[1].wins += 1
                pair[0].losses += 1
                pair[0].opponents.append(pair[1].name)
                pair[1].opponents.append(pair[0].name)
                pair[0].results_vs_opponents.append("loss")
                pair[1].results_vs_opponents.append("win")
            elif result == "draw":
                pair[0].draws += 1
                pair[1].draws += 1
                pair[0].opponents.append(pair[1].name)
                pair[1].opponents.append(pair[0].name)
                pair[0].results_vs_opponents.append("draw")
                pair[1].results_vs_opponents.append("draw")

        # Apply rating changes based on mode
        if self.rating_mode == "automatic" and self.game_type == "chess":
            self.apply_automatic_elo_changes()
            self.show_dual_standings()
        elif self.rating_mode == "manual" or (
            self.rating_mode == "ranked" and self.game_type == "esports"
        ):
            self.show_manual_rating_update(self.show_dual_standings)
        else:
            self.show_dual_standings()

    def show_dual_standings(self):
        """Show current standings after dual round"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame,
            text=f"Dual Mode - Standings After Round {self.current_round}",
            font=("Arial", 18, "bold"),
        )
        title.pack(pady=10)

        # Sort by win rate
        active_players = [p for p in self.players if not p.eliminated]
        sorted_players = sorted(active_players, key=lambda p: p.win_rate, reverse=True)

        # Results table
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=[
                "rank",
                "name",
                "rating",
                "wins",
                "losses",
                "draws",
                "byes",
                "hbyes",
                "winrate",
            ],
            show="headings",
            height=15,
        )

        tree.heading("rank", text="Rank")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO" if self.game_type == "chess" else "Trophies")
        tree.heading("wins", text="W")
        tree.heading("losses", text="L")
        tree.heading("draws", text="D")
        tree.heading("byes", text="Bye")
        tree.heading("hbyes", text="½Bye")
        tree.heading("winrate", text="Win Rate %")

        tree.column("rank", width=45)
        tree.column("name", width=115)
        tree.column("rating", width=65)
        tree.column("wins", width=35)
        tree.column("losses", width=35)
        tree.column("draws", width=35)
        tree.column("byes", width=35)
        tree.column("hbyes", width=40)
        tree.column("winrate", width=85)

        for i, player in enumerate(sorted_players, 1):
            tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    player.name,
                    player.rating,
                    player.wins,
                    player.losses,
                    player.draws,
                    player.byes,
                    player.half_byes,
                    f"{player.win_rate:.1f}%",
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )

        # Check if max rounds reached
        if self.max_rounds and self.current_round >= self.max_rounds:
            # Max rounds reached - auto finish
            ttk.Button(
                btn_frame,
                text="View Final Standings",
                command=self.show_dual_final_standings,
            ).pack(side=tk.LEFT, padx=5)
        else:
            # Can continue
            ttk.Button(btn_frame, text="Next Round", command=self.next_dual_round).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(
                btn_frame,
                text="Finish Tournament",
                command=self.show_dual_final_standings,
            ).pack(side=tk.LEFT, padx=5)

    def show_dual_final_standings(self):
        """Show final standings for dual mode"""
        # Auto-save players when tournament ends
        self.auto_save_players()

        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame, text="Dual Mode - Final Standings", font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        # Sort by win rate
        active_players = [p for p in self.players if not p.eliminated]
        sorted_players = sorted(active_players, key=lambda p: p.win_rate, reverse=True)

        # Show winner
        if sorted_players:
            winner = sorted_players[0]
            ttk.Label(
                frame, text=f"🏆 Winner: {winner.name} 🏆", font=("Arial", 16, "bold")
            ).pack(pady=10)

        # Results table
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=[
                "rank",
                "name",
                "rating",
                "wins",
                "losses",
                "draws",
                "byes",
                "hbyes",
                "winrate",
            ],
            show="headings",
            height=15,
        )

        tree.heading("rank", text="Rank")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO" if self.game_type == "chess" else "Trophies")
        tree.heading("wins", text="W")
        tree.heading("losses", text="L")
        tree.heading("draws", text="D")
        tree.heading("byes", text="Bye")
        tree.heading("hbyes", text="½Bye")
        tree.heading("winrate", text="Win Rate %")

        tree.column("rank", width=45)
        tree.column("name", width=115)
        tree.column("rating", width=65)
        tree.column("wins", width=35)
        tree.column("losses", width=35)
        tree.column("draws", width=35)
        tree.column("byes", width=35)
        tree.column("hbyes", width=40)
        tree.column("winrate", width=85)

        for i, player in enumerate(sorted_players, 1):
            tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    player.name,
                    player.rating,
                    player.wins,
                    player.losses,
                    player.draws,
                    player.byes,
                    player.half_byes,
                    f"{player.win_rate:.1f}%",
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button
        ttk.Button(frame, text="← Back to Setup", command=self.back_to_setup).pack(
            pady=10
        )

    def next_dual_round(self):
        """Start next dual round"""
        self.current_round += 1
        self.show_dual_game()

    def show_battle_royale_game(self):
        """Show battle royale game interface with win/loss/draw tracking"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        active_players = [p for p in self.players if not p.eliminated]
        title = ttk.Label(
            frame,
            text=(
                f"Battle Royale - Round {self.current_round} "
                f"({len(active_players)} players remaining)"
            ),
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        # Instructions
        ttk.Label(
            frame,
            text="Add wins, losses, or draws for each player, then finish the round.",
            font=("Arial", 10),
        ).pack(pady=5)
        ttk.Label(
            frame,
            text="Bottom 3 players will be eliminated after each round.",
            font=("Arial", 9, "italic"),
        ).pack(pady=2)

        # Player table with action buttons
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create tree with columns
        columns = ["name", "rating", "wins", "losses", "draws", "winrate", "actions"]
        self.br_tree = ttk.Treeview(
            table_frame, columns=columns[:-1], show="headings", height=12
        )

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"
        self.br_tree.heading("name", text="Name")
        self.br_tree.heading("rating", text=rating_name)
        self.br_tree.heading("wins", text="Wins")
        self.br_tree.heading("losses", text="Losses")
        self.br_tree.heading("draws", text="Draws")
        self.br_tree.heading("winrate", text="Win Rate %")

        self.br_tree.column("name", width=150)
        self.br_tree.column("rating", width=80)
        self.br_tree.column("wins", width=60)
        self.br_tree.column("losses", width=60)
        self.br_tree.column("draws", width=60)
        self.br_tree.column("winrate", width=100)

        # Sort by current win rate
        active_players.sort(key=lambda p: p.win_rate, reverse=True)

        for player in active_players:
            self.br_tree.insert(
                "",
                tk.END,
                values=(
                    player.name,
                    player.rating,
                    player.wins,
                    player.losses,
                    player.draws,
                    f"{player.win_rate:.1f}%",
                ),
            )

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.br_tree.yview
        )
        self.br_tree.configure(yscroll=scrollbar.set)

        self.br_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons for selected player
        action_frame = ttk.LabelFrame(
            frame, text="Add Result for Selected Player", padding="10"
        )
        action_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            action_frame, text="+ Win", command=lambda: self.add_br_result("win")
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            action_frame, text="+ Loss", command=lambda: self.add_br_result("loss")
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            action_frame, text="+ Draw", command=lambda: self.add_br_result("draw")
        ).pack(side=tk.LEFT, padx=5)

        # Control buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Finish Round", command=self.finish_br_round).pack(
            side=tk.LEFT, padx=5
        )

    def add_br_result(self, result_type: str):
        """Add a win/loss/draw to selected player in battle royale"""
        selected = self.br_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a player")
            return

        index = self.br_tree.index(selected[0])
        active_players = [p for p in self.players if not p.eliminated]
        active_players.sort(key=lambda p: p.win_rate, reverse=True)

        player = active_players[index]

        if result_type == "win":
            player.wins += 1
        elif result_type == "loss":
            player.losses += 1
        elif result_type == "draw":
            player.draws += 1

        # Refresh display
        self.show_battle_royale_game()

    def finish_br_round(self):
        """Finish battle royale round and eliminate bottom 3 players"""

        def _do_eliminations():
            active_players = [p for p in self.players if not p.eliminated]

            # Check if game should end
            if len(active_players) <= 1:
                self.show_br_winner()
                return

            # Sort by win rate
            active_players.sort(key=lambda p: p.win_rate, reverse=True)

            # Eliminate bottom 3 (or fewer if not enough players)
            num_to_eliminate = min(3, len(active_players) - 1)

            if len(active_players) <= 3:
                # Final round - eliminate all but winner
                for player in active_players[1:]:
                    player.eliminated = True
                self.show_br_winner()
            else:
                # Eliminate bottom 3
                for i in range(num_to_eliminate):
                    active_players[-(i + 1)].eliminated = True

                # Show elimination results
                self.show_br_elimination(active_players[-num_to_eliminate:])

        # Manual rating updates (chess "manual" / e-sports "ranked") happen
        # before eliminations are computed, same ordering as every other
        # mode's round-finish flow. Automatic ELO never applies here (see
        # show_simple_rating_mode_selection and apply_automatic_elo_changes)
        # since Battle Royale has no paired opponent to compute it against.
        if self.rating_mode == "manual" or (
            self.rating_mode == "ranked" and self.game_type == "esports"
        ):
            self.show_manual_rating_update(_do_eliminations)
        else:
            _do_eliminations()

    def show_br_elimination(self, eliminated_players: List[Player]):
        """Show which players were eliminated"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame,
            text=f"Round {self.current_round} - Eliminations",
            font=("Arial", 18, "bold"),
        )
        title.pack(pady=20)

        # Eliminated players
        elim_frame = ttk.LabelFrame(frame, text="Eliminated Players", padding="20")
        elim_frame.pack(pady=20)

        for player in eliminated_players:
            ttk.Label(
                elim_frame,
                text=f"❌ {player.name} (Win Rate: {player.win_rate:.1f}%)",
                font=("Arial", 12),
            ).pack(pady=5)

        # Remaining count
        remaining = len([p for p in self.players if not p.eliminated])
        ttk.Label(
            frame, text=f"{remaining} players remaining", font=("Arial", 11)
        ).pack(pady=10)

        # Button
        ttk.Button(
            frame, text="Continue to Next Round", command=self.next_br_round
        ).pack(pady=20)

    def next_br_round(self):
        """Start next battle royale round.

        finish_br_round's general elimination branch (more than 3 active
        players at the start of the round) always removes exactly the
        bottom 3, which can leave exactly 1 player standing whenever the
        round started with exactly 4. That case was falling through to
        another game round with a single player and nobody to record a
        result against - a dead round the user still had to click through
        before finally reaching the winner screen. Checking here, right
        before dispatching to the next round, catches it regardless of
        which elimination branch produced the 1-remaining state.
        """
        active_players = [p for p in self.players if not p.eliminated]
        if len(active_players) <= 1:
            self.show_br_winner()
            return
        self.current_round += 1
        self.show_battle_royale_game()

    def show_br_winner(self):
        """Show battle royale winner"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        active_players = [p for p in self.players if not p.eliminated]
        if not active_players:
            active_players = sorted(
                self.players, key=lambda p: p.win_rate, reverse=True
            )[:1]

        winner = active_players[0]

        # Title
        ttk.Label(frame, text="🏆 WINNER! 🏆", font=("Arial", 24, "bold")).pack(pady=20)

        # Winner info
        winner_frame = ttk.LabelFrame(frame, text="Champion", padding="20")
        winner_frame.pack(pady=20)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"
        ttk.Label(winner_frame, text=winner.name, font=("Arial", 20, "bold")).pack(
            pady=10
        )
        ttk.Label(
            winner_frame, text=f"{rating_name}: {winner.rating}", font=("Arial", 14)
        ).pack(pady=5)
        ttk.Label(
            winner_frame, text=f"Win Rate: {winner.win_rate:.1f}%", font=("Arial", 14)
        ).pack(pady=5)

        record = f"Record: {winner.wins}W - {winner.losses}L - {winner.draws}D"
        if winner.byes > 0:
            record += f" - {winner.byes}Bye"
        if winner.half_byes > 0:
            record += f" - {winner.half_byes}½Bye"

        ttk.Label(winner_frame, text=record, font=("Arial", 12)).pack(pady=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame, text="View Final Standings", command=self.show_br_final_standings
        ).pack(side=tk.LEFT, padx=5)

    def show_br_final_standings(self):
        """Show final standings for battle royale"""
        # Auto-save players when tournament ends
        self.auto_save_players()

        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            frame, text="Battle Royale - Final Standings", font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        # Sort all players by win rate
        sorted_players = sorted(self.players, key=lambda p: p.win_rate, reverse=True)

        # The actual winner is whoever is NOT eliminated - the same check
        # show_br_winner() uses. This can legitimately differ from "the
        # player with the single highest win rate": elimination is
        # relative to each round's active pool, so a player eliminated
        # early after a couple of good games can end up with a higher
        # final win rate than the player who actually won the whole
        # event. Re-deriving "winner" from win-rate sort position here
        # (as this used to do) could then label the WRONG player as
        # Winner, disagreeing with the winner screen the player just came
        # from.
        not_eliminated = [p for p in self.players if not p.eliminated]
        if len(not_eliminated) == 1:
            actual_winner = not_eliminated[0]
        elif sorted_players:
            # Degenerate fallback (shouldn't normally happen): mirror
            # show_br_winner()'s own fallback so the two screens always
            # agree on who's labelled the winner.
            actual_winner = sorted_players[0]
        else:
            actual_winner = None

        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=[
                "rank",
                "name",
                "rating",
                "wins",
                "losses",
                "draws",
                "byes",
                "hbyes",
                "winrate",
                "status",
            ],
            show="headings",
            height=15,
        )

        tree.heading("rank", text="Rank")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO" if self.game_type == "chess" else "Trophies")
        tree.heading("wins", text="W")
        tree.heading("losses", text="L")
        tree.heading("draws", text="D")
        tree.heading("byes", text="Bye")
        tree.heading("hbyes", text="½Bye")
        tree.heading("winrate", text="Win Rate %")
        tree.heading("status", text="Status")

        tree.column("rank", width=45)
        tree.column("name", width=110)
        tree.column("rating", width=60)
        tree.column("wins", width=35)
        tree.column("losses", width=35)
        tree.column("draws", width=35)
        tree.column("byes", width=35)
        tree.column("hbyes", width=40)
        tree.column("winrate", width=85)
        tree.column("status", width=85)

        for i, player in enumerate(sorted_players, 1):
            status = (
                "🏆 Winner"
                if player is actual_winner
                else ("❌ Eliminated" if player.eliminated else "Active")
            )
            tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    player.name,
                    player.rating,
                    player.wins,
                    player.losses,
                    player.draws,
                    player.byes,
                    player.half_byes,
                    f"{player.win_rate:.1f}%",
                    status,
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(frame, text="← Back to Setup", command=self.back_to_setup).pack(
            pady=10
        )

    def show_team_configuration(self):
        """Show team configuration dialog"""
        if len(self.players) < 2:
            messagebox.showwarning(
                "Not Enough Players", "Need at least 2 players for team mode"
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Team Configuration")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(expand=True)

        ttk.Label(frame, text="Number of Teams:", font=("Arial", 11)).pack(pady=10)

        num_teams_var = tk.IntVar(value=2)
        spinbox = ttk.Spinbox(
            frame,
            from_=2,
            to=min(10, len(self.players)),
            textvariable=num_teams_var,
            width=10,
        )
        spinbox.pack(pady=10)

        def create_teams():
            num_teams = num_teams_var.get()
            if num_teams < 2:
                messagebox.showwarning("Invalid Input", "Need at least 2 teams")
                return
            if num_teams > len(self.players):
                messagebox.showwarning(
                    "Invalid Input",
                    f"Cannot create {num_teams} teams with {len(self.players)} players",
                )
                return

            dialog.destroy()
            self.teams = self.balance_teams(num_teams)
            self.in_game = True
            self.current_round = 1
            self.show_team_game()

        ttk.Button(frame, text="Create Teams", command=create_teams).pack(pady=10)

    def show_team_game(self):
        """Show team game interface with win/loss/draw tracking"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame,
            text=f"Teams Mode - Round {self.current_round}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        # Instructions
        ttk.Label(
            frame,
            text="Add wins, losses, or draws for each player, then finish the round.",
            font=("Arial", 10),
        ).pack(pady=5)

        # Teams display with player stats
        teams_frame = ttk.Frame(frame)
        teams_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(teams_frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(teams_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        for i, team in enumerate(self.teams, 1):
            avg_rating = sum(p.rating for p in team) / len(team) if team else 0
            # Average per-player win rate, not the sum - summing percentages
            # would reward a team purely for having more players, regardless
            # of whether those extra players are actually any good.
            avg_winrate = sum(p.win_rate for p in team) / len(team) if team else 0

            team_frame = ttk.LabelFrame(
                scrollable_frame,
                text=(
                    f"Team {i} (Avg {rating_name}: {avg_rating:.1f}, "
                    f"Avg WR: {avg_winrate:.1f}%)"
                ),
                padding="10",
            )
            team_frame.pack(fill=tk.X, padx=5, pady=5)

            for player in team:
                player_frame = ttk.Frame(team_frame)
                player_frame.pack(fill=tk.X, pady=2)

                # Player info
                info_text = (
                    f"{player.name} ({rating_name}: {player.rating}, "
                    f"WR: {player.win_rate:.1f}%)"
                )
                ttk.Label(
                    player_frame, text=info_text, font=("Arial", 9), width=40
                ).pack(side=tk.LEFT)

                # Action buttons
                btn_frame = ttk.Frame(player_frame)
                btn_frame.pack(side=tk.RIGHT)

                ttk.Button(
                    btn_frame,
                    text="+W",
                    width=3,
                    command=lambda p=player: self.add_team_result(p, "win"),
                ).pack(side=tk.LEFT, padx=1)
                ttk.Button(
                    btn_frame,
                    text="+L",
                    width=3,
                    command=lambda p=player: self.add_team_result(p, "loss"),
                ).pack(side=tk.LEFT, padx=1)
                ttk.Button(
                    btn_frame,
                    text="+D",
                    width=3,
                    command=lambda p=player: self.add_team_result(p, "draw"),
                ).pack(side=tk.LEFT, padx=1)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Finish Round", command=self.finish_team_round).pack(
            side=tk.LEFT, padx=5
        )

    def add_team_result(self, player: Player, result_type: str):
        """Add a win/loss/draw to a player in team mode"""
        if result_type == "win":
            player.wins += 1
        elif result_type == "loss":
            player.losses += 1
        elif result_type == "draw":
            player.draws += 1

        # Refresh display
        self.show_team_game()

    def finish_team_round(self):
        """Finish team round and show standings with MVPs"""
        # Manual rating updates (chess "manual" / e-sports "ranked"), same
        # as every other mode. Automatic ELO never applies here since Teams
        # has no paired opponent to compute it against.
        if self.rating_mode == "manual" or (
            self.rating_mode == "ranked" and self.game_type == "esports"
        ):
            self.show_manual_rating_update(self.show_team_standings)
        else:
            self.show_team_standings()

    def show_team_standings(self):
        """Show team standings with MVPs after a round"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame,
            text=f"Teams Mode - Standings After Round {self.current_round}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        # Calculate team statistics and sort
        team_stats = []
        for i, team in enumerate(self.teams, 1):
            # Average per-player win rate, not the sum - see show_team_game
            # for why summing percentages would unfairly favor larger teams.
            avg_winrate = sum(p.win_rate for p in team) / len(team) if team else 0
            avg_rating = sum(p.rating for p in team) / len(team) if team else 0
            mvp = max(team, key=lambda p: p.win_rate) if team else None
            team_stats.append((i, team, avg_winrate, avg_rating, mvp))

        # Sort by average win rate per player
        team_stats.sort(key=lambda x: x[2], reverse=True)

        # Display teams
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(results_frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        for rank, (team_num, team, avg_wr, avg_rating, mvp) in enumerate(
            team_stats, 1
        ):
            team_frame = ttk.LabelFrame(
                scrollable_frame,
                text=(
                    f"#{rank} - Team {team_num} (Avg WR: {avg_wr:.1f}%, "
                    f"Avg {rating_name}: {avg_rating:.1f})"
                ),
                padding="10",
            )
            team_frame.pack(fill=tk.X, padx=5, pady=5)

            # MVP
            if mvp:
                mvp_frame = ttk.Frame(team_frame)
                mvp_frame.pack(fill=tk.X, pady=5)
                ttk.Label(mvp_frame, text="🏅 MVP:", font=("Arial", 10, "bold")).pack(
                    side=tk.LEFT
                )
                ttk.Label(
                    mvp_frame,
                    text=f"{mvp.name} (WR: {mvp.win_rate:.1f}%)",
                    font=("Arial", 10),
                ).pack(side=tk.LEFT, padx=5)

            # Players
            for player in sorted(team, key=lambda p: p.win_rate, reverse=True):
                player_text = (
                    f"  • {player.name} - {rating_name}: {player.rating}, "
                    f"WR: {player.win_rate:.1f}% "
                    f"({player.wins}W-{player.losses}L-{player.draws}D)"
                )
                ttk.Label(team_frame, text=player_text, font=("Arial", 9)).pack(
                    anchor=tk.W, pady=1
                )

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )

        # Check if max rounds reached
        if self.max_rounds and self.current_round >= self.max_rounds:
            # Max rounds reached - auto finish
            ttk.Button(
                btn_frame,
                text="View Final Standings",
                command=self.show_team_final_standings,
            ).pack(side=tk.LEFT, padx=5)
        else:
            # Can continue
            ttk.Button(btn_frame, text="Next Round", command=self.next_team_round).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(
                btn_frame,
                text="Finish Tournament",
                command=self.show_team_final_standings,
            ).pack(side=tk.LEFT, padx=5)

    def show_team_final_standings(self):
        """Show final team standings"""
        # Auto-save players when tournament ends
        self.auto_save_players()

        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame, text="Teams Mode - Final Standings", font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        # Calculate team statistics and sort
        team_stats = []
        for i, team in enumerate(self.teams, 1):
            # Average per-player win rate, not the sum. Teams here are
            # often different sizes (balance_teams balances by total
            # rating, not headcount), and summing percentages would crown
            # whichever team happens to have more players as "winning"
            # even if its players are individually weaker - this is the
            # actual winner determination for the whole event, so this is
            # the most consequential of the three Total-WR -> Avg-WR
            # fixes in this file.
            avg_winrate = sum(p.win_rate for p in team) / len(team) if team else 0
            avg_rating = sum(p.rating for p in team) / len(team) if team else 0
            mvp = max(team, key=lambda p: p.win_rate) if team else None
            team_stats.append((i, team, avg_winrate, avg_rating, mvp))

        # Sort by average win rate per player
        team_stats.sort(key=lambda x: x[2], reverse=True)

        # Show winner
        if team_stats:
            winning_team = team_stats[0]
            ttk.Label(
                frame,
                text=f"🏆 Winning Team: Team {winning_team[0]} 🏆",
                font=("Arial", 16, "bold"),
            ).pack(pady=10)

        # Display teams
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(results_frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        for rank, (team_num, team, avg_wr, avg_rating, mvp) in enumerate(
            team_stats, 1
        ):
            team_frame = ttk.LabelFrame(
                scrollable_frame,
                text=(
                    f"#{rank} - Team {team_num} "
                    f"(Avg WR: {avg_wr:.1f}%, Avg {rating_name}: {avg_rating:.1f})"
                ),
                padding="10",
            )
            team_frame.pack(fill=tk.X, padx=5, pady=5)

            # MVP
            if mvp:
                mvp_frame = ttk.Frame(team_frame)
                mvp_frame.pack(fill=tk.X, pady=5)
                ttk.Label(mvp_frame, text="🏅 MVP:", font=("Arial", 10, "bold")).pack(
                    side=tk.LEFT
                )
                ttk.Label(
                    mvp_frame,
                    text=f"{mvp.name} (WR: {mvp.win_rate:.1f}%)",
                    font=("Arial", 10),
                ).pack(side=tk.LEFT, padx=5)

            # Players
            for player in sorted(team, key=lambda p: p.win_rate, reverse=True):
                player_text = (
                    f"  • {player.name} - {rating_name}: {player.rating}, "
                    f"WR: {player.win_rate:.1f}% "
                    f"({player.wins}W-{player.losses}L-{player.draws}D)"
                )
                ttk.Label(team_frame, text=player_text, font=("Arial", 9)).pack(
                    anchor=tk.W, pady=1
                )

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button
        ttk.Button(frame, text="← Back to Setup", command=self.back_to_setup).pack(
            pady=10
        )

    def next_team_round(self):
        """Start next team round"""
        self.current_round += 1
        self.show_team_game()

    # ============ RATING CALCULATION METHODS ============

    def calculate_elo_change(
        self, player_rating: int, opponent_rating: int, result: float, mode: str = "otb"
    ) -> int:
        """
        Calculate ELO rating change based on game result
        result: 1.0 for win, 0.5 for draw, 0.0 for loss
        mode: 'otb' for Online/OTB (K=32),
        'correspondence' for Daily/Correspondence (K=48)
        """
        # Set K-factor based on mode
        if mode == "correspondence":
            k_factor = 48  # More drastic changes for correspondence chess
        else:  # otb (online/over-the-board)
            k_factor = 32  # Balanced changes

        # Expected score calculation
        expected_score = 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

        # Rating change
        change = k_factor * (result - expected_score)

        return round(change)

    def apply_automatic_elo_changes(self):
        """Apply automatic ELO changes based on tournament results from last round"""
        # Get all matches from last round
        if not hasattr(self, "tournament_results"):
            return

        # Hard guard: the ELO expected-score formula is a chess-rating
        # concept. It must never run for e-sports (Trophies), regardless
        # of how this method got called - this is enforced here as well
        # as at every call site, so there's no path that can slip through.
        if self.game_type != "chess":
            return

        # Determine which sub-mode to use based on rating_mode
        elo_mode = getattr(self, "elo_submode", None) or "otb"

        elo_changes = {}  # Player object -> accumulated change. Keyed by
        # object identity (not name) so two players who happen to share a
        # display name never collide and merge into one combined change
        # that both would otherwise incorrectly receive.

        for pairing, result_var in self.tournament_results:
            p1, p2, pairing_type = pairing
            result = result_var.get()

            # Skip byes and half-byes
            if result in ["bye", "half_bye"] or p2 is None:
                continue

            # Determine result values
            if result == "p1_win":
                p1_result, p2_result = 1.0, 0.0
            elif result == "p2_win":
                p1_result, p2_result = 0.0, 1.0
            elif result == "draw":
                p1_result, p2_result = 0.5, 0.5
            else:
                continue

            # Calculate ELO changes with selected mode
            p1_change = self.calculate_elo_change(
                p1.rating, p2.rating, p1_result, elo_mode
            )
            p2_change = self.calculate_elo_change(
                p2.rating, p1.rating, p2_result, elo_mode
            )

            # Store changes
            if p1 not in elo_changes:
                elo_changes[p1] = 0
            if p2 not in elo_changes:
                elo_changes[p2] = 0

            elo_changes[p1] += p1_change
            elo_changes[p2] += p2_change

        # Apply changes to players
        for player in self.players:
            if player in elo_changes:
                player.rating += elo_changes[player]
                # Ensure rating doesn't go below 100
                if player.rating < 100:
                    player.rating = 100

    def show_manual_rating_update(self, callback):
        """Show manual rating update interface"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"
        title = ttk.Label(
            frame, text=f"Update {rating_name} Ratings", font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        ttk.Label(
            frame,
            text=f"Manually adjust {rating_name} ratings based on round performance:",
            font=("Arial", 10),
        ).pack(pady=5)

        # Scrollable player list with rating inputs
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(list_frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Store rating entry widgets, keyed by player object (not name) so
        # two players who happen to share a display name don't collide
        # and overwrite each other's entry widget.
        self.rating_entries = {}

        # Show each player with current rating
        active_players = [
            p for p in self.players if not p.eliminated and not p.withdrawn
        ]
        for player in sorted(active_players, key=lambda p: p.points, reverse=True):
            player_frame = ttk.Frame(scrollable_frame)
            player_frame.pack(fill=tk.X, pady=5, padx=10)

            # Player info
            info_text = f"{player.name} (Points: {player.points})"
            ttk.Label(player_frame, text=info_text, width=35, anchor=tk.W).pack(
                side=tk.LEFT, padx=5
            )

            # Current rating
            ttk.Label(player_frame, text=f"Current {rating_name}:").pack(
                side=tk.LEFT, padx=5
            )
            ttk.Label(player_frame, text=str(player.rating), width=8).pack(side=tk.LEFT)

            # New rating input
            ttk.Label(player_frame, text=f"→ New {rating_name}:").pack(
                side=tk.LEFT, padx=10
            )
            entry = ttk.Entry(player_frame, width=10)
            entry.insert(0, str(player.rating))
            entry.pack(side=tk.LEFT, padx=5)

            self.rating_entries[player] = entry

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Skip (No Changes)", command=callback).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="Apply Changes",
            command=lambda: self.apply_manual_ratings(callback),
        ).pack(side=tk.LEFT, padx=5)

    def apply_manual_ratings(self, callback):
        """Apply manual rating changes.

        Validates every entry first, with zero mutation, before applying
        anything. Previously, validation and mutation happened in the
        same pass: if player #5 (in iteration order) had an invalid
        entry, players #1-4 had already had their ratings permanently
        changed by the time the warning appeared, with no way to retry
        cleanly - the warning implied nothing had happened yet, but it
        had.
        """
        min_rating = 100 if self.game_type == "chess" else 0
        new_ratings = {}  # player -> validated new rating, nothing applied yet

        for player in self.players:
            if player not in self.rating_entries:
                continue
            new_rating_str = self.rating_entries[player].get().strip()
            if not new_rating_str:
                continue
            try:
                new_rating = int(new_rating_str)
            except ValueError:
                messagebox.showwarning(
                    "Invalid Input", "All ratings must be valid numbers"
                )
                return
            if new_rating < min_rating:
                messagebox.showwarning(
                    "Invalid Input",
                    f"Rating for {player.name} cannot be below {min_rating}",
                )
                return
            new_ratings[player] = new_rating

        # Every entry validated cleanly - now it's safe to apply them all.
        for player, new_rating in new_ratings.items():
            player.rating = new_rating

        callback()

    def _reset_players_for_new_session(self) -> None:
        """Reset all per-session state on every Player object.

        wins/losses/draws/byes/half_byes/opponents accumulate from the
        player-roster save file across app launches. Without this reset,
        starting a new session (Tournament, Dual, Battle Royale, or Teams)
        would begin with leftover stats from whatever was last played,
        corrupting every standing, tiebreak, and win-rate calculation from
        round 1 onward. Shared by start_tournament() and
        confirm_simple_rating_mode() so Dual/Battle Royale/Teams reset
        exactly the same way Tournament mode always has.
        """
        for player in self.players:
            player.wins = 0
            player.losses = 0
            player.draws = 0
            player.byes = 0
            player.half_byes = 0
            player.eliminated = False
            player.withdrawn = False
            player.withdrawal_round = None
            player.opponents = []
            player.results_vs_opponents = []
            # This was missed when Colour Balancing was first added: without
            # resetting it here too, colour history from a PREVIOUS
            # tournament in the same app session would carry over and
            # corrupt colour-balance decisions (streaks, W/B counts) from
            # round 1 of a new one.
            player.colors = []
            player.requested_half_bye = False
            # Snapshot the rating this player is STARTING this session
            # with. Used for TRF16 starting-rank assignment and its
            # FIDE-Rating column - both should reflect the rating a
            # player entered with, not one automatic ELO mode may since
            # have adjusted mid-session.
            player.initial_rating = player.rating

    # ============ TOURNAMENT MODE METHODS ============

    def start_tournament(self):
        """Initialize and start tournament"""
        min_players = {"swiss": 4, "round_robin": 3, "knockout": 4, "scheveningen": 4}

        min_req = min_players.get(self.tournament_system, 2)

        if self.tournament_system == "scheveningen":
            required = self.scheveningen_team_size * 2
            if len(self.players) != required:
                messagebox.showwarning(
                    "Wrong Number of Players",
                    (
                        f"Need exactly {required} players for Scheveningen "
                        f"with {self.scheveningen_team_size} per team "
                        f"(you currently have {len(self.players)})."
                    ),
                )
                return
        elif len(self.players) < min_req:
            messagebox.showwarning(
                "Not Enough Players",
                f"Need at least {min_req} players for {self.tournament_system}",
            )
            return

        self.in_game = True
        self.tournament_history = []
        self.tournament_start_time = datetime.datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        self.current_round = 1

        # Reset all per-tournament state on every Player object (see
        # _reset_players_for_new_session for why this is needed).
        self._reset_players_for_new_session()

        # TRF16 starting ranks: assigned once, here, by descending rating
        # AT tournament start (ties broken by original entry order, since
        # Python's sort is stable) - the standard convention, and never
        # recomputed later even if automatic ELO mode subsequently moves
        # players' ratings.
        self.trf_starting_rank_names = [
            p.name
            for p in sorted(
                self.players, key=lambda p: p.initial_rating, reverse=True
            )
        ]

        if self.tournament_system == "swiss":
            self.show_swiss_round()
        elif self.tournament_system == "round_robin":
            # Record the stable round count from the initial player pool.
            # Half-byes temporarily shrink playing_players mid-tournament, so
            # recomputing total_rounds from that list each round causes premature
            # termination.  Capturing it once here (before any half-byes or
            # withdrawals) keeps it correct for the whole tournament.
            n_start = len(self.players)
            self.round_robin_total_rounds = (
                n_start - 1 if n_start % 2 == 0 else n_start
            )
            # Record the fixed rotation order too. generate_round_robin_pairings
            # rotates this exact list every round - it must never change shape
            # or order once the tournament starts, or the round-robin schedule
            # guarantee (everyone plays everyone exactly once) breaks. Half-byes
            # and withdrawals are handled later by substituting byes into that
            # round's OUTPUT, not by removing anyone from this list.
            self.round_robin_player_order = list(self.players)
            # New tournament - any cached colour plan from a previous
            # Round-Robin tournament this session must not carry over.
            self.round_robin_color_plan = None
            self.show_round_robin_round()
        elif self.tournament_system == "knockout":
            self.show_knockout_round()
        elif self.tournament_system == "scheveningen":
            self.setup_scheveningen_teams()

    # ===== SWISS SYSTEM =====

    def show_swiss_round(self):
        """Show Swiss system round with pairings"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Generate pairings
        pairings = self.generate_swiss_pairings()

        title = ttk.Label(
            frame,
            text=f"Swiss System - Round {self.current_round}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        # Display pairings
        self.display_tournament_pairings(frame, pairings, "swiss")

    # ===== COLOUR BALANCING (Chess tournament formats only) =====
    #
    # Applied to Swiss, Round-Robin, Knockout and Scheveningen. Modelled
    # on the FIDE colour-allocation rules (FIDE Handbook C.04.1/C.04.3):
    #   - A bye/half-bye is colourless: it neither counts towards the
    #     White/Black balance nor breaks a same-colour streak.
    #   - A player's "colour preference" for their next REAL game is:
    #       * ABSOLUTE if their colour difference (white - black) is
    #         already +/-2 or worse, or if their last two real games
    #         were the same colour (never allow a 3rd in a row).
    #       * otherwise a soft preference: the colour that would even
    #         out the difference, or - if already even - whichever
    #         colour they didn't just play (alternation).
    #   - When assigning colours for an already-decided pair: an
    #     absolute preference always wins; if both have one (shouldn't
    #     normally happen - see _colors_conflict below), the player with
    #     the bigger need wins and the other accepts a documented
    #     exception (mirrors FIDE C.04.1 #6/#7, which allow rare
    #     exceptions when there's no legal alternative); otherwise ties
    #     are broken by alternating from these two players' most recent
    #     meeting, then by rating, then - if truly no information exists
    #     (e.g. round 1) - by a coin flip ("drawing of lots", the actual
    #     FIDE round-1 rule).
    def _color_preference(self, player):
        """Return (preferred_color, is_absolute, is_streak) for a
        player's next real game. preferred_color is 'white', 'black', or
        None (no games played yet, or - defensively - unrecognised
        data). is_streak marks the specific case where the preference is
        absolute because they'd otherwise get a 3rd-in-a-row - this is
        treated as more urgent than merely being at the +/-2 colour
        difference boundary when resolving a genuine conflict (see
        _assign_colors), since FIDE's own wording singles out "same
        colour three times in a row" ("no participant shall receive...")
        as the one exception-averse case, whereas a +/-2 difference is
        already explicitly tolerated."""
        colors = player.colors
        if not colors:
            return None, False, False
        if len(colors) >= 2 and colors[-1] == colors[-2]:
            # Same colour last two real games -> must switch (absolute)
            return ("black" if colors[-1] == "white" else "white"), True, True
        diff = player.color_difference
        if diff >= 2:
            return "black", True, False
        if diff <= -2:
            return "white", True, False
        if diff == 1:
            return "black", False, False
        if diff == -1:
            return "white", False, False
        # Perfectly balanced: alternate from the last real game played
        return ("black" if colors[-1] == "white" else "white"), False, False

    def _colors_conflict(self, a, b):
        """True if both players have an ABSOLUTE preference for the same
        colour, meaning no matter how we assign this pair, one of them
        must take a documented exception. Used as a secondary (softer
        than repeat-opponent-avoidance) constraint in Swiss pairing, so
        the matcher tries to avoid creating such pairs in the first
        place - matching FIDE C.04.3 [C3]."""
        pref_a, abs_a, _ = self._color_preference(a)
        pref_b, abs_b, _ = self._color_preference(b)
        return abs_a and abs_b and pref_a == pref_b

    def _last_color_vs(self, player, opponent_name):
        """The colour `player` had the most recent time they played
        `opponent_name`, or None if they've never met (or data is old)."""
        for opp, col in zip(reversed(player.opponents), reversed(player.colors)):
            if opp == opponent_name:
                return col
        return None

    def _assign_colors(self, a, b):
        """Decide who of (a, b) plays White vs Black for a game that has
        already been decided as a pairing. Returns (white_player,
        black_player)."""
        pref_a, abs_a, streak_a = self._color_preference(a)
        pref_b, abs_b, streak_b = self._color_preference(b)

        # 1) An absolute preference wins over a non-absolute one.
        if abs_a and not abs_b:
            return (a, b) if pref_a == "white" else (b, a)
        if abs_b and not abs_a:
            return (b, a) if pref_b == "white" else (a, b)

        # 2) Both absolute: if for different colours, trivial; if for
        # the SAME colour (a genuine conflict - rare, and Swiss pairing
        # tries hard to avoid ever creating this pair at all; in
        # Round-Robin/Scheveningen, whose schedules are fixed, it can be
        # genuinely unavoidable), give it to whoever needs it more:
        # first, a streak-based need (would otherwise get a 3rd colour
        # in a row) outranks a difference-based one (already tolerated
        # up to +/-2 by FIDE); ties within that broken by bigger
        # |colour difference|, then by rating.
        if abs_a and abs_b:
            if pref_a != pref_b:
                return (a, b) if pref_a == "white" else (b, a)
            if streak_a != streak_b:
                winner, loser = (a, b) if streak_a else (b, a)
            else:
                need_a = abs(a.color_difference)
                need_b = abs(b.color_difference)
                if need_a != need_b:
                    winner, loser = (a, b) if need_a > need_b else (b, a)
                else:
                    # Genuinely tied on every measure that should matter.
                    # Deliberately NOT using rating here: a fixed,
                    # deterministic tiebreak (e.g. "higher rated wins")
                    # would mean the same player (e.g. whoever has the
                    # single lowest rating in the field) loses every
                    # future tie too, compounding into a long run of
                    # forced same-colour exceptions for them specifically
                    # - exactly what happened in testing. A coin flip
                    # spreads exceptions around instead.
                    winner, loser = (a, b) if random.random() < 0.5 else (b, a)
            winner_pref, _, _ = self._color_preference(winner)
            return (winner, loser) if winner_pref == "white" else (loser, winner)

        # 3) Neither has an absolute preference. If they have opposite
        # soft preferences, grant them.
        if pref_a and pref_b and pref_a != pref_b:
            return (a, b) if pref_a == "white" else (b, a)

        # 4) Same soft preference (or one/both have none, e.g. round 1,
        # or a perfectly-tied alternation) - alternate from the last
        # time these two specific players met, if ever.
        last = self._last_color_vs(a, b.name)
        if last:
            return (b, a) if last == "white" else (a, b)

        # 5) Still nothing to go on - prefer the higher-rated player's
        # soft preference if there is one...
        if pref_a and not pref_b:
            return (a, b) if pref_a == "white" else (b, a)
        if pref_b and not pref_a:
            return (b, a) if pref_b == "white" else (a, b)

        # 6) ...otherwise (true round-1-style tie) decide by lot.
        return (a, b) if random.random() < 0.5 else (b, a)

    def generate_swiss_pairings(self):
        """Generate Swiss system pairings"""
        active = [p for p in self.players if not p.eliminated and not p.withdrawn]

        # Separate players who requested half-bye
        halfbye_players = [p for p in active if p.requested_half_bye]
        playing_players = [p for p in active if not p.requested_half_bye]

        pairings = []

        # Add half-bye players first
        for player in halfbye_players:
            pairings.append([player, None, "half_bye"])
            player.requested_half_bye = False  # Reset flag

        if self.current_round == 1:
            # First round: pair by rating
            playing_players.sort(key=lambda p: p.rating, reverse=True)
            mid = len(playing_players) // 2
            top_half = playing_players[:mid]
            bottom_half = playing_players[mid:]

            for i in range(min(len(top_half), len(bottom_half))):
                # No colour history exists yet, so who gets White is
                # decided purely by lot (this is the actual FIDE round-1
                # rule, not just a simplification).
                a, b = top_half[i], bottom_half[i]
                white, black = self._assign_colors(a, b)
                pairings.append([white, black, None])

            # Handle odd number
            if len(playing_players) % 2 == 1:
                pairings.append([playing_players[-1], None, "bye"])
        else:
            # Sort by points, then rating
            playing_players.sort(key=lambda p: (p.points, p.rating), reverse=True)

            matching = self._find_swiss_matching(playing_players)
            for a, b in matching:
                if b is None:
                    pairings.append([a, None, "bye"])
                else:
                    white, black = self._assign_colors(a, b)
                    pairings.append([white, black, None])

        return pairings

    def _find_swiss_matching(self, playing_players):
        """Find a full pairing of playing_players (already sorted by
        pairing priority - closest-ranked first) using backtracking,
        rather than the simple greedy "first compatible opponent" scan
        this used to use.

        Greedy without backtracking can pick a locally-valid opponent
        that turns out to make a complete pairing impossible later in
        the list, even when a valid complete pairing exists - it just
        wasn't the first one greedy happened to try. That produced
        unnecessary byes for players who didn't need one. Backtracking
        undoes a bad pick and tries the next candidate instead of
        giving up on the whole round.

        Returns a list of (player, opponent_or_None) tuples. opponent is
        None for a bye. At most one bye is ever produced for one call.
        If a complete pairing using only never-played-before opponents
        is impossible (can happen with an unlucky history), falls back
        to allowing exactly the repeat pairing(s) needed to avoid
        handing out more than one bye - a repeat is the standard Swiss
        convention for an otherwise-unresolvable round, and is less
        disruptive than multiple simultaneous byes.

        Colour balancing note: avoiding a repeat opponent still ranks
        above colour concerns (matches FIDE C1 outranking C3), but right
        below that we also try to avoid ever pairing two players who
        BOTH have an absolute colour preference for the same colour
        (_colors_conflict) - since if we do, one of them is guaranteed a
        documented colour-rule exception no matter how colours are then
        assigned. That's tried before we're willing to allow a repeat
        opponent, and only given up on (in that order) if truly no legal
        full pairing exists that avoids it.
        """
        # Hard safety cap: backtracking search is worst-case exponential.
        # Realistic Swiss fields (dozens of players, sparse "already
        # played" history) resolve in well under a thousand recursive
        # calls in testing. If something pathological blows past this,
        # fall back to the old unconditional-greedy behaviour rather than
        # risk hanging the UI - a few unnecessary byes is a much smaller
        # problem than the app freezing.
        call_budget = [20000]

        def can_play(a, b, allow_repeats, avoid_color_conflicts):
            if not allow_repeats:
                if b.name in a.opponents or a.name in b.opponents:
                    return False
            if avoid_color_conflicts and self._colors_conflict(a, b):
                return False
            return True

        def backtrack(remaining, allow_repeats, avoid_color_conflicts):
            call_budget[0] -= 1
            if call_budget[0] <= 0:
                return None
            if not remaining:
                return []
            if len(remaining) == 1:
                return [(remaining[0], None)]

            first = remaining[0]
            rest = remaining[1:]

            for i, candidate in enumerate(rest):
                if can_play(first, candidate, allow_repeats, avoid_color_conflicts):
                    new_remaining = rest[:i] + rest[i + 1 :]
                    sub_result = backtrack(
                        new_remaining, allow_repeats, avoid_color_conflicts
                    )
                    if sub_result is not None:
                        return [(first, candidate)] + sub_result

            # Odd-sized remaining group: `first` could be the bye instead
            # of being forced into one of the pairings tried above.
            if len(remaining) % 2 == 1:
                sub_result = backtrack(rest, allow_repeats, avoid_color_conflicts)
                if sub_result is not None:
                    return [(first, None)] + sub_result

            return None

        result = None
        # Tiers in descending priority: (no repeats, no colour conflicts)
        # -> (no repeats, colour conflicts allowed) -> (repeats allowed,
        # no colour conflicts) -> (repeats allowed, colour conflicts
        # allowed). Each tier is only tried while budget remains.
        for allow_repeats, avoid_color_conflicts in (
            (False, True),
            (False, False),
            (True, True),
            (True, False),
        ):
            if call_budget[0] <= 0:
                break
            result = backtrack(
                list(playing_players), allow_repeats, avoid_color_conflicts
            )
            if result is not None:
                break
        if result is None:
            # Either the safety cap was hit, or even allowing repeats
            # failed (shouldn't happen for an even count, but playing it
            # safe). Fall back to the simple greedy pass the app used
            # before, which always terminates even if not optimal.
            result = []
            paired = set()
            for player in playing_players:
                if player.name in paired:
                    continue
                opponent = None
                for candidate in playing_players:
                    if (
                        candidate.name != player.name
                        and candidate.name not in paired
                        and candidate.name not in player.opponents
                    ):
                        opponent = candidate
                        break
                if opponent:
                    result.append((player, opponent))
                    paired.add(player.name)
                    paired.add(opponent.name)
                else:
                    result.append((player, None))
                    paired.add(player.name)
        return result

    def _compute_round_robin_color_plan(self, order, total_rounds):
        """Precompute a colour assignment for EVERY game of a Round-Robin
        tournament, assuming full attendance, and return it as a dict
        {(round_idx_0_based, frozenset({name_a, name_b})): white_name}.

        Why precompute instead of deciding colours round-by-round as they
        happen (like Swiss does): unlike Swiss, a Round-Robin's entire
        WHO-PLAYS-WHOM schedule for every round is already fully
        determined at tournament start - it never depends on results.
        That means colours can and should be planned for the whole event
        at once rather than greedily round-by-round, because a greedy
        per-round choice has no way to see that an easy, arbitrary
        choice now (e.g. an unconstrained tie) will box a player into an
        unavoidable same-colour-twice-in-a-row situation several rounds
        later - and testing confirmed this actually happens occasionally
        with a purely greedy approach, even with full attendance and an
        even number of players. A full round-robin colouring that never
        needs a 3rd-in-a-row exception is mathematically always
        possible (this is exactly what published Berger tables
        guarantee), so backtracking - trying the balance-preferred
        colour first at each game, backing up when a later game turns
        out to be impossible - is guaranteed to find a clean assignment,
        and in practice needs little to no backtracking since the
        balance-first heuristic already mirrors how Berger tables are
        built.

        Half-byes/withdrawals aren't modelled here (this assumes full
        attendance) because they're requested round-by-round and can't
        be known in advance; when an individual player's real history
        ends up desynced from this plan by a bye, the caller falls back
        to per-player override logic (see generate_round_robin_pairings)
        exactly like Scheveningen does for the same reason.
        """
        n = len(order)
        rotation_input = list(order)
        if n % 2 == 1:
            rotation_input.append(None)
            n += 1

        schedule = []  # list of rounds, each a list of (name_a, name_b)
        rotated = rotation_input.copy()
        for _ in range(total_rounds):
            round_pairs = []
            for i in range(n // 2):
                pa, pb = rotated[i], rotated[n - 1 - i]
                if pa is not None and pb is not None:
                    round_pairs.append((pa.name, pb.name))
            schedule.append(round_pairs)
            rotated = [rotated[0]] + [rotated[-1]] + rotated[1:-1]

        flat_games = [
            (r_idx, a, b)
            for r_idx, pairs in enumerate(schedule)
            for (a, b) in pairs
        ]

        histories = {p.name: [] for p in order}

        def would_violate(name, color):
            """Mirrors _color_preference's definition of an ABSOLUTE
            violation exactly (streak of 2, or already at the +/-2
            colour-difference boundary) - the plan and the per-player
            override check in generate_round_robin_pairings must always
            agree on what counts as a violation, or the override ends up
            fighting a plan that already thought it had this handled."""
            h = histories[name]
            if len(h) >= 2 and h[-1] == color and h[-2] == color:
                return True
            diff = h.count("white") - h.count("black")
            new_diff = diff + (1 if color == "white" else -1)
            return new_diff > 2 or new_diff < -2

        plan = {}

        def backtrack(idx):
            if idx == len(flat_games):
                return True
            r_idx, a, b = flat_games[idx]
            diff_a = histories[a].count("white") - histories[a].count("black")
            diff_b = histories[b].count("white") - histories[b].count("black")
            # Try giving White to whoever currently has fewer Whites
            # relative to Blacks first - this single heuristic is enough
            # to make backtracking essentially unnecessary in practice,
            # since it's the same logic a Berger table encodes directly.
            order_ab = diff_a <= diff_b
            for white_is_a in (order_ab, not order_ab):
                white_name, black_name = (a, b) if white_is_a else (b, a)
                if would_violate(white_name, "white") or would_violate(
                    black_name, "black"
                ):
                    continue
                histories[white_name].append("white")
                histories[black_name].append("black")
                plan[(r_idx, frozenset((a, b)))] = white_name
                if backtrack(idx + 1):
                    return True
                histories[white_name].pop()
                histories[black_name].pop()
                del plan[(r_idx, frozenset((a, b)))]
            return False

        if not backtrack(0):
            # Mathematically shouldn't happen for a standard round-robin
            # schedule, but if it somehow did, an empty plan makes every
            # lookup miss, and the caller's per-player override logic
            # (the same one used for bye-desync) becomes the sole
            # decision-maker instead - degraded, but still safe.
            return {}
        return plan

    # ===== ROUND-ROBIN =====

    def show_round_robin_round(self):
        """Show Round-Robin round"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        pairings = self.generate_round_robin_pairings()

        if not pairings:
            # Tournament complete
            self.show_tournament_final_standings()
            return

        title = ttk.Label(
            frame,
            text=f"Round-Robin - Round {self.current_round}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        self.display_tournament_pairings(frame, pairings, "round_robin")

    def generate_round_robin_pairings(self):
        """Generate Round-Robin pairings using the round-robin (circle)
        algorithm, rotating a FIXED player order that is captured once at
        tournament start and never changes shape afterward.

        This matters because of how half-byes and withdrawals work: if we
        rotated whatever subset of players happens to be "active" THIS
        round, removing a player for one round (a half-bye) would change
        the size/order of the list being rotated, which desyncs the
        rotation from every other round's schedule - producing repeated
        pairings and missed pairings elsewhere in the tournament, since
        round-robin's "everyone plays everyone exactly once" guarantee
        only holds if the same fixed list is rotated round after round.

        Instead: rotate the fixed order to get THIS round's scheduled
        pairs first, then substitute byes/half-byes into the output for
        whoever requested one or has withdrawn, without touching the
        rotation itself.
        """
        order = getattr(self, "round_robin_player_order", None)
        if not order:
            # Fallback for saves that predate this field: the original
            # order is lost, so the best we can do is fix one in place now
            # and keep it stable for the rest of the tournament, rather
            # than recomputing (and reshaping) it every round as before.
            order = list(self.players)
            self.round_robin_player_order = order

        # Use the stable total recorded at tournament start rather than
        # recomputing from however many players are still active.  Half-byes
        # and withdrawals must not change how many rounds a round-robin is
        # supposed to run for.
        total_rounds = getattr(self, "round_robin_total_rounds", 0)
        if not total_rounds:
            n_all = len(order)
            total_rounds = n_all - 1 if n_all % 2 == 0 else n_all
            self.round_robin_total_rounds = total_rounds  # cache for next rounds

        if self.current_round > total_rounds:
            return []  # Tournament complete

        n = len(order)
        rotation_input = order.copy()
        if n % 2 == 1:
            rotation_input.append(None)  # Dummy bye slot, rotates like anyone else
            n += 1

        round_idx = self.current_round - 1

        # Fixed position rotation algorithm, applied to the STABLE order
        rotated = rotation_input.copy()
        for _ in range(round_idx):
            rotated = [rotated[0]] + [rotated[-1]] + rotated[1:-1]

        # This round's schedule, before any half-bye/withdrawal substitution
        scheduled_pairs = []
        for i in range(n // 2):
            scheduled_pairs.append((rotated[i], rotated[n - 1 - i]))

        pairings = []
        for p1, p2 in scheduled_pairs:
            # Dummy slot -> the real player gets the rotation's bye, same
            # as before.
            if p1 is None or p2 is None:
                real = p1 if p1 is not None else p2
                if real is not None and not real.withdrawn:
                    if real.requested_half_bye:
                        pairings.append([real, None, "half_bye"])
                        real.requested_half_bye = False
                    else:
                        pairings.append([real, None, "bye"])
                continue

            p1_out = p1.withdrawn
            p2_out = p2.withdrawn
            if p1_out and p2_out:
                # Both scheduled players are gone - nothing to schedule.
                continue
            if p1_out:
                # p1 withdrew; p2's scheduled opponent isn't there to play.
                # p2 still gets their own half-bye entry if they asked for
                # one (it's their choice being recorded, not a consequence
                # of p1 withdrawing), otherwise a bye.
                if p2.requested_half_bye:
                    pairings.append([p2, None, "half_bye"])
                    p2.requested_half_bye = False
                else:
                    pairings.append([p2, None, "bye"])
                continue
            if p2_out:
                if p1.requested_half_bye:
                    pairings.append([p1, None, "half_bye"])
                    p1.requested_half_bye = False
                else:
                    pairings.append([p1, None, "bye"])
                continue

            # Both scheduled players are present. A half-bye request takes
            # priority for whichever of them asked for it: that player gets
            # their own half_bye entry, and since their scheduled opponent
            # now has no one to play, the opponent gets a bye instead of
            # being silently dropped from the round (this was the actual
            # bug - the old code pulled half-bye players out before
            # pairing, leaving their would-be opponent unpaired and
            # reshaping the rotation for every round after).
            p1_half = p1.requested_half_bye
            p2_half = p2.requested_half_bye
            if p1_half and p2_half:
                # Both wanted to sit out the same scheduled game - honour
                # both as half-byes rather than picking one arbitrarily.
                pairings.append([p1, None, "half_bye"])
                pairings.append([p2, None, "half_bye"])
                p1.requested_half_bye = False
                p2.requested_half_bye = False
            elif p1_half:
                pairings.append([p1, None, "half_bye"])
                pairings.append([p2, None, "bye"])
                p1.requested_half_bye = False
            elif p2_half:
                pairings.append([p2, None, "half_bye"])
                pairings.append([p1, None, "bye"])
                p2.requested_half_bye = False
            else:
                # Colour Balancing: look up this game's colour in the
                # precomputed full-attendance plan (see
                # _compute_round_robin_color_plan for why this is
                # precomputed rather than decided greedily per round).
                # Computed once and cached, keyed off the same stable
                # round_robin_player_order the schedule itself is based
                # on.
                if getattr(self, "round_robin_color_plan", None) is None:
                    self.round_robin_color_plan = self._compute_round_robin_color_plan(
                        order, total_rounds
                    )
                plan_key = (round_idx, frozenset((p1.name, p2.name)))
                planned_white_name = self.round_robin_color_plan.get(plan_key)

                if planned_white_name == p1.name:
                    default_white, default_black = p1, p2
                elif planned_white_name == p2.name:
                    default_white, default_black = p2, p1
                else:
                    # Plan lookup somehow missed (shouldn't normally
                    # happen) - fall back to the general cascade.
                    default_white, default_black = self._assign_colors(p1, p2)

                # A half-bye/withdrawal earlier in the tournament can
                # still desync an individual player's REAL colour
                # history from what the full-attendance plan assumed for
                # them. If honouring the plan's default here would force
                # an absolute violation for either player, don't just
                # swap the two colours - swapping to fix one player can
                # just as easily create a brand new violation for the
                # other (whoever wasn't a problem under the default may
                # have had their OWN absolute preference for the colour
                # the default already gave them). Defer entirely to the
                # general cascade instead, which already correctly
                # handles every combination of single/double absolute
                # preference - same mechanism used for the same reason
                # in Scheveningen.
                pref_w, abs_w, _ = self._color_preference(default_white)
                pref_b, abs_b, _ = self._color_preference(default_black)
                violation_white = abs_w and pref_w != "white"
                violation_black = abs_b and pref_b != "black"
                if violation_white or violation_black:
                    white, black = self._assign_colors(p1, p2)
                else:
                    white, black = default_white, default_black

                pairings.append([white, black, None])

        return pairings

    # ===== KNOCKOUT =====

    def show_knockout_round(self):
        """Show Knockout/Elimination bracket round"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        active = [p for p in self.players if not p.eliminated]

        if len(active) == 1:
            self.show_tournament_winner(active[0])
            return

        pairings = self.generate_knockout_pairings()

        # Derive the round label from how many players are still active, so
        # "Semifinals" appears when 4 remain regardless of how many started.
        num_active = len(active)
        if num_active <= 2:
            round_name = "Final"
        elif num_active <= 4:
            round_name = "Semifinals"
        elif num_active <= 8:
            round_name = "Quarterfinals"
        elif num_active <= 16:
            round_name = "Round of 16"
        elif num_active <= 32:
            round_name = "Round of 32"
        else:
            round_name = f"Round {self.current_round}"

        title = ttk.Label(
            frame, text=f"Knockout - {round_name}", font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        self.display_tournament_pairings(frame, pairings, "knockout")

    def generate_knockout_pairings(self):
        """Generate Knockout pairings"""
        active = [p for p in self.players if not p.eliminated]

        if self.current_round == 1:
            # Seed by rating
            active.sort(key=lambda p: p.rating, reverse=True)
        else:
            # Sort by points
            active.sort(key=lambda p: p.points, reverse=True)

        pairings = []
        while len(active) >= 2:
            p1 = active.pop(0)
            p2 = active.pop(0)
            # If these two are meeting again (e.g. a drawn final that has
            # to be replayed), _assign_colors' step 4 (alternate from
            # their most recent meeting) takes care of flipping colours
            # for the rematch automatically.
            white, black = self._assign_colors(p1, p2)
            pairings.append([white, black, None])

        # Bye for odd player
        if active:
            pairings.append([active[0], None, "bye"])

        return pairings

    # ===== SCHEVENINGEN =====

    def setup_scheveningen_teams(self):
        """Setup two teams for Scheveningen"""
        team_size = self.scheveningen_team_size

        if len(self.players) != team_size * 2:
            messagebox.showerror("Error", f"Need exactly {team_size * 2} players")
            return

        # Sort by rating and split into two teams
        sorted_players = sorted(self.players, key=lambda p: p.rating, reverse=True)

        # Alternate distribution for balance
        self.schev_team_a = []
        self.schev_team_b = []

        for i, player in enumerate(sorted_players):
            if i % 2 == 0:
                self.schev_team_a.append(player)
            else:
                self.schev_team_b.append(player)

        self.schev_round = 0
        self.schev_total_rounds = team_size
        # Classic Scheveningen colour convention: the whole team plays one
        # colour for the entire round, and teams swap colours every round.
        # Which team gets White in round 1 is decided by lot, same as any
        # other "no history yet" colour decision (FIDE's round-1 rule).
        self.schev_team_a_white_first = random.random() < 0.5
        self.show_scheveningen_round()

    def show_scheveningen_round(self):
        """Show Scheveningen round"""
        self.schev_round += 1

        if self.schev_round > self.schev_total_rounds:
            self.show_scheveningen_final()
            return

        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            frame,
            text=f"Scheveningen - Round {self.schev_round}/{self.schev_total_rounds}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        pairings = self._generate_scheveningen_pairings(self.schev_round)

        self.display_tournament_pairings(frame, pairings, "scheveningen")

    def _scheveningen_team_a_is_white(self, schev_round):
        """Whether Team A plays White this round, under the classic
        Scheveningen convention (whole team plays one colour, alternating
        every round). Falls back to a fresh lot for saves from before
        this feature existed, same pattern as other backward-compat
        fallbacks in this file."""
        white_first = getattr(self, "schev_team_a_white_first", None)
        if white_first is None:
            white_first = random.random() < 0.5
            self.schev_team_a_white_first = white_first
        return white_first if (schev_round % 2 == 1) else (not white_first)

    def _scheveningen_assign_colors(self, a_player, b_player, team_a_is_white):
        """Colour assignment for one Scheveningen pairing: uses the
        team-wide default, but overrides it for an individual player if
        the default would force an absolute colour-rule violation for
        them (possible because half-byes/withdrawals can desync one
        player's personal streak/balance from their team's round-parity
        schedule). Falls back to the general cross-format cascade in the
        rare case both players would be violated by the same default."""
        default_white, default_black = (
            (a_player, b_player) if team_a_is_white else (b_player, a_player)
        )

        pref_w, abs_w, _ = self._color_preference(default_white)
        pref_b, abs_b, _ = self._color_preference(default_black)
        violation_white = abs_w and pref_w != "white"
        violation_black = abs_b and pref_b != "black"

        if not violation_white and not violation_black:
            return default_white, default_black
        # Don't just swap to fix a single violation - swapping to fix one
        # player can just as easily create a brand new violation for the
        # other, if they had their own absolute preference for the
        # colour the team default already (correctly) gave them. Defer
        # to the general cascade, which correctly handles every
        # combination of single/double absolute preference.
        return self._assign_colors(a_player, b_player)

    def _generate_scheveningen_pairings(self, schev_round):
        """Generate this round's Scheveningen pairings by rotating the
        FIXED team rosters (self.schev_team_a / self.schev_team_b, which
        are set once at setup and never resized afterward), then
        substituting byes/half-byes into the output for whoever has
        withdrawn or requested one this round.

        This mirrors the round-robin fix for the same underlying problem:
        the rotation formula `(i + round - 1) % len(team)` only produces a
        correct "everyone plays everyone" schedule if it's applied to a
        team of the SAME fixed size every round. The previous
        implementation computed it directly against the half-bye- and
        withdrawal-filtered team lists, which shrink on whichever round a
        player sits out - silently desyncing the rotation from every
        other round's schedule, producing repeated pairings for some
        players and missed pairings for others, for the rest of the
        tournament.
        """
        team_a = self.schev_team_a
        team_b = self.schev_team_b
        n_a, n_b = len(team_a), len(team_b)

        # This round's schedule against the FULL, fixed rosters - the part
        # that must stay stable across every round regardless of who sits
        # out. (Team sizes are equal in every case the current UI allows,
        # but this also works correctly if they aren't.)
        scheduled = []
        for i in range(n_a):
            if n_b == 0:
                scheduled.append((team_a[i], None))
            else:
                opponent_idx = (i + schev_round - 1) % n_b
                scheduled.append((team_a[i], team_b[opponent_idx]))

        # Team B players who aren't scheduled against anyone this round
        # (only possible when Team A is smaller than Team B) still need
        # their own bye/half-bye entry rather than being silently dropped.
        scheduled_b_players = {b for _, b in scheduled if b is not None}
        unscheduled_b = [p for p in team_b if p not in scheduled_b_players]

        pairings = []
        for a_player, b_player in scheduled:
            a_out = a_player.withdrawn
            b_out = b_player.withdrawn if b_player is not None else True

            if a_out and (b_player is None or b_out):
                continue  # Nobody real scheduled on either side

            if a_out:
                # Team A's scheduled player is gone; b_player still gets
                # their own entry - a half-bye if they asked for one
                # (their choice, not a consequence of a_player withdrawing),
                # otherwise a bye since their opponent isn't there to play.
                if b_player.requested_half_bye:
                    pairings.append([b_player, None, "half_bye"])
                    b_player.requested_half_bye = False
                else:
                    pairings.append([b_player, None, "bye"])
                continue

            if b_player is None or b_out:
                if a_player.requested_half_bye:
                    pairings.append([a_player, None, "half_bye"])
                    a_player.requested_half_bye = False
                else:
                    pairings.append([a_player, None, "bye"])
                continue

            # Both scheduled players are present. A half-bye request takes
            # priority: that player gets their own half_bye entry, and
            # since their scheduled opponent now has no one to play this
            # round, the opponent gets a bye instead of being silently
            # left out of the pairings list.
            a_half = a_player.requested_half_bye
            b_half = b_player.requested_half_bye
            if a_half and b_half:
                pairings.append([a_player, None, "half_bye"])
                pairings.append([b_player, None, "half_bye"])
                a_player.requested_half_bye = False
                b_player.requested_half_bye = False
            elif a_half:
                pairings.append([a_player, None, "half_bye"])
                pairings.append([b_player, None, "bye"])
                a_player.requested_half_bye = False
            elif b_half:
                pairings.append([b_player, None, "half_bye"])
                pairings.append([a_player, None, "bye"])
                b_player.requested_half_bye = False
            else:
                team_a_is_white = self._scheveningen_team_a_is_white(schev_round)
                white, black = self._scheveningen_assign_colors(
                    a_player, b_player, team_a_is_white
                )
                pairings.append([white, black, None])

        for b_player in unscheduled_b:
            if b_player.withdrawn:
                continue
            if b_player.requested_half_bye:
                pairings.append([b_player, None, "half_bye"])
                b_player.requested_half_bye = False
            else:
                pairings.append([b_player, None, "bye"])

        return pairings

    def show_scheveningen_standings(self):
        """Show Scheveningen standings after a round"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            frame,
            text=f"Scheveningen - Standings After Round {self.schev_round}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        # Combine both teams for standings
        all_players = self.schev_team_a + self.schev_team_b
        sorted_players = self.apply_tiebreak(all_players)

        # Display standings
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=[
                "rank",
                "team",
                "name",
                "rating",
                "points",
                "wins",
                "losses",
                "draws",
                "byes",
                "hbyes",
                "tiebreak",
            ],
            show="headings",
            height=12,
        )

        tree.heading("rank", text="Rank")
        tree.heading("team", text="Team")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO")
        tree.heading("points", text="Points")
        tree.heading("wins", text="W")
        tree.heading("losses", text="L")
        tree.heading("draws", text="D")
        tree.heading("byes", text="Bye")
        tree.heading("hbyes", text="½Bye")
        tree.heading("tiebreak", text="TB")

        tree.column("rank", width=45)
        tree.column("team", width=55)
        tree.column("name", width=110)
        tree.column("rating", width=55)
        tree.column("points", width=55)
        tree.column("wins", width=35)
        tree.column("losses", width=35)
        tree.column("draws", width=35)
        tree.column("byes", width=35)
        tree.column("hbyes", width=40)
        tree.column("tiebreak", width=60)

        for i, (player, tb_score) in enumerate(sorted_players, 1):
            # Determine team
            team = "A" if player in self.schev_team_a else "B"

            tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    team,
                    player.name,
                    player.rating,
                    player.points,
                    player.wins,
                    player.losses,
                    player.draws,
                    player.byes,
                    player.half_byes,
                    f"{tb_score:.1f}" if tb_score is not None else "-",
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Half-bye request section (if enabled)
        if self.half_bye_enabled:
            halfbye_frame = ttk.LabelFrame(
                frame, text="Half-Bye Requests for Next Round", padding="10"
            )
            halfbye_frame.pack(fill=tk.X, pady=5, padx=10)

            ttk.Label(
                halfbye_frame,
                text=(
                    "Players can request a half-bye (0.5 points) "
                    "to skip the next round."
                ),
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each active player, keyed by player
            # object (not name) so two same-named players never collide.
            self.halfbye_vars = {}
            players_per_row = 3
            row_frame = None

            active_players = [
                p for p in all_players if not p.eliminated and not p.withdrawn
            ]
            for i, player in enumerate(active_players):
                if i % players_per_row == 0:
                    row_frame = ttk.Frame(halfbye_frame)
                    row_frame.pack(fill=tk.X, pady=2)

                var = tk.BooleanVar(value=False)
                self.halfbye_vars[player] = var

                cb = ttk.Checkbutton(row_frame, text=player.name, variable=var)
                cb.pack(side=tk.LEFT, padx=10)

        # Withdrawal request section (if enabled)
        if self.withdrawal_enabled:
            withdrawal_frame = ttk.LabelFrame(
                frame, text="Player Withdrawals", padding="10"
            )
            withdrawal_frame.pack(fill=tk.X, pady=5, padx=10)

            ttk.Label(
                withdrawal_frame,
                text=(
                    "Select players to withdraw from the tournament "
                    "(they keep their current score)."
                ),
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each active player, keyed by player
            # object (not name) so two same-named players never collide.
            self.withdrawal_vars = {}
            players_per_row = 3
            row_frame = None

            active_players = [
                p for p in all_players if not p.eliminated and not p.withdrawn
            ]
            for i, player in enumerate(active_players):
                if i % players_per_row == 0:
                    row_frame = ttk.Frame(withdrawal_frame)
                    row_frame.pack(fill=tk.X, pady=2)

                var = tk.BooleanVar(value=False)
                self.withdrawal_vars[player] = var

                cb = ttk.Checkbutton(row_frame, text=player.name, variable=var)
                cb.pack(side=tk.LEFT, padx=10)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="💾 Save & Exit",
            command=self._save_and_exit_tournament,
        ).pack(side=tk.LEFT, padx=5)

        # Check if tournament is complete
        if self.schev_round >= self.schev_total_rounds:
            ttk.Button(
                btn_frame,
                text="View Final Standings",
                command=self.show_scheveningen_final,
            ).pack(side=tk.LEFT, padx=5)
        else:
            ttk.Button(
                btn_frame, text="Next Round", command=self.next_scheveningen_round
            ).pack(side=tk.LEFT, padx=5)
            ttk.Button(
                btn_frame,
                text="Finish Tournament",
                command=self.show_scheveningen_final,
            ).pack(side=tk.LEFT, padx=5)

    def next_scheveningen_round(self):
        """Process half-bye and withdrawal requests,
        then continue to next Scheveningen round"""
        self._flush_pending_round_requests()
        self.show_scheveningen_round()

    def show_scheveningen_final(self):
        """Show Scheveningen final results"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            frame, text="Scheveningen - Final Results", font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        # Calculate team scores
        team_a_score = sum(p.points for p in self.schev_team_a)
        team_b_score = sum(p.points for p in self.schev_team_b)

        # Determine winner
        if team_a_score > team_b_score:
            winner_text = f"Team A Wins! ({team_a_score} - {team_b_score})"
        elif team_b_score > team_a_score:
            winner_text = f"Team B Wins! ({team_b_score} - {team_a_score})"
        else:
            winner_text = f"Draw! ({team_a_score} - {team_b_score})"

        ttk.Label(frame, text=winner_text, font=("Arial", 16, "bold")).pack(pady=20)

        # Display teams with individual scores
        teams_frame = ttk.Frame(frame)
        teams_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Team A
        team_a_frame = ttk.LabelFrame(
            teams_frame, text=f"Team A ({team_a_score} points)", padding="10"
        )
        team_a_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        for p in sorted(self.schev_team_a, key=lambda x: x.points, reverse=True):
            ttk.Label(
                team_a_frame,
                text=f"{p.name}: {p.points} pts ({p.wins}W-{p.losses}L-{p.draws}D)",
                font=("Arial", 10),
            ).pack(anchor=tk.W, pady=2)

        # Team B
        team_b_frame = ttk.LabelFrame(
            teams_frame, text=f"Team B ({team_b_score} points)", padding="10"
        )
        team_b_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        for p in sorted(self.schev_team_b, key=lambda x: x.points, reverse=True):
            ttk.Label(
                team_b_frame,
                text=f"{p.name}: {p.points} pts ({p.wins}W-{p.losses}L-{p.draws}D)",
                font=("Arial", 10),
            ).pack(anchor=tk.W, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="📋 View Round-by-Round Details",
            command=lambda: self.show_round_by_round_viewer(
                self.tournament_history,
                return_to=self.show_scheveningen_final,
            ),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="💾 Save Tournament",
            command=self._save_finished_tournament,
        ).pack(side=tk.LEFT, padx=5)

    # ===== SHARED TOURNAMENT METHODS =====
    def _record_round_to_history(self, system):
        """Capture the current round's pairings and standings into tournament_history.
        Call this AFTER results have been applied to Player objects."""
        round_num = self.current_round  # For scheveningen, use self.schev_round instead

        # For scheveningen, use the schev_round counter
        if system == "scheveningen":
            round_num = getattr(self, "schev_round", self.current_round)

        # Build pairings record from self.tournament_results
        pairings_record = []
        for board_idx, (pairing, result_var) in enumerate(self.tournament_results, 1):
            p1, p2, pairing_type = pairing
            result = result_var.get()

            # Colour Balancing (chess tournament formats): by the time a
            # pairing reaches this point, p1 is always the White player
            # and p2 the Black player for a real game - byes are
            # colourless and get None/None. Recorded explicitly (rather
            # than leaving it as an implicit positional convention) so
            # history/exports/older code reading this back stay
            # unambiguous even if that convention ever changes.
            entry = {
                "board": board_idx,
                "player1": p1.name if p1 else None,
                "player2": p2.name if p2 else None,
                "player1_color": "white" if p2 else None,
                "player2_color": "black" if p2 else None,
                "result": result,  # "p1_win", "p2_win", "draw", "bye", "half_bye"
                "type": "bye" if p2 is None else "game",
            }
            pairings_record.append(entry)

        # Build standings snapshot AFTER results applied (captures post-round state)
        # For scheveningen, use combined player list
        if system == "scheveningen":
            all_players = getattr(self, "schev_team_a", []) + getattr(
                self, "schev_team_b", []
            )
            sorted_snap = self.apply_tiebreak(all_players)
        else:
            sorted_snap = self.apply_tiebreak(self.players)

        standings_snapshot = []
        for rank, (player, tb_score) in enumerate(sorted_snap, 1):
            # Determine status for display
            if player.withdrawn:
                status = f"Withdrew after R{player.withdrawal_round}"
            elif player.eliminated:
                status = "Eliminated"
            else:
                status = "Active"

            # For scheveningen, record team membership
            team = None
            if system == "scheveningen":
                if player in getattr(self, "schev_team_a", []):
                    team = "A"
                elif player in getattr(self, "schev_team_b", []):
                    team = "B"

            standings_snapshot.append(
                {
                    "rank": rank,
                    "name": player.name,
                    "rating": player.rating,
                    "points": player.points,
                    "wins": player.wins,
                    "losses": player.losses,
                    "draws": player.draws,
                    "byes": player.byes,
                    "half_byes": player.half_byes,
                    "white_games": player.white_games,
                    "black_games": player.black_games,
                    "tiebreak": round(tb_score, 2) if tb_score is not None else None,
                    "status": status,
                    "team": team,
                }
            )

        round_record = {
            "round_number": round_num,
            "system": system,
            "pairings": pairings_record,
            "standings_after_round": standings_snapshot,
        }

        self.tournament_history.append(round_record)

    def display_tournament_pairings(self, parent_frame, pairings, system):
        """Display tournament pairings with result selection"""
        results_frame = ttk.Frame(parent_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(results_frame, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        rating_name = "ELO" if self.game_type == "chess" else "Trophies"

        self.tournament_results = []

        for i, pairing in enumerate(pairings):
            p1, p2, result = pairing

            pair_frame = ttk.LabelFrame(
                scrollable_frame, text=f"Board {i + 1}", padding="10"
            )
            pair_frame.pack(fill=tk.X, padx=5, pady=5)

            if p2 is None:  # Bye or Half-bye
                if result == "half_bye":
                    ttk.Label(
                        pair_frame,
                        text=f"{p1.name} - HALF-BYE (0.5 points)",
                        font=("Arial", 11, "bold"),
                        foreground="blue",
                    ).pack(anchor=tk.W)
                    result_var = tk.StringVar(value="half_bye")
                else:
                    ttk.Label(
                        pair_frame,
                        text=f"{p1.name} - BYE (1 point)",
                        font=("Arial", 11, "bold"),
                    ).pack(anchor=tk.W)
                    result_var = tk.StringVar(value="bye")
                self.tournament_results.append((pairing, result_var))
            else:
                # Colour Balancing: p1/p2 arrive here already decided as
                # White/Black respectively (chess tournament formats
                # only) - show it so the director can see it, not just
                # infer it after the fact from exports.
                show_colors = self.game_type == "chess" and system in (
                    "swiss",
                    "round_robin",
                    "knockout",
                    "scheveningen",
                )
                p1_color_suffix = " (White)" if show_colors else ""
                p2_color_suffix = " (Black)" if show_colors else ""

                # Player 1
                p1_label = (
                    f"{p1.name}{p1_color_suffix} "
                    f"({rating_name}: {p1.rating}, Pts: {p1.points})"
                )
                ttk.Label(pair_frame, text=p1_label, font=("Arial", 10)).grid(
                    row=0, column=0, sticky=tk.W, padx=5
                )

                # VS
                ttk.Label(pair_frame, text="vs", font=("Arial", 10, "italic")).grid(
                    row=0, column=1, padx=10
                )

                # Player 2
                p2_label = (
                    f"{p2.name}{p2_color_suffix} "
                    f"({rating_name}: {p2.rating}, Pts: {p2.points})"
                )
                ttk.Label(pair_frame, text=p2_label, font=("Arial", 10)).grid(
                    row=0, column=2, sticky=tk.W, padx=5
                )

                # Result selection
                result_var = tk.StringVar(value="")
                self.tournament_results.append((pairing, result_var))

                result_frame = ttk.Frame(pair_frame)
                result_frame.grid(row=1, column=0, columnspan=3, pady=5)

                ttk.Radiobutton(
                    result_frame,
                    text=f"{p1.name} Wins",
                    variable=result_var,
                    value="p1_win",
                ).pack(side=tk.LEFT, padx=5)
                ttk.Radiobutton(
                    result_frame, text="Draw", variable=result_var, value="draw"
                ).pack(side=tk.LEFT, padx=5)
                ttk.Radiobutton(
                    result_frame,
                    text=f"{p2.name} Wins",
                    variable=result_var,
                    value="p2_win",
                ).pack(side=tk.LEFT, padx=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(parent_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="Finish Round",
            command=lambda: self.finish_tournament_round(system),
        ).pack(side=tk.LEFT, padx=5)

    def finish_tournament_round(self, system):
        """Process tournament round results"""
        # Check all matches have results
        for pairing, result_var in self.tournament_results:
            if result_var.get() == "" or result_var.get() not in [
                "p1_win", "p2_win", "draw", "bye", "half_bye"
            ]:
                messagebox.showwarning(
                    "Incomplete", "Please set results for all matches"
                )
                return

        # Apply results
        for pairing, result_var in self.tournament_results:
            p1, p2, _ = pairing
            result = result_var.get()

            if result == "bye":
                p1.byes += 1
                # No colour is recorded for a bye - FIDE treats it as
                # colourless, so it neither counts towards the balance
                # nor breaks a same-colour streak.
            elif result == "half_bye":
                p1.half_byes += 1
            elif result == "p1_win":
                p1.wins += 1
                p2.losses += 1
                p1.opponents.append(p2.name)
                p2.opponents.append(p1.name)
                p1.results_vs_opponents.append("win")
                p2.results_vs_opponents.append("loss")
                p1.colors.append("white")
                p2.colors.append("black")
            elif result == "p2_win":
                p2.wins += 1
                p1.losses += 1
                p1.opponents.append(p2.name)
                p2.opponents.append(p1.name)
                p1.results_vs_opponents.append("loss")
                p2.results_vs_opponents.append("win")
                p1.colors.append("white")
                p2.colors.append("black")
            elif result == "draw":
                p1.draws += 1
                p2.draws += 1
                p1.opponents.append(p2.name)
                p2.opponents.append(p1.name)
                p1.results_vs_opponents.append("draw")
                p2.results_vs_opponents.append("draw")
                p1.colors.append("white")
                p2.colors.append("black")

        # Handle elimination for knockout
        if system == "knockout":
            # Standard rule: a draw eliminates BOTH players, since neither
            # has earned the right to advance over the other.
            #
            # Exception: if eliminating every drawn pair this round would
            # leave the bracket with zero active players, that's not a
            # valid outcome (the tournament needs a winner) - so none of
            # this round's drawn players are eliminated, and they simply
            # get re-paired next round (generate_knockout_pairings already
            # re-pairs anyone still active) to play it out again. This
            # covers the common case of a drawn final, and the rarer case
            # of a round where every single pairing ends in a draw.
            active_before = [p for p in self.players if not p.eliminated]
            decisive_losers = set()
            drawn_players = set()
            for pairing, result_var in self.tournament_results:
                p1, p2, _ = pairing
                result = result_var.get()
                if result == "p1_win" and p2:
                    decisive_losers.add(p2)
                elif result == "p2_win" and p1:
                    decisive_losers.add(p1)
                elif result == "draw" and p2:
                    drawn_players.add(p1)
                    drawn_players.add(p2)

            would_remain = [
                p
                for p in active_before
                if p not in decisive_losers and p not in drawn_players
            ]
            draws_must_replay = bool(drawn_players) and not would_remain

            for player in decisive_losers:
                player.eliminated = True
            if not draws_must_replay:
                for player in drawn_players:
                    player.eliminated = True

        self._record_round_to_history(system)

        # Apply rating changes based on mode
        if self.rating_mode == "automatic" and self.game_type == "chess":
            # Automatic ELO calculation
            self.apply_automatic_elo_changes()
            # Then show standings
            if system == "swiss" or system == "round_robin":
                self.show_tournament_standings(system)
            elif system == "knockout":
                active = [p for p in self.players if not p.eliminated]
                if len(active) == 1:
                    self.show_tournament_winner(active[0])
                else:
                    self.current_round += 1
                    self.show_knockout_round()
            elif system == "scheveningen":
                self.show_scheveningen_standings()

        elif self.rating_mode == "manual" or (
            self.rating_mode == "ranked" and self.game_type == "esports"
        ):
            # Manual rating update - show interface then proceed
            def proceed_after_rating_update():
                if system == "swiss" or system == "round_robin":
                    self.show_tournament_standings(system)
                elif system == "knockout":
                    active = [p for p in self.players if not p.eliminated]
                    if len(active) == 1:
                        self.show_tournament_winner(active[0])
                    else:
                        self.current_round += 1
                        self.show_knockout_round()
                elif system == "scheveningen":
                    self.show_scheveningen_standings()

            self.show_manual_rating_update(proceed_after_rating_update)

        else:
            # Unranked - no rating changes, proceed directly
            if system == "swiss" or system == "round_robin":
                self.show_tournament_standings(system)
            elif system == "knockout":
                active = [p for p in self.players if not p.eliminated]
                if len(active) == 1:
                    self.show_tournament_winner(active[0])
                else:
                    self.current_round += 1
                    self.show_knockout_round()
            elif system == "scheveningen":
                self.show_scheveningen_standings()

    def show_tournament_standings(self, system):
        """Show tournament standings after a round"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        system_name = "Swiss System" if system == "swiss" else "Round-Robin"
        title = ttk.Label(
            frame,
            text=f"{system_name} - Standings After Round {self.current_round}",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        # Sort with tiebreak
        sorted_players = self.apply_tiebreak(self.players)

        # Display standings
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=[
                "rank",
                "name",
                "rating",
                "points",
                "wins",
                "losses",
                "draws",
                "byes",
                "hbyes",
                "white",
                "black",
                "tiebreak",
            ],
            show="headings",
            height=12,
        )

        tree.heading("rank", text="Rank")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO")
        tree.heading("points", text="Points")
        tree.heading("wins", text="W")
        tree.heading("losses", text="L")
        tree.heading("draws", text="D")
        tree.heading("byes", text="Bye")
        tree.heading("hbyes", text="½Bye")
        tree.heading("white", text="White")
        tree.heading("black", text="Black")
        tree.heading("tiebreak", text="TB")

        tree.column("rank", width=45)
        tree.column("name", width=110)
        tree.column("rating", width=55)
        tree.column("points", width=55)
        tree.column("wins", width=35)
        tree.column("losses", width=35)
        tree.column("draws", width=35)
        tree.column("byes", width=35)
        tree.column("hbyes", width=40)
        tree.column("white", width=45)
        tree.column("black", width=45)
        tree.column("tiebreak", width=60)

        for i, (player, tb_score) in enumerate(sorted_players, 1):
            tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    player.name,
                    player.rating,
                    player.points,
                    player.wins,
                    player.losses,
                    player.draws,
                    player.byes,
                    player.half_byes,
                    player.white_games,
                    player.black_games,
                    f"{tb_score:.1f}" if tb_score is not None else "-",
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Half-bye request section (if enabled)
        if self.half_bye_enabled:
            halfbye_frame = ttk.LabelFrame(
                frame, text="Half-Bye Requests for Next Round", padding="10"
            )
            halfbye_frame.pack(fill=tk.X, pady=5, padx=10)

            ttk.Label(
                halfbye_frame,
                text=(
                    "Players can request a half-bye (0.5 points) "
                    "to skip the next round."
                ),
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each player, keyed by player object
            # (not name) so two same-named players never collide.
            self.halfbye_vars = {}
            players_per_row = 3
            row_frame = None

            for i, player in enumerate(
                [p for p in self.players if not p.eliminated and not p.withdrawn]
            ):
                if i % players_per_row == 0:
                    row_frame = ttk.Frame(halfbye_frame)
                    row_frame.pack(fill=tk.X, pady=2)

                var = tk.BooleanVar(value=False)
                self.halfbye_vars[player] = var

                cb = ttk.Checkbutton(row_frame, text=player.name, variable=var)
                cb.pack(side=tk.LEFT, padx=10)

        # Withdrawal request section (if enabled)
        if self.withdrawal_enabled:
            withdrawal_frame = ttk.LabelFrame(
                frame, text="Player Withdrawals", padding="10"
            )
            withdrawal_frame.pack(fill=tk.X, pady=5, padx=10)

            ttk.Label(
                withdrawal_frame,
                text=(
                    "Select players to withdraw from the tournament "
                    "(they keep their current score)."
                ),
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each active player, keyed by player
            # object (not name) so two same-named players never collide.
            self.withdrawal_vars = {}
            players_per_row = 3
            row_frame = None

            for i, player in enumerate(
                [p for p in self.players if not p.eliminated and not p.withdrawn]
            ):
                if i % players_per_row == 0:
                    row_frame = ttk.Frame(withdrawal_frame)
                    row_frame.pack(fill=tk.X, pady=2)

                var = tk.BooleanVar(value=False)
                self.withdrawal_vars[player] = var

                cb = ttk.Checkbutton(row_frame, text=player.name, variable=var)
                cb.pack(side=tk.LEFT, padx=10)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="💾 Save & Exit",
            command=self._save_and_exit_tournament,
        ).pack(side=tk.LEFT, padx=5)

        # Check if tournament should continue or auto-finish
        should_auto_finish = False

        if system == "swiss":
            # Check if max rounds set and reached
            if self.max_rounds and self.current_round >= self.max_rounds:
                should_auto_finish = True

        elif system == "round_robin":
            # Use the stable total set at tournament start; fall back to
            # computing from non-withdrawn players only for old saves.
            natural_total_rounds = getattr(self, "round_robin_total_rounds", 0)
            if not natural_total_rounds:
                n = len([p for p in self.players if not p.withdrawn])
                natural_total_rounds = n - 1 if n % 2 == 0 else n

            if self.max_rounds:
                # Max rounds set - use it
                if self.current_round >= self.max_rounds:
                    should_auto_finish = True
            else:
                # No max rounds - use natural end
                if self.current_round >= natural_total_rounds:
                    should_auto_finish = True

        # Show appropriate buttons
        if should_auto_finish:
            # Max rounds reached - only show finish button
            ttk.Button(
                btn_frame,
                text="View Final Standings",
                command=self.show_tournament_final_standings,
            ).pack(side=tk.LEFT, padx=5)
        else:
            # Can continue - show next round button
            ttk.Button(
                btn_frame,
                text="Next Round",
                command=lambda: self.next_tournament_round_with_settings(system),
            ).pack(side=tk.LEFT, padx=5)

            # Also show finish tournament button (director can end early)
            ttk.Button(
                btn_frame,
                text="Finish Tournament",
                command=self.show_tournament_final_standings,
            ).pack(side=tk.LEFT, padx=5)

    def _flush_pending_round_requests(self):
        """Write any pending half-bye and withdrawal checkbox states to player
        objects.  Must be called before saving or advancing to the next round
        so that requests made on the standings screen are not lost.
        Safe to call even when the checkboxes were never shown (no-ops).

        Shared by every tournament system (Swiss, Round-Robin, and
        Scheveningen) - there is no per-system variant of this logic
        anymore, so a future fix here automatically applies everywhere.
        """
        # Use the correct round counter — Scheveningen tracks its own round.
        current_rnd = getattr(self, "schev_round", None) or self.current_round

        # Apply withdrawal requests
        if self.withdrawal_enabled and hasattr(self, "withdrawal_vars"):
            for player, var in self.withdrawal_vars.items():
                if var.get():
                    player.withdrawn = True
                    player.withdrawal_round = current_rnd

        # Apply half-bye requests
        if self.half_bye_enabled and hasattr(self, "halfbye_vars"):
            for player, var in self.halfbye_vars.items():
                if var.get():
                    player.requested_half_bye = True

    def next_tournament_round_with_settings(self, system):
        """Process half-bye and withdrawal requests, then continue to next round"""
        self._flush_pending_round_requests()
        self.next_tournament_round()

    def apply_tiebreak(self, players):
        """Apply tiebreak method and return sorted players with tiebreak scores"""
        # Separate withdrawn and active players
        active_players = [p for p in players if not p.withdrawn]
        withdrawn_players = [p for p in players if p.withdrawn]

        result = []

        # Process active players with tiebreaks
        for player in active_players:
            tb_score = None

            # opponents/results_vs_opponents are parallel lists - pair them
            # up safely even if an old save has a length mismatch (results
            # missing or shorter), treating any unmatched entry as unknown.
            opponent_results = list(
                zip(player.opponents, player.results_vs_opponents)
            )
            if len(player.opponents) > len(opponent_results):
                opponent_results += [
                    (n, "") for n in player.opponents[len(opponent_results) :]
                ]

            if self.tiebreak_method == "buchholz":
                # Sum of opponents' scores
                tb_score = 0
                for opp_name in player.opponents:
                    for p in players:
                        if p.name == opp_name:
                            tb_score += p.points
                            break
            elif self.tiebreak_method == "sonneborn_berger":
                # Sum of each opponent's own score, weighted by how the
                # player did against THEM specifically: full credit for a
                # win, half for a draw, nothing for a loss. This is the
                # standard FIDE definition - it depends on the outcome of
                # each individual game, not just who was played.
                tb_score = 0
                for opp_name, outcome in opponent_results:
                    for p in players:
                        if p.name == opp_name:
                            if outcome == "win":
                                tb_score += p.points
                            elif outcome == "draw":
                                tb_score += p.points * 0.5
                            # "loss" (or unknown, from an old save)
                            # contributes 0.
                            break
            elif self.tiebreak_method == "rating":
                tb_score = player.rating
            elif self.tiebreak_method == "direct_encounter":
                # Result of the head-to-head game(s) against opponents who
                # are tied with this player on points - the standard
                # Direct Encounter definition. Restricting to opponents
                # with the SAME points total is what makes this a
                # standalone numeric score rather than a special grouping
                # pass: a player's score only reflects games that are
                # actually relevant to resolving their current tie.
                #
                # If the tied players never played each other (common in
                # Swiss events, since pairings aren't guaranteed to cover
                # every tied pair), this naturally comes out to 0 for
                # everyone involved - an honest "unresolved" result,
                # rather than a guess. There's no secondary tiebreak
                # configured in this app to fall back to in that case.
                tb_score = 0
                for opp_name, outcome in opponent_results:
                    for p in players:
                        if p.name == opp_name and p.points == player.points:
                            if outcome == "win":
                                tb_score += 1.0
                            elif outcome == "draw":
                                tb_score += 0.5
                            # "loss" contributes 0.
                            break

            result.append((player, tb_score))

        # Sort active players by points (primary) and tiebreak (secondary)
        result.sort(
            key=lambda x: (x[0].points, x[1] if x[1] is not None else 0), reverse=True
        )

        # Sort withdrawn players by points (primary), then score_rate, then games_played
        # This ensures fair ranking: 3/3 (withdrawn) > 2/2 (withdrawn) > 2/5 (active)
        withdrawn_sorted = sorted(
            withdrawn_players,
            key=lambda p: (p.points, p.score_rate, p.games_played),
            reverse=True,
        )

        # Integrate withdrawn players into the main ranking based on points
        """Players with equal points: active players rank first
        (they completed the tournament)"""
        final_result = []
        active_idx = 0
        withdrawn_idx = 0

        while active_idx < len(result) or withdrawn_idx < len(withdrawn_sorted):
            # If we've exhausted one list, add from the other
            if active_idx >= len(result):
                final_result.append((withdrawn_sorted[withdrawn_idx], None))
                withdrawn_idx += 1
                continue

            if withdrawn_idx >= len(withdrawn_sorted):
                final_result.append(result[active_idx])
                active_idx += 1
                continue

            # Compare points - higher points come first regardless of withdrawal status
            active_player, active_tb = result[active_idx]
            withdrawn_player = withdrawn_sorted[withdrawn_idx]

            if active_player.points > withdrawn_player.points:
                # Active player has more points - they rank higher
                final_result.append((active_player, active_tb))
                active_idx += 1
            elif withdrawn_player.points > active_player.points:
                # Withdrawn player has more points - they rank higher
                # Example: 3/3 withdrawn ranks above 2/5 active
                final_result.append((withdrawn_player, None))
                withdrawn_idx += 1
            else:
                # Equal points - active players rank first (completed tournament)
                # Example: 2/5 active ranks above 2/2 withdrawn (same 2 points)
                final_result.append((active_player, active_tb))
                active_idx += 1

        return final_result

    def next_tournament_round(self):
        """Continue to next tournament round"""
        self.current_round += 1

        if self.tournament_system == "swiss":
            self.show_swiss_round()
        elif self.tournament_system == "round_robin":
            self.show_round_robin_round()

    def show_tournament_final_standings(self):
        """Show final tournament standings"""
        # Auto-save players when tournament ends
        self.auto_save_players()

        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        system_names = {
            "swiss": "Swiss System",
            "round_robin": "Round-Robin",
            "knockout": "Knockout",
        }
        system_name = system_names.get(self.tournament_system, "Tournament")

        title = ttk.Label(
            frame, text=f"{system_name} - Final Standings", font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        # Get sorted players with tiebreak
        sorted_players = self.apply_tiebreak(self.players)

        # Show winner
        if sorted_players:
            winner = sorted_players[0][0]
            ttk.Label(
                frame, text=f"🏆 Winner: {winner.name} 🏆", font=("Arial", 16, "bold")
            ).pack(pady=10)

        # Display full standings
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=[
                "rank",
                "name",
                "rating",
                "points",
                "record",
                "status",
                "tiebreak",
            ],
            show="headings",
            height=15,
        )

        tree.heading("rank", text="Rank")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO")
        tree.heading("points", text="Points")
        tree.heading("record", text="Record")
        tree.heading("status", text="Status")
        tree.heading("tiebreak", text="Tiebreak")

        tree.column("rank", width=50)
        tree.column("name", width=130)
        tree.column("rating", width=70)
        tree.column("points", width=70)
        tree.column("record", width=120)
        tree.column("status", width=100)
        tree.column("tiebreak", width=80)

        for i, (player, tb_score) in enumerate(sorted_players, 1):
            record = f"{player.wins}W-{player.losses}L-{player.draws}D"
            if player.byes > 0:
                record += f"-{player.byes}Bye"
            if player.half_byes > 0:
                record += f"-{player.half_byes}½Bye"

            # Status column
            if player.withdrawn:
                status = f"Withdrew after R{player.withdrawal_round}"
            else:
                status = "Completed"

            tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    player.name,
                    player.rating,
                    player.points,
                    record,
                    status,
                    f"{tb_score:.1f}" if tb_score is not None else "-",
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="📋 View Round-by-Round Details",
            command=lambda: self.show_round_by_round_viewer(
                self.tournament_history,
                return_to=self.show_tournament_final_standings,
            ),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="💾 Save Tournament",
            command=self._save_finished_tournament,
        ).pack(side=tk.LEFT, padx=5)

    def show_tournament_winner(self, winner):
        """Show tournament winner"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        ttk.Label(
            frame, text="🏆 TOURNAMENT WINNER! 🏆", font=("Arial", 24, "bold")
        ).pack(pady=20)

        winner_frame = ttk.LabelFrame(frame, text="Champion", padding="20")
        winner_frame.pack(pady=20)

        ttk.Label(winner_frame, text=winner.name, font=("Arial", 20, "bold")).pack(
            pady=10
        )
        ttk.Label(winner_frame, text=f"ELO: {winner.rating}", font=("Arial", 14)).pack(
            pady=5
        )
        ttk.Label(
            winner_frame, text=f"Points: {winner.points}", font=("Arial", 14)
        ).pack(pady=5)

        record = f"Record: {winner.wins}W - {winner.losses}L - {winner.draws}D"
        if winner.byes > 0:
            record += f" - {winner.byes}Bye"
        if winner.half_byes > 0:
            record += f" - {winner.half_byes}½Bye"

        ttk.Label(winner_frame, text=record, font=("Arial", 12)).pack(pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame,
            text="📋 View Round-by-Round Details",
            command=lambda: self.show_round_by_round_viewer(
                self.tournament_history,
                return_to=lambda: self.show_tournament_winner(winner),
            ),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="💾 Save Tournament",
            command=self._save_finished_tournament,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="View Final Standings",
            command=self.show_tournament_final_standings,
        ).pack(side=tk.LEFT, padx=5)

    # ============ CSV EXPORT ============

    def export_tournament_to_csv(self, history: list, meta: dict = None) -> None:
        """Export tournament history to a user-chosen CSV file.

        The file is written with a UTF-8 BOM so that Excel opens it correctly
        without any import-wizard steps.  Sections are separated by blank rows
        so the file is still human-readable in a plain text editor.

        Parameters
        ----------
        history : list
            List of round dicts (same structure as ``tournament_history``).
        meta : dict, optional
            Extra metadata fields.  Expected keys (all optional):
            ``tournament_system``, ``tournament_start_time``, ``finished``,
            ``tiebreak_method``, ``current_round``.
        """
        if not history:
            messagebox.showinfo("No Data", "No round history available to export.")
            return

        if meta is None:
            meta = {}

        # Build a sensible default filename ─────────────────────────────────
        system = meta.get("tournament_system") or "tournament"
        timestamp = (meta.get("tournament_start_time") or "").replace(":", "-").replace(" ", "_")
        hint = (
            f"tournament_{timestamp}_{system}_export"
            if timestamp
            else f"tournament_{system}_export"
        )

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=hint,
            title="Export Tournament as CSV",
        )
        if not save_path:
            return  # User cancelled

        # Display-friendly labels ────────────────────────────────────────────
        system_display = {
            "swiss": "Swiss System",
            "round_robin": "Round-Robin",
            "knockout": "Knockout",
            "scheveningen": "Scheveningen",
        }.get(system, system.replace("_", " ").title())

        tiebreak_raw = meta.get("tiebreak_method") or ""
        tiebreak_display = {
            "buchholz": "Buchholz",
            "sonneborn_berger": "Sonneborn-Berger",
            "direct_encounter": "Direct Encounter",
            "rating": "Rating",
        }.get(tiebreak_raw, tiebreak_raw.replace("_", " ").title() if tiebreak_raw else "—")

        result_map = {
            "p1_win": "1 – 0",
            "p2_win": "0 – 1",
            "draw": "½ – ½",
            "bye": "BYE (+1 pt)",
            "half_bye": "HALF-BYE (+0.5 pt)",
        }

        is_schev = (system == "scheveningen")

        try:
            # utf-8-sig writes a BOM, which tells Excel the file is UTF-8.
            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)

                # ── Section 1: Tournament metadata ───────────────────────────
                w.writerow(["TOURNAMENT INFO"])
                w.writerow(["System", system_display])
                start_raw = meta.get("tournament_start_time") or ""
                w.writerow(["Start Time", start_raw.replace("_", " ")])
                w.writerow(
                    ["Status", "Finished" if meta.get("finished", True) else "Unfinished"]
                )
                w.writerow(["Tiebreak Method", tiebreak_display])
                w.writerow(
                    ["Total Rounds Played", meta.get("current_round", len(history))]
                )

                # ── Section 2: Final standings ────────────────────────────────
                w.writerow([])
                w.writerow(["FINAL STANDINGS"])
                last_round = history[-1]
                standings = last_round.get("standings_after_round", [])

                if is_schev:
                    w.writerow(
                        ["Rank", "Team", "Name", "ELO", "Points",
                         "Wins", "Losses", "Draws", "Byes", "Half-Byes",
                         "White", "Black", "Tiebreak", "Status"]
                    )
                    for s in standings:
                        w.writerow([
                            s["rank"],
                            s.get("team") or "—",
                            s["name"],
                            s["rating"],
                            s["points"],
                            s["wins"],
                            s["losses"],
                            s["draws"],
                            s["byes"],
                            s["half_byes"],
                            s.get("white_games", "—"),
                            s.get("black_games", "—"),
                            s["tiebreak"] if s["tiebreak"] is not None else "—",
                            s["status"],
                        ])
                else:
                    w.writerow(
                        ["Rank", "Name", "ELO", "Points",
                         "Wins", "Losses", "Draws", "Byes", "Half-Byes",
                         "White", "Black", "Tiebreak", "Status"]
                    )
                    for s in standings:
                        w.writerow([
                            s["rank"],
                            s["name"],
                            s["rating"],
                            s["points"],
                            s["wins"],
                            s["losses"],
                            s["draws"],
                            s["byes"],
                            s["half_byes"],
                            s.get("white_games", "—"),
                            s.get("black_games", "—"),
                            s["tiebreak"] if s["tiebreak"] is not None else "—",
                            s["status"],
                        ])

                # ── Section 3+: Per-round details ─────────────────────────────
                for rnd in history:
                    rnum = rnd["round_number"]

                    w.writerow([])
                    w.writerow([f"ROUND {rnum} – PAIRINGS"])
                    w.writerow(["Board", "Player 1 (White)", "Result", "Player 2 (Black)"])
                    for p in rnd.get("pairings", []):
                        p2_disp = p["player2"] if p["player2"] else "—"
                        res_disp = result_map.get(p["result"], p["result"])
                        w.writerow([p["board"], p["player1"], res_disp, p2_disp])

                    w.writerow([])
                    w.writerow([f"ROUND {rnum} – STANDINGS AFTER ROUND"])
                    round_standings = rnd.get("standings_after_round", [])

                    if is_schev:
                        w.writerow(
                            ["Rank", "Team", "Name", "Points",
                             "Wins", "Losses", "Draws", "Byes", "Half-Byes",
                             "White", "Black", "Tiebreak", "Status"]
                        )
                        for s in round_standings:
                            w.writerow([
                                s["rank"],
                                s.get("team") or "—",
                                s["name"],
                                s["points"],
                                s["wins"],
                                s["losses"],
                                s["draws"],
                                s["byes"],
                                s["half_byes"],
                                s.get("white_games", "—"),
                                s.get("black_games", "—"),
                                s["tiebreak"] if s["tiebreak"] is not None else "—",
                                s["status"],
                            ])
                    else:
                        w.writerow(
                            ["Rank", "Name", "Points",
                             "Wins", "Losses", "Draws", "Byes", "Half-Byes",
                             "White", "Black", "Tiebreak", "Status"]
                        )
                        for s in round_standings:
                            w.writerow([
                                s["rank"],
                                s["name"],
                                s["points"],
                                s["wins"],
                                s["losses"],
                                s["draws"],
                                s["byes"],
                                s["half_byes"],
                                s.get("white_games", "—"),
                                s.get("black_games", "—"),
                                s["tiebreak"] if s["tiebreak"] is not None else "—",
                                s["status"],
                            ])

            messagebox.showinfo(
                "Export Successful", f"Tournament exported to:\n{save_path}"
            )

        except Exception as exc:
            messagebox.showerror("Export Error", f"Could not write CSV file:\n{exc}")

    def _export_csv_from_filepath(self, filepath: str) -> None:
        """Load a saved tournament JSON file and export its history to CSV.

        Used by the Load Tournament screen so the user can export a tournament
        without having to open it first.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not read tournament file:\n{exc}")
            return

        history = data.get("tournament_history", [])
        if not history:
            messagebox.showinfo(
                "No Data",
                "This tournament has no round-by-round history to export.\n\n"
                "Only tournaments that have completed at least one round "
                "contain exportable data.",
            )
            return

        meta = {
            "tournament_system": data.get("tournament_system"),
            "tournament_start_time": data.get("tournament_start_time", ""),
            "finished": data.get("finished", False),
            "tiebreak_method": data.get("tiebreak_method", ""),
            "current_round": data.get("current_round", len(history)),
        }
        self.export_tournament_to_csv(history, meta)

    # ============ END CSV EXPORT ============

    # ============ TRF16 EXPORT ============
    #
    # FIDE's "Tournament Report File" format (C.04 Annex 2, TRF16),
    # https://www.fide.com/FIDE/handbook/C04Annex2_TRF16.pdf - a fixed-
    # column-width plain text format used for pairing/tiebreak
    # verification tools and, when the demographic fields are filled in,
    # for actual FIDE rating submission. Every column position below is
    # taken directly from that spec.

    _TRF_TITLES = ("GM", "IM", "WGM", "FM", "WIM", "CM", "WFM", "WCM")

    @staticmethod
    def _trf_set(line: list, col_1indexed: int, text: str, width: int) -> None:
        """Place `text` (left-justified, space-padded/truncated to
        `width`) starting at 1-indexed column `col_1indexed` of a
        mutable list of characters, extending the list with spaces if
        it isn't long enough yet."""
        start = col_1indexed - 1
        text = (text or "")[:width]
        needed = start + width
        if len(line) < needed:
            line.extend([" "] * (needed - len(line)))
        for i, ch in enumerate(text):
            line[start + i] = ch

    def _trf_tournament_lines(self, meta: dict) -> list:
        """Build the Tournament Section lines (012, 022, 032, ...). Every
        one of these fields is free text after the 3-digit code (per the
        spec's own "position 1-3 ... from position 5 (free text)"
        pattern) - there's no numeric code table to get right here,
        unlike the Player Section."""
        lines = []

        def add(code, text):
            if text:
                lines.append(f"{code} {text}")

        add("012", meta.get("name"))
        add("022", meta.get("city"))
        add("032", meta.get("federation"))
        add("042", meta.get("date_start"))
        add("052", meta.get("date_end"))
        add("062", str(meta.get("num_players")) if meta.get("num_players") else None)
        add("092", meta.get("tournament_type"))
        add("102", meta.get("chief_arbiter"))
        add("112", meta.get("deputy_arbiters"))
        add("122", meta.get("time_control"))

        round_dates = meta.get("round_dates") or []
        if round_dates:
            line = list("132")
            for i, d in enumerate(round_dates):
                col = 92 + i * 10
                self._trf_set(line, col, d, 8)
            lines.append("".join(line).rstrip())

        return lines

    def _trf_result_for_player(self, player_name, rank_by_name, round_entry):
        """Return (opponent_id_str, colour_char, result_char) for one
        player in one already-played round, or the "absent" triple if
        they don't appear in that round's pairings at all (this is how a
        withdrawn or eliminated player's later rounds show up, since
        this app simply stops generating pairings for them - see
        _build_players_from_save_data/withdrawn filtering)."""
        for pr in round_entry.get("pairings", []):
            side = None
            if pr.get("player1") == player_name:
                side = "p1"
            elif pr.get("player2") == player_name:
                side = "p2"
            if side is None:
                continue

            if pr.get("player2") is None:
                # A bye of some kind - never colourless-mandatory Z here,
                # since the player WAS accounted for this round, just not
                # paired against anyone.
                result = pr.get("result")
                # "half_bye" is this app's voluntary, 0.5-point sit-out -
                # exactly TRF's "H". Anything else unpaired ("bye") is a
                # bye the PAIRING SYSTEM assigned (an odd player out, or
                # the opponent of someone else's half-bye) - TRF's "U".
                result_char = "H" if result == "half_bye" else "U"
                return "0000", "-", result_char

            opp_name = pr["player2"] if side == "p1" else pr["player1"]
            opp_rank = rank_by_name.get(opp_name)
            opp_id_str = f"{opp_rank:04d}" if opp_rank else "0000"

            color_raw = pr.get("player1_color") if side == "p1" else pr.get(
                "player2_color"
            )
            color_char = {"white": "w", "black": "b"}.get(color_raw, "-")

            result = pr.get("result")
            if side == "p1":
                result_char = {"p1_win": "1", "p2_win": "0", "draw": "="}.get(
                    result, " "
                )
            else:
                result_char = {"p1_win": "0", "p2_win": "1", "draw": "="}.get(
                    result, " "
                )
            return opp_id_str, color_char, result_char

        # Not found in this round at all - known absence (withdrawn or
        # eliminated before this round; TRF's "Z").
        return "0000", "-", "Z"

    def _trf_player_line(self, player, starting_rank, standing_rank, rank_by_name, history):
        line = list("001")
        self._trf_set(line, 5, str(starting_rank), 4)
        self._trf_set(line, 10, (player.sex or "").lower(), 1)
        self._trf_set(line, 11, player.title or "", 3)
        display_name = f"{player.last_name}, {player.first_name}".strip(", ")
        if not display_name:
            display_name = player.name
        self._trf_set(line, 15, display_name, 33)
        fide_rating = player.initial_rating if player.initial_rating is not None else player.rating
        self._trf_set(line, 49, str(fide_rating), 4)
        self._trf_set(line, 54, player.fide_federation or "", 3)
        self._trf_set(line, 58, player.fide_id or "", 11)
        self._trf_set(line, 70, player.birth_date or "", 10)
        # Points field is a fixed 4-char column (81-84). "%.1f" normally
        # fits ("11.5"), but at 100+ points ("100.0") that's 5 chars -
        # slicing it in _trf_set would silently drop the decimal digit
        # and leave a malformed trailing-dot token ("100."). Fall back to
        # an integer-only representation in that case instead - still
        # technically off-spec (FIDE never anticipated 100+ point
        # totals) but at least a valid, unambiguous number rather than a
        # truncated non-number.
        points_str = f"{player.points:.1f}"
        if len(points_str) > 4:
            points_str = f"{player.points:.0f}"
        self._trf_set(line, 81, points_str, 4)
        self._trf_set(line, 86, str(standing_rank), 4)

        for round_idx, round_entry in enumerate(history):
            opp_id, color_char, result_char = self._trf_result_for_player(
                player.name, rank_by_name, round_entry
            )
            base = 92 + round_idx * 10
            self._trf_set(line, base, opp_id, 4)
            self._trf_set(line, base + 5, color_char, 1)
            self._trf_set(line, base + 7, result_char, 1)

        return "".join(line).rstrip()

    def _trf_team_line(self, team_name, member_names, rank_by_name):
        line = list("013")
        self._trf_set(line, 5, team_name, 32)
        for i, name in enumerate(member_names):
            rank = rank_by_name.get(name)
            col = 37 + i * 5
            self._trf_set(line, col, str(rank) if rank else "", 4)
        return "".join(line).rstrip()

    def build_trf16_content(
        self, players: list, history: list, starting_rank_names: list, meta: dict,
        team_a=None, team_b=None, team_a_name="Team A", team_b_name="Team B",
    ) -> str:
        """Assemble the full TRF16 text content. `players` must be full
        Player objects (apply_tiebreak needs opponents/results_vs_opponents).
        `starting_rank_names` is the tournament's fixed starting-rank
        order (see _compute at tournament start) - falls back to
        descending current rating if unavailable (e.g. a very old save)."""
        if not starting_rank_names:
            starting_rank_names = [
                p.name
                for p in sorted(players, key=lambda p: p.rating, reverse=True)
            ]
        rank_by_name = {name: i + 1 for i, name in enumerate(starting_rank_names)}
        # Any player not in the starting-rank list at all (shouldn't
        # normally happen) still gets a rank rather than breaking export.
        next_rank = len(rank_by_name) + 1
        for p in players:
            if p.name not in rank_by_name:
                rank_by_name[p.name] = next_rank
                next_rank += 1

        meta = dict(meta or {})
        meta.setdefault("num_players", len(players))

        lines = self._trf_tournament_lines(meta)

        # Standing rank (column 86-89) reflects FINAL tiebreak-resolved
        # standing, not starting rank - these are two different numbers
        # in TRF and this app already computes the former via
        # apply_tiebreak exactly as the standings screens do.
        sorted_players = self.apply_tiebreak(players)
        standing_rank = {p.name: i + 1 for i, (p, _tb) in enumerate(sorted_players)}

        for player in sorted(players, key=lambda p: rank_by_name.get(p.name, 1 << 30)):
            starting_rank = rank_by_name[player.name]
            standing_rank_value = standing_rank.get(player.name, starting_rank)
            lines.append(
                self._trf_player_line(
                    player, starting_rank, standing_rank_value, rank_by_name, history
                )
            )

        if team_a is not None and team_b is not None:
            lines.append(
                self._trf_team_line(team_a_name, [p.name for p in team_a], rank_by_name)
            )
            lines.append(
                self._trf_team_line(team_b_name, [p.name for p in team_b], rank_by_name)
            )

        return "\n".join(lines) + "\n"

    def _show_trf_metadata_dialog(self, default_name: str, on_confirm):
        """Small modal dialog collecting the Tournament Section fields
        TRF16 doesn't have anywhere else to pull from (this app has no
        persistent notion of tournament name/city/arbiter/time control).
        Every field is optional except Tournament Name - a blank name is
        allowed too (TRF only warns, doesn't reject), but a real name
        makes the file far more useful, so it's the one field with a
        sensible pre-filled default instead of being left empty.
        Calls on_confirm(meta_dict) if the user clicks Export, or does
        nothing if they cancel."""
        dialog = tk.Toplevel(self.root)
        dialog.title("TRF16 Export Details")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="These details are optional (except leaving Tournament\n"
            "Name blank is allowed too) - fill in what you have.",
            font=("Arial", 9, "italic"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)

        fields = [
            ("name", "Tournament Name:", default_name),
            ("city", "City:", ""),
            ("federation", "Federation (3-letter code):", ""),
            ("chief_arbiter", "Chief Arbiter:", ""),
            ("deputy_arbiters", "Deputy Arbiter(s):", ""),
            ("time_control", "Time Control:", ""),
            ("date_start", "Start Date (YYYY/MM/DD):", ""),
            ("date_end", "End Date (YYYY/MM/DD):", ""),
        ]
        entries = {}
        for i, (key, label, default) in enumerate(fields, start=1):
            ttk.Label(frame, text=label, font=("Arial", 10)).grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=4
            )
            entry = ttk.Entry(frame, width=30, font=("Arial", 10))
            entry.insert(0, default)
            entry.grid(row=i, column=1, padx=5, pady=4)
            entries[key] = entry

        def confirm():
            result_meta = {k: e.get().strip() or None for k, e in entries.items()}
            dialog.destroy()
            on_confirm(result_meta)

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Export", command=confirm).pack(
            side=tk.LEFT, padx=5
        )

        dialog.wait_window()

    def _write_trf16(
        self, players, history, starting_rank_names, tournament_system,
        default_name, team_a=None, team_b=None, team_a_name="Team A",
        team_b_name="Team B",
    ):
        """Shared tail end of both TRF export entry points: Knockout
        warning, metadata dialog, save-file dialog, write."""
        if tournament_system == "knockout":
            proceed = messagebox.askyesno(
                "TRF16 and Knockout",
                "TRF16 assumes every player's score accumulates across "
                "all rounds of the same event - it's built around Swiss "
                "and Round-Robin-style tournaments. A Knockout eliminates "
                "players partway through, which doesn't really fit that "
                "model (and FIDE wouldn't rate a Knockout using this "
                "format).\n\n"
                "A file can still be generated - eliminated players will "
                "simply show as absent for their remaining rounds - but "
                "it may not be meaningful for real submission or for "
                "other software to import.\n\n"
                "Export anyway?",
            )
            if not proceed:
                return

        def on_confirm(meta):
            meta["tournament_type"] = {
                "swiss": "Individual: Swiss System",
                "round_robin": "Individual: Round-Robin",
                "knockout": "Individual: Knockout",
                "scheveningen": "Team-Swiss: Scheveningen System",
            }.get(tournament_system, "Individual")

            filename = filedialog.asksaveasfilename(
                defaultextension=".trf",
                filetypes=[("TRF16 files", "*.trf"), ("All files", "*.*")],
                title="Export Tournament as TRF16",
                initialfile="tournament.trf",
            )
            if not filename:
                return
            try:
                content = self.build_trf16_content(
                    players, history, starting_rank_names, meta,
                    team_a=team_a, team_b=team_b,
                    team_a_name=team_a_name, team_b_name=team_b_name,
                )
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Exported", f"TRF16 file saved to:\n{filename}")
            except Exception as exc:
                messagebox.showerror(
                    "Export Error", f"Could not write TRF16 file:\n{exc}"
                )

        self._show_trf_metadata_dialog(default_name, on_confirm)

    def export_tournament_to_trf(self) -> None:
        """Export the CURRENTLY LOADED (live, in-memory) tournament."""
        if not getattr(self, "tournament_history", None):
            messagebox.showinfo(
                "No Data",
                "This tournament has no round-by-round history to export.\n\n"
                "Only tournaments that have completed at least one round "
                "contain exportable data.",
            )
            return
        team_a = getattr(self, "schev_team_a", None) or None
        team_b = getattr(self, "schev_team_b", None) or None
        self._write_trf16(
            self.players,
            self.tournament_history,
            getattr(self, "trf_starting_rank_names", None),
            getattr(self, "tournament_system", None),
            default_name="",
            team_a=team_a,
            team_b=team_b,
        )

    def _export_trf_from_filepath(self, filepath: str) -> None:
        """Export a saved tournament JSON file straight to TRF16, without
        requiring the user to open it first - mirrors
        _export_csv_from_filepath/_export_html_from_filepath."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not read tournament file:\n{exc}")
            return

        history = data.get("tournament_history", [])
        if not history:
            messagebox.showinfo(
                "No Data",
                "This tournament has no round-by-round history to export.\n\n"
                "Only tournaments that have completed at least one round "
                "contain exportable data.",
            )
            return

        team_a = team_b = None
        schev_a_names = data.get("schev_team_a_names") or []
        schev_b_names = data.get("schev_team_b_names") or []
        players = self._build_players_from_save_data(data)
        if schev_a_names and schev_b_names:
            by_name = {p.name: p for p in players}
            team_a = [by_name[n] for n in schev_a_names if n in by_name]
            team_b = [by_name[n] for n in schev_b_names if n in by_name]

        # apply_tiebreak reads self.tiebreak_method - temporarily swap it
        # to the SAVED file's own setting for this export, then restore
        # whatever it was before. Without the restore, exporting some
        # OTHER, past tournament from the "browse saved tournaments"
        # screen while a different tournament is live in memory would
        # silently corrupt that live tournament's tiebreak calculations
        # from this point on.
        previous_tiebreak_method = getattr(self, "tiebreak_method", None)
        self.tiebreak_method = data.get("tiebreak_method")
        try:
            self._write_trf16(
                players,
                history,
                data.get("trf_starting_rank_names"),
                data.get("tournament_system"),
                default_name="",
                team_a=team_a,
                team_b=team_b,
            )
        finally:
            self.tiebreak_method = previous_tiebreak_method

    # ============ END TRF16 EXPORT ============

    # ============ HTML EXPORT ============

    def _html_theme_css(self) -> str:
        """Build a <style> block from the currently selected in-app theme, so
        exported HTML tournament reports visually match the app itself.

        Uses the same THEMES.get(..., THEMES["Simple Light"]) fallback
        pattern used everywhere else in the app for consistency.
        """
        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        return f"""
        :root {{
            --bg: {theme['bg']};
            --fg: {theme['fg']};
            --border: {theme['border']};
            --title-fg: {theme['title_fg']};
            --subtitle-fg: {theme['subtitle_fg']};
            --button-bg: {theme['button_bg']};
            --button-fg: {theme['button_fg']};
            --accent-bg: {theme['accent_button_bg']};
            --select-bg: {theme['select_bg']};
            --select-fg: {theme['select_fg']};
        }}
        * {{
            box-sizing: border-box;
            /* Without this, browsers strip background colors when printing/
               saving as PDF by default, so themed exports would print as
               plain white regardless of which theme was selected. */
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
            color-adjust: exact;
        }}
        body {{
            background: var(--bg);
            color: var(--fg);
            font-family: "Segoe UI", Arial, sans-serif;
            margin: 0;
            padding: 24px 32px 48px;
            line-height: 1.4;
        }}
        h1 {{
            color: var(--title-fg);
            font-size: 26px;
            margin-bottom: 4px;
        }}
        h2 {{
            color: var(--title-fg);
            border-bottom: 2px solid var(--accent-bg);
            padding-bottom: 6px;
            margin-top: 40px;
        }}
        h3 {{
            color: var(--subtitle-fg);
            margin-top: 24px;
            margin-bottom: 8px;
        }}
        .subtitle {{ color: var(--subtitle-fg); margin-top: 0; }}
        .print-btn {{
            background: var(--button-bg);
            color: var(--button-fg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            cursor: pointer;
            margin: 12px 0 8px;
        }}
        .print-btn:hover {{ opacity: 0.85; }}
        @media print {{
            /* Don't include the on-screen print button in the printed
               output/PDF itself. */
            .no-print {{ display: none !important; }}
        }}
        table.meta-table {{ border-collapse: collapse; margin: 12px 0 28px; }}
        table.meta-table td {{ padding: 4px 16px 4px 0; }}
        table.meta-table td.meta-label {{ color: var(--subtitle-fg); font-weight: 600; }}
        table.data {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 12px;
        }}
        table.data th, table.data td {{
            border: 1px solid var(--border);
            padding: 6px 10px;
            text-align: left;
            font-size: 14px;
        }}
        table.data th {{
            background: var(--button-bg);
            color: var(--button-fg);
        }}
        table.data tr.rank-1 td {{
            background: var(--select-bg);
            color: var(--select-fg);
            font-weight: 700;
        }}
        .status-inactive {{ color: var(--subtitle-fg); font-style: italic; }}
        details.round-block {{
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 16px;
            margin-bottom: 16px;
        }}
        details.round-block > summary {{
            cursor: pointer;
            font-weight: 700;
            color: var(--title-fg);
            font-size: 16px;
        }}
        footer {{
            margin-top: 40px;
            color: var(--subtitle-fg);
            font-size: 12px;
        }}
        """

    def export_tournament_to_html(self, history: list, meta: dict = None) -> None:
        """Export tournament history to a user-chosen, self-contained HTML file.

        Mirrors export_tournament_to_csv() section-for-section (tournament
        info, final standings, then per-round pairings/standings) so the two
        exports always describe the same data. Styled inline (no external
        CSS/JS/fonts) to match the app's currently selected theme, keeping
        the file fully offline-viewable in line with the app's own
        zero-dependency design.

        Like CSV export, this is only wired up for the four Tournament-mode
        systems (Swiss, Round-Robin, Knockout, Scheveningen) - the only
        systems that populate tournament_history. Dual, Battle Royale, and
        Teams modes have no history and are out of scope here, same as CSV.

        Parameters
        ----------
        history : list
            List of round dicts (same structure as ``tournament_history``).
        meta : dict, optional
            Extra metadata fields. Expected keys (all optional):
            ``tournament_system``, ``tournament_start_time``, ``finished``,
            ``tiebreak_method``, ``current_round``.
        """
        if not history:
            messagebox.showinfo("No Data", "No round history available to export.")
            return

        if meta is None:
            meta = {}

        # Build a sensible default filename ─────────────────────────────────
        system = meta.get("tournament_system") or "tournament"
        timestamp = (meta.get("tournament_start_time") or "").replace(":", "-").replace(" ", "_")
        hint = (
            f"tournament_{timestamp}_{system}_export"
            if timestamp
            else f"tournament_{system}_export"
        )

        save_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            initialfile=hint,
            title="Export Tournament as HTML",
        )
        if not save_path:
            return  # User cancelled

        # Display-friendly labels ────────────────────────────────────────────
        system_display = {
            "swiss": "Swiss System",
            "round_robin": "Round-Robin",
            "knockout": "Knockout",
            "scheveningen": "Scheveningen",
        }.get(system, system.replace("_", " ").title())

        tiebreak_raw = meta.get("tiebreak_method") or ""
        tiebreak_display = {
            "buchholz": "Buchholz",
            "sonneborn_berger": "Sonneborn-Berger",
            "direct_encounter": "Direct Encounter",
            "rating": "Rating",
        }.get(tiebreak_raw, tiebreak_raw.replace("_", " ").title() if tiebreak_raw else "—")

        result_map = {
            "p1_win": "1 – 0",
            "p2_win": "0 – 1",
            "draw": "½ – ½",
            "bye": "BYE (+1 pt)",
            "half_bye": "HALF-BYE (+0.5 pt)",
        }

        is_schev = (system == "scheveningen")
        esc = html.escape

        def cell(value) -> str:
            """Escape a value for safe HTML display. Mirrors the CSV export's
            "—" fallback for missing/None values, but is careful not to treat
            a genuine 0 (e.g. 0 wins, 0 points) as "missing"."""
            if value is None or value == "":
                return "—"
            return esc(str(value))

        def standings_table(standings: list, include_rating: bool) -> str:
            """Render a standings snapshot as an HTML table.

            include_rating controls whether an ELO column is shown - the CSV
            export only includes it in the FINAL standings section, not in
            the per-round "standings after round" sections, so this mirrors
            that exactly rather than showing it everywhere.
            """
            headers = ["Rank"]
            if is_schev:
                headers.append("Team")
            headers.append("Name")
            if include_rating:
                headers.append("ELO")
            headers += [
                "Points", "Wins", "Losses", "Draws", "Byes", "Half-Byes",
                "White", "Black", "Tiebreak", "Status",
            ]
            header_html = "".join(f"<th>{esc(h)}</th>" for h in headers)

            body_rows = []
            for s in standings:
                status = s.get("status", "")
                row_class = ' class="rank-1"' if s.get("rank") == 1 else ""

                values = [s.get("rank")]
                if is_schev:
                    values.append(s.get("team"))
                values.append(s.get("name"))
                if include_rating:
                    values.append(s.get("rating"))
                values += [
                    s.get("points"), s.get("wins"), s.get("losses"),
                    s.get("draws"), s.get("byes"), s.get("half_byes"),
                    s.get("white_games"), s.get("black_games"),
                    s.get("tiebreak"),
                ]

                tds = "".join(f"<td>{cell(v)}</td>" for v in values)
                status_class = (
                    ' class="status-inactive"' if status and status != "Active" else ""
                )
                tds += f"<td{status_class}>{cell(status)}</td>"

                body_rows.append(f"<tr{row_class}>{tds}</tr>")

            return (
                '<table class="data">'
                f"<thead><tr>{header_html}</tr></thead>"
                f"<tbody>{''.join(body_rows)}</tbody>"
                "</table>"
            )

        def pairings_table(pairings: list) -> str:
            header_html = "".join(
                f"<th>{esc(h)}</th>"
                for h in ["Board", "Player 1 (White)", "Result", "Player 2 (Black)"]
            )
            body_rows = []
            for p in pairings:
                p2_disp = p.get("player2") if p.get("player2") else "—"
                res_disp = result_map.get(p.get("result"), p.get("result"))
                tds = "".join(
                    f"<td>{cell(v)}</td>"
                    for v in [p.get("board"), p.get("player1"), res_disp, p2_disp]
                )
                body_rows.append(f"<tr>{tds}</tr>")
            return (
                '<table class="data">'
                f"<thead><tr>{header_html}</tr></thead>"
                f"<tbody>{''.join(body_rows)}</tbody>"
                "</table>"
            )

        try:
            parts = [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                f"<title>{esc(system_display)} Tournament Export</title>",
                f"<style>{self._html_theme_css()}</style>",
                "</head>",
                "<body>",
                f"<h1>{esc(system_display)} — Tournament Export</h1>",
                '<p class="subtitle">Exported from Player Sorter</p>',
                '<button class="print-btn no-print" onclick="window.print()">'
                "🖨️ Print / Save as PDF</button>",
            ]

            # ── Section 1: Tournament metadata ───────────────────────────
            start_raw = meta.get("tournament_start_time") or ""
            parts.append("<h2>Tournament Info</h2>")
            parts.append('<table class="meta-table">')
            parts.append(
                f'<tr><td class="meta-label">System</td>'
                f'<td>{cell(system_display)}</td></tr>'
            )
            parts.append(
                f'<tr><td class="meta-label">Start Time</td>'
                f'<td>{cell(start_raw.replace("_", " "))}</td></tr>'
            )
            parts.append(
                f'<tr><td class="meta-label">Status</td>'
                f'<td>{cell("Finished" if meta.get("finished", True) else "Unfinished")}</td></tr>'
            )
            parts.append(
                f'<tr><td class="meta-label">Tiebreak Method</td>'
                f'<td>{cell(tiebreak_display)}</td></tr>'
            )
            parts.append(
                f'<tr><td class="meta-label">Total Rounds Played</td>'
                f'<td>{cell(meta.get("current_round", len(history)))}</td></tr>'
            )
            parts.append("</table>")

            # ── Section 2: Final standings ────────────────────────────────
            parts.append("<h2>Final Standings</h2>")
            last_round = history[-1]
            standings = last_round.get("standings_after_round", [])
            parts.append(standings_table(standings, include_rating=True))

            # ── Section 3+: Per-round details ─────────────────────────────
            parts.append("<h2>Round-by-Round Details</h2>")
            for rnd in history:
                rnum = rnd.get("round_number")
                parts.append('<details class="round-block" open>')
                parts.append(f"<summary>Round {esc(str(rnum))}</summary>")

                parts.append(f"<h3>Round {esc(str(rnum))} – Pairings</h3>")
                parts.append(pairings_table(rnd.get("pairings", [])))

                parts.append(f"<h3>Round {esc(str(rnum))} – Standings After Round</h3>")
                round_standings = rnd.get("standings_after_round", [])
                parts.append(standings_table(round_standings, include_rating=False))

                parts.append("</details>")

            parts.append(
                "<footer>Generated by Player Sorter — "
                f'{esc(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))}</footer>'
            )
            parts.append("</body>")
            parts.append("</html>")

            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(parts))

            messagebox.showinfo(
                "Export Successful", f"Tournament exported to:\n{save_path}"
            )

        except Exception as exc:
            messagebox.showerror("Export Error", f"Could not write HTML file:\n{exc}")

    def _export_html_from_filepath(self, filepath: str) -> None:
        """Load a saved tournament JSON file and export its history to HTML.

        Used by the Load Tournament screen so the user can export a tournament
        without having to open it first. Mirrors _export_csv_from_filepath().
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not read tournament file:\n{exc}")
            return

        history = data.get("tournament_history", [])
        if not history:
            messagebox.showinfo(
                "No Data",
                "This tournament has no round-by-round history to export.\n\n"
                "Only tournaments that have completed at least one round "
                "contain exportable data.",
            )
            return

        meta = {
            "tournament_system": data.get("tournament_system"),
            "tournament_start_time": data.get("tournament_start_time", ""),
            "finished": data.get("finished", False),
            "tiebreak_method": data.get("tiebreak_method", ""),
            "current_round": data.get("current_round", len(history)),
        }
        self.export_tournament_to_html(history, meta)

    # ============ END HTML EXPORT ============

    def show_round_by_round_viewer(self, history: list, return_to=None):
        """Display a round-by-round viewer for a finished tournament.
        history: list of round dicts (from tournament_history or loaded file).
        return_to: optional no-arg callable for the "Back" button to invoke
            instead of jumping to the main menu. Callers should pass the
            screen the viewer was opened from (e.g. the final-standings
            screen, the winner screen, or the Load Tournament list) so "Back"
            actually goes back, rather than stranding the user on the main
            menu with no way to return to (and save) the tournament they
            were just looking at. Falls back to show_initial_selection() if
            not given.
        """
        if not history:
            messagebox.showinfo("No Data", "No round history available to display.")
            return

        self.clear_window()
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Tournament Round-by-Round Details",
            font=("Arial", 18, "bold"),
        ).pack(pady=10)

        # Round selector
        selector_frame = ttk.Frame(frame)
        selector_frame.pack(pady=5)

        ttk.Label(selector_frame, text="Select Round:", font=("Arial", 12)).pack(
            side=tk.LEFT, padx=5
        )

        round_labels = [f"Round {r['round_number']}" for r in history]
        round_var = tk.StringVar(value=round_labels[0])

        round_dropdown = ttk.Combobox(
            selector_frame,
            textvariable=round_var,
            values=round_labels,
            state="readonly",
            width=15,
            font=("Arial", 11),
        )
        round_dropdown.pack(side=tk.LEFT, padx=5)

        # Content area (will be refreshed on round selection)
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        def render_round(event=None):
            # Destroy and recreate content frame
            for widget in content_frame.winfo_children():
                widget.destroy()

            selected_label = round_var.get()
            round_index = round_labels.index(selected_label)
            round_data = history[round_index]

            # Left panel: pairings
            left_frame = ttk.LabelFrame(
                content_frame, text="Pairings & Results", padding="10"
            )
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

            pair_tree = ttk.Treeview(
                left_frame,
                columns=["board", "player1", "result_label", "player2"],
                show="headings",
                height=14,
            )
            pair_tree.heading("board", text="#")
            pair_tree.heading("player1", text="Player 1 (White)")
            pair_tree.heading("result_label", text="Result")
            pair_tree.heading("player2", text="Player 2 (Black)")
            pair_tree.column("board", width=30)
            pair_tree.column("player1", width=160)
            pair_tree.column("result_label", width=120)
            pair_tree.column("player2", width=160)

            result_map = {
                "p1_win": "1 – 0",
                "p2_win": "0 – 1",
                "draw": "½ – ½",
                "bye": "BYE (+1 pt)",
                "half_bye": "HALF-BYE (+0.5)",
            }

            for p in round_data["pairings"]:
                p2_display = p["player2"] if p["player2"] else "—"
                result_display = result_map.get(p["result"], p["result"])
                pair_tree.insert(
                    "",
                    tk.END,
                    values=(p["board"], p["player1"], result_display, p2_display),
                )

            pair_scroll = ttk.Scrollbar(
                left_frame, orient=tk.VERTICAL, command=pair_tree.yview
            )
            pair_tree.configure(yscroll=pair_scroll.set)
            pair_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            pair_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            # Right panel: standings after this round
            right_frame = ttk.LabelFrame(
                content_frame, text="Standings After This Round", padding="10"
            )
            right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

            cols = ["rank", "name", "points", "record", "white", "black", "tiebreak", "status"]
            stand_tree = ttk.Treeview(
                right_frame, columns=cols, show="headings", height=14
            )
            stand_tree.heading("rank", text="#")
            stand_tree.heading("name", text="Name")
            stand_tree.heading("points", text="Pts")
            stand_tree.heading("record", text="W-L-D")
            stand_tree.heading("white", text="White")
            stand_tree.heading("black", text="Black")
            stand_tree.heading("tiebreak", text="TB")
            stand_tree.heading("status", text="Status")
            stand_tree.column("rank", width=30)
            stand_tree.column("name", width=140)
            stand_tree.column("points", width=40)
            stand_tree.column("record", width=80)
            stand_tree.column("white", width=45)
            stand_tree.column("black", width=45)
            stand_tree.column("tiebreak", width=55)
            stand_tree.column("status", width=120)

            for s in round_data["standings_after_round"]:
                record = f"{s['wins']}W-{s['losses']}L-{s['draws']}D"
                stand_tree.insert(
                    "",
                    tk.END,
                    values=(
                        s["rank"],
                        s["name"],
                        s["points"],
                        record,
                        s.get("white_games", "—"),
                        s.get("black_games", "—"),
                        s["tiebreak"] if s["tiebreak"] is not None else "-",
                        s["status"],
                    ),
                )

            stand_scroll = ttk.Scrollbar(
                right_frame, orient=tk.VERTICAL, command=stand_tree.yview
            )
            stand_tree.configure(yscroll=stand_scroll.set)
            stand_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            stand_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        round_dropdown.bind("<<ComboboxSelected>>", render_round)
        render_round()  # Render first round immediately

        # Navigation buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text="← Back",
            command=return_to if return_to else self.show_initial_selection,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="💾 Save Tournament",
            command=self._save_finished_tournament,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="📄 Export as CSV",
            command=lambda: self.export_tournament_to_csv(
                history,
                {
                    "tournament_system": getattr(self, "tournament_system", None),
                    "tournament_start_time": getattr(
                        self, "tournament_start_time", ""
                    ),
                    "finished": True,
                    "tiebreak_method": getattr(self, "tiebreak_method", None),
                    "current_round": getattr(self, "current_round", len(history)),
                },
            ),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="🌐 Export as HTML",
            command=lambda: self.export_tournament_to_html(
                history,
                {
                    "tournament_system": getattr(self, "tournament_system", None),
                    "tournament_start_time": getattr(
                        self, "tournament_start_time", ""
                    ),
                    "finished": True,
                    "tiebreak_method": getattr(self, "tiebreak_method", None),
                    "current_round": getattr(self, "current_round", len(history)),
                },
            ),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="♟ Export as TRF16",
            command=self.export_tournament_to_trf,
        ).pack(side=tk.LEFT, padx=5)

    # ============ END TOURNAMENT MODE ============

    def balance_teams(self, num_teams: int) -> List[List[Player]]:
        """Create balanced teams using a greedy algorithm"""
        # Sort players by rating (descending)
        sorted_players = sorted(self.players, key=lambda p: p.rating, reverse=True)

        # Initialize teams
        teams = [[] for _ in range(num_teams)]
        team_ratings = [0] * num_teams

        # Distribute players to teams (greedy approach)
        for player in sorted_players:
            # Find team with lowest total rating
            min_team_idx = team_ratings.index(min(team_ratings))
            teams[min_team_idx].append(player)
            team_ratings[min_team_idx] += player.rating

        return teams

    def back_to_setup(self):
        """Return to setup screen, keeping player data.

        Always passes auto_load=False to show_player_input(): whatever is
        currently in self.players (live tournament progress, or a loaded
        tournament's roster) must not be silently overwritten by whatever
        happens to be saved on disk, which is exactly what auto-loading
        would otherwise do here.
        """
        if self.in_game:
            if messagebox.askyesno(
                "Confirm", "Return to setup? Current game progress will be kept."
            ):
                self.in_game = False
                self.show_player_input(auto_load=False)
        else:
            self.show_player_input(auto_load=False)

    def clear_window(self):
        """Clear all widgets from the window"""
        for widget in self.root.winfo_children():
            widget.destroy()


def main():
    root = tk.Tk()
    PlayerSorterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
