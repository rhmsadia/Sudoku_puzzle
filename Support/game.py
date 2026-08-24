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

# Import Tkinter for creating the graphical user interface.
import tkinter as tk

# Import messagebox for displaying popup messages.
from tkinter import messagebox

# Import the AI hint function.
from ai_hint import get_hint

# Import the scoring function.
from scoring import calculate_score

# Import the Sudoku puzzle generator.
from sudoku_generator import generate_puzzle

# Import functions used to check player answers and puzzle completion.
from sudoku_solver import is_board_complete_and_correct, is_correct_number


# ============================================================
# GAME SETTINGS  (edit these values to customize the game)
# ============================================================
# Easy:   more given numbers, 10 minutes
# Medium: fewer given numbers, 7 minutes
# Hard:   fewest given numbers, 5 minutes
DIFFICULTY_SETTINGS = {
    "Easy": {
        # Maximum time allowed for an Easy puzzle.
        "time_seconds": 10 * 60,

        # Number of starting clues shown to the player.
        "clues": 40,
    },
    "Medium": {
        # Maximum time allowed for a Medium puzzle.
        "time_seconds": 7 * 60,

        # Number of starting clues shown to the player.
        "clues": 32,
    },
    "Hard": {
        # Maximum time allowed for a Hard puzzle.
        "time_seconds": 5 * 60,

        # Number of starting clues shown to the player.
        "clues": 26,
    },
}

# Give one AI hint after every 2 mistakes, up to 3 hints total.
MISTAKES_PER_AI_HINT = 2
MAX_AI_HINTS = 3

# Set Easy as the starting difficulty.
DEFAULT_DIFFICULTY = "Easy"

# ============================================================
# VISUAL DESIGN
# ============================================================
# Main font used throughout the application.
FONT = "Helvetica Neue"

# Store all colors used by the game interface.
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

# Size of each Sudoku cell in pixels.
CELL_SIZE = 58

# Space around the Sudoku board.
BOARD_PAD = 10

# Width of normal grid lines.
THIN_LINE = 1

# Width of the thicker 3x3 box lines.
THICK_LINE = 3


def format_time(seconds):
    """Turn 322 seconds into '05:22'."""
    # Make sure the time is never negative and is an integer.
    seconds = max(0, int(seconds))

    # Calculate the number of complete minutes.
    minutes = seconds // 60

    # Calculate the remaining seconds.
    secs = seconds % 60

    # Return the time in MM:SS format.
    return f"{minutes:02d}:{secs:02d}"


def ui_font(size, weight="normal"):
    # Return a font configuration used by Tkinter widgets.
    return (FONT, size, weight)


