"""
Sudoku Game GUI
===============
This file controls the playable game:

* 9x9 board and user input
* timer, mistakes, undo, levels
* visual feedback (green / red)
* AI hints and game completion

The AI solver itself lives in sudoku_solver.py.
This file only calls it.
"""

import tkinter as tk
from tkinter import messagebox

# Import the AI hint system.
# This file provides candidates and an AI-recommended number.
from ai_hint import get_hint

# Import the scoring system.
# This calculates the player's score based on difficulty,
# mistakes, hints, and remaining time.
from scoring import calculate_score

# Import the puzzle generator.
# This creates a new Sudoku puzzle and its complete solution.
from sudoku_generator import generate_puzzle

# Import functions from the AI solver.
# game.py uses these functions to check player answers
# and to determine whether the puzzle is completely solved.
from sudoku_solver import is_board_complete_and_correct, is_correct_number


# ============================================================
# GAME SETTINGS  (edit these values to customize the game)
# ============================================================
# Easy:   more given numbers, 10 minutes
# Medium: fewer given numbers, 7 minutes
# Hard:   fewest given numbers, 5 minutes
#
# These settings determine:
# 1. How many clues are shown at the beginning.
# 2. How much time the player gets.
DIFFICULTY_SETTINGS = {
    "Easy": {
        "time_seconds": 10 * 60,
        "clues": 40,
    },
    "Medium": {
        "time_seconds": 7 * 60,
        "clues": 32,
    },
    "Hard": {
        "time_seconds": 5 * 60,
        "clues": 26,
    },
}

# Give one AI hint after every 2 mistakes, up to 3 hints total.
MISTAKES_PER_AI_HINT = 2
MAX_AI_HINTS = 3

# The game starts with Easy difficulty.
DEFAULT_DIFFICULTY = "Easy"

# ============================================================
# VISUAL DESIGN
# ============================================================
# Font used throughout the game interface.
FONT = "Helvetica Neue"

# All colors used by the Sudoku interface.
# Keeping them together makes the visual design easier to edit.
COLORS = {
    "bg": "#0B1220",
    "header": "#0F172A",
    "surface": "#121A2B",
    "card": "#182338",
    "text": "#F1F5F9",
    "muted": "#8B9BB4",
    "accent": "#3B82F6",
    "accent_deep": "#1D4ED8",
    "good": "#10B981",
    "bad": "#F43F5E",
    "board_frame": "#E8EEF7",
    "cell": "#FFFFFF",
    "cell_given": "#F3F6FB",
    "cell_hover": "#EEF3FF",
    "cell_peer": "#E4ECFA",
    "cell_same": "#D5E3FF",
    "cell_selected": "#BFDBFE",
    "cell_correct": "#D1FAE5",
    "cell_wrong": "#FFE4E6",
    "given_fg": "#0F172A",
    "player_fg": "#1D4ED8",
    "correct_fg": "#047857",
    "wrong_fg": "#E11D48",
    "grid_thin": "#C5D0E3",
    "grid_thick": "#0F172A",
    "btn_text": "#FFFFFF",
    "btn_erase": "#E11D48",
    "btn_undo": "#7C3AED",
    "btn_hint": "#059669",
    "btn_new": "#2563EB",
    "btn_number": "#1D4ED8",
    "btn_number_done": "#1E293B",
    "level_off": "#1E293B",
    "level_on": "#2563EB",
}

# Size of each Sudoku cell.
CELL_SIZE = 58

# Padding around the board.
BOARD_PAD = 10

# Width of normal grid lines.
THIN_LINE = 1

# Width of the thicker 3x3 box lines.
THICK_LINE = 3


def format_time(seconds):
    """Turn 322 seconds into '05:22'."""
    # Make sure the displayed time is never negative.
    seconds = max(0, int(seconds))

    # Convert total seconds into minutes.
    minutes = seconds // 60

    # Get the remaining seconds after the minutes.
    secs = seconds % 60

    # Return the time in MM:SS format.
    return f"{minutes:02d}:{secs:02d}"


def ui_font(size, weight="normal"):
    # Create a font tuple used by Tkinter labels and buttons.
    return (FONT, size, weight)


def _lighten(hex_color, amount=0.18):
    """Mix a hex color toward white for hover."""
    # Remove the # from the hexadecimal color.
    hex_color = hex_color.lstrip("#")

    # Convert each hexadecimal color component into a number.
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)

    # Move each color closer to white.
    red = min(255, int(red + (255 - red) * amount))
    green = min(255, int(green + (255 - green) * amount))
    blue = min(255, int(blue + (255 - blue) * amount))

    # Convert the RGB values back into hexadecimal format.
    return f"#{red:02x}{green:02x}{blue:02x}"


