from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

from resizable_board import ResizableBoard

from engine import Game, load_cards
from algorithms import quicksort_player_indices

ROOT = Path(__file__).resolve().parent


# The new artwork belongs to every game/dialog screen, never the menu or rulebook.
BACKGROUND_IMAGE = ROOT / "game_background.png"
PAPER_RED = "#dd2411"
PAPER_GOLD = "#ffed91"
PAPER_INK = "#281008"


def _load_game_art():
    with Image.open(BACKGROUND_IMAGE) as source:
        return source.convert("RGB")


class WallpaperFrame(tk.Frame):
    """A normal Tk frame with resizable artwork behind its child widgets."""

    def __init__(self, parent, source, *, inside=False, **options):
        super().__init__(parent, **options)
        # Interior containers use the actual central red paper, not a second
        # yellow border. The full artwork stays visible on the outer screen.
        self._wallpaper_source = (source.crop((85, 65, source.width - 95,
                                               source.height - 125)) if inside
                                  else source)
        self._wallpaper_label = None
        self._wallpaper_photo = None
        self._wallpaper_size = None
        self._wallpaper_pending = None
        self.bind("<Configure>", self._wallpaper_changed, add="+")
        self.bind("<Destroy>", self._wallpaper_destroyed, add="+")

    def winfo_children(self):
        # Decoration is implementation detail, not a screen control.
        return [child for child in super().winfo_children()
                if child is not self._wallpaper_label]

    def _wallpaper_changed(self, event):
        if event.widget is self and self._wallpaper_pending is None:
            self._wallpaper_pending = self.after_idle(self._draw_wallpaper)

    def _wallpaper_destroyed(self, event):
        if event.widget is self and self._wallpaper_pending is not None:
            self.after_cancel(self._wallpaper_pending)
            self._wallpaper_pending = None

    def _draw_wallpaper(self):
        self._wallpaper_pending = None
        if not self.winfo_exists():
            return
        size = max(1, self.winfo_width()), max(1, self.winfo_height())
        if size == self._wallpaper_size:
            return
        image = None
        parent = self.master
        if isinstance(parent, (WallpaperFrame, WallpaperCanvas)):
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = self.winfo_rootx() - parent.winfo_rootx()
            y = self.winfo_rooty() - parent.winfo_rooty()
            if (pw > 1 and ph > 1 and x >= 0 and y >= 0
                    and x + size[0] <= pw and y + size[1] <= ph):
                # Match the surrounding wallpaper instead of drawing an
                # additional yellow border inside the text area.
                parent_image = parent._wallpaper_source.resize(
                    (pw, ph), Image.Resampling.BILINEAR)
                image = parent_image.crop((x, y, x + size[0], y + size[1]))
        if image is None:
            image = self._wallpaper_source.resize(size, Image.Resampling.BILINEAR)
        self._wallpaper_photo = ImageTk.PhotoImage(image, master=self)
        if self._wallpaper_label is None:
            # Creating the decoration only after all the controls avoids
            # changing their insertion order and is compatible with the tests.
            self._wallpaper_label = tk.Label(
                self, image=self._wallpaper_photo, bd=0, highlightthickness=0)
            self._wallpaper_label.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self._wallpaper_label.configure(image=self._wallpaper_photo)
        self._wallpaper_label.lower()
        self._wallpaper_size = size


class WallpaperCanvas(tk.Canvas):
    """Scrolling content keeps the user's artwork visible behind the panels."""

    def __init__(self, parent, source, **options):
        super().__init__(parent, **options)
        self._wallpaper_source = source
        self._wallpaper_item = self.create_image(0, 0, anchor="nw")
        self._wallpaper_photo = None
        self._wallpaper_size = None
        self._wallpaper_pending = None
        self.bind("<Configure>", self._wallpaper_changed, add="+")
        self.bind("<Destroy>", self._wallpaper_destroyed, add="+")

    def _wallpaper_changed(self, event):
        if event.widget is self and self._wallpaper_pending is None:
            self._wallpaper_pending = self.after_idle(self._draw_wallpaper)

    def _wallpaper_destroyed(self, event):
        if event.widget is self and self._wallpaper_pending is not None:
            self.after_cancel(self._wallpaper_pending)
            self._wallpaper_pending = None

    def _draw_wallpaper(self):
        self._wallpaper_pending = None
        if not self.winfo_exists():
            return
        size = max(1, self.winfo_width()), max(1, self.winfo_height())
        if size == self._wallpaper_size:
            return
        image = self._wallpaper_source.resize(size, Image.Resampling.BILINEAR)
        self._wallpaper_photo = ImageTk.PhotoImage(image, master=self)
        self.itemconfigure(self._wallpaper_item, image=self._wallpaper_photo)
        self.tag_lower(self._wallpaper_item)
        self._wallpaper_size = size


class ThemedMessageBox:
    """Replace native OS dialogs, which cannot display an image background."""

    @staticmethod
    def _dialog(title, message, parent, *, confirm):
        if parent is None:
            raise ValueError("The game window is required for a themed dialog")
        source = _load_game_art()
        window = tk.Toplevel(parent)
        window.withdraw()
        window.title(title)
        window.transient(parent)
        window.resizable(False, False)
        width = min(630, max(340, parent.winfo_width() - 80))
        height = 325 if confirm else 290
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width)//2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height)//2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        backdrop = WallpaperFrame(window, source, bg=PAPER_RED)
        backdrop.pack(fill="both", expand=True)
        content = WallpaperFrame(backdrop, source, inside=True, bg=PAPER_RED)
        content.place(relx=0.5, rely=0.5, anchor="center",
                      relwidth=0.88, relheight=0.75)
        content.grid_columnconfigure(0, weight=1)
        result = [False]

        def close(answer=False):
            result[0] = answer
            window.destroy()

        tk.Label(content, text=title.upper(), font=("Arial", 19, "bold"),
                 bg=PAPER_RED, fg=PAPER_GOLD).grid(row=0, column=0, pady=(20, 14))
        tk.Label(content, text=message, font=("Arial", 15),
                 wraplength=max(270, width - 135), justify="center",
                 bg=PAPER_RED, fg=PAPER_GOLD).grid(row=1, column=0, pady=(0, 22))
        controls = tk.Frame(content, bg=PAPER_RED)
        controls.grid(row=2, column=0, pady=(2, 12))
        for label, answer in ((('NO', False), ('YES', True)) if confirm
                              else (('OK', True),)):
            tk.Button(controls, text=label, command=lambda a=answer: close(a),
                      font=("Arial", 14, "bold"), bg=PAPER_GOLD, fg=PAPER_INK,
                      activebackground="#d71920", activeforeground="#fff5bd",
                      bd=2, relief="solid", width=10, cursor="hand2").pack(
                          side="left", padx=12)
        window.protocol("WM_DELETE_WINDOW", lambda: close(False))
        window.bind("<Escape>", lambda event: close(False))
        if confirm:
            window.bind("<Return>", lambda event: close(True))
        window.deiconify()
        window.lift()
        window.grab_set()
        window.wait_window()
        return result[0]

    @staticmethod
    def askyesno(title, message, *, parent=None):
        return ThemedMessageBox._dialog(title, message, parent, confirm=True)

    @staticmethod
    def showerror(title, message, *, parent=None):
        ThemedMessageBox._dialog(title, message, parent, confirm=False)


messagebox = ThemedMessageBox()


def short(value: str, limit: int = 17) -> str:
    return value if len(value) <= limit else value[:limit - 1] + "…"


