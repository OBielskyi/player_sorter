#!/usr/bin/env python3
"""
Player Sorter - A simple GUI application for creating and sorting player tables
Supports Chess (ELO) and E-sports (Trophies) with three modes:
- Dual: Pair players based on rating with randomness
- Battle Royale: Sort by win rate
- Teams: Create balanced teams
"""

import json
import os
import random
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Tuple

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
        self.colors = []  # Track colors played (for Swiss: 'W' or 'B')
        self.requested_half_bye = False  # For current round

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
    def full_name(self):
        """Get full real name (first + last)"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """Get name for display (prioritize nickname for e-sports, full name for chess)"""
        return self.name

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
    def performance_score(self):
        """Performance score for ranking withdrawn players"""
        # Favors players with more rounds played, but balanced
        # Formula: points + (games_played * 0.01) to break ties
        return self.points + (self.games_played * 0.01)

    def to_dict(self):
        return {
            "name": self.name,
            "rating": self.rating,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "byes": self.byes,
            "half_byes": self.half_byes,
            "eliminated": self.eliminated,
            "withdrawn": self.withdrawn,
            "withdrawal_round": self.withdrawal_round,
        }

    @classmethod
    def from_dict(cls, data):
        player = cls(
            data["name"],
            data["rating"],
            data.get("wins", 0),
            data.get("losses", 0),
            data.get("draws", 0),
            data.get("byes", 0),
            data.get("half_byes", 0),
        )
        player.eliminated = data.get("eliminated", False)
        player.withdrawn = data.get("withdrawn", False)
        player.withdrawal_round = data.get("withdrawal_round", None)
        return player


class PlayerSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Player Sorter")

        # Load theme preference
        self.current_theme = self.load_theme_preference()

        # Maximize window - cross-platform approach
        try:
            # Try Windows/Linux method first
            self.root.state("zoomed")
        except:
            try:
                # Try macOS method
                self.root.attributes("-zoomed", True)
            except:
                # Fallback: maximize manually by setting geometry to screen size
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        # Allow window resizing
        self.root.resizable(True, True)

        self.game_type = None
        self.sort_mode = None
        self.players: List[Player] = []
        self.current_round = 0
        self.teams: List[List[Player]] = []
        self.in_game = False  # Track if we're in an active game
        self.half_bye_enabled = False  # Track if half-byes are allowed
        self.withdrawal_enabled = False  # Track if withdrawals are allowed
        self.max_rounds = None  # Maximum rounds (None = unlimited)
        self.rating_mode = None  # 'automatic', 'manual', or 'unranked' for chess; 'ranked' or 'unranked' for esports
        self.min_elo = 1000  # Minimum ELO for tournament (chess only)
        self.max_elo = None  # Maximum ELO for tournament (chess only, None = unlimited)

        # Apply theme before showing UI
        self.apply_theme(self.current_theme)

        self.show_theme_selection()

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
        except:
            pass
        return "Simple Light"  # Default theme

    def save_theme_preference(self, theme_name):
        """Save theme preference to file"""
        try:
            with open("player_sorter_theme.json", "w") as f:
                json.dump({"theme": theme_name}, f)
        except:
            pass

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

        # Try to use a theme that supports dark backgrounds if needed
        if theme_name != "Simple Light":
            try:
                style.theme_use("clam")  # Most customizable theme
            except:
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
            font=("Arial", 12),
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
            font=("Arial", 14, "bold"),
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
            font=("Arial", 11),
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
                font=("Arial", 11, "bold"),
            )
        else:
            # Simple themes keep subdued headings
            style.configure(
                "Treeview.Heading",
                background=theme["button_bg"],
                foreground=theme.get("button_fg", theme["fg"]),
                bordercolor=theme["border"],
                font=("Arial", 11, "bold"),
            )

        style.map(
            "Treeview",
            background=[("selected", theme["select_bg"])],
            foreground=[("selected", theme["select_fg"])],
        )
        style.configure("Treeview", font=("Arial", 10), rowheight=25)

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

        frame = ttk.Frame(self.root, padding="60")
        frame.pack(expand=True, fill=tk.BOTH)

        # Title
        title = ttk.Label(frame, text="Player Sorter", font=("Arial", 32, "bold"))
        title.pack(pady=30)

        subtitle = ttk.Label(frame, text="Select Theme", font=("Arial", 18))
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
                    theme_frame, text="✓ Current", font=("Arial", 9, "italic")
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

        frame = ttk.Frame(self.root, padding="60")
        frame.pack(expand=True, fill=tk.BOTH)

        # Title with larger font
        title = ttk.Label(frame, text="Player Sorter", font=("Arial", 32, "bold"))
        title.pack(pady=50)

        # Game Type Selection
        ttk.Label(frame, text="Select Game Type:", font=("Arial", 16)).pack(pady=20)

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

        # Theme switcher button at bottom
        ttk.Button(
            frame, text="🎨 Change Theme", width=20, command=self.show_theme_selection
        ).pack(pady=20)

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
        """Show tournament configuration options (half-byes, withdrawals, max rounds, rating mode)"""
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
            text="Allow players to withdraw from the tournament between rounds?\nWithdrawn players keep their score but stop playing.",
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
                            f"Maximum ELO ({self.max_elo}) must be greater than or equal to minimum ELO ({self.min_elo})",
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
        """Show Knockout tournament settings (rating mode only, no half-byes/withdrawals/max rounds)"""
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
                            f"Maximum ELO ({self.max_elo}) must be greater than or equal to minimum ELO ({self.min_elo})",
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
        frame.pack(expand=True)

        title = ttk.Label(
            frame, text="Scheveningen - Tournament Settings", font=("Arial", 16, "bold")
        )
        title.pack(pady=20)

        # Scrollable frame
        theme = THEMES.get(self.current_theme, THEMES["Simple Light"])
        canvas = tk.Canvas(frame, height=400, bg=theme["bg"], highlightthickness=0)
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
        rating_frame.pack(pady=10, padx=20, fill=tk.X)

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

        # Half-Byes (Scheveningen supports this)
        hb_frame = ttk.LabelFrame(scrollable_frame, text="Half-Byes", padding="15")
        hb_frame.pack(pady=10, padx=20, fill=tk.X)

        ttk.Label(
            hb_frame,
            text="Allow players to request half-byes (0.5 points) between rounds?",
            font=("Arial", 10),
            wraplength=450,
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
        wd_frame.pack(pady=10, padx=20, fill=tk.X)

        ttk.Label(
            wd_frame,
            text="Allow players to withdraw from the tournament between rounds?\nWithdrawn players keep their score but stop playing.",
            font=("Arial", 10),
            wraplength=450,
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
        note_frame.pack(pady=10, padx=20, fill=tk.X)
        ttk.Label(
            note_frame,
            text=f"Scheveningen has fixed rounds:\n"
            f"Team size: {self.scheveningen_team_size} players per team\n"
            f"Total rounds: {self.scheveningen_team_size} (each player plays each opponent once)",
            font=("Arial", 9),
            justify=tk.LEFT,
        ).pack()

        # ELO Limits (Chess only)
        if self.game_type == "chess":
            elo_frame = ttk.LabelFrame(
                scrollable_frame, text="ELO Requirements", padding="15"
            )
            elo_frame.pack(pady=10, padx=20, fill=tk.X)

            ttk.Label(
                elo_frame,
                text="Set minimum and maximum ELO for tournament participants:",
                font=("Arial", 10),
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
                            f"Maximum ELO ({self.max_elo}) must be greater than or equal to minimum ELO ({self.min_elo})",
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

    def show_player_input(self):
        """Show player input interface"""
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
        req_label.grid(row=2, column=0, columnspan=5, pady=5)

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
            command=lambda: self.load_players() and self.refresh_player_list(),
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
            style="Accent.TButton",
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

        # Auto-load players from save file (if exists)
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

        index = self.tree.index(selected[0])
        player = self.players[index]

        # Load player data into entry fields
        self.first_name_entry.delete(0, tk.END)
        self.first_name_entry.insert(0, player.first_name)

        self.last_name_entry.delete(0, tk.END)
        self.last_name_entry.insert(0, player.last_name)

        self.nickname_entry.delete(0, tk.END)
        self.nickname_entry.insert(0, player.nickname)

        self.rating_entry.delete(0, tk.END)
        self.rating_entry.insert(0, str(player.rating))

        # Change button text
        self.add_update_btn.config(text="Update Player")
        self.first_name_entry.focus()

    def add_or_update_player(self):
        """Add a new player or update existing one with name validation"""
        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
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
                    "Please enter either:\n- First Name AND Last Name\n- OR Nickname\n- OR all three",
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

        # Validate rating constraints (Chess only)
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

        # Check if updating existing player (match by full identity)
        existing_player = None
        for player in self.players:
            # Match by exact name combination
            if (
                player.first_name == first_name
                and player.last_name == last_name
                and player.nickname == nickname
            ):
                existing_player = player
                break

        if existing_player:
            # Update existing player
            existing_player.rating = rating
            self.add_update_btn.config(text="Add Player")
        else:
            # Add new player
            player = Player(
                first_name=first_name,
                last_name=last_name,
                nickname=nickname,
                rating=rating,
            )
            self.players.append(player)

        # Clear entries
        self.first_name_entry.delete(0, tk.END)
        self.last_name_entry.delete(0, tk.END)
        self.nickname_entry.delete(0, tk.END)
        self.rating_entry.delete(0, tk.END)
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

        index = self.tree.index(selected[0])
        del self.players[index]
        self.refresh_player_list()

    def clear_players(self):
        """Clear all players"""
        if self.players and messagebox.askyesno("Confirm", "Clear all players?"):
            self.players.clear()
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
                    f"Save file is for {data.get('game_type', 'unknown')} but current mode is {self.game_type}",
                )
                return False

            # Clear current players
            self.players = []

            # Load players
            for player_data in data.get("players", []):
                # Support both old format (name) and new format (first_name, last_name, nickname)
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

    def auto_load_players(self):
        """Automatically load players when entering player input screen"""
        if self.load_players():
            self.refresh_player_list()

    def auto_save_players(self):
        """Automatically save players after game ends"""
        self.save_players()

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

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

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
                return
            self.show_dual_game()
        elif self.sort_mode == "battle_royale":
            if len(self.players) < 4:
                messagebox.showwarning(
                    "Not Enough Players", "Need at least 4 players for battle royale"
                )
                return
            self.show_battle_royale_game()
        elif self.sort_mode == "teams":
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
                text=f"{leftover.name} ({rating_name}: {leftover.rating}, WR: {leftover.win_rate:.1f}%)",
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
            if result_var.get() == "" and result_var.get() != "bye":
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
            elif result == "p2_win":
                pair[1].wins += 1
                pair[0].losses += 1
                pair[0].opponents.append(pair[1].name)
                pair[1].opponents.append(pair[0].name)
            elif result == "draw":
                pair[0].draws += 1
                pair[1].draws += 1
                pair[0].opponents.append(pair[1].name)
                pair[1].opponents.append(pair[0].name)

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
            text=f"Battle Royale - Round {self.current_round} ({len(active_players)} players remaining)",
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
        """Start next battle royale round"""
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
                if i == 1
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

    def generate_team_results(self):
        """Generate balanced teams"""
        self.show_team_configuration()

    def show_dual_results(
        self, pairs: List[Tuple[Player, Player]], leftover: Player = None
    ):
        """Display dual pairing results"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(frame, text="Dual Pairings", font=("Arial", 18, "bold"))
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

        for i, (p1, p2) in enumerate(pairs, 1):
            pair_frame = ttk.LabelFrame(
                scrollable_frame, text=f"Match {i}", padding="10"
            )
            pair_frame.pack(fill=tk.X, padx=5, pady=5)

            ttk.Label(
                pair_frame,
                text=f"{p1.name} ({rating_name}: {p1.rating})",
                font=("Arial", 11),
            ).pack(anchor=tk.W)
            ttk.Label(pair_frame, text="vs", font=("Arial", 10, "italic")).pack(
                anchor=tk.W, padx=20
            )
            ttk.Label(
                pair_frame,
                text=f"{p2.name} ({rating_name}: {p2.rating})",
                font=("Arial", 11),
            ).pack(anchor=tk.W)

        if leftover:
            leftover_frame = ttk.LabelFrame(
                scrollable_frame, text="No Match", padding="10"
            )
            leftover_frame.pack(fill=tk.X, padx=5, pady=5)
            ttk.Label(
                leftover_frame,
                text=f"{leftover.name} ({rating_name}: {leftover.rating})",
                font=("Arial", 11),
            ).pack(anchor=tk.W)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame, text="← Back to Input", command=self.show_player_input
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Regenerate", command=self.generate_results).pack(
            side=tk.LEFT, padx=5
        )

    def show_battle_royale_results(self, sorted_players: List[Player]):
        """Display battle royale results"""
        self.clear_window()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            frame, text="Battle Royale Rankings", font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        # Results
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        tree = ttk.Treeview(
            results_frame,
            columns=["rank", "name", "rating", "winrate"],
            show="headings",
            height=15,
        )

        tree.heading("rank", text="Rank")
        tree.heading("name", text="Name")
        tree.heading("rating", text="ELO" if self.game_type == "chess" else "Trophies")
        tree.heading("winrate", text="Win Rate %")

        tree.column("rank", width=60)
        tree.column("name", width=200)
        tree.column("rating", width=100)
        tree.column("winrate", width=100)

        for i, player in enumerate(sorted_players, 1):
            tree.insert(
                "",
                tk.END,
                values=(i, player.name, player.rating, f"{player.win_rate:.1f}%"),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame, text="← Back to Input", command=self.show_player_input
        ).pack(side=tk.LEFT, padx=5)

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

        # Store player widgets for interaction
        self.team_player_buttons = []

        for i, team in enumerate(self.teams, 1):
            avg_rating = sum(p.rating for p in team) / len(team) if team else 0
            total_winrate = sum(p.win_rate for p in team)

            team_frame = ttk.LabelFrame(
                scrollable_frame,
                text=f"Team {i} (Avg {rating_name}: {avg_rating:.1f}, Total WR: {total_winrate:.1f}%)",
                padding="10",
            )
            team_frame.pack(fill=tk.X, padx=5, pady=5)

            for player in team:
                player_frame = ttk.Frame(team_frame)
                player_frame.pack(fill=tk.X, pady=2)

                # Player info
                info_text = f"{player.name} ({rating_name}: {player.rating}, WR: {player.win_rate:.1f}%)"
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
            total_winrate = sum(p.win_rate for p in team)
            avg_rating = sum(p.rating for p in team) / len(team) if team else 0
            mvp = max(team, key=lambda p: p.win_rate) if team else None
            team_stats.append((i, team, total_winrate, avg_rating, mvp))

        # Sort by total win rate
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

        for rank, (team_num, team, total_wr, avg_rating, mvp) in enumerate(
            team_stats, 1
        ):
            team_frame = ttk.LabelFrame(
                scrollable_frame,
                text=f"#{rank} - Team {team_num} (Total WR: {total_wr:.1f}%, Avg {rating_name}: {avg_rating:.1f})",
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
                    f"WR: {player.win_rate:.1f}% ({player.wins}W-{player.losses}L-{player.draws}D)"
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
            total_winrate = sum(p.win_rate for p in team)
            avg_rating = sum(p.rating for p in team) / len(team) if team else 0
            mvp = max(team, key=lambda p: p.win_rate) if team else None
            team_stats.append((i, team, total_winrate, avg_rating, mvp))

        # Sort by total win rate
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

        for rank, (team_num, team, total_wr, avg_rating, mvp) in enumerate(
            team_stats, 1
        ):
            team_frame = ttk.LabelFrame(
                scrollable_frame,
                text=f"#{rank} - Team {team_num} (Total WR: {total_wr:.1f}%, Avg {rating_name}: {avg_rating:.1f})",
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
                    f"WR: {player.win_rate:.1f}% ({player.wins}W-{player.losses}L-{player.draws}D)"
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
        mode: 'otb' for Online/OTB (K=32), 'correspondence' for Daily/Correspondence (K=48)
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

        # Determine which sub-mode to use based on rating_mode
        elo_mode = "otb"  # default
        if hasattr(self, "elo_submode"):
            elo_mode = self.elo_submode

        elo_changes = {}  # Track changes for each player

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
            if p1.name not in elo_changes:
                elo_changes[p1.name] = 0
            if p2.name not in elo_changes:
                elo_changes[p2.name] = 0

            elo_changes[p1.name] += p1_change
            elo_changes[p2.name] += p2_change

        # Apply changes to players
        for player in self.players:
            if player.name in elo_changes:
                player.rating += elo_changes[player.name]
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

        # Store rating entry widgets
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

            self.rating_entries[player.name] = entry

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
        """Apply manual rating changes"""
        try:
            for player in self.players:
                if player.name in self.rating_entries:
                    new_rating_str = self.rating_entries[player.name].get().strip()
                    if new_rating_str:
                        new_rating = int(new_rating_str)
                        if new_rating < 0:
                            messagebox.showwarning(
                                "Invalid Input",
                                f"Rating for {player.name} cannot be negative",
                            )
                            return
                        player.rating = new_rating

            # Proceed to callback
            callback()
        except ValueError:
            messagebox.showwarning("Invalid Input", "All ratings must be valid numbers")

    # ============ TOURNAMENT MODE METHODS ============

    def start_tournament(self):
        """Initialize and start tournament"""
        min_players = {"swiss": 4, "round_robin": 3, "knockout": 4, "scheveningen": 4}

        min_req = min_players.get(self.tournament_system, 2)

        if self.tournament_system == "scheveningen":
            required = self.scheveningen_team_size * 2
            if len(self.players) < required:
                messagebox.showwarning(
                    "Not Enough Players",
                    f"Need exactly {required} players for Scheveningen with {self.scheveningen_team_size} per team",
                )
                return
        elif len(self.players) < min_req:
            messagebox.showwarning(
                "Not Enough Players",
                f"Need at least {min_req} players for {self.tournament_system}",
            )
            return

        self.in_game = True
        self.current_round = 1

        # Clear previous tournament data
        for player in self.players:
            player.opponents = []
            player.colors = []

        if self.tournament_system == "swiss":
            self.show_swiss_round()
        elif self.tournament_system == "round_robin":
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
                pairings.append([top_half[i], bottom_half[i], None])

            # Handle odd number
            if len(playing_players) % 2 == 1:
                pairings.append([playing_players[-1], None, "bye"])
        else:
            # Sort by points, then rating
            playing_players.sort(key=lambda p: (p.points, p.rating), reverse=True)

            paired = set()

            for player in playing_players:
                if player.name in paired:
                    continue

                # Find best opponent they haven't played
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
                    pairings.append([player, opponent, None])
                    paired.add(player.name)
                    paired.add(opponent.name)
                else:
                    # Give bye if no valid opponent
                    pairings.append([player, None, "bye"])
                    paired.add(player.name)

        return pairings

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
        """Generate Round-Robin pairings using round-robin algorithm"""
        active = [p for p in self.players if not p.eliminated and not p.withdrawn]

        # Separate players who requested half-bye
        halfbye_players = [p for p in active if p.requested_half_bye]
        playing_players = [p for p in active if not p.requested_half_bye]

        pairings = []

        # Add half-bye players first
        for player in halfbye_players:
            pairings.append([player, None, "half_bye"])
            player.requested_half_bye = False  # Reset flag

        n = len(playing_players)

        # Calculate total rounds needed
        total_rounds = n - 1 if n % 2 == 0 else n

        if self.current_round > total_rounds:
            return []  # Tournament complete

        # Use round-robin rotation algorithm
        if n % 2 == 1:
            playing_players.append(None)  # Add dummy for odd players
            n += 1

        round_idx = self.current_round - 1

        # Fixed position rotation algorithm
        players = playing_players.copy()
        for _ in range(round_idx):
            players = [players[0]] + [players[-1]] + players[1:-1]

        # Create pairings for this round
        for i in range(n // 2):
            p1 = players[i]
            p2 = players[n - 1 - i]

            if p1 is not None and p2 is not None:
                pairings.append([p1, p2, None])
            elif p1 is not None:
                pairings.append([p1, None, "bye"])
            elif p2 is not None:
                pairings.append([p2, None, "bye"])

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

        round_names = {
            1: "Round 1",
            2: "Round 2",
            3: "Quarterfinals",
            4: "Semifinals",
            5: "Finals",
        }
        round_name = round_names.get(self.current_round, f"Round {self.current_round}")

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
            pairings.append([p1, p2, None])

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

        # Get active players (not withdrawn)
        active_team_a = [p for p in self.schev_team_a if not p.withdrawn]
        active_team_b = [p for p in self.schev_team_b if not p.withdrawn]

        # Separate players who requested half-bye
        halfbye_team_a = [p for p in active_team_a if p.requested_half_bye]
        halfbye_team_b = [p for p in active_team_b if p.requested_half_bye]
        playing_team_a = [p for p in active_team_a if not p.requested_half_bye]
        playing_team_b = [p for p in active_team_b if not p.requested_half_bye]

        pairings = []

        # Add half-bye players first
        for player in halfbye_team_a + halfbye_team_b:
            pairings.append([player, None, "half_bye"])
            player.requested_half_bye = False  # Reset flag

        # Each playing player from Team A plays one player from Team B per round
        # Use rotation to ensure everyone plays everyone
        for i in range(len(playing_team_a)):
            if i < len(playing_team_b):
                opponent_idx = (i + self.schev_round - 1) % len(playing_team_b)
                if opponent_idx < len(playing_team_b):
                    pairings.append(
                        [playing_team_a[i], playing_team_b[opponent_idx], None]
                    )

        # Handle case where teams are unbalanced due to withdrawals
        if len(playing_team_a) > len(playing_team_b):
            for i in range(len(playing_team_b), len(playing_team_a)):
                pairings.append([playing_team_a[i], None, "bye"])
        elif len(playing_team_b) > len(playing_team_a):
            for i in range(len(playing_team_a), len(playing_team_b)):
                pairings.append([playing_team_b[i], None, "bye"])

        self.display_tournament_pairings(frame, pairings, "scheveningen")

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
                    f"{tb_score:.1f}" if tb_score else "-",
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
                text="Players can request a half-bye (0.5 points) to skip the next round.",
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each active player
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
                self.halfbye_vars[player.name] = var

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
                text="Select players to withdraw from the tournament (they keep their current score).",
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each active player
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
                self.withdrawal_vars[player.name] = var

                cb = ttk.Checkbutton(row_frame, text=player.name, variable=var)
                cb.pack(side=tk.LEFT, padx=10)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )

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
        """Process half-bye and withdrawal requests, then continue to next Scheveningen round"""
        # Apply withdrawal requests if enabled
        if self.withdrawal_enabled and hasattr(self, "withdrawal_vars"):
            for player_name, var in self.withdrawal_vars.items():
                if var.get():
                    # Find player and mark as withdrawn
                    for player in self.schev_team_a + self.schev_team_b:
                        if player.name == player_name:
                            player.withdrawn = True
                            player.withdrawal_round = self.schev_round
                            break

        # Apply half-bye requests if enabled
        if self.half_bye_enabled and hasattr(self, "halfbye_vars"):
            for player_name, var in self.halfbye_vars.items():
                if var.get():
                    # Find player and mark for half-bye
                    for player in self.schev_team_a + self.schev_team_b:
                        if player.name == player_name:
                            player.requested_half_bye = True
                            break

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

        ttk.Button(frame, text="← Back to Setup", command=self.back_to_setup).pack(
            pady=20
        )

    # ===== SHARED TOURNAMENT METHODS =====

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
                # Player 1
                p1_label = f"{p1.name} ({rating_name}: {p1.rating}, Pts: {p1.points})"
                ttk.Label(pair_frame, text=p1_label, font=("Arial", 10)).grid(
                    row=0, column=0, sticky=tk.W, padx=5
                )

                # VS
                ttk.Label(pair_frame, text="vs", font=("Arial", 10, "italic")).grid(
                    row=0, column=1, padx=10
                )

                # Player 2
                p2_label = f"{p2.name} ({rating_name}: {p2.rating}, Pts: {p2.points})"
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
            if result_var.get() == "" and result_var.get() not in ["bye", "half_bye"]:
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
            elif result == "half_bye":
                p1.half_byes += 1
            elif result == "p1_win":
                p1.wins += 1
                p2.losses += 1
                p1.opponents.append(p2.name)
                p2.opponents.append(p1.name)
            elif result == "p2_win":
                p2.wins += 1
                p1.losses += 1
                p1.opponents.append(p2.name)
                p2.opponents.append(p1.name)
            elif result == "draw":
                p1.draws += 1
                p2.draws += 1
                p1.opponents.append(p2.name)
                p2.opponents.append(p1.name)

        # Handle elimination for knockout
        if system == "knockout":
            for pairing, result_var in self.tournament_results:
                p1, p2, _ = pairing
                result = result_var.get()

                if result == "p1_win" and p2:
                    p2.eliminated = True
                elif result == "p2_win" and p1:
                    p1.eliminated = True
                # In knockout, draws might need resolution - for now treat as p1 win
                elif result == "draw" and p2:
                    p2.eliminated = True

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
                    f"{tb_score:.1f}" if tb_score else "-",
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
                text="Players can request a half-bye (0.5 points) to skip the next round.",
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each player
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
                self.halfbye_vars[player.name] = var

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
                text="Select players to withdraw from the tournament (they keep their current score).",
                font=("Arial", 9),
            ).pack(pady=5)

            # Create checkboxes for each active player
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
                self.withdrawal_vars[player.name] = var

                cb = ttk.Checkbutton(row_frame, text=player.name, variable=var)
                cb.pack(side=tk.LEFT, padx=10)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="← Back to Setup", command=self.back_to_setup).pack(
            side=tk.LEFT, padx=5
        )

        # Check if tournament should continue or auto-finish
        should_auto_finish = False

        if system == "swiss":
            # Check if max rounds set and reached
            if self.max_rounds and self.current_round >= self.max_rounds:
                should_auto_finish = True

        elif system == "round_robin":
            # Round-robin: check max rounds if set, otherwise natural end
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

    def next_tournament_round_with_settings(self, system):
        """Process half-bye and withdrawal requests, then continue to next round"""
        # Apply withdrawal requests if enabled
        if self.withdrawal_enabled and hasattr(self, "withdrawal_vars"):
            for player_name, var in self.withdrawal_vars.items():
                if var.get():
                    # Find player and mark as withdrawn
                    for player in self.players:
                        if player.name == player_name:
                            player.withdrawn = True
                            player.withdrawal_round = self.current_round
                            break

        # Apply half-bye requests if enabled
        if self.half_bye_enabled and hasattr(self, "halfbye_vars"):
            for player_name, var in self.halfbye_vars.items():
                if var.get():
                    # Find player and mark for half-bye
                    for player in self.players:
                        if player.name == player_name:
                            player.requested_half_bye = True
                            break

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

            if self.tiebreak_method == "buchholz":
                # Sum of opponents' scores
                tb_score = 0
                for opp_name in player.opponents:
                    for p in players:
                        if p.name == opp_name:
                            tb_score += p.points
                            break
            elif self.tiebreak_method == "sonneborn_berger":
                # Weighted opponents' scores (win=full score, draw=half score)
                tb_score = 0
                for p in players:
                    if p.name in player.opponents:
                        # Find result against this opponent
                        idx = player.opponents.index(p.name)
                        # Simplified: assume we can determine result from records
                        tb_score += p.points * 0.5  # Approximate
            elif self.tiebreak_method == "rating":
                tb_score = player.rating
            elif self.tiebreak_method == "direct_encounter":
                tb_score = player.rating  # Fallback to rating for now

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
        # Players with equal points: active players rank first (they completed the tournament)
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
                status = f"Withdrew R{player.withdrawal_round}"
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
                    f"{tb_score:.1f}" if tb_score else "-",
                ),
            )

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(frame, text="← Back to Setup", command=self.back_to_setup).pack(
            pady=10
        )

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
            text="View Final Standings",
            command=self.show_tournament_final_standings,
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
        """Return to setup screen, keeping player data"""
        if self.in_game:
            if messagebox.askyesno(
                "Confirm", "Return to setup? Current game progress will be kept."
            ):
                self.in_game = False
                self.show_player_input()
        else:
            self.show_player_input()

    def clear_window(self):
        """Clear all widgets from the window"""
        for widget in self.root.winfo_children():
            widget.destroy()


def main():
    root = tk.Tk()
    app = PlayerSorterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