def _lighten(hex_color, amount=0.18):
    """Mix a hex color toward white for hover."""
    # Remove the # symbol from the hexadecimal color.
    hex_color = hex_color.lstrip("#")

    # Convert each pair of hexadecimal characters into RGB values.
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)

    # Move each RGB value slightly toward white.
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

        # Set the window title.
        self.root.title("Sudoku Puzzle")

        # Set the background color of the main window.
        self.root.configure(bg=COLORS["bg"])

        # Prevent the user from resizing the window.
        self.root.resizable(False, False)

        # Game state
        # Store the current difficulty level.
        self.difficulty = DEFAULT_DIFFICULTY

        # Store the original puzzle.
        self.puzzle = None

        # Store the completed solution.
        self.solution = None

        # Store the current state of the board.
        self.current = None

        # Store the status of every cell.
        self.cell_status = None

        # Store the currently selected cell.
        self.selected = None

        # Store the cell currently under the mouse pointer.
        self.hover_cell = None

        # Store previous moves for the undo feature.
        self.undo_stack = []

        # Count the number of incorrect answers.
        self.mistakes = 0

        # Count the number of AI hints used.
        self.hints_used = 0

        # Store the remaining time.
        self.time_left = 0

        # Store the original total time for the puzzle.
        self.total_time = 0

        # Store the Tkinter timer ID.
        self.timer_id = None

        # Track whether the timer has started.
        self.timer_started = False

        # Track whether the game is currently active.
        self.game_active = False

        # Track whether the game is temporarily paused.
        self.paused = False

        # Store the previous puzzle to avoid generating the same puzzle again.
        self.previous_puzzle = None

        # Widgets filled in by _build_ui
        # Store references to the main board canvas.
        self.board_canvas = None

        # Store references to the statistic labels.
        self.stat_level = None
        self.stat_time = None
        self.stat_mistakes = None
        self.stat_hints = None
        self.stat_score = None

        # Store the status message label.
        self.status_label = None

        # Store the difficulty buttons.
        self.level_buttons = {}

        # Store the number buttons.
        self.number_tiles = {}

        # Build the graphical interface.
        self._build_ui()

        # Handle the window close button.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Listen for keyboard input.
        self.root.bind("<Key>", self._on_key)

        # Start the first game after the window is drawn.
        self.root.after(50, self.start_new_game)

    # ----------------------------------------------------------
    # User interface
    # ----------------------------------------------------------
    def _build_ui(self):
        """Create the modern header, canvas board, and side controls."""
        # Create the top header.
        self._build_header()

        # Create the main body area.
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=(6, 8))

        # Create the Sudoku board.
        self._build_board(body)

        # Create the controls on the right side.
        self._build_sidebar(body)

        # Create the status message bar.
        self._build_status_bar()

    def _build_header(self):
        # Create the header background.
        header = tk.Frame(self.root, bg=COLORS["header"])
        header.pack(fill="x")

        # Create the inner header area.
        inner = tk.Frame(header, bg=COLORS["header"])
        inner.pack(fill="x", padx=24, pady=16)

        # Create the brand section.
        brand = tk.Frame(inner, bg=COLORS["header"])
        brand.pack(side="left")

        # Display the game title.
        tk.Label(
            brand,
            text="Sudoku Puzzle",
            font=ui_font(26, "bold"),
            bg=COLORS["header"],
            fg=COLORS["text"],
        ).pack(anchor="w")

        # Create the statistics section.
        stats = tk.Frame(inner, bg=COLORS["header"])
        stats.pack(side="right")

        # Create cards for the game statistics.
        self.stat_level = self._stat_card(stats, "LEVEL", "Easy")
        self.stat_time = self._stat_card(stats, "TIME LEFT", "10:00")
        self.stat_mistakes = self._stat_card(stats, "MISTAKES", "0")
        self.stat_hints = self._stat_card(stats, "AI HINTS", "0/3")
        self.stat_score = self._stat_card(stats, "SCORE", "0")

        # Add a colored line below the header.
        tk.Frame(self.root, bg=COLORS["accent"], height=3).pack(fill="x")

    def _stat_card(self, parent, caption, value):
        # Create the card that displays one game statistic.
        card = tk.Frame(parent, bg=COLORS["card"], padx=10, pady=8)
        card.pack(side="left", padx=(10, 0))

        # Display the statistic name.
        tk.Label(
            card,
            text=caption,
            font=ui_font(8, "bold"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).pack(anchor="w")

        # Display the current statistic value.
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
        # Create a frame around the Sudoku board.
        wrap = tk.Frame(parent, bg=COLORS["surface"], padx=14, pady=14)
        wrap.pack(side="left")

        # Calculate the total size of the board.
        board_px = BOARD_PAD * 2 + CELL_SIZE * 9

        # Create the canvas used to draw the Sudoku board.
        self.board_canvas = tk.Canvas(
            wrap,
            width=board_px,
            height=board_px,
            bg=COLORS["board_frame"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.board_canvas.pack()

        # Detect mouse clicks on the board.
        self.board_canvas.bind("<Button-1>", self._on_board_click)

        # Detect mouse movement over the board.
        self.board_canvas.bind("<Motion>", self._on_board_move)

        # Detect when the mouse leaves the board.
        self.board_canvas.bind("<Leave>", self._on_board_leave)

        # Draw the initial board.
        self._draw_board()

    def _build_sidebar(self, parent):
        # Create the sidebar containing difficulty, numbers, and actions.
        side = tk.Frame(parent, bg=COLORS["bg"], width=300)
        side.pack(side="left", fill="both", padx=(20, 0))

        # Display the difficulty section title.
        tk.Label(
            side,
            text="DIFFICULTY",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(2, 8))

        # Create the difficulty button area.
        levels = tk.Frame(side, bg=COLORS["card"])
        levels.pack(fill="x")

        # Create buttons for Easy, Medium, and Hard.
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

            # Change the difficulty when the button is clicked.
            button.bind("<Button-1>", lambda _event, d=name: self.change_difficulty(d))

            # Store the button so its appearance can be updated later.
            self.level_buttons[name] = button

        # Display the number section title.
        tk.Label(
            side,
            text="NUMBERS",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(18, 8))

        # Create the number pad.
        pad = tk.Frame(side, bg=COLORS["bg"])
        pad.pack(fill="x")

        # Create buttons for numbers 1 through 9.
        for index, number in enumerate(range(1, 10)):
            row = index // 3
            col = index % 3

            # Create one number tile.
            tile = self._number_tile(pad, number)

            # Place the tile in a 3x3 layout.
            tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            pad.grid_columnconfigure(col, weight=1)

        # Display the actions section title.
        tk.Label(
            side,
            text="ACTIONS",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(16, 8))

        # Create the action buttons.
        actions = tk.Frame(side, bg=COLORS["bg"])
        actions.pack(fill="x")

        # Add the Erase button.
        self._action_tile(actions, "Erase", "Remove a number", COLORS["btn_erase"], self.delete_number, 0, 0)

        # Add the Undo button.
        self._action_tile(actions, "Undo", "Reverse last move", COLORS["btn_undo"], self.undo, 0, 1)

        # Add the AI Hint button.
        self._action_tile(actions, "AI Hint", "Show candidates", COLORS["btn_hint"], self.show_ai_hint, 1, 0)

        # Add the New Game button.
        self._action_tile(actions, "New Game", "Shuffle a puzzle", COLORS["btn_new"], self.start_new_game, 1, 1)

        # Allow both action columns to expand equally.
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

    def _build_status_bar(self):
        """Full-width message bar so feedback is never clipped under the buttons."""
        # Create the status bar container.
        bar = tk.Frame(self.root, bg=COLORS["card"])
        bar.pack(fill="x", padx=24, pady=(0, 18))

        # Create the label that displays game messages.
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
        # Create the button for a Sudoku number.
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

        # Display how many times the number can still be placed.
        count_label = tk.Label(
            tile,
            text="9 left",
            font=ui_font(10, "bold"),
            bg=COLORS["btn_number"],
            fg="#FFFFFF",
        )
        count_label.pack()

        # Store the widgets so their appearance can be updated later.
        self.number_tiles[number] = {
            "frame": tile,
            "number": number_label,
            "count": count_label,
        }

        # Make the tile clickable.
        self._bind_tile(tile, lambda n=number: self.enter_number(n), COLORS["btn_number"])

        return tile

    def _action_tile(self, parent, title, subtitle, color, command, row, col):
        # Create a colored action tile.
        tile = tk.Frame(parent, bg=color, padx=10, pady=12)

        # Place the tile in the action grid.
        tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        # Display the action title.
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

        # Make the whole tile clickable.
        self._bind_tile(tile, command, color)

    def _bind_tile(self, tile, command, color):
        """Make a Frame and its labels act like a colored button (works on macOS)."""

        # Change the background color of the tile and its children.
        def apply(fill):
            tile.configure(bg=fill)
            for child in tile.winfo_children():
                child.configure(bg=fill)

        # Lighten the tile when the mouse enters.
        def on_enter(_event):
            apply(_lighten(tile._normal_bg))

        # Restore the original color when the mouse leaves.
        def on_leave(_event):
            apply(tile._normal_bg)

        # Store the normal background color.
        tile._normal_bg = color

        # Include the tile and all its child widgets.
        widgets = [tile] + list(tile.winfo_children())

        # Bind mouse actions to every widget.
        for widget in widgets:
            widget.configure(cursor="hand2")

            # Run the command when clicked.
            widget.bind("<Button-1>", lambda _event: command())

            # Change the color when the mouse enters.
            widget.bind("<Enter>", on_enter)

            # Restore the color when the mouse leaves.
            widget.bind("<Leave>", on_leave)

    def _ui_button(self, parent, text, bg, command, width=12):
        # Create a reusable button-like label.
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

        # Store the normal button color.
        button._normal_bg = bg

        # Run the command when clicked.
        button.bind("<Button-1>", lambda _event: command())

        # Lighten the button when hovered.
        button.bind("<Enter>", lambda _event: button.config(bg=_lighten(button._normal_bg)))

        # Restore the normal color after hovering.
        button.bind("<Leave>", lambda _event: button.config(bg=button._normal_bg))

        return button

    # ----------------------------------------------------------
    # Canvas board
    # ----------------------------------------------------------
    def _cell_at(self, x, y):
        # Calculate which column the mouse is over.
        col = (x - BOARD_PAD) // CELL_SIZE

        # Calculate which row the mouse is over.
        row = (y - BOARD_PAD) // CELL_SIZE

        # Make sure the position is inside the 9x9 board.
        if 0 <= row < 9 and 0 <= col < 9:
            return (int(row), int(col))

        # Return None when the position is outside the board.
        return None

    def _on_board_click(self, event):
        # Find the cell clicked by the user.
        cell = self._cell_at(event.x, event.y)

        # Select the cell if the click was inside the board.
        if cell is not None:
            self.select_cell(*cell)

    def _on_board_move(self, event):
        # Find the cell currently under the mouse.
        cell = self._cell_at(event.x, event.y)

        # Redraw the board only when the hovered cell changes.
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

        # Update the number buttons.
        self._refresh_number_pad()

    def _draw_board(self):
        # Get the board canvas.
        canvas = self.board_canvas

        # Remove everything currently drawn on the canvas.
        canvas.delete("all")

        # Draw all 81 Sudoku cells.
        for row in range(9):
            for col in range(9):
                # Calculate the coordinates of the current cell.
                x1 = BOARD_PAD + col * CELL_SIZE
                y1 = BOARD_PAD + row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                # Get the cell's colors, value, and font weight.
                bg, fg, text, weight = self._cell_style(row, col)

                # Draw the cell background.
                canvas.create_rectangle(x1, y1, x2, y2, fill=bg, outline="")

                # Draw the number if the cell is not empty.
                if text:
                    canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=text,
                        fill=fg,
                        font=ui_font(22, weight),
                    )

                # Draw a border around the selected cell.
                if self.selected == (row, col):
                    canvas.create_rectangle(
                        x1 + 3,
                        y1 + 3,
                        x2 - 3,
                        y2 - 3,
                        outline=COLORS["accent_deep"],
                        width=2,
                    )

        # Calculate the board boundaries.
        start = BOARD_PAD
        end = BOARD_PAD + CELL_SIZE * 9

        # Draw the horizontal and vertical grid lines.
        for index in range(10):
            pos = BOARD_PAD + index * CELL_SIZE

            # Every third line is a thick 3x3 box boundary.
            thick = index % 3 == 0
            width = THICK_LINE if thick else THIN_LINE
            color = COLORS["grid_thick"] if thick else COLORS["grid_thin"]

            # Draw vertical and horizontal lines.
            canvas.create_line(pos, start, pos, end, fill=color, width=width)
            canvas.create_line(start, pos, end, pos, fill=color, width=width)

        # Show a loading message before the puzzle is ready.
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
        # Use a blank style while the puzzle is being prepared.
        if self.current is None:
            return COLORS["cell"], COLORS["given_fg"], "", "bold"

        # Get the value and status of the selected cell.
        value = self.current[row][col]
        status = self.cell_status[row][col]

        # Hide zero values because zero represents an empty cell.
        text = "" if value == 0 else str(value)

        # Check whether this cell is selected or hovered.
        selected = self.selected == (row, col)
        hovered = self.hover_cell == (row, col)

        # Track whether the cell shares a row, column, or box with the selected cell.
        peer = False

        # Track whether the cell contains the same number as the selected cell.
        same_number = False

        # Apply highlighting only when a cell is selected.
        if self.selected is not None:
            selected_row, selected_col = self.selected

            # Check whether the cell is in the same row, column, or 3x3 box.
            peer = (
                row == selected_row
                or col == selected_col
                or (row // 3 == selected_row // 3 and col // 3 == selected_col // 3)
            ) and not selected

            # Get the number from the selected cell.
            selected_value = self.current[selected_row][selected_col]

            # Highlight other cells containing the same number.
            same_number = (
                selected_value != 0
                and value == selected_value
                and not selected
            )

        # Choose the default appearance based on the cell status.
        if status == "given":
            bg, fg, weight = COLORS["cell_given"], COLORS["given_fg"], "bold"
        elif status == "correct":
            bg, fg, weight = COLORS["cell_correct"], COLORS["correct_fg"], "bold"
        elif status == "incorrect":
            bg, fg, weight = COLORS["cell_wrong"], COLORS["wrong_fg"], "bold"
        else:
            bg, fg, weight = COLORS["cell"], COLORS["player_fg"], "bold"

        # Give incorrect cells a red background.
        if status == "incorrect":
            bg = COLORS["cell_wrong"]

        # Give the selected cell the strongest highlight.
        elif selected:
            bg = COLORS["cell_selected"]

        # Highlight matching numbers.
        elif same_number:
            bg = COLORS["cell_same"]

        # Highlight cells in the same row, column, or box.
        elif peer:
            bg = COLORS["cell_peer"]

        # Apply a hover effect to available cells.
        elif hovered and status in ("empty", "given", "correct"):
            bg = COLORS["cell_hover"]

        return bg, fg, text, weight

    def _refresh_number_pad(self):
        # Do nothing if a puzzle has not been created yet.
        if self.current is None:
            return

        # Update each number button.
        for number, widgets in self.number_tiles.items():
            # Count how many times this number has already been placed.
            remaining = 9 - self._count_placed(number)

            # Check whether all nine copies have been used.
            done = remaining <= 0

            # Use a darker color when the number is complete.
            bg = COLORS["btn_number_done"] if done else COLORS["btn_number"]

            # Use muted text for completed numbers.
            count_fg = COLORS["muted"] if done else "#FFFFFF"

            # Show "done" or the number of remaining placements.
            text = "done" if done else f"{remaining} left"

            # Update the tile and its labels.
            widgets["frame"]._normal_bg = bg
            widgets["frame"].configure(bg=bg)
            widgets["number"].configure(bg=bg, fg=COLORS["btn_text"] if not done else COLORS["muted"])
            widgets["count"].configure(bg=bg, fg=count_fg, text=text)

    def _count_placed(self, number):
        # Start the counter at zero.
        total = 0

        # Check every cell on the board.
        for row in range(9):
            for col in range(9):

                # Count valid placements of the selected number.
                if self.current[row][col] == number and self.cell_status[row][col] != "incorrect":
                    total += 1

        return total

    # ----------------------------------------------------------
    # Starting and resetting a game
    # ----------------------------------------------------------
    def start_new_game(self, difficulty=None):
        """Generate a new shuffled puzzle and reset all counters."""
        # Update the difficulty if a new difficulty was provided.
        if difficulty is not None:
            self.difficulty = difficulty

        # Stop the timer from the previous game.
        self._stop_timer()

        # Temporarily disable the active game.
        self.game_active = False
        self.paused = True

        # Tell the user that a puzzle is being generated.
        self.set_status("Generating a new puzzle...", "info")

        # Change the cursor to indicate that the program is busy.
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        # Get the settings for the selected difficulty.
        settings = DIFFICULTY_SETTINGS[self.difficulty]

        # Generate a new puzzle and its solution.
        puzzle, solution = generate_puzzle(
            difficulty=self.difficulty,
            clue_count=settings["clues"],
            previous_puzzle=self.previous_puzzle,
        )

        # Store a copy of the puzzle to avoid repeating it.
        self.previous_puzzle = [row[:] for row in puzzle]

        # Store the puzzle and solution.
        self.puzzle = puzzle
        self.solution = solution

        # Create the player's current board from the puzzle.
        self.current = [row[:] for row in puzzle]

        # Mark original numbers as "given" and empty cells as "empty".
        self.cell_status = [
            ["given" if puzzle[r][c] != 0 else "empty" for c in range(9)]
            for r in range(9)
        ]

        # Reset the selected and hovered cells.
        self.selected = None
        self.hover_cell = None

        # Clear the undo history.
        self.undo_stack = []

        # Reset mistakes and hints.
        self.mistakes = 0
        self.hints_used = 0

        # Set the timer according to the difficulty.
        self.total_time = settings["time_seconds"]
        self.time_left = settings["time_seconds"]

        # The timer will start after the first player action.
        self.timer_started = False

        # Activate the new game.
        self.paused = False
        self.game_active = True

        # Restore the normal cursor.
        self.root.config(cursor="")

        # Update the difficulty buttons.
        self._update_level_buttons()

        # Redraw the board.
        self.refresh_board()

        # Update the header statistics.
        self.refresh_header()

        # Display the starting instructions.
        self.set_status("Select a cell, then enter a number. The timer starts when you make a move.", "info")

    def change_difficulty(self, difficulty):
        """Start a brand-new game at a different level."""
        # Start a new game using the selected difficulty.
        self.start_new_game(difficulty)

    # ----------------------------------------------------------
    # Header and status
    # ----------------------------------------------------------
    def refresh_header(self):
        """Update level, timer, mistakes, and live score."""
        # Calculate the player's current score.
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
        # Update the appearance of all difficulty buttons.
        for name, button in self.level_buttons.items():
            # Highlight the currently selected difficulty.
            if name == self.difficulty:
                button.config(bg=COLORS["level_on"], fg=COLORS["btn_text"])
            else:
                # Use the inactive style for other levels.
                button.config(bg=COLORS["level_off"], fg=COLORS["muted"])

    def set_status(self, message, kind="info"):
        # Define colors for different types of status messages.
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
        # Ignore selection if the game is not active.
        if not self.game_active:
            return

        # Start the timer when the player first interacts.
        self._begin_timer()

        # Store the selected cell.
        self.selected = (row, col)

        # Redraw the board to show the selection.
        self.refresh_board()

    def enter_number(self, number):
        """Place a number in the selected empty cell and check it with AI."""
        # Prevent editing when the game cannot be edited.
        if not self._can_edit():
            return

        # Start the timer.
        self._begin_timer()

        # Require the player to select a cell first.
        if self.selected is None:
            self.set_status("Select an empty cell first.", "info")
            return

        # Get the selected cell coordinates.
        row, col = self.selected

        # Prevent changing original puzzle clues.
        if self.cell_status[row][col] == "given":
            self.set_status("Original numbers cannot be changed.", "info")
            return

        # Do nothing if the same number is already in the cell.
        if self.current[row][col] == number:
            return

        # Save the current state so the action can be undone.
        self._save_undo(row, col)

        # Place the player's number.
        self.current[row][col] = number

        # Check the entered number against the solution.
        if is_correct_number(self.solution, row, col, number):
            # Mark the cell as correct.
            self.cell_status[row][col] = "correct"

            # Show a positive message.
            self.set_status("Correct!", "correct")
        else:
            # Mark the cell as incorrect.
            self.cell_status[row][col] = "incorrect"

            # Increase the mistake counter.
            self.mistakes += 1

            # Show an error message.
            self.set_status("Incorrect number.", "incorrect")

            # Update the board and statistics.
            self.refresh_board()
            self.refresh_header()

            # Give an automatic hint after the required number of mistakes.
            if self.mistakes % MISTAKES_PER_AI_HINT == 0:
                self._give_mistake_hint()

            return

        # Refresh the board and statistics after a correct answer.
        self.refresh_board()
        self.refresh_header()

        # Check whether the puzzle has been completed.
        self._check_completion()

    def delete_number(self):
        """Clear a player-entered number. Original clues stay locked."""
        # Prevent editing when the game cannot be edited.
        if not self._can_edit():
            return

        # Start the timer.
        self._begin_timer()

        # Require a selected cell.
        if self.selected is None:
            self.set_status("Select a cell to delete.", "info")
            return

        # Get the selected cell coordinates.
        row, col = self.selected

        # Prevent deletion of original puzzle clues.
        if self.cell_status[row][col] == "given":
            self.set_status("Original numbers cannot be deleted.", "info")
            return

        # Do nothing if the cell is already empty.
        if self.current[row][col] == 0:
            return

        # Save the current state for undo.
        self._save_undo(row, col)

        # Empty the selected cell.
        self.current[row][col] = 0
        self.cell_status[row][col] = "empty"

        # Refresh the board and statistics.
        self.refresh_board()
        self.refresh_header()

        # Tell the player the number was deleted.
        self.set_status("Number deleted.", "info")

    def undo(self):
        """Undo the most recent player entry or delete."""
        # Prevent undo when the game cannot be edited.
        if not self._can_edit():
            return

        # Start the timer.
        self._begin_timer()

        # Check whether there is an action to undo.
        if not self.undo_stack:
            self.set_status("Nothing to undo.", "info")
            return

        # Get the most recent action.
        action = self.undo_stack.pop()

        # Restore the cell coordinates.
        row = action["row"]
        col = action["col"]

        # Restore the previous value and status.
        self.current[row][col] = action["prev_value"]
        self.cell_status[row][col] = action["prev_status"]

        # Select the restored cell.
        self.selected = (row, col)

        # Refresh the board and statistics.
        self.refresh_board()
        self.refresh_header()

        # Inform the player that the action was undone.
        self.set_status("Last move undone.", "info")

    def show_ai_hint(self):
        """Show candidates and one AI recommendation for the selected cell."""
        # Do nothing if the game is inactive.
        if not self.game_active:
            return

        # Start the timer.
        self._begin_timer()

        # Check whether the maximum number of hints has been reached.
        if self.hints_used >= MAX_AI_HINTS:
            self.set_status("No more AI hints remaining.", "info")
            return

        # Find a suitable cell for the hint.
        cell = self._cell_for_hint()

        # Stop if there is no empty cell available.
        if cell is None:
            self.set_status("Select an empty cell to get an AI hint.", "info")
            return

        # Get the selected cell coordinates.
        row, col = cell

        # Select the cell that will receive the hint.
        self.selected = (row, col)
        self.refresh_board()

        # Generate the AI hint using the current board and solution.
        hint = get_hint(self._board_for_hints(), row, col, self.solution)

        # Stop if no hint could be generated.
        if hint is None:
            self.set_status("Select an empty cell to get an AI hint.", "info")
            return

        # Increase the number of hints used.
        self.hints_used += 1

        # Update the header.
        self.refresh_header()

        # Pause the game while the popup is displayed.
        self.paused = True

        # Display the AI hint in a popup.
        messagebox.showinfo("AI Hint", hint["message"])

        # Resume the game after the popup is closed.
        self.paused = False

        # Display the recommended number in the status bar.
        self.set_status(
            f"AI Recommendation: {hint['recommendation']}",
            "info",
        )

    def _save_undo(self, row, col):
        # Save the current state of a cell before changing it.
        self.undo_stack.append(
            {
                "row": row,
                "col": col,
                "prev_value": self.current[row][col],
                "prev_status": self.cell_status[row][col],
            }
        )

    def _can_edit(self):
        # Return True only when the game is active and not paused.
        return self.game_active and not self.paused

    def _cell_for_hint(self):
        """Use the selected empty cell, or the first empty cell if needed."""
        # Prefer the currently selected cell.
        if self.selected is not None:
            row, col = self.selected

            # Make sure the selected cell is empty.
            if self.current[row][col] == 0:
                return (row, col)

        # If the selected cell is not suitable, find the first empty cell.
        for row in range(9):
            for col in range(9):
                if self.current[row][col] == 0:
                    return (row, col)

        # Return None if there are no empty cells.
        return None

    def _board_for_hints(self):
        """Copy the board but treat incorrect guesses as empty."""
        # Make a copy so the original game board is not changed.
        board = [row[:] for row in self.current]

        # Check every cell for incorrect guesses.
        for row in range(9):
            for col in range(9):

                # Treat incorrect numbers as empty when generating hints.
                if self.cell_status[row][col] == "incorrect":
                    board[row][col] = 0

        return board

    def _on_key(self, event):
        """Allow typing 1-9, Delete, Backspace, and arrow-key navigation."""
        # Check if the user pressed a number from 1 to 9.
        if event.char in "123456789":
            self.enter_number(int(event.char))

        # Allow Backspace and Delete to remove numbers.
        elif event.keysym in ("BackSpace", "Delete"):
            self.delete_number()

        # Allow arrow keys to move around the board.
        elif event.keysym in ("Up", "Down", "Left", "Right"):
            self._move_selection(event.keysym)

    def _move_selection(self, direction):
        # Do nothing if the game is not active.
        if not self.game_active:
            return

        # Use the current selection or start at the top-left cell.
        row, col = self.selected if self.selected is not None else (0, 0)

        # Move one cell upward.
        if direction == "Up":
            row = (row - 1) % 9

        # Move one cell downward.
        elif direction == "Down":
            row = (row + 1) % 9

        # Move one cell left.
        elif direction == "Left":
            col = (col - 1) % 9

        # Move one cell right.
        elif direction == "Right":
            col = (col + 1) % 9

        # Select the new cell.
        self.select_cell(row, col)

    # ----------------------------------------------------------
    # AI assistance after every 2 mistakes (max 3 hints)
    # ----------------------------------------------------------
    def _give_mistake_hint(self):
        """Automatically give an AI hint after 2, 4, and 6 mistakes."""
        # Stop if all available hints have already been used.
        if self.hints_used >= MAX_AI_HINTS:
            self.set_status("No more AI hints remaining.", "info")
            return

        # Show an AI hint automatically.
        self.show_ai_hint()

    # ----------------------------------------------------------
    # Timer
    # ----------------------------------------------------------
    def _begin_timer(self):
        """Start the countdown after the player's first action."""
        # Prevent the timer from starting more than once.
        if self.timer_started or not self.game_active:
            return

        # Mark the timer as started.
        self.timer_started = True

        # Start the countdown.
        self._start_timer()

    def _start_timer(self):
        # Cancel any existing timer before starting a new one.
        self._stop_timer()

        # Schedule the timer to update after one second.
        self.timer_id = self.root.after(1000, self._tick)

    def _stop_timer(self):
        # Check whether a timer is currently active.
        if self.timer_id is not None:

            # Cancel the scheduled timer.
            self.root.after_cancel(self.timer_id)

            # Clear the timer ID.
            self.timer_id = None

    def _tick(self):
        # Stop updating the timer if the game is no longer active.
        if not self.game_active:
            return

        # Only decrease the time when the game is not paused.
        if not self.paused:
            self.time_left -= 1

            # Check whether the time has reached zero.
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
        # Mark the current game as inactive.
        self.game_active = False

        # Stop the timer.
        self._stop_timer()

        # Inform the player that time has expired.
        messagebox.showinfo(
            "Time's Up!",
            "Time's Up!\n\n"
            "You could not complete the puzzle in time.\n\n"
            "A new shuffled puzzle will now start.",
        )

        # Automatically start another puzzle at the same difficulty.
        self.start_new_game(self.difficulty)

    # ----------------------------------------------------------
    # Puzzle completion
    # ----------------------------------------------------------
    def _check_completion(self):
        # Check whether the player's board is complete and correct.
        if not is_board_complete_and_correct(self.current, self.solution):
            return

        # Stop the game and timer after a successful completion.
        self.game_active = False
        self._stop_timer()

        # Calculate how much time the player used.
        time_used = self.total_time - self.time_left

        # Calculate the final score.
        score = calculate_score(
            self.difficulty,
            self.time_left,
            self.mistakes,
            self.hints_used,
            completed=True,
        )

        # Display the final score in the header.
        self.stat_score.config(text=str(score))

        # Show a success message in the status bar.
        self.set_status("Congratulations! You solved the Sudoku!", "correct")

        # Open the completion dialog.
        self._show_win_dialog(time_used, score)

    def _show_win_dialog(self, time_used, score):
        # Create a separate popup window for the completion message.
        dialog = tk.Toplevel(self.root)

        # Set the popup title.
        dialog.title("Puzzle Complete")

        # Set the popup background.
        dialog.configure(bg=COLORS["bg"])

        # Prevent resizing of the popup.
        dialog.resizable(False, False)

        # Keep the popup above the main window.
        dialog.transient(self.root)

        # Prevent interaction with the main window until the popup is closed.
        dialog.grab_set()

        # Create the main popup card.
        card = tk.Frame(dialog, bg=COLORS["surface"], padx=28, pady=24)
        card.pack(padx=8, pady=8)

        # Display the completion title.
        tk.Label(
            card,
            text="Puzzle complete",
            font=ui_font(20, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"],
        ).pack(pady=(0, 6))

        # Display the completion message.
        tk.Label(
            card,
            text="You solved the Sudoku!",
            font=ui_font(12),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
        ).pack()

        # Create the summary area.
        summary = tk.Frame(card, bg=COLORS["card"])
        summary.pack(fill="x", pady=18)

        # Display the final game statistics.
        for label, value in (
            ("Time", format_time(time_used)),
            ("Mistakes", str(self.mistakes)),
            ("Hints", str(self.hints_used)),
            ("Score", str(score)),
        ):
            # Create one row for each statistic.
            row = tk.Frame(summary, bg=COLORS["card"])
            row.pack(fill="x", padx=16, pady=6)

            # Display the statistic name.
            tk.Label(row, text=label, font=ui_font(11), bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")

            # Display the statistic value.
            tk.Label(row, text=value, font=ui_font(12, "bold"), bg=COLORS["card"], fg=COLORS["text"]).pack(side="right")

        # Create the popup button area.
        buttons = tk.Frame(card, bg=COLORS["surface"])
        buttons.pack()

        # Add the Play Again button.
        self._ui_button(
            buttons,
            "Play Again",
            COLORS["btn_hint"],
            lambda: self._close_win_dialog(dialog, play_again=True),
        ).pack(side="left", padx=6)

        # Add the Change Level button.
        self._ui_button(
            buttons,
            "Change Level",
            COLORS["btn_new"],
            lambda: self._close_win_dialog(dialog, play_again=False),
        ).pack(side="left", padx=6)

        # Update the popup size before centering it.
        dialog.update_idletasks()

        # Center the popup on the main window.
        self._center_dialog(dialog)

    def _close_win_dialog(self, dialog, play_again):
        # Close the completion popup.
        dialog.destroy()

        # Start another game if the player selected Play Again.
        if play_again:
            self.start_new_game(self.difficulty)

        # Otherwise, open the level selection dialog.
        else:
            self._show_level_picker()

    def _show_level_picker(self):
        # Create a popup for selecting a new difficulty.
        picker = tk.Toplevel(self.root)

        # Set the popup title.
        picker.title("Change Level")

        # Set the popup background.
        picker.configure(bg=COLORS["bg"])

        # Prevent resizing.
        picker.resizable(False, False)

        # Keep the popup connected to the main window.
        picker.transient(self.root)

        # Prevent interaction with the main window.
        picker.grab_set()

        # Create the popup card.
        card = tk.Frame(picker, bg=COLORS["surface"], padx=24, pady=20)
        card.pack(padx=8, pady=8)

        # Display the popup title.
        tk.Label(
            card,
            text="Choose a level",
            font=ui_font(16, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"],
        ).pack(pady=(0, 14))

        # Create the level button row.
        row = tk.Frame(card, bg=COLORS["surface"])
        row.pack()

        # Create buttons for all three difficulty levels.
        for name, color in (("Easy", "#059669"), ("Medium", "#2563EB"), ("Hard", "#E11D48")):
            self._ui_button(
                row,
                name,
                color,
                lambda d=name: self._pick_level(picker, d),
                width=10,
            ).pack(side="left", padx=6)

        # Update the popup size before centering it.
        picker.update_idletasks()

        # Center the level selection popup.
        self._center_dialog(picker)

    def _pick_level(self, picker, difficulty):
        # Close the level selection popup.
        picker.destroy()

        # Start a new game using the selected difficulty.
        self.start_new_game(difficulty)

    def _center_dialog(self, dialog):
        # Update the dialog dimensions before calculating its position.
        dialog.update_idletasks()

        # Get the dialog's width and height.
        width = dialog.winfo_width()
        height = dialog.winfo_height()

        # Calculate the horizontal center position.
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2

        # Calculate the vertical center position.
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2

        # Move the dialog to the calculated center position.
        dialog.geometry(f"+{x}+{y}")

    def _on_close(self):
        # Mark the game as inactive before closing.
        self.game_active = False

        # Stop the timer.
        self._stop_timer()

        # Close the main application window.
        self.root.destroy()