class GameApp:
    ROWS, COLS = 9, 6

    MENU_OPTIONS = ("MAIN MODE", "CLASSIC BATTLE", "BATTLE MODE", "RULEBOOK", "EXIT")

    def __init__(self):
        self.board = ResizableBoard(self.ROWS, self.COLS)
        self.board.title = "The Character Challenge"
        self.board.cell_size = (157, 68)
        self.board.margin = 9
        self.board.cell_spacing = 3
        self.board.cell_color = "#ffffff"
        self.board.margin_color = "#ffffff"
        self.board.grid_color = "#ffffff"
        self.board.resize_callback = self._window_resized
        self.board.on_mouse_click = self._mouse
        self.board.on_key_press = self._key
        self.board.on_start = self._started

        self.actions: dict[tuple[int, int], object] = {}
        self.game: Game | None = None
        self.screen = "menu"
        self._overlay: tk.Frame | None = None

        self._transition_old_overlay: tk.Frame | None = None
        self._menu_buttons: list[tk.Button] = []
        self._game_background_source = _load_game_art()
        self._menu_background_label: tk.Label | None = None
        self._menu_background_source: Image.Image | None = None
        self._menu_background_photo: ImageTk.PhotoImage | None = None
        self._menu_background_size: tuple[int, int] | None = None
        self._goal_label: tk.Label | None = None
        self._character_canvas: tk.Canvas | None = None
        self._character_inner: tk.Frame | None = None
        self._character_scrollbar: tk.Scrollbar | None = None
        self._character_window: int | None = None
        self._character_buttons: list[tk.Button] = []
        self._character_wheel_binds: dict[str, str] = {}
        self._character_refresh_id: str | None = None
        self._attribute_canvas: tk.Canvas | None = None
        self._attribute_scrollbar: tk.Scrollbar | None = None
        self._attribute_inner: tk.Frame | None = None
        self._attribute_window: int | None = None
        self._attribute_refresh_id: str | None = None
        self._attribute_cards_frame: tk.Frame | None = None
        self._attribute_card_buttons: list[tk.Button] = []
        self._attribute_recipient_labels: list[tk.Label] = []
        self._attribute_player_buttons: dict[int, tk.Button] = {}
        self._attribute_targets_frame: tk.Frame | None = None
        self._attribute_notice: tk.Label | None = None
        self._attribute_scroll_position = 0.0
        self._attribute_columns = 4

        self._presentation_canvas: tk.Canvas | None = None
        self._presentation_scrollbar: tk.Scrollbar | None = None
        self._presentation_inner: tk.Frame | None = None
        self._presentation_window: int | None = None
        self._presentation_cards_frame: tk.Frame | None = None
        self._presentation_player_frames: list[tk.Frame] = []
        self._presentation_text_labels: list[tk.Label] = []
        self._presentation_character_labels: list[tk.Label] = []
        self._presentation_refresh_id: str | None = None
        self._presentation_columns = 0


        self.last_winner_character: str | None = None
        self.last_winner_attributes: list[str] = []
        self._result_canvas: tk.Canvas | None = None
        self._result_inner: tk.Frame | None = None
        self._result_window: int | None = None
        self._result_scrollbar: tk.Scrollbar | None = None
        self._result_character_label: tk.Label | None = None
        self._result_attribute_labels: list[tk.Label] = []
        self._result_refresh_id: str | None = None

        self._end_canvas: tk.Canvas | None = None
        self._end_scrollbar: tk.Scrollbar | None = None
        self._end_inner: tk.Frame | None = None
        self._end_window: int | None = None
        self._end_name_labels: list[tk.Label] = []
        self._end_refresh_id: str | None = None
        self._rulebook_image_label: tk.Label | None = None
        self._rulebook_image_source: Image.Image | None = None
        self._rulebook_image_photo: ImageTk.PhotoImage | None = None
        self._rulebook_resize_id: str | None = None
        self._rulebook_rendered_size: tuple[int, int] | None = None
        self._setup_mode: str | None = None
        self._player_count: tk.IntVar | None = None
        self._name_vars: list[tk.StringVar] = []
        self._name_rows: list[tk.Frame] = []
        self._count_buttons: dict[int, tk.Button] = {}
        self._setup_error: tk.Label | None = None
        self.actor_pos = 0
        self.selected_attribute: int | None = None
        self.proposed_recipients: list[int | None] = [None] * 4
        self.last_winner: int | None = None
        self.render()

    def run(self) -> None:
        self.board.show()

    def _started(self) -> None:
        self.board.maximize_window()

    def _key(self, key: str) -> None:
        key = str(key).lower()
        if key == "f11":
            self.board.toggle_fullscreen()
        elif key == "escape":
            if self.board.fullscreen:
                self.board.toggle_fullscreen()
            elif self.screen == "rulebook":
                self._back_to_opening_menu()
            elif self.screen == "rulebook_classical":
                self._show_rulebook_page("rulebook")
            elif self.screen == "rulebook_battle":
                self._show_rulebook_page("rulebook_classical")
            elif self.screen == "exit_confirm":
                self._cancel_exit()
            elif self.game is not None or self.screen == "setup":
                self._to_menu()

    def _mouse(self, button, row: int, col: int) -> None:
        if row < 0 or col < 0:
            return
        action = self.actions.get((row, col))
        if action is not None:
            try:
                action()
            except (ValueError, RuntimeError) as exc:
                messagebox.showerror("Game rule", str(exc), parent=self.board._root)

    def _put(self, row: int, col: int, title: str, action=None) -> None:
        self.board[row][col] = title
        if action is not None:
            self.actions[(row, col)] = action

    def _base(self, title: str) -> None:
        self.actions.clear()
        self.board.clear()
        self._put(0, 0, "CARD CHALLENGE")
        self._put(0, 2, title)
        if self.game is not None:
            self._put(0, 1, "MAIN" if self.game.mode == "main" else "BATTLE")
            self._put(0, 3, f"ROUND {self.game.rounds_completed + 1}/{self.game.total_rounds}"
                      if not self.game.game_over else "GAME OVER")

        if self.game is not None:
            self._put(0, 5, "MAIN MENU", self._to_menu)

    def _to_menu(self) -> None:
        if self.game and not self.game.game_over:
            if not messagebox.askyesno("End game?", "Leave the current game and lose its progress?",
                                      parent=self.board._root):
                return
        self.game = None
        self.screen = "menu"
        self.render()

    def _quit(self) -> None:
        self.screen = "exit_confirm"
        self.render()

    def _cancel_exit(self) -> None:
        self.screen = "menu"
        self.render()

    def _confirm_exit(self) -> None:
        self.board.close()

    def _back_to_opening_menu(self) -> None:
        self.screen = "menu"
        self.render()


    def _clear_overlay(self, *, destroy: bool = True) -> None:
        if self._rulebook_resize_id is not None:
            self.board._root.after_cancel(self._rulebook_resize_id)
            self._rulebook_resize_id = None
        self._rulebook_image_label = None
        self._rulebook_image_source = None
        self._rulebook_image_photo = None
        self._rulebook_rendered_size = None
        if self._attribute_canvas is not None and self._attribute_canvas.winfo_exists():
            self._attribute_scroll_position = self._attribute_canvas.yview()[0]
        if self._attribute_refresh_id is not None:
            self.board._root.after_cancel(self._attribute_refresh_id)
            self._attribute_refresh_id = None
        if self._character_refresh_id is not None:
            self.board._root.after_cancel(self._character_refresh_id)
            self._character_refresh_id = None
        if self._presentation_refresh_id is not None:
            self.board._root.after_cancel(self._presentation_refresh_id)
            self._presentation_refresh_id = None
        if self._result_refresh_id is not None:
            self.board._root.after_cancel(self._result_refresh_id)
            self._result_refresh_id = None
        if self._end_refresh_id is not None:
            self.board._root.after_cancel(self._end_refresh_id)
            self._end_refresh_id = None


        for event_name, binding in self._character_wheel_binds.items():
            self.board._root.unbind(event_name, binding)
        self._character_wheel_binds.clear()
        if self._overlay is not None:
            if destroy:
                self._overlay.destroy()
            self._overlay = None
        self._menu_buttons = []
        self._menu_background_label = None
        self._menu_background_source = None
        self._menu_background_photo = None
        self._menu_background_size = None
        self._goal_label = None
        self._character_canvas = None
        self._character_inner = None
        self._character_scrollbar = None
        self._character_window = None
        self._character_buttons = []
        self._attribute_canvas = None
        self._attribute_scrollbar = None
        self._attribute_inner = None
        self._attribute_window = None
        self._attribute_cards_frame = None
        self._attribute_card_buttons = []
        self._attribute_recipient_labels = []
        self._attribute_player_buttons = {}
        self._attribute_targets_frame = None
        self._attribute_notice = None
        self._presentation_canvas = None
        self._presentation_scrollbar = None
        self._presentation_inner = None
        self._presentation_window = None
        self._presentation_cards_frame = None
        self._presentation_player_frames = []
        self._presentation_text_labels = []
        self._presentation_character_labels = []
        self._presentation_columns = 0
        self._result_canvas = None
        self._result_inner = None
        self._result_window = None
        self._result_scrollbar = None
        self._result_character_label = None
        self._result_attribute_labels = []
        self._end_canvas = None
        self._end_scrollbar = None
        self._end_inner = None
        self._end_window = None
        self._end_name_labels = []

    def _wallpaper_panel(self, parent) -> tk.Frame:
        return WallpaperFrame(parent, self._game_background_source,
                              inside=True, bg=PAPER_RED, bd=0, highlightthickness=0)

    def _wallpaper_canvas(self, parent) -> tk.Canvas:
        return WallpaperCanvas(parent, self._game_background_source,
                               bg=PAPER_RED, bd=0, highlightthickness=0)

    @staticmethod
    def _align_wallpaper(content) -> None:
        # Scrollable content is positioned after layout; refresh its image
        # crop so it aligns with the surrounding full-window background.
        if isinstance(content, WallpaperFrame) and content.winfo_exists():
            content._wallpaper_size = None
            content._draw_wallpaper()

    def _new_overlay(self, *, full_window: bool = False) -> tk.Frame:
        # The menu and three illustrated rulebook pages are intentionally kept
        # as-is. Every other screen receives the complete red/yellow artwork.
        untouched = self.screen in (
            "menu", "rulebook", "rulebook_classical", "rulebook_battle")
        if untouched:
            frame = tk.Frame(self.board._canvas, bg="white", bd=0,
                             highlightthickness=0)
            if full_window:
                frame.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                frame.place(relx=0.5, rely=0.5, anchor="center")
        else:
            frame = WallpaperFrame(self.board._canvas, self._game_background_source,
                                   bg=PAPER_RED, bd=0, highlightthickness=0)
            frame.place(x=0, y=0, relwidth=1, relheight=1)
        if (self._transition_old_overlay is not None
                and self._transition_old_overlay.winfo_exists()):
            frame.lower(self._transition_old_overlay)
        self._overlay = frame
        if not untouched and not full_window:
            panel = self._wallpaper_panel(frame)
            panel.place(relx=0.5, rely=0.5, anchor="center")
            return panel
        return frame

    @staticmethod
    def _button(parent, text: str, action, *, width: int = 22) -> tk.Button:
        return tk.Button(
            parent, text=text, command=action, width=width,
            font=("Arial", 16), bg=PAPER_GOLD, fg=PAPER_INK,
            activebackground="#d71920", activeforeground="#fff5bd",
            relief="solid", bd=1, highlightthickness=0,
            padx=12, pady=10, cursor="hand2",
        )

    def _render_menu_overlay(self) -> None:
        frame = self._new_overlay(full_window=True)
        frame.configure(bg="#170a06")
        self._menu_background_source = Image.open(ROOT / "main_menu_background.jpg").convert("RGB")
        self._menu_background_label = tk.Label(frame, bg="#170a06", bd=0,
                                               highlightthickness=0)
        handlers = (
            lambda: self._start_game("main"),
            lambda: self._start_game("battle"),
            lambda: None,
            self._rulebook,
            self._quit,
        )
        for label, handler in zip(self.MENU_OPTIONS, handlers):
            button = self._button(frame, label, handler)
            button.configure(bg="#ffed83", fg="#190d08", font=("Arial", 14, "bold"),
                             activebackground="#d71920", activeforeground="#fff5bd",
                             bd=2, padx=3, pady=0)
            button.bind("<Enter>", lambda _event, b=button: b.configure(
                bg="#d71920", fg="#fff5bd"))
            button.bind("<Leave>", lambda _event, b=button: b.configure(
                bg="#ffed83", fg="#190d08"))
            self._menu_buttons.append(button)
        self._layout_menu_screen(self.board._canvas.winfo_width(),
                                 self.board._canvas.winfo_height())

    def _layout_menu_screen(self, width: int, height: int) -> None:
        if self._menu_background_label is None or self._menu_background_source is None:
            return
        width, height = max(1, int(width)), max(1, int(height))
        source_width, source_height = self._menu_background_source.size
        scale = min(width / source_width, height / source_height)
        image_width = max(1, round(source_width * scale))
        image_height = max(1, round(source_height * scale))
        left = (width - image_width) // 2
        top = (height - image_height) // 2
        if self._menu_background_size != (image_width, image_height):
            resized = self._menu_background_source.resize(
                (image_width, image_height), Image.Resampling.LANCZOS)
            self._menu_background_photo = ImageTk.PhotoImage(resized, master=self.board._root)
            self._menu_background_label.configure(image=self._menu_background_photo)
            self._menu_background_size = (image_width, image_height)
        self._menu_background_label.place(x=left, y=top,
                                          width=image_width, height=image_height)
        available_height = image_height * 0.345
        gap = max(3, round(image_height * 0.01))
        button_height = min(50, max(20, int((available_height - 4 * gap) / 5)))
        button_width = min(370, max(145, round(image_width * 0.265)))
        font_size = max(10, min(17, round(button_height * 0.37)))
        first_y = top + round(image_height * 0.54)
        center_x = left + round(image_width * 0.525)
        for i, button in enumerate(self._menu_buttons):
            button.configure(font=("Arial", font_size, "bold"))
            button.place(x=center_x, y=first_y + i * (button_height + gap),
                         anchor="n", width=button_width, height=button_height)


    def _render_handoff_overlay(self) -> None:
        assert self.game is not None
        game = self.game
        player_id = self._actor()
        page = self._new_overlay(full_window=True)
        content = self._wallpaper_panel(page)
        content.place(relx=0.5, rely=0.5, anchor="center",
                      relwidth=0.94, relheight=0.95)
        content.grid_columnconfigure(0, weight=1)
        for row in range(6):
            content.grid_rowconfigure(row, weight=1, uniform="handoff")

        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=5)

        line_style = {"bg": PAPER_RED, "fg": PAPER_GOLD,
                      "font": ("Arial", 19), "justify": "center"}
        tk.Label(content,
                 text=f"ROUND {game.rounds_completed + 1}/{game.total_rounds}",
                 **line_style).grid(row=1, column=0, pady=5)
        tk.Label(content, text=f"JUDGE: {game.players[game.judge].name}",
                 **line_style).grid(row=2, column=0, pady=5)

        self._goal_label = tk.Label(
            content, text=f"GOAL: {game.goal or ''}",
            bg=PAPER_RED, fg=PAPER_GOLD, font=("Arial", 19),
            justify="center", wraplength=800,
        )
        self._goal_label.grid(row=3, column=0, pady=4, sticky="ew")
        tk.Label(content, text=f"PASS TO: {game.players[player_id].name}",
                 **line_style).grid(row=4, column=0, pady=5)
        self._button(content, "REVEAL HAND", self._reveal_hand, width=18).grid(
            row=5, column=0, pady=5)
        self._window_resized(self.board._canvas.winfo_width(),
                             self.board._canvas.winfo_height())

    def _render_character_overlay(self) -> None:
        assert self.game is not None
        game = self.game
        pid = self._actor()
        page = self._new_overlay(full_window=True)
        viewport = self._wallpaper_canvas(page)
        scrollbar = tk.Scrollbar(page, orient="vertical", command=viewport.yview)
        viewport.configure(yscrollcommand=scrollbar.set)
        viewport.pack(side="left", fill="both", expand=True)

        content = self._wallpaper_panel(viewport)
        window_item = viewport.create_window(0, 0, anchor="n", window=content)
        content.grid_columnconfigure(0, weight=1)


        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(18, 32))
        label_style = {"bg": PAPER_RED, "fg": PAPER_GOLD,
                       "font": ("Arial", 19), "justify": "center"}
        tk.Label(content,
                 text=f"ROUND {game.rounds_completed + 1}/{game.total_rounds}",
                 **label_style).grid(row=1, column=0, pady=(0, 27))
        tk.Label(content, text=f"PLAYER: {game.players[pid].name}",
                 **label_style).grid(row=2, column=0, pady=(0, 27))
        self._goal_label = tk.Label(
            content, text=f"GOAL: {game.goal or ''}", wraplength=750,
            **label_style)
        self._goal_label.grid(row=3, column=0, padx=12, pady=(0, 27), sticky="ew")
        tk.Label(content, text="Keep 1 of 2", **label_style).grid(
            row=4, column=0, pady=(0, 32))

        cards = tk.Frame(content, bg=PAPER_RED)
        cards.grid(row=5, column=0, padx=8, pady=(0, 25), sticky="ew")
        for col in range(2):
            cards.grid_columnconfigure(col, weight=1, uniform="character_cards")
        self._character_buttons = []
        for n, card in enumerate(game.hands[pid].characters):
            button = tk.Button(
                cards, text=f"{n + 1}. {card}",
                command=lambda number=n: self._choose_character(number),
                font=("Arial", 17), bg=PAPER_GOLD, fg=PAPER_INK,
                activebackground="#ffe09a", activeforeground=PAPER_INK,
                relief="solid", bd=1, highlightthickness=0,
                padx=22, pady=26, cursor="hand2", justify="center",
                anchor="center", wraplength=530,
            )
            button.grid(row=0, column=n, padx=15, sticky="nsew")
            self._character_buttons.append(button)

        self._character_canvas = viewport
        self._character_inner = content
        self._character_scrollbar = scrollbar
        self._character_window = window_item

        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._character_wheel_binds[event_name] = self.board._root.bind(
                event_name, self._scroll_characters, add="+")
        viewport.bind("<Configure>", lambda event:
                      self._layout_character_screen(event.width, event.height), add="+")
        viewport.bind("<Destroy>", self._character_canvas_destroyed)
        self._layout_character_screen(self.board._canvas.winfo_width(),
                                      self.board._canvas.winfo_height())

    def _character_canvas_destroyed(self, event) -> None:
        if event.widget is self._character_canvas and self._character_refresh_id is not None:
            self.board._root.after_cancel(self._character_refresh_id)
            self._character_refresh_id = None

    def _scroll_characters(self, event) -> None:
        if self.screen != "choose_character" or self._character_canvas is None:
            return
        if getattr(event, "num", None) == 4:
            amount = -3
        elif getattr(event, "num", None) == 5:
            amount = 3
        else:
            delta = getattr(event, "delta", 0)
            amount = (-3 if delta > 0 else 3) if delta else 0
        if amount:
            self._character_canvas.yview_scroll(amount, "units")

    def _layout_character_screen(self, width: int, height: int) -> None:
        if (self._character_canvas is None or self._character_inner is None
                or self._character_window is None):
            return
        width, height = max(1, width), max(1, height)


        content_width = max(560, round(width * 0.91))
        self._character_canvas.itemconfigure(self._character_window,
                                              width=content_width)
        wrap = max(180, round(content_width * 0.43) - 65)
        size = max(14, min(19, round(min(width / 82, height / 47))))
        for button in self._character_buttons:
            button.configure(wraplength=wrap, font=("Arial", size))
        if self._goal_label is not None:
            self._goal_label.configure(wraplength=max(230, round(width * 0.8)),
                                        font=("Arial", max(14, size + 1)))
        if self._character_refresh_id is not None:
            self.board._root.after_cancel(self._character_refresh_id)
        self._character_refresh_id = self.board._root.after_idle(
            self._refresh_character_scrollregion)

    def _refresh_character_scrollregion(self) -> None:
        self._character_refresh_id = None
        canvas = self._character_canvas
        inner = self._character_inner
        if canvas is None or inner is None or not canvas.winfo_exists():
            return
        canvas.update_idletasks()
        height = max(1, canvas.winfo_height())
        width = max(1, canvas.winfo_width())
        required = inner.winfo_reqheight()


        top = max(12, (height - required) // 2)
        canvas.coords(self._character_window, width / 2, top)
        self._align_wallpaper(inner)
        canvas.configure(scrollregion=(0, 0, width,
                                       max(height, required + top + 14)))
        scrollbar = self._character_scrollbar
        if scrollbar is not None:
            if required + 26 > height:
                if not scrollbar.winfo_manager():
                    scrollbar.pack(side="right", fill="y")
            elif scrollbar.winfo_manager():
                scrollbar.pack_forget()
                canvas.yview_moveto(0)

    def _render_presentation_overlay(self) -> None:
        assert self.game is not None
        game = self.game
        page = self._new_overlay(full_window=True)
        viewport = self._wallpaper_canvas(page)
        scrollbar = tk.Scrollbar(page, orient="vertical", command=viewport.yview)
        viewport.configure(yscrollcommand=scrollbar.set)
        viewport.pack(side="left", fill="both", expand=True)

        content = self._wallpaper_panel(viewport)
        canvas_window = viewport.create_window(0, 0, anchor="n", window=content)
        content.grid_columnconfigure(0, weight=1)
        heading_style = {"bg": PAPER_RED, "fg": PAPER_GOLD,
                         "font": ("Arial", 19), "justify": "center"}

        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(14, 22))
        tk.Label(content,
                 text=f"ROUND {game.rounds_completed + 1}/{game.total_rounds}",
                 **heading_style).grid(row=1, column=0, pady=(0, 20))
        tk.Label(content, text=f"JUDGE: {game.players[game.judge].name}",
                 **heading_style).grid(row=2, column=0, pady=(0, 20))
        self._goal_label = tk.Label(
            content, text=f"GOAL: {game.goal or ''}", wraplength=1060,
            **heading_style)
        self._goal_label.grid(row=3, column=0, padx=16, pady=(0, 25), sticky="ew")


        player_area = tk.Frame(content, bg=PAPER_RED)
        player_area.grid(row=4, column=0, padx=8, pady=(0, 24), sticky="ew")
        self._presentation_cards_frame = player_area
        self._presentation_player_frames = []
        self._presentation_text_labels = []
        self._presentation_character_labels = []
        for pid in game.competitors:
            frame = tk.Frame(player_area, bg=PAPER_RED, bd=1,
                             relief="solid", highlightthickness=0)
            self._presentation_player_frames.append(frame)
            name = tk.Label(frame, text=game.players[pid].name,
                            bg=PAPER_RED, fg=PAPER_GOLD, font=("Arial", 18, "bold"),
                            justify="center", anchor="center")
            name.pack(fill="x", padx=16, pady=(16, 12))
            char_text = game.hands[pid].chosen_character or "?"
            char = tk.Label(frame, text=char_text, bg=PAPER_RED, fg=PAPER_GOLD,
                            font=("Arial", 17), wraplength=360, justify="center",
                            anchor="center")
            char.pack(fill="x", padx=14, pady=(0, 17))
            self._presentation_text_labels.append(char)
            self._presentation_character_labels.append(char)
            attrs = game.final_attributes.get(pid, [])
            for attribute in attrs:
                label = tk.Label(frame, text=attribute, bg=PAPER_RED, fg=PAPER_GOLD,
                                 font=("Arial", 15), wraplength=360,
                                 justify="center", anchor="center")
                label.pack(fill="x", padx=14, pady=(0, 13))
                self._presentation_text_labels.append(label)
            if self.screen == "judge":
                self._button(
                    frame, f"PICK {game.players[pid].name}",
                    lambda player=pid: self._award(player), width=15,
                ).pack(side="bottom", padx=15, pady=(8, 16), fill="x")
            else:
                tk.Frame(frame, height=9, bg=PAPER_RED).pack()

        if self.screen == "arguments":
            self._button(content, "JUDGE NOW", self._to_judge, width=18).grid(
                row=5, column=0, pady=(2, 17))

        self._presentation_canvas = viewport
        self._presentation_scrollbar = scrollbar
        self._presentation_inner = content
        self._presentation_window = canvas_window
        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._character_wheel_binds[event_name] = self.board._root.bind(
                event_name, self._scroll_presentation, add="+")
        viewport.bind("<Configure>", lambda event:
                      self._layout_presentation_screen(event.width, event.height), add="+")
        viewport.bind("<Destroy>", self._presentation_canvas_destroyed)
        self._layout_presentation_screen(self.board._canvas.winfo_width(),
                                         self.board._canvas.winfo_height())

    def _presentation_canvas_destroyed(self, event) -> None:
        if (event.widget is self._presentation_canvas
                and self._presentation_refresh_id is not None):
            self.board._root.after_cancel(self._presentation_refresh_id)
            self._presentation_refresh_id = None

    def _scroll_presentation(self, event) -> None:
        if self.screen not in ("arguments", "judge") or self._presentation_canvas is None:
            return
        if getattr(event, "num", None) == 4:
            amount = -3
        elif getattr(event, "num", None) == 5:
            amount = 3
        else:
            delta = getattr(event, "delta", 0)
            amount = (-3 if delta > 0 else 3) if delta else 0
        if amount:
            self._presentation_canvas.yview_scroll(amount, "units")

    def _layout_presentation_screen(self, width: int, height: int) -> None:
        if (self._presentation_canvas is None
                or self._presentation_inner is None
                or self._presentation_window is None
                or self._presentation_cards_frame is None):
            return
        width, height = max(1, width), max(1, height)
        panel_width = max(280, int(width * 0.94))
        viewport = self._presentation_canvas
        viewport.itemconfigure(self._presentation_window, width=panel_width)

        count = len(self._presentation_player_frames)
        columns = (count if width >= 1300
                   else min(2, count) if width >= 860 else 1)
        cards = self._presentation_cards_frame
        if columns != self._presentation_columns:
            for frame in self._presentation_player_frames:
                frame.grid_forget()
            for col in range(max(count, 1)):
                cards.grid_columnconfigure(
                    col, weight=1 if col < columns else 0,
                    uniform="presentation" if col < columns else "")
            for index, frame in enumerate(self._presentation_player_frames):
                row, col = divmod(index, columns)
                frame.grid(row=row, column=col, padx=9, pady=9, sticky="nsew")
            self._presentation_columns = columns

        wrap = max(170, int((panel_width - 18 * columns - 18) / columns) - 40)
        size = max(13, min(18, round(min(width / 95, height / 54))))
        for label in self._presentation_text_labels:
            is_character = label in self._presentation_character_labels
            label.configure(wraplength=wrap,
                            font=("Arial", min(19, size + 1) if is_character else size))
        if self._goal_label is not None:
            self._goal_label.configure(
                wraplength=max(240, int(width * 0.85)),
                font=("Arial", max(14, min(21, size + 2))))
        if self._presentation_refresh_id is not None:
            self.board._root.after_cancel(self._presentation_refresh_id)
        self._presentation_refresh_id = self.board._root.after_idle(
            self._refresh_presentation_scrollregion)

    def _refresh_presentation_scrollregion(self) -> None:
        self._presentation_refresh_id = None
        viewport = self._presentation_canvas
        content = self._presentation_inner
        if viewport is None or content is None or not viewport.winfo_exists():
            return
        viewport.update_idletasks()
        width, height = max(1, viewport.winfo_width()), max(1, viewport.winfo_height())
        required = content.winfo_reqheight()
        top = max(12, (height - required) // 2)
        viewport.coords(self._presentation_window, width / 2, top)
        self._align_wallpaper(content)
        viewport.configure(scrollregion=(0, 0, width, max(height, top + required + 16)))
        scrollbar = self._presentation_scrollbar
        if scrollbar is not None:
            if top + required + 16 > height:
                if not scrollbar.winfo_manager():
                    scrollbar.pack(side="right", fill="y")
            elif scrollbar.winfo_manager():
                scrollbar.pack_forget()
                viewport.yview_moveto(0)

    def _render_round_result_overlay(self) -> None:
        assert self.game is not None and self.last_winner is not None
        game = self.game
        winner = game.players[self.last_winner]
        page = self._new_overlay(full_window=True)
        viewport = self._wallpaper_canvas(page)
        scrollbar = tk.Scrollbar(page, orient="vertical", command=viewport.yview)
        viewport.configure(yscrollcommand=scrollbar.set)
        viewport.pack(side="left", fill="both", expand=True)
        content = self._wallpaper_panel(viewport)
        canvas_window = viewport.create_window(0, 0, anchor="n", window=content)
        content.grid_columnconfigure(0, weight=1)
        heading_style = {"bg": PAPER_RED, "fg": PAPER_GOLD, "justify": "center"}

        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(16, 32))
        tk.Label(content, text="ROUND WINNER", font=("Arial", 25, "bold"),
                 **heading_style).grid(row=1, column=0, pady=(0, 26))
        tk.Label(content, text=f"PLAYER: {winner.name}", font=("Arial", 21),
                 wraplength=800, **heading_style).grid(
                     row=2, column=0, padx=14, pady=(0, 28), sticky="ew")
        self._result_character_label = tk.Label(
            content, text=self.last_winner_character or "",
            font=("Arial", 20, "bold"), wraplength=900, **heading_style)
        self._result_character_label.grid(
            row=3, column=0, padx=18, pady=(0, 14), sticky="ew")
        self._result_attribute_labels = []
        for i, attribute in enumerate(self.last_winner_attributes):
            label = tk.Label(content, text=attribute, font=("Arial", 16),
                             wraplength=900, **heading_style)
            label.grid(row=4+i, column=0, padx=20, pady=(0, 13), sticky="ew")
            self._result_attribute_labels.append(label)
        next_row = 4 + len(self.last_winner_attributes)
        self._button(content, "FINAL RESULTS" if game.game_over else "NEXT ROUND",
                     self._advance_round, width=18).grid(
                         row=next_row, column=0, pady=(20, 20))

        self._result_canvas = viewport
        self._result_scrollbar = scrollbar
        self._result_inner = content
        self._result_window = canvas_window
        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._character_wheel_binds[event_name] = self.board._root.bind(
                event_name, self._scroll_round_result, add="+")
        viewport.bind("<Configure>", lambda event:
                      self._layout_round_result_screen(event.width, event.height), add="+")
        viewport.bind("<Destroy>", self._result_canvas_destroyed)
        self._layout_round_result_screen(self.board._canvas.winfo_width(),
                                         self.board._canvas.winfo_height())

    def _result_canvas_destroyed(self, event) -> None:
        if (event.widget is self._result_canvas
                and self._result_refresh_id is not None):
            self.board._root.after_cancel(self._result_refresh_id)
            self._result_refresh_id = None

    def _scroll_round_result(self, event) -> None:
        if self.screen != "round_result" or self._result_canvas is None:
            return
        if getattr(event, "num", None) == 4:
            amount = -3
        elif getattr(event, "num", None) == 5:
            amount = 3
        else:
            delta = getattr(event, "delta", 0)
            amount = (-3 if delta > 0 else 3) if delta else 0
        if amount:
            self._result_canvas.yview_scroll(amount, "units")

    def _layout_round_result_screen(self, width: int, height: int) -> None:
        if (self._result_canvas is None or self._result_inner is None
                or self._result_window is None):
            return
        width, height = max(1, width), max(1, height)
        content_width = max(300, int(width * 0.88))
        self._result_canvas.itemconfigure(self._result_window, width=content_width)
        wrap = max(230, content_width - 90)
        text_size = max(14, min(20, round(min(width / 78, height / 42))))
        if self._result_character_label is not None:
            self._result_character_label.configure(
                wraplength=wrap, font=("Arial", text_size, "bold"))
        for label in self._result_attribute_labels:
            label.configure(wraplength=wrap, font=("Arial", max(13, text_size-3)))
        if self._result_refresh_id is not None:
            self.board._root.after_cancel(self._result_refresh_id)
        self._result_refresh_id = self.board._root.after_idle(
            self._refresh_round_result_scrollregion)

    def _refresh_round_result_scrollregion(self) -> None:
        self._result_refresh_id = None
        viewport = self._result_canvas
        content = self._result_inner
        if viewport is None or content is None or not viewport.winfo_exists():
            return
        viewport.update_idletasks()
        width, height = max(1, viewport.winfo_width()), max(1, viewport.winfo_height())
        needed = content.winfo_reqheight()
        top = max(12, (height - needed)//2)
        viewport.coords(self._result_window, width//2, top)
        self._align_wallpaper(content)
        viewport.configure(scrollregion=(0, 0, width, max(height, top+needed+16)))
        bar = self._result_scrollbar
        if bar is not None:
            if needed + 28 > height:
                if not bar.winfo_manager():
                    bar.pack(side="right", fill="y")
            elif bar.winfo_manager():
                bar.pack_forget()
                viewport.yview_moveto(0)

    def _render_end_overlay(self) -> None:
        assert self.game is not None
        game = self.game
        winners = game.final_winners()

        ranked = quicksort_player_indices(game.players)

        page = self._new_overlay(full_window=True)
        viewport = self._wallpaper_canvas(page)
        scrollbar = tk.Scrollbar(page, orient="vertical", command=viewport.yview)
        viewport.configure(yscrollcommand=scrollbar.set)
        viewport.pack(side="left", fill="both", expand=True)
        content = self._wallpaper_panel(viewport)
        canvas_window = viewport.create_window(0, 0, anchor="n", window=content)
        content.grid_columnconfigure(0, weight=1)
        style = {"bg": PAPER_RED, "fg": PAPER_GOLD, "justify": "center"}

        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(18, 35))
        tk.Label(content, text="WINNER" if len(winners) == 1 else "WINNERS",
                 font=("Arial", 26, "bold"), **style).grid(
                     row=1, column=0, pady=(0, 14))
        winner_label = tk.Label(
            content, text="\n".join(game.players[pid].name for pid in winners),
            font=("Arial", 24, "bold"), wraplength=800, **style)
        winner_label.grid(row=2, column=0, padx=16, pady=(0, 32), sticky="ew")
        self._end_name_labels = [winner_label]


        for row, pid in enumerate(ranked, start=3):
            player = game.players[pid]
            line = tk.Frame(content, bg=PAPER_RED)
            line.grid(row=row, column=0, padx=12, pady=(7, 7))
            name = tk.Label(line, text=player.name, font=("Arial", 18, "bold"),
                            **style)
            name.pack(side="left")
            tk.Label(line, text=f" — {player.score} pts", font=("Arial", 18),
                     **style).pack(side="left")
            self._end_name_labels.append(name)

        self._end_canvas = viewport
        self._end_scrollbar = scrollbar
        self._end_inner = content
        self._end_window = canvas_window
        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._character_wheel_binds[event_name] = self.board._root.bind(
                event_name, self._scroll_end, add="+")
        viewport.bind("<Configure>", lambda event:
                      self._layout_end_screen(event.width, event.height), add="+")
        viewport.bind("<Destroy>", self._end_canvas_destroyed)
        self._layout_end_screen(self.board._canvas.winfo_width(),
                                self.board._canvas.winfo_height())

    def _end_canvas_destroyed(self, event) -> None:
        if (event.widget is self._end_canvas
                and self._end_refresh_id is not None):
            self.board._root.after_cancel(self._end_refresh_id)
            self._end_refresh_id = None

    def _scroll_end(self, event) -> None:
        if self.screen != "end" or self._end_canvas is None:
            return
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            units = (-3 if delta > 0 else 3) if delta else 0
        if units:
            self._end_canvas.yview_scroll(units, "units")

    def _layout_end_screen(self, width: int, height: int) -> None:
        if self._end_canvas is None or self._end_window is None:
            return
        content_width = max(280, int(max(1, width) * 0.9))
        self._end_canvas.itemconfigure(self._end_window, width=content_width)
        for name in self._end_name_labels:
            name.configure(wraplength=max(170, content_width - 190))
        if self._end_refresh_id is not None:
            self.board._root.after_cancel(self._end_refresh_id)
        self._end_refresh_id = self.board._root.after_idle(
            self._refresh_end_scrollregion)

    def _refresh_end_scrollregion(self) -> None:
        self._end_refresh_id = None
        viewport, content = self._end_canvas, self._end_inner
        if viewport is None or content is None or not viewport.winfo_exists():
            return
        viewport.update_idletasks()
        width = max(1, viewport.winfo_width())
        height = max(1, viewport.winfo_height())
        needed = content.winfo_reqheight()
        top = max(12, (height - needed) // 2)
        viewport.coords(self._end_window, width // 2, top)
        self._align_wallpaper(content)
        viewport.configure(scrollregion=(0, 0, width, max(height, top + needed + 16)))
        bar = self._end_scrollbar
        if bar is not None:
            if needed + 28 > height:
                if not bar.winfo_manager():
                    bar.pack(side="right", fill="y")
            elif bar.winfo_manager():
                bar.pack_forget()
                viewport.yview_moveto(0)

    def _render_attribute_overlay(self) -> None:
        assert self.game is not None
        game = self.game
        source = self._actor()
        page = self._new_overlay(full_window=True)
        viewport = self._wallpaper_canvas(page)
        scrollbar = tk.Scrollbar(page, orient="vertical", command=viewport.yview)
        viewport.configure(yscrollcommand=scrollbar.set)
        viewport.pack(side="left", fill="both", expand=True)
        content = self._wallpaper_panel(viewport)
        window_item = viewport.create_window(0, 0, anchor="n", window=content)
        content.grid_columnconfigure(0, weight=1)
        label_style = {"bg": PAPER_RED, "fg": PAPER_GOLD, "font": ("Arial", 19),
                       "justify": "center"}

        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(12, 24))
        tk.Label(content,
                 text=f"ROUND {game.rounds_completed + 1}/{game.total_rounds}",
                 **label_style).grid(row=1, column=0, pady=(0, 20))
        self._goal_label = tk.Label(
            content, text=f"GOAL: {game.goal or ''}",
            wraplength=1050, **label_style,
        )
        self._goal_label.grid(row=2, column=0, padx=18, pady=(0, 30), sticky="ew")

        cards = tk.Frame(content, bg=PAPER_RED)
        cards.grid(row=3, column=0, padx=18, pady=(0, 28), sticky="ew")
        self._attribute_cards_frame = cards
        self._attribute_card_buttons = []
        self._attribute_recipient_labels = []
        for n, description in enumerate(game.hands[source].attributes):
            selected = n == self.selected_attribute
            button = tk.Button(
                cards, text=f"{n + 1}. {description}",
                command=lambda number=n: self._select_attribute(number),
                font=("Arial", 16),
                bg="#ffe09a" if selected else PAPER_GOLD, fg=PAPER_INK,
                activebackground="#ffe09a", activeforeground=PAPER_INK,


                relief="solid", bd=2,
                highlightthickness=0, padx=18, pady=17, cursor="hand2",
                wraplength=280, anchor="center", justify="center",
            )
            self._attribute_card_buttons.append(button)
            recipient = self.proposed_recipients[n]
            owner = game.players[recipient].name if recipient is not None else "Unassigned"
            to = tk.Label(cards, text=f"TO: {owner}",
                          bg=PAPER_RED, fg=PAPER_GOLD, font=("Arial", 15),
                          anchor="center", justify="center", wraplength=280)
            self._attribute_recipient_labels.append(to)

        targets = tk.Frame(content, bg=PAPER_RED)
        targets.grid(row=4, column=0, padx=15, pady=(0, 24))
        self._attribute_targets_frame = targets
        for pid in game.competitors:
            quota = game.keep_quota() if pid == source else game.give_quota()
            used = self.proposed_recipients.count(pid)
            button = self._button(
                targets, f"{game.players[pid].name} ({used}/{quota})",
                lambda target=pid: self._give_to(target), width=16)
            button.grid(row=0, column=len(self._attribute_player_buttons), padx=9, pady=6)
            if self.selected_attribute is None or used >= quota:
                button.config(state=tk.DISABLED, disabledforeground="#777e88")
            self._attribute_player_buttons[pid] = button

        self._button(content, "CONFIRM", self._confirm_distribution, width=18).grid(
            row=5, column=0, pady=(0, 14))
        notice = tk.Label(content, text="", fg=PAPER_GOLD, bg=PAPER_RED,
                          justify="center", wraplength=900, font=("Arial", 12))
        notice.grid(row=6, column=0, pady=(0, 8))
        self._attribute_notice = notice

        self._attribute_canvas = viewport
        self._attribute_scrollbar = scrollbar
        self._attribute_inner = content
        self._attribute_window = window_item
        for name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._character_wheel_binds[name] = self.board._root.bind(
                name, self._scroll_attributes, add="+")
        viewport.bind("<Configure>", lambda event:
                      self._layout_attribute_screen(event.width, event.height), add="+")
        viewport.bind("<Destroy>", self._attribute_canvas_destroyed)
        self._layout_attribute_screen(self.board._canvas.winfo_width(),
                                      self.board._canvas.winfo_height())

    def _attribute_canvas_destroyed(self, event) -> None:
        if (event.widget is self._attribute_canvas
                and self._attribute_refresh_id is not None):
            self.board._root.after_cancel(self._attribute_refresh_id)
            self._attribute_refresh_id = None

    def _scroll_attributes(self, event) -> None:
        if self.screen != "assign" or self._attribute_canvas is None:
            return
        if getattr(event, "num", None) == 4:
            amount = -3
        elif getattr(event, "num", None) == 5:
            amount = 3
        else:
            delta = getattr(event, "delta", 0)
            amount = (-3 if delta > 0 else 3) if delta else 0
        if amount:
            self._attribute_canvas.yview_scroll(amount, "units")

    def _layout_attribute_screen(self, width: int, height: int) -> None:
        if (self._attribute_canvas is None or self._attribute_inner is None
                or self._attribute_window is None
                or self._attribute_cards_frame is None):
            return
        width, height = max(1, width), max(1, height)
        content_width = max(570, round(width * 0.94))
        self._attribute_canvas.itemconfigure(self._attribute_window,
                                             width=content_width)
        columns = 4 if width >= 1100 else 2
        cards = self._attribute_cards_frame
        if columns != self._attribute_columns or not self._attribute_card_buttons[0].winfo_manager():
            for child in cards.winfo_children():
                child.grid_forget()
            for col in range(4):
                cards.grid_columnconfigure(col, weight=1 if col < columns else 0,
                                            uniform="attribute_cards" if col < columns else "")
            for n, (button, to) in enumerate(zip(
                    self._attribute_card_buttons, self._attribute_recipient_labels)):
                row, col = divmod(n, columns)
                button.grid(row=row * 2, column=col, padx=9, pady=(0, 10),
                            sticky="nsew")
                to.grid(row=row * 2 + 1, column=col, padx=9,
                        pady=(0, 17 if columns == 2 else 2), sticky="ew")
            self._attribute_columns = columns
        wrap = max(170, round(content_width / columns) - 70)
        font_size = max(13, min(17, round(min(width / 90, height / 48))))
        if self._attribute_targets_frame is not None:
            player_columns = 4 if width >= 1100 else 2
            targets = list(self._attribute_player_buttons.values())
            for n, player_button in enumerate(targets):
                row, col = divmod(n, player_columns)
                single_last = (player_columns == 2 and len(targets) % 2 == 1
                               and n == len(targets) - 1)
                player_button.grid(row=row, column=0 if single_last else col,
                                   columnspan=2 if single_last else 1,
                                   padx=9, pady=6)
        for button, to in zip(self._attribute_card_buttons,
                              self._attribute_recipient_labels):
            button.config(wraplength=wrap, font=("Arial", font_size))
            to.config(wraplength=wrap, font=("Arial", max(12, font_size - 1)))
        if self._goal_label is not None:
            self._goal_label.config(wraplength=max(270, int(width * 0.83)),
                                    font=("Arial", max(14, font_size + 2)))
        if self._attribute_refresh_id is not None:
            self.board._root.after_cancel(self._attribute_refresh_id)
        self._attribute_refresh_id = self.board._root.after_idle(
            self._refresh_attribute_scrollregion)

    def _refresh_attribute_scrollregion(self) -> None:
        self._attribute_refresh_id = None
        viewport = self._attribute_canvas
        content = self._attribute_inner
        if viewport is None or content is None or not viewport.winfo_exists():
            return
        viewport.update_idletasks()
        width = max(1, viewport.winfo_width())
        height = max(1, viewport.winfo_height())
        required = content.winfo_reqheight()
        top = max(12, (height - required) // 2)
        viewport.coords(self._attribute_window, width / 2, top)
        self._align_wallpaper(content)
        viewport.configure(scrollregion=(0, 0, width,
                                       max(height, top + required + 12)))
        scrollbar = self._attribute_scrollbar
        if scrollbar is not None:
            if top + required + 12 > height:
                if not scrollbar.winfo_manager():
                    scrollbar.pack(side="right", fill="y")
            elif scrollbar.winfo_manager():
                scrollbar.pack_forget()
        viewport.yview_moveto(self._attribute_scroll_position)

    def _attribute_message(self, message: str) -> None:
        if self._attribute_notice is not None:
            self._attribute_notice.configure(text=message)

    def _render_goal_banner(self, *, y: float, width_fraction: float,
                            height_fraction: float) -> None:
        assert self.game is not None
        panel = self._new_overlay()
        panel.place(relx=0.5, rely=y, anchor="center",
                    relwidth=width_fraction, relheight=height_fraction)
        self._goal_label = tk.Label(
            panel, text=f"GOAL: {self.game.goal or ''}",
            bg=PAPER_RED, fg=PAPER_GOLD, font=("Arial", 15),
            justify="center", wraplength=750,
        )
        self._goal_label.pack(expand=True, fill="both")
        self._window_resized(self.board._canvas.winfo_width(),
                             self.board._canvas.winfo_height())

    def _start_game(self, mode: str) -> None:
        if mode not in ("main", "battle"):
            raise ValueError("Unknown game mode")
        self._setup_mode = mode
        self._player_count = tk.IntVar(master=self.board._root, value=3)
        self._name_vars = [tk.StringVar(master=self.board._root, value=f"Player {i + 1}")
                           for i in range(5)]
        self.screen = "setup"
        self.render()

    def _render_setup_overlay(self) -> None:
        panel = self._new_overlay()
        title = "MAIN MODE" if self._setup_mode == "main" else "CLASSIC BATTLE"
        tk.Label(panel, text=title, bg=PAPER_RED, fg=PAPER_GOLD,
                 font=("Arial", 19, "bold")).grid(
                     row=0, column=0, columnspan=3, pady=(0, 7))
        tk.Label(panel, text="Number of players (including judge)", bg=PAPER_RED,
                 fg=PAPER_GOLD, font=("Arial", 12)).grid(
                     row=2, column=0, columnspan=3, pady=(0, 8))

        selector = tk.Frame(panel, bg=PAPER_RED)
        selector.grid(row=3, column=0, columnspan=3, pady=(0, 18))
        self._count_buttons = {}
        for count in (3, 4, 5):
            button = self._button(selector, str(count),
                                  lambda number=count: self._set_player_count(number), width=4)
            button.pack(side="left", padx=7)
            self._count_buttons[count] = button

        self._name_rows = []
        for i in range(5):
            row = tk.Frame(panel, bg=PAPER_RED)
            tk.Label(row, text=f"Player {i + 1}", font=("Arial", 12),
                     width=10, anchor="w", bg=PAPER_RED, fg=PAPER_GOLD).pack(side="left")
            entry = tk.Entry(row, textvariable=self._name_vars[i], width=24,
                             font=("Arial", 13), bd=1, relief="solid")
            entry.pack(side="left", ipady=5, padx=(8, 0))
            entry.bind("<Return>", lambda _ev: self._submit_setup())
            row.grid(row=4 + i, column=0, columnspan=3, pady=5)
            self._name_rows.append(row)

        self._setup_error = tk.Label(panel, text="", bg=PAPER_RED, fg=PAPER_GOLD,
                                     font=("Arial", 11), wraplength=420)
        self._setup_error.grid(row=9, column=0, columnspan=3, pady=(9, 3))

        footer = tk.Frame(panel, bg=PAPER_RED)
        footer.grid(row=10, column=0, columnspan=3, pady=(6, 0))
        self._button(footer, "BACK", self._to_menu, width=11).pack(side="left", padx=9)
        self._button(footer, "START GAME", self._submit_setup, width=14).pack(side="left", padx=9)
        self._set_player_count(self._player_count.get())

        self._name_rows[0].winfo_children()[1].focus_set()

    def _set_player_count(self, count: int) -> None:
        assert self._player_count is not None
        if count not in (3, 4, 5):
            raise ValueError("Game requires 3–5 players")
        self._player_count.set(count)
        for n, button in self._count_buttons.items():
            selected = n == count
            button.config(bg="#d71920" if selected else PAPER_GOLD,
                          fg=PAPER_GOLD if selected else PAPER_INK,
                          activebackground="#a51412" if selected else "#ffe09a")
        for i, row in enumerate(self._name_rows):
            if i < count:
                row.grid()
            else:
                row.grid_remove()
        if self._setup_error is not None:
            self._setup_error.config(text="")

    @staticmethod
    def _validate_names(raw_names: list[str]) -> list[str]:
        if not 3 <= len(raw_names) <= 5:
            raise ValueError("Choose between 3 and 5 players.")
        names = [name.strip() for name in raw_names]
        if not all(names):
            raise ValueError("Every player needs a name.")
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("Player names must be different.")
        return names

    def _submit_setup(self) -> None:
        assert self._player_count is not None
        try:
            raw = [v.get() for v in self._name_vars[:self._player_count.get()]]
            names = self._validate_names(raw)
            self._begin_game(names, self._setup_mode)
        except (ValueError, RuntimeError) as exc:
            if self._setup_error is not None:
                self._setup_error.config(text=str(exc))

    def _begin_game(self, names: list[str], mode: str | None) -> None:
        if mode not in ("main", "battle"):
            raise ValueError("Unknown game mode")
        names = self._validate_names(names)
        game = Game(names, mode, load_cards(ROOT / "cards.json"))
        game.start_round()
        self.game = game
        self.actor_pos = 0
        self.screen = "handoff"
        self.render()

    def _window_resized(self, width: int, height: int) -> None:
        if self.screen == "menu":
            self._layout_menu_screen(width, height)
            return
        if self.screen == "choose_character":
            self._layout_character_screen(width, height)
            return
        if self.screen == "assign":
            self._layout_attribute_screen(width, height)
            return
        if self.screen in ("arguments", "judge"):
            self._layout_presentation_screen(width, height)
            return
        if self.screen == "round_result":
            self._layout_round_result_screen(width, height)
            return
        if self.screen == "end":
            self._layout_end_screen(width, height)
            return
        if self._goal_label is not None:
            if self.screen in ("handoff", "assign"):
                available_width = width * 0.84
            else:
                available_width = width * 0.48
            self._goal_label.configure(
                wraplength=max(240, round(available_width)),
                font=("Arial", max(13, min(21, round(min(width / 78, height / 40))))),
            )

    def _actor(self) -> int:
        assert self.game is not None
        return self.game.competitors[self.actor_pos]

    def _reveal_hand(self) -> None:
        self.screen = "choose_character"
        self.render()

    def _choose_character(self, card_num: int) -> None:
        assert self.game is not None
        pid = self._actor()
        card = self.game.hands[pid].characters[card_num]
        if not messagebox.askyesno("Choose your character",
                                   "Use this character for the round?",
                                   parent=self.board._root):
            return
        self.game.choose_character(pid, card_num)
        self.proposed_recipients = [None] * 4
        self.selected_attribute = None
        self._attribute_scroll_position = 0.0
        self.screen = "assign"
        self.render()

    def _update_attribute_controls(self) -> None:
        if self.game is None or self.screen != "assign":
            return
        game = self.game
        source = self._actor()

        for n, button in enumerate(self._attribute_card_buttons):
            selected = (n == self.selected_attribute)
            button.configure(bg="#ffe09a" if selected else PAPER_GOLD,


                             bd=2)
            recipient = self.proposed_recipients[n]
            owner = (game.players[recipient].name if recipient is not None
                     else "Unassigned")
            self._attribute_recipient_labels[n].configure(text=f"TO: {owner}")

        for pid, button in self._attribute_player_buttons.items():
            quota = (game.keep_quota() if pid == source
                     else game.give_quota())
            used = self.proposed_recipients.count(pid)
            button.configure(
                text=f"{game.players[pid].name} ({used}/{quota})",
                state=(tk.NORMAL if (self.selected_attribute is not None
                                     and used < quota) else tk.DISABLED),
                disabledforeground="#777e88",
            )


        self._attribute_message("")

    def _select_attribute(self, number: int) -> None:
        if self.proposed_recipients[number] is not None:
            self.proposed_recipients[number] = None
            self.selected_attribute = number
        elif self.selected_attribute == number:
            self.selected_attribute = None
        else:
            self.selected_attribute = number
        self._update_attribute_controls()

    def _give_to(self, target: int) -> None:
        assert self.game is not None
        if self.selected_attribute is None:
            self._attribute_message("Select an Attribute card first.")
            return
        card_num = self.selected_attribute
        source = self._actor()
        quota = self.game.keep_quota() if target == source else self.game.give_quota()
        used = sum(target == p for i, p in enumerate(self.proposed_recipients)
                   if i != card_num)
        if used >= quota:
            self._attribute_message("That player has already received the maximum allowed cards.")
            return
        self.proposed_recipients[card_num] = target
        self.selected_attribute = None
        self._update_attribute_controls()

    def _confirm_distribution(self) -> None:
        assert self.game is not None
        if any(value is None for value in self.proposed_recipients):
            self._attribute_message("Assign all four Attribute cards before continuing.")
            return
        self.game.set_distribution(self._actor(), list(self.proposed_recipients))
        self._attribute_scroll_position = 0.0
        self.actor_pos += 1
        if self.actor_pos < len(self.game.competitors):
            self.screen = "handoff"
        else:
            self.game.build_characters()
            self.screen = "arguments"
        self.render()

    def _to_judge(self) -> None:
        self.screen = "judge"
        self.render()

    def _award(self, pid: int) -> None:
        assert self.game is not None
        if not messagebox.askyesno("Judge's decision", f"Award one point to {self.game.players[pid].name}?",
                                   parent=self.board._root):
            return


        winning_character = self.game.hands[pid].chosen_character
        winning_attributes = list(self.game.final_attributes.get(pid, []))
        self.game.award_point(pid)
        self.last_winner = pid
        self.last_winner_character = winning_character
        self.last_winner_attributes = winning_attributes
        self.screen = "round_result"
        self.render()

    def _advance_round(self) -> None:
        assert self.game is not None
        if self.game.game_over:
            self.screen = "end"
        else:
            self.game.start_round()
            self.actor_pos = 0
            self.screen = "handoff"
        self.render()

    def _rulebook(self) -> None:
        self._show_rulebook_page("rulebook")

    def _show_rulebook_page(self, page_name: str) -> None:
        self.screen = page_name
        self.render()

    def _set_rulebook_image_size(self, available_width: int, available_height: int) -> None:
        label = self._rulebook_image_label
        source = self._rulebook_image_source
        if label is None or source is None or not label.winfo_exists():
            return
        if available_width < 10 or available_height < 10:
            return
        image_width = max(1, int(available_width))
        image_height = max(1, int(available_height))
        if self._rulebook_rendered_size == (image_width, image_height):
            return
        resized = source.resize((image_width, image_height), Image.Resampling.LANCZOS)
        self._rulebook_image_photo = ImageTk.PhotoImage(resized, master=self.board._root)
        label.configure(image=self._rulebook_image_photo)
        self._rulebook_rendered_size = (image_width, image_height)

    def _refresh_rulebook_image(self) -> None:
        self._rulebook_resize_id = None
        label = self._rulebook_image_label
        if label is None or not label.winfo_exists():
            return
        self._set_rulebook_image_size(label.winfo_width(), label.winfo_height())

    def _rulebook_image_resized(self, event) -> None:
        if self._rulebook_resize_id is not None:
            self.board._root.after_cancel(self._rulebook_resize_id)
        self._rulebook_resize_id = self.board._root.after_idle(self._refresh_rulebook_image)

    def _rulebook_button(self, parent, label: str, action, width: int) -> tk.Button:
        button = self._button(parent, label, action, width=width)
        button.configure(bg="#ffed83", fg="#190d08", font=("Arial", 14, "bold"),
                         activebackground="#d71920", activeforeground="#fff5bd",
                         bd=2, padx=4, pady=3)
        button.bind("<Enter>", lambda _event, b=button: b.configure(
            bg="#d71920", fg="#fff5bd"))
        button.bind("<Leave>", lambda _event, b=button: b.configure(
            bg="#ffed83", fg="#190d08"))
        return button

    def _render_rulebook_overlay(self) -> None:
        pages = {
            "rulebook": ("main_mode.png", None, "CLASSICAL MODE", "rulebook_classical"),
            "rulebook_classical": ("classical_mode.png", "MAIN MODE", "BATTLE MODE", "rulebook_battle"),
            "rulebook_battle": ("battle_mode.png", "CLASSICAL MODE", None, None),
        }
        image_name, previous_label, next_label, next_page = pages[self.screen]
        page = self._new_overlay(full_window=True)

        image_label = tk.Label(page, bg="white", borderwidth=0, highlightthickness=0)
        image_label.place(x=0, y=0, relwidth=1, relheight=1)
        image_path = ROOT / "rulebook_images" / image_name
        with Image.open(image_path) as image_file:
            self._rulebook_image_source = image_file.convert("RGB")
        self._rulebook_image_label = image_label
        image_label.bind("<Configure>", self._rulebook_image_resized)

        back = self._rulebook_button(page, "BACK", self._back_to_opening_menu, width=10)

        previous = None
        if previous_label is not None:
            previous_page = ("rulebook" if self.screen == "rulebook_classical"
                             else "rulebook_classical")
            previous = self._rulebook_button(
                page, previous_label,
                lambda target=previous_page: self._show_rulebook_page(target), width=19)

        following = None
        if next_label is not None:
            following = self._rulebook_button(
                page, next_label,
                lambda target=next_page: self._show_rulebook_page(target), width=19)

        def place_navigation(event=None):
            width = max(1, page.winfo_width() if event is None else event.width)
            height = max(1, page.winfo_height() if event is None else event.height)
            margin = max(4, min(12, round(min(width, height) * 0.01)))
            button_height = max(26, min(40, round(height * 0.043)))
            back_width = max(90, min(135, round(width * 0.12)))
            mode_width = max(130, min(190, round(width * 0.22)))
            font_size = max(9, min(14, round(button_height * 0.34)))

            back.configure(font=("Arial", font_size, "bold"))
            back.place(x=margin, y=margin, anchor="nw",
                       width=back_width, height=button_height)
            if previous is not None:
                previous.configure(font=("Arial", font_size, "bold"))
                previous.place(x=margin, y=height - margin, anchor="sw",
                               width=mode_width, height=button_height)
            if following is not None:
                following.configure(font=("Arial", font_size, "bold"))
                following.place(x=width - margin, y=height - margin, anchor="se",
                                width=mode_width, height=button_height)

        page.bind("<Configure>", place_navigation)
        place_navigation()
        self._set_rulebook_image_size(
            self.board._canvas.winfo_width(), self.board._canvas.winfo_height())

    def _render_exit_overlay(self) -> None:
        page = self._new_overlay(full_window=True)
        body = self._wallpaper_panel(page)
        body.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(body, text="ARE YOU SURE YOU WANT TO EXIT?", bg=PAPER_RED,
                 fg=PAPER_GOLD, font=("Arial", 23, "bold")).pack(pady=(0, 25))
        tk.Label(body, text="Be Gay, Do Drugs and Hail Satan.", bg=PAPER_RED,
                 fg=PAPER_GOLD, font=("Arial", 16)).pack(pady=(0, 35))
        choices = tk.Frame(body, bg=PAPER_RED)
        choices.pack()
        self._button(choices, "NO", self._cancel_exit, width=12).pack(side="left", padx=12)
        self._button(choices, "YES", self._confirm_exit, width=12).pack(side="left", padx=12)

    def render(self) -> None:
        previous = self._overlay
        previous_rulebook_image = self._rulebook_image_photo
        previous_menu_image = self._menu_background_photo
        self._clear_overlay(destroy=False)
        self._transition_old_overlay = previous
        try:
            self._render_screen()
        except Exception:
            replacement = self._overlay
            if replacement is not None and replacement.winfo_exists():
                replacement.destroy()
            self._overlay = previous
            raise
        else:
            if self._overlay is not None and self._overlay.winfo_exists():
                self._overlay.lift()
            if previous is not None and previous.winfo_exists():
                previous.destroy()
        finally:
            self._transition_old_overlay = None

    def _render_screen(self) -> None:
        self.actions.clear()
        self.board.clear()
        if self.screen in ("menu", "setup", "rulebook", "rulebook_classical",
                           "rulebook_battle", "exit_confirm"):
            self.board.mark_buttons(set())
            if self.screen == "menu":
                self._render_menu_overlay()
            elif self.screen == "setup":
                self._render_setup_overlay()
            elif self.screen in ("rulebook", "rulebook_classical", "rulebook_battle"):
                self._render_rulebook_overlay()
            else:
                self._render_exit_overlay()
            return

        assert self.game is not None
        g = self.game
        if self.screen == "handoff":
            self.board.mark_buttons(set())
            self._render_handoff_overlay()
            return

        elif self.screen == "choose_character":
            self.board.mark_buttons(set())
            self._render_character_overlay()
            return

        elif self.screen == "assign":
            self.board.mark_buttons(set())
            self._render_attribute_overlay()
            return

        elif self.screen in ("arguments", "judge"):
            self.board.mark_buttons(set())
            self._render_presentation_overlay()
            return

        elif self.screen == "round_result":
            self.board.mark_buttons(set())
            self._render_round_result_overlay()
            return

        elif self.screen == "end":
            self.board.mark_buttons(set())
            self._render_end_overlay()
            return
        else:
            raise RuntimeError(f"Unknown screen {self.screen}")

        self.board.mark_buttons(set(self.actions))


if __name__ == "__main__":
    GameApp().run()