class SudokuGame:
    """Main Tkinter window and game controller."""

    def __init__(self, root):
        # Store the main Tkinter window.
        self.root = root

        # Set the title shown at the top of the window.
        self.root.title("Sudoku Puzzle")

        # Set the main background color.
        self.root.configure(bg=COLORS["bg"])

        # Prevent the window from being resized.
        self.root.resizable(False, False)

        # Game state
        # These variables store the current state of the Sudoku game.
        self.difficulty = DEFAULT_DIFFICULTY
        self.puzzle = None
        self.solution = None
        self.current = None
        self.cell_status = None
        self.selected = None
        self.hover_cell = None
        self.undo_stack = []
        self.mistakes = 0
        self.hints_used = 0
        self.time_left = 0
        self.total_time = 0
        self.timer_id = None
        self.timer_started = False
        self.game_active = False
        self.paused = False
        self.previous_puzzle = None

        # Widgets filled in by _build_ui
        # These variables will later store references to GUI elements.
        self.board_canvas = None
        self.stat_level = None
        self.stat_time = None
        self.stat_mistakes = None
        self.stat_hints = None
        self.stat_score = None
        self.status_label = None
        self.level_buttons = {}
        self.number_tiles = {}

        # Build the complete user interface.
        self._build_ui()

        # Make sure the timer and other resources are stopped
        # properly when the user closes the window.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Listen for keyboard input such as numbers, Delete, and arrow keys.
        self.root.bind("<Key>", self._on_key)

        # Start the first game after the window is drawn.
        self.root.after(50, self.start_new_game)

    # ----------------------------------------------------------
    # User interface
    # ----------------------------------------------------------
    def _build_ui(self):
        """Create the modern header, canvas board, and side controls."""
        # Build the top section containing the title and game statistics.
        self._build_header()

        # Create the main body area of the application.
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=(6, 8))

        # Create the Sudoku board.
        self._build_board(body)

        # Create the difficulty, number, and action controls.
        self._build_sidebar(body)

        # Create the message/status bar at the bottom.
        self._build_status_bar()

    def _build_header(self):
        # Create the dark header area.
        header = tk.Frame(self.root, bg=COLORS["header"])
        header.pack(fill="x")

        # Create an inner frame to keep the header content aligned.
        inner = tk.Frame(header, bg=COLORS["header"])
        inner.pack(fill="x", padx=24, pady=16)

        # Create the area containing the game title.
        brand = tk.Frame(inner, bg=COLORS["header"])
        brand.pack(side="left")

        tk.Label(
            brand,
            text="Sudoku Puzzle",
            font=ui_font(26, "bold"),
            bg=COLORS["header"],
            fg=COLORS["text"],
        ).pack(anchor="w")

        # Create the area containing game statistics.
        stats = tk.Frame(inner, bg=COLORS["header"])
        stats.pack(side="right")

        # Create cards showing the current game information.
        self.stat_level = self._stat_card(stats, "LEVEL", "Easy")
        self.stat_time = self._stat_card(stats, "TIME LEFT", "10:00")
        self.stat_mistakes = self._stat_card(stats, "MISTAKES", "0")
        self.stat_hints = self._stat_card(stats, "AI HINTS", "0/3")
        self.stat_score = self._stat_card(stats, "SCORE", "0")

        # Add the blue line below the header.
        tk.Frame(self.root, bg=COLORS["accent"], height=3).pack(fill="x")

    def _stat_card(self, parent, caption, value):
        # Create a small card for one game statistic.
        card = tk.Frame(parent, bg=COLORS["card"], padx=10, pady=8)
        card.pack(side="left", padx=(10, 0))

        # Display the name of the statistic.
        tk.Label(
            card,
            text=caption,
            font=ui_font(8, "bold"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).pack(anchor="w")

        # Display the current value of the statistic.
        value_label = tk.Label(
            card,
            text=value,
            font=ui_font(16, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
        )
        value_label.pack(anchor="w")

        # Return the label so its value can be updated later.
        return value_label

    def _build_board(self, parent):
        # Create the frame surrounding the Sudoku board.
        wrap = tk.Frame(parent, bg=COLORS["surface"], padx=14, pady=14)
        wrap.pack(side="left")

        # Calculate the total board size in pixels.
        board_px = BOARD_PAD * 2 + CELL_SIZE * 9

        # Canvas is used to draw the Sudoku grid and numbers.
        self.board_canvas = tk.Canvas(
            wrap,
            width=board_px,
            height=board_px,
            bg=COLORS["board_frame"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.board_canvas.pack()

        # Mouse click selects a Sudoku cell.
        self.board_canvas.bind("<Button-1>", self._on_board_click)

        # Mouse movement highlights the cell being hovered over.
        self.board_canvas.bind("<Motion>", self._on_board_move)

        # Remove the hover effect when the mouse leaves the board.
        self.board_canvas.bind("<Leave>", self._on_board_leave)

        # Draw the initial board.
        self._draw_board()

    def _build_sidebar(self, parent):
        # Create the right-side control panel.
        side = tk.Frame(parent, bg=COLORS["bg"], width=300)
        side.pack(side="left", fill="both", padx=(20, 0))

        # Difficulty section title.
        tk.Label(
            side,
            text="DIFFICULTY",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(2, 8))

        # Frame containing the difficulty buttons.
        levels = tk.Frame(side, bg=COLORS["card"])
        levels.pack(fill="x")

        # Create Easy, Medium, and Hard buttons.
        for name in ("Easy", "Medium", "Hard"):
            button = tk.Label(
                levels,
                text=name,
                font=ui_font(12, "bold"),
                bg=COLORS["level_off"],
                fg=COLORS["muted"],
                pady=10,
                cursor="hand2",
            )
            button.pack(side="left", expand=True, fill="x")

            # Clicking a level starts a new game at that difficulty.
            button.bind("<Button-1>", lambda _event, d=name: self.change_difficulty(d))

            # Store the button so its appearance can be updated later.
            self.level_buttons[name] = button

        # Numbers section title.
        tk.Label(
            side,
            text="NUMBERS",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(18, 8))

        # Create the number-pad area.
        pad = tk.Frame(side, bg=COLORS["bg"])
        pad.pack(fill="x")

        # Create number buttons from 1 to 9.
        for index, number in enumerate(range(1, 10)):
            row = index // 3
            col = index % 3

            # Create one number tile.
            tile = self._number_tile(pad, number)

            # Place the tile in a 3x3 arrangement.
            tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            pad.grid_columnconfigure(col, weight=1)

        # Actions section title.
        tk.Label(
            side,
            text="ACTIONS",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(16, 8))

        # Create the action button area.
        actions = tk.Frame(side, bg=COLORS["bg"])
        actions.pack(fill="x")

        # Erase removes a player's number.
        self._action_tile(
            actions,
            "Erase",
            "Remove a number",
            COLORS["btn_erase"],
            self.delete_number,
            0,
            0,
        )

        # Undo reverses the player's most recent action.
        self._action_tile(
            actions,
            "Undo",
            "Reverse last move",
            COLORS["btn_undo"],
            self.undo,
            0,
            1,
        )

        # AI Hint gives the player a hint for an empty cell.
        self._action_tile(
            actions,
            "AI Hint",
            "Show candidates",
            COLORS["btn_hint"],
            self.show_ai_hint,
            1,
            0,
        )

        # New Game generates a new Sudoku puzzle.
        self._action_tile(
            actions,
            "New Game",
            "Shuffle a puzzle",
            COLORS["btn_new"],
            self.start_new_game,
            1,
            1,
        )

        # Make both action columns expand equally.
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

    def _build_status_bar(self):
        """Full-width message bar so feedback is never clipped under the buttons."""
        # Create the message bar at the bottom of the window.
        bar = tk.Frame(self.root, bg=COLORS["card"])
        bar.pack(fill="x", padx=24, pady=(0, 18))

        # This label displays messages such as Correct!, Incorrect,
        # and instructions for the player.
        self.status_label = tk.Label(
            bar,
            text="Select a cell, then enter a number. The timer starts when you make a move.",
            font=ui_font(13, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            justify="center",
            pady=14,
        )
        self.status_label.pack(fill="x")

    def _number_tile(self, parent, number):
        # Create a button-like tile for one number.
        tile = tk.Frame(parent, bg=COLORS["btn_number"], padx=2, pady=6)

        # Display the number.
        number_label = tk.Label(
            tile,
            text=str(number),
            font=ui_font(22, "bold"),
            bg=COLORS["btn_number"],
            fg=COLORS["btn_text"],
        )
        number_label.pack()

        # Display how many copies of the number are still available.
        count_label = tk.Label(
            tile,
            text="9 left",
            font=ui_font(10, "bold"),
            bg=COLORS["btn_number"],
            fg="#FFFFFF",
        )
        count_label.pack()

        # Store the widgets so their appearance/count can be updated.
        self.number_tiles[number] = {
            "frame": tile,
            "number": number_label,
            "count": count_label,
        }

        # Make the tile clickable.
        self._bind_tile(
            tile,
            lambda n=number: self.enter_number(n),
            COLORS["btn_number"],
        )

        return tile

    def _action_tile(self, parent, title, subtitle, color, command, row, col):
        # Create one action tile such as Erase, Undo, AI Hint, or New Game.
        tile = tk.Frame(parent, bg=color, padx=10, pady=12)

        # Position the tile in the action grid.
        tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        # Display the main action name.
        tk.Label(
            tile,
            text=title,
            font=ui_font(13, "bold"),
            bg=color,
            fg=COLORS["btn_text"],
        ).pack()

        # Display a short description of the action.
        tk.Label(
            tile,
            text=subtitle,
            font=ui_font(11, "bold"),
            bg=color,
            fg="#FFFFFF",
        ).pack(pady=(4, 0))

        # Make the entire tile clickable.
        self._bind_tile(tile, command, color)

    def _bind_tile(self, tile, command, color):
        """Make a Frame and its labels act like a colored button (works on macOS)."""
        # Change the tile and all its children to the given color.
        def apply(fill):
            tile.configure(bg=fill)
            for child in tile.winfo_children():
                child.configure(bg=fill)

        # Lighten the tile when the mouse enters it.
        def on_enter(_event):
            apply(_lighten(tile._normal_bg))

        # Restore the original color when the mouse leaves it.
        def on_leave(_event):
            apply(tile._normal_bg)

        # Save the original color.
        tile._normal_bg = color

        # Make both the frame and its labels behave like a button.
        widgets = [tile] + list(tile.winfo_children())
        for widget in widgets:
            widget.configure(cursor="hand2")

            # Run the command when the tile is clicked.
            widget.bind("<Button-1>", lambda _event: command())

            # Apply hover effect.
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _ui_button(self, parent, text, bg, command, width=12):
        # Create a label that visually works like a button.
        button = tk.Label(
            parent,
            text=text,
            font=ui_font(12, "bold"),
            bg=bg,
            fg=COLORS["btn_text"],
            width=width,
            padx=12,
            pady=10,
            cursor="hand2",
        )

        # Save the normal background color.
        button._normal_bg = bg

        # Run the command when clicked.
        button.bind("<Button-1>", lambda _event: command())

        # Lighten the button when hovered.
        button.bind(
            "<Enter>",
            lambda _event: button.config(bg=_lighten(button._normal_bg)),
        )

        # Restore the original color when the mouse leaves.
        button.bind(
            "<Leave>",
            lambda _event: button.config(bg=button._normal_bg),
        )

        return button

    # ----------------------------------------------------------
    # Canvas board
    # ----------------------------------------------------------
    def _cell_at(self, x, y):
        # Convert the mouse's pixel position into a Sudoku row and column.
        col = (x - BOARD_PAD) // CELL_SIZE
        row = (y - BOARD_PAD) // CELL_SIZE

        # Make sure the position is inside the 9x9 board.
        if 0 <= row < 9 and 0 <= col < 9:
            return (int(row), int(col))

        return None

    def _on_board_click(self, event):
        # Find which Sudoku cell was clicked.
        cell = self._cell_at(event.x, event.y)

        # Select the cell if the click was inside the board.
        if cell is not None:
            self.select_cell(*cell)

    def _on_board_move(self, event):
        # Find which cell the mouse is currently over.
        cell = self._cell_at(event.x, event.y)

        # Redraw only when the hovered cell changes.
        if cell != self.hover_cell:
            self.hover_cell = cell
            self._draw_board()

    def _on_board_leave(self, _event):
        # Remove the hover effect when the mouse leaves the board.
        if self.hover_cell is not None:
            self.hover_cell = None
            self._draw_board()

    def refresh_board(self):
        # Redraw the Sudoku board.
        self._draw_board()

        # Update the number buttons and how many numbers remain.
        self._refresh_number_pad()

    def _draw_board(self):
        # Get the canvas used to display the Sudoku board.
        canvas = self.board_canvas

        # Remove the previous drawing before drawing the updated board.
        canvas.delete("all")

        # Draw all 81 Sudoku cells.
        for row in range(9):
            for col in range(9):
                # Calculate the pixel coordinates of this cell.
                x1 = BOARD_PAD + col * CELL_SIZE
                y1 = BOARD_PAD + row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                # Get the correct background, text color, number, and font weight.
                bg, fg, text, weight = self._cell_style(row, col)

                # Draw the cell background.
                canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=bg,
                    outline="",
                )

                # Draw the number if the cell is not empty.
                if text:
                    canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=text,
                        fill=fg,
                        font=ui_font(22, weight),
                    )

                # Draw a blue border around the currently selected cell.
                if self.selected == (row, col):
                    canvas.create_rectangle(
                        x1 + 3,
                        y1 + 3,
                        x2 - 3,
                        y2 - 3,
                        outline=COLORS["accent_deep"],
                        width=2,
                    )

        # Calculate the full board boundaries.
        start = BOARD_PAD
        end = BOARD_PAD + CELL_SIZE * 9

        # Draw the Sudoku grid lines.
        for index in range(10):
            pos = BOARD_PAD + index * CELL_SIZE

            # Every third line separates a 3x3 box.
            thick = index % 3 == 0

            # Use a thicker line for the 3x3 box boundaries.
            width = THICK_LINE if thick else THIN_LINE

            # Choose the appropriate line color.
            color = COLORS["grid_thick"] if thick else COLORS["grid_thin"]

            # Draw vertical and horizontal grid lines.
            canvas.create_line(
                pos,
                start,
                pos,
                end,
                fill=color,
                width=width,
            )
            canvas.create_line(
                start,
                pos,
                end,
                pos,
                fill=color,
                width=width,
            )

        # Show a temporary message before the puzzle is ready.
        if self.current is None:
            canvas.create_text(
                (start + end) / 2,
                (start + end) / 2,
                text="Preparing puzzle…",
                fill=COLORS["muted"],
                font=ui_font(16),
            )

    def _cell_style(self, row, col):
        """Choose fill, text color, glyph, and weight for one cell."""

        # If a puzzle has not been generated yet, return default styling.
        if self.current is None:
            return COLORS["cell"], COLORS["given_fg"], "", "bold"

        # Get the current value and status of the cell.
        value = self.current[row][col]
        status = self.cell_status[row][col]

        # Empty cells show no number.
        text = "" if value == 0 else str(value)

        # Check whether this is the selected or hovered cell.
        selected = self.selected == (row, col)
        hovered = self.hover_cell == (row, col)

        peer = False
        same_number = False

        # Highlight cells related to the selected cell.
        if self.selected is not None:
            selected_row, selected_col = self.selected

            # A peer shares the same row, column, or 3x3 box.
            peer = (
                row == selected_row
                or col == selected_col
                or (
                    row // 3 == selected_row // 3
                    and col // 3 == selected_col // 3
                )
            ) and not selected

            # Get the number currently selected.
            selected_value = self.current[selected_row][selected_col]

            # Highlight other cells containing the same number.
            same_number = (
                selected_value != 0
                and value == selected_value
                and not selected
            )

        # Choose the normal style according to the cell status.
        if status == "given":
            # Original puzzle numbers.
            bg, fg, weight = COLORS["cell_given"], COLORS["given_fg"], "bold"
        elif status == "correct":
            # Correct numbers entered by the player.
            bg, fg, weight = COLORS["cell_correct"], COLORS["correct_fg"], "bold"
        elif status == "incorrect":
            # Incorrect numbers entered by the player.
            bg, fg, weight = COLORS["cell_wrong"], COLORS["wrong_fg"], "bold"
        else:
            # Empty cells and normal player cells.
            bg, fg, weight = COLORS["cell"], COLORS["player_fg"], "bold"

        # Incorrect cells always remain red.
        if status == "incorrect":
            bg = COLORS["cell_wrong"]

        # Selected cell gets the selected-cell color.
        elif selected:
            bg = COLORS["cell_selected"]

        # Cells containing the same number are highlighted.
        elif same_number:
            bg = COLORS["cell_same"]

        # Cells in the same row, column, or box are highlighted.
        elif peer:
            bg = COLORS["cell_peer"]

        # Empty/given/correct cells receive a hover effect.
        elif hovered and status in ("empty", "given", "correct"):
            bg = COLORS["cell_hover"]

        return bg, fg, text, weight

    def _refresh_number_pad(self):
        # Do nothing if a puzzle has not been loaded.
        if self.current is None:
            return

        # Update each number tile.
        for number, widgets in self.number_tiles.items():
            # Count how many copies of this number are already placed.
            remaining = 9 - self._count_placed(number)

            # A number is done when all 9 copies are placed.
            done = remaining <= 0

            # Use a darker color when the number is finished.
            bg = COLORS["btn_number_done"] if done else COLORS["btn_number"]

            # Use muted text for completed numbers.
            count_fg = COLORS["muted"] if done else "#FFFFFF"

            # Display "done" or the number of remaining copies.
            text = "done" if done else f"{remaining} left"

            # Update the tile colors and text.
            widgets["frame"]._normal_bg = bg
            widgets["frame"].configure(bg=bg)
            widgets["number"].configure(
                bg=bg,
                fg=COLORS["btn_text"] if not done else COLORS["muted"],
            )
            widgets["count"].configure(
                bg=bg,
                fg=count_fg,
                text=text,
            )

    def _count_placed(self, number):
        # Count how many valid copies of a number are currently on the board.
        total = 0

        for row in range(9):
            for col in range(9):
                # Incorrect guesses are not counted as valid placements.
                if (
                    self.current[row][col] == number
                    and self.cell_status[row][col] != "incorrect"
                ):
                    total += 1

        return total

    # ----------------------------------------------------------
    # Starting and resetting a game
    # ----------------------------------------------------------
    def start_new_game(self, difficulty=None):
        """Generate a new shuffled puzzle and reset all counters."""

        # Change difficulty if one was provided.
        if difficulty is not None:
            self.difficulty = difficulty

        # Stop the timer from the previous game.
        self._stop_timer()

        # Temporarily disable the active game state.
        self.game_active = False
        self.paused = True

        # Tell the player that a new puzzle is being generated.
        self.set_status("Generating a new puzzle...", "info")

        # Show the waiting cursor while generating.
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        # Get the settings for the selected difficulty.
        settings = DIFFICULTY_SETTINGS[self.difficulty]

        # Ask sudoku_generator.py to create a puzzle and solution.
        puzzle, solution = generate_puzzle(
            difficulty=self.difficulty,
            clue_count=settings["clues"],
            previous_puzzle=self.previous_puzzle,
        )

        # Save the puzzle so the next game can try to be different.
        self.previous_puzzle = [row[:] for row in puzzle]

        # Store the new puzzle and its solution.
        self.puzzle = puzzle
        self.solution = solution

        # Create the player's current board from the puzzle.
        self.current = [row[:] for row in puzzle]

        # Mark original numbers as "given" and empty cells as "empty".
        self.cell_status = [
            ["given" if puzzle[r][c] != 0 else "empty" for c in range(9)]
            for r in range(9)
        ]

        # Reset the selection and hover state.
        self.selected = None
        self.hover_cell = None

        # Clear the undo history.
        self.undo_stack = []

        # Reset mistakes and hints.
        self.mistakes = 0
        self.hints_used = 0

        # Set the timer based on the selected difficulty.
        self.total_time = settings["time_seconds"]
        self.time_left = settings["time_seconds"]

        # The timer will start when the player makes the first action.
        self.timer_started = False

        # Activate the new game.
        self.paused = False
        self.game_active = True

        # Restore the normal cursor.
        self.root.config(cursor="")

        # Update the selected difficulty button.
        self._update_level_buttons()

        # Draw the new board and update the interface.
        self.refresh_board()
        self.refresh_header()

        # Display the starting instruction.
        self.set_status(
            "Select a cell, then enter a number. The timer starts when you make a move.",
            "info",
        )

    def change_difficulty(self, difficulty):
        """Start a brand-new game at a different level."""

        # Generate a new puzzle using the selected difficulty.
        self.start_new_game(difficulty)

    # ----------------------------------------------------------
    # Header and status
    # ----------------------------------------------------------
    def refresh_header(self):
        """Update level, timer, mistakes, and live score."""

        # Calculate the current score.
        # Time bonus is only applied after completion.
        score = calculate_score(
            self.difficulty,
            self.time_left,
            self.mistakes,
            self.hints_used,
            completed=False,
        )

        # Update all header statistics.
        self.stat_level.config(text=self.difficulty)
        self.stat_time.config(text=format_time(self.time_left))
        self.stat_mistakes.config(text=str(self.mistakes))
        self.stat_hints.config(text=f"{self.hints_used}/{MAX_AI_HINTS}")
        self.stat_score.config(text=str(score))

    def _update_level_buttons(self):
        # Update the visual appearance of the difficulty buttons.
        for name, button in self.level_buttons.items():
            if name == self.difficulty:
                # Highlight the currently selected difficulty.
                button.config(
                    bg=COLORS["level_on"],
                    fg=COLORS["btn_text"],
                )
            else:
                # Keep other difficulty buttons inactive.
                button.config(
                    bg=COLORS["level_off"],
                    fg=COLORS["muted"],
                )

    def set_status(self, message, kind="info"):
        # Define the colors used for different types of messages.
        colors = {
            "correct": COLORS["good"],
            "incorrect": COLORS["bad"],
            "info": COLORS["text"],
        }

        # Update the status message and its color.
        self.status_label.config(
            text=message,
            fg=colors.get(kind, COLORS["text"]),
        )

    # ----------------------------------------------------------
    # Player actions
    # ----------------------------------------------------------
    def select_cell(self, row, col):
        # Do not allow cell selection after the game ends.
        if not self.game_active:
            return

        # Start the timer when the player first interacts with the board.
        self._begin_timer()

        # Store the selected cell.
        self.selected = (row, col)

        # Redraw the board to show the selection.
        self.refresh_board()

    def enter_number(self, number):
        """Place a number in the selected empty cell and check it with AI."""

        # Check whether the game currently allows editing.
        if not self._can_edit():
            return

        # Start the timer when the player enters a number.
        self._begin_timer()

        # A cell must be selected before entering a number.
        if self.selected is None:
            self.set_status("Select an empty cell first.", "info")
            return

        # Get the selected cell coordinates.
        row, col = self.selected

        # Original puzzle numbers cannot be changed.
        if self.cell_status[row][col] == "given":
            self.set_status("Original numbers cannot be changed.", "info")
            return

        # Do nothing if the same number is already in the cell.
        if self.current[row][col] == number:
            return

        # Save the previous state so the action can be undone.
        self._save_undo(row, col)

        # Put the player's number into the board.
        self.current[row][col] = number

        # Ask sudoku_solver.py whether the entered number
        # matches the generated AI solution.
        if is_correct_number(self.solution, row, col, number):
            # Correct answer.
            self.cell_status[row][col] = "correct"
            self.set_status("Correct!", "correct")
        else:
            # Wrong answer.
            self.cell_status[row][col] = "incorrect"
            self.mistakes += 1
            self.set_status("Incorrect number.", "incorrect")

            # Update the board and statistics.
            self.refresh_board()
            self.refresh_header()

            # Every 2 mistakes can trigger an automatic AI hint.
            if self.mistakes % MISTAKES_PER_AI_HINT == 0:
                self._give_mistake_hint()

            return

        # Refresh the interface after a correct answer.
        self.refresh_board()
        self.refresh_header()

        # Check whether the entire Sudoku has been solved.
        self._check_completion()

    def delete_number(self):
        """Clear a player-entered number. Original clues stay locked."""

        # Do not allow editing if the game is inactive or paused.
        if not self._can_edit():
            return

        # Start the timer.
        self._begin_timer()

        # A cell must be selected first.
        if self.selected is None:
            self.set_status("Select a cell to delete.", "info")
            return

        # Get the selected cell coordinates.
        row, col = self.selected

        # Original clues cannot be deleted.
        if self.cell_status[row][col] == "given":
            self.set_status("Original numbers cannot be deleted.", "info")
            return

        # Nothing needs to be deleted if the cell is already empty.
        if self.current[row][col] == 0:
            return

        # Save the current state for undo.
        self._save_undo(row, col)

        # Clear the cell.
        self.current[row][col] = 0
        self.cell_status[row][col] = "empty"

        # Update the board and statistics.
        self.refresh_board()
        self.refresh_header()

        # Tell the player the number was removed.
        self.set_status("Number deleted.", "info")

    def undo(self):
        """Undo the most recent player entry or delete."""

        # Do not allow undo when the game is inactive or paused.
        if not self._can_edit():
            return

        # Start the timer.
        self._begin_timer()

        # Check whether there is an action to undo.
        if not self.undo_stack:
            self.set_status("Nothing to undo.", "info")
            return

        # Get the most recent saved action.
        action = self.undo_stack.pop()

        # Restore the cell's previous coordinates, value, and status.
        row = action["row"]
        col = action["col"]
        self.current[row][col] = action["prev_value"]
        self.cell_status[row][col] = action["prev_status"]

        # Select the restored cell.
        self.selected = (row, col)

        # Update the interface.
        self.refresh_board()
        self.refresh_header()

        # Tell the player the action was undone.
        self.set_status("Last move undone.", "info")

    def show_ai_hint(self):
        """Show candidates and one AI recommendation for the selected cell."""

        # Do nothing if the game is no longer active.
        if not self.game_active:
            return

        # Start the timer.
        self._begin_timer()

        # Stop if the maximum number of hints has already been used.
        if self.hints_used >= MAX_AI_HINTS:
            self.set_status("No more AI hints remaining.", "info")
            return

        # Find an empty cell for the hint.
        cell = self._cell_for_hint()

        # If no empty cell exists, show a message.
        if cell is None:
            self.set_status("Select an empty cell to get an AI hint.", "info")
            return

        # Get the selected cell coordinates.
        row, col = cell
        self.selected = (row, col)

        # Highlight the cell.
        self.refresh_board()

        # Ask ai_hint.py to create the hint.
        # The hint system uses the solver to find legal candidates.
        hint = get_hint(
            self._board_for_hints(),
            row,
            col,
            self.solution,
        )

        # If the cell is not valid for a hint, show an instruction.
        if hint is None:
            self.set_status("Select an empty cell to get an AI hint.", "info")
            return

        # Increase the number of hints used.
        self.hints_used += 1
        self.refresh_header()

        # Pause the game while the hint popup is displayed.
        self.paused = True

        # Display the AI hint to the player.
        messagebox.showinfo("AI Hint", hint["message"])

        # Resume the game after the popup is closed.
        self.paused = False

        # Show the recommended number in the status bar.
        self.set_status(
            f"AI Recommendation: {hint['recommendation']}",
            "info",
        )

    def _save_undo(self, row, col):
        # Save the current state of a cell before changing it.
        # This information is later used by the undo function.
        self.undo_stack.append(
            {
                "row": row,
                "col": col,
                "prev_value": self.current[row][col],
                "prev_status": self.cell_status[row][col],
            }
        )

    def _can_edit(self):
        # Return True only when the player is allowed to modify the board.
        return self.game_active and not self.paused

    def _cell_for_hint(self):
        """Use the selected empty cell, or the first empty cell if needed."""

        # If the selected cell is empty, use it.
        if self.selected is not None:
            row, col = self.selected
            if self.current[row][col] == 0:
                return (row, col)

        # Otherwise, find the first empty cell on the board.
        for row in range(9):
            for col in range(9):
                if self.current[row][col] == 0:
                    return (row, col)

        # Return None if there are no empty cells.
        return None

    def _board_for_hints(self):
        """Copy the board but treat incorrect guesses as empty."""

        # Create a copy so the actual game board is not changed.
        board = [row[:] for row in self.current]

        # Incorrect guesses should not interfere with candidate calculation.
        for row in range(9):
            for col in range(9):
                if self.cell_status[row][col] == "incorrect":
                    board[row][col] = 0

        return board

    def _on_key(self, event):
        """Allow typing 1-9, Delete, Backspace, and arrow-key navigation."""

        # Allow the player to enter numbers using the keyboard.
        if event.char in "123456789":
            self.enter_number(int(event.char))

        # Allow Backspace or Delete to erase a number.
        elif event.keysym in ("BackSpace", "Delete"):
            self.delete_number()

        # Allow arrow keys to move between cells.
        elif event.keysym in ("Up", "Down", "Left", "Right"):
            self._move_selection(event.keysym)

    def _move_selection(self, direction):
        # Do not move the selection after the game ends.
        if not self.game_active:
            return

        # Use the selected cell, or start at the top-left cell.
        row, col = self.selected if self.selected is not None else (0, 0)

        # Move the selected cell according to the arrow key.
        if direction == "Up":
            row = (row - 1) % 9
        elif direction == "Down":
            row = (row + 1) % 9
        elif direction == "Left":
            col = (col - 1) % 9
        elif direction == "Right":
            col = (col + 1) % 9

        # Select the new cell.
        self.select_cell(row, col)

    # ----------------------------------------------------------
    # AI assistance after every 2 mistakes (max 3 hints)
    # ----------------------------------------------------------
    def _give_mistake_hint(self):
        """Automatically give an AI hint after 2, 4, and 6 mistakes."""

        # Stop giving hints after the maximum number has been reached.
        if self.hints_used >= MAX_AI_HINTS:
            self.set_status("No more AI hints remaining.", "info")
            return

        # Show the AI hint.
        self.show_ai_hint()

    # ----------------------------------------------------------
    # Timer
    # ----------------------------------------------------------
    def _begin_timer(self):
        """Start the countdown after the player's first action."""

        # Do not start another timer if one is already running.
        if self.timer_started or not self.game_active:
            return

        # Mark the timer as started.
        self.timer_started = True

        # Start the countdown.
        self._start_timer()

    def _start_timer(self):
        # Stop any previous timer callback.
        self._stop_timer()

        # Schedule _tick to run every second.
        self.timer_id = self.root.after(1000, self._tick)

    def _stop_timer(self):
        # Cancel the scheduled timer if one exists.
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def _tick(self):
        # Stop updating the timer if the game is no longer active.
        if not self.game_active:
            return

        # Only decrease the timer when the game is not paused.
        if not self.paused:
            self.time_left -= 1

            # If the timer reaches zero, end the game.
            if self.time_left <= 0:
                self.time_left = 0
                self.refresh_header()
                self._on_timeout()
                return

            # Update the displayed timer.
            self.refresh_header()

        # Schedule the next timer update.
        self.timer_id = self.root.after(1000, self._tick)

    def _on_timeout(self):
        # Mark the game as finished.
        self.game_active = False

        # Stop the timer.
        self._stop_timer()

        # Tell the player that time has expired.
        messagebox.showinfo(
            "Time's Up!",
            "Time's Up!\n\n"
            "You could not complete the puzzle in time.\n\n"
            "A new shuffled puzzle will now start.",
        )

        # Automatically start a new puzzle at the same difficulty.
        self.start_new_game(self.difficulty)

    # ----------------------------------------------------------
    # Puzzle completion
    # ----------------------------------------------------------
    def _check_completion(self):
        # Ask sudoku_solver.py whether every cell is filled correctly.
        if not is_board_complete_and_correct(self.current, self.solution):
            return

        # Stop the game because the puzzle has been solved.
        self.game_active = False
        self._stop_timer()

        # Calculate how much time the player used.
        time_used = self.total_time - self.time_left

        # Calculate the final score.
        # This time the leftover-time and completion bonuses are included.
        score = calculate_score(
            self.difficulty,
            self.time_left,
            self.mistakes,
            self.hints_used,
            completed=True,
        )

        # Display the final score.
        self.stat_score.config(text=str(score))

        # Display the success message.
        self.set_status(
            "Congratulations! You solved the Sudoku!",
            "correct",
        )

        # Open the completion dialog.
        self._show_win_dialog(time_used, score)

    def _show_win_dialog(self, time_used, score):
        # Create a separate popup window for the completed game.
        dialog = tk.Toplevel(self.root)
        dialog.title("Puzzle Complete")
        dialog.configure(bg=COLORS["bg"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Create the main card inside the popup.
        card = tk.Frame(
            dialog,
            bg=COLORS["surface"],
            padx=28,
            pady=24,
        )
        card.pack(padx=8, pady=8)

        # Display the completion title.
        tk.Label(
            card,
            text="Puzzle complete",
            font=ui_font(20, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"],
        ).pack(pady=(0, 6))

        # Display the success message.
        tk.Label(
            card,
            text="You solved the Sudoku!",
            font=ui_font(12),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
        ).pack()

        # Create a summary section for the final statistics.
        summary = tk.Frame(card, bg=COLORS["card"])
        summary.pack(fill="x", pady=18)

        # Display time, mistakes, hints, and final score.
        for label, value in (
            ("Time", format_time(time_used)),
            ("Mistakes", str(self.mistakes)),
            ("Hints", str(self.hints_used)),
            ("Score", str(score)),
        ):
            row = tk.Frame(summary, bg=COLORS["card"])
            row.pack(fill="x", padx=16, pady=6)

            # Statistic name.
            tk.Label(
                row,
                text=label,
                font=ui_font(11),
                bg=COLORS["card"],
                fg=COLORS["muted"],
            ).pack(side="left")

            # Statistic value.
            tk.Label(
                row,
                text=value,
                font=ui_font(12, "bold"),
                bg=COLORS["card"],
                fg=COLORS["text"],
            ).pack(side="right")

        # Create the area containing the two options.
        buttons = tk.Frame(card, bg=COLORS["surface"])
        buttons.pack()

        # Start another puzzle at the same difficulty.
        self._ui_button(
            buttons,
            "Play Again",
            COLORS["btn_hint"],
            lambda: self._close_win_dialog(dialog, play_again=True),
        ).pack(side="left", padx=6)

        # Open the difficulty selector.
        self._ui_button(
            buttons,
            "Change Level",
            COLORS["btn_new"],
            lambda: self._close_win_dialog(dialog, play_again=False),
        ).pack(side="left", padx=6)

        # Center the popup on the main game window.
        dialog.update_idletasks()
        self._center_dialog(dialog)

    def _close_win_dialog(self, dialog, play_again):
        # Close the completion popup.
        dialog.destroy()

        # Either start another game or show the difficulty selector.
        if play_again:
            self.start_new_game(self.difficulty)
        else:
            self._show_level_picker()

    def _show_level_picker(self):
        # Create a popup for selecting a new difficulty.
        picker = tk.Toplevel(self.root)
        picker.title("Change Level")
        picker.configure(bg=COLORS["bg"])
        picker.resizable(False, False)
        picker.transient(self.root)
        picker.grab_set()

        # Create the popup card.
        card = tk.Frame(
            picker,
            bg=COLORS["surface"],
            padx=24,
            pady=20,
        )
        card.pack(padx=8, pady=8)

        # Display the popup title.
        tk.Label(
            card,
            text="Choose a level",
            font=ui_font(16, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"],
        ).pack(pady=(0, 14))

        # Create the row containing the three difficulty buttons.
        row = tk.Frame(card, bg=COLORS["surface"])
        row.pack()

        # Create Easy, Medium, and Hard buttons.
        for name, color in (
            ("Easy", "#059669"),
            ("Medium", "#2563EB"),
            ("Hard", "#E11D48"),
        ):
            self._ui_button(
                row,
                name,
                color,
                lambda d=name: self._pick_level(picker, d),
                width=10,
            ).pack(side="left", padx=6)

        # Center the difficulty popup.
        picker.update_idletasks()
        self._center_dialog(picker)

    def _pick_level(self, picker, difficulty):
        # Close the level selector.
        picker.destroy()

        # Start a new game using the selected difficulty.
        self.start_new_game(difficulty)

    def _center_dialog(self, dialog):
        # Make sure the popup's size has been calculated.
        dialog.update_idletasks()

        # Get the popup dimensions.
        width = dialog.winfo_width()
        height = dialog.winfo_height()

        # Calculate the position needed to center it over the main window.
        x = self.root.winfo_x() + (
            self.root.winfo_width() - width
        ) // 2
        y = self.root.winfo_y() + (
            self.root.winfo_height() - height
        ) // 2

        # Move the popup to the calculated position.
        dialog.geometry(f"+{x}+{y}")

    def _on_close(self):
        # Mark the game as inactive before closing.
        self.game_active = False

        # Stop the timer.
        self._stop_timer()

        # Close the main Tkinter window.
        self.root.destroy()
