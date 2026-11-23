# BATTLE MODE screens ("Battle of Imagination", 2 players).
# Rules: battle_engine.py | Data structures: battle_algorithms.py | app.py is not changed.
# BattleGameApp is a subclass of GameApp: it keeps every existing screen and adds Battle Mode.
from __future__ import annotations

import tkinter as tk

from app import ROOT, GameApp, PAPER_RED, PAPER_GOLD, PAPER_INK, messagebox
from engine import load_cards
from battle_engine import (ATTACK, DEFENSE, SKIP, START_HEALTH,
                           TRICK, BattleGame)


class BattleGameApp(GameApp):
    """GameApp + a playable BATTLE MODE button."""

    def __init__(self):
        # Battle state must exist before GameApp.__init__ draws the first screen.
        self.battle: BattleGame | None = None
        self._battle_name_vars: list[tk.StringVar] = []
        self._battle_error: tk.Label | None = None
        self._battle_canvas: tk.Canvas | None = None
        self._battle_scrollbar: tk.Scrollbar | None = None
        self._battle_inner: tk.Frame | None = None
        self._battle_window: int | None = None
        self._battle_refresh_id: str | None = None
        self._battle_wraps: list[tuple[tk.Widget, float]] = []
        self._battle_hand_frame: tk.Frame | None = None
        self._battle_hand_buttons: list[tk.Button] = []
        self._battle_panel_frame: tk.Frame | None = None
        self._battle_panels: list[tk.Frame] = []
        self._battle_columns = (0, 0)
        super().__init__()

    # ==================================================================
    # Hooks: small overrides of GameApp methods. Each one handles the
    # Battle Mode case and otherwise calls the original GameApp method.
    # ==================================================================
    def _render_menu_overlay(self) -> None:
        super()._render_menu_overlay()
        # works whether app.py calls the button BATTLE MODE or STORY MODE
        label = "BATTLE MODE" if "BATTLE MODE" in self.MENU_OPTIONS else "STORY MODE"
        battle_index = self.MENU_OPTIONS.index(label)
        self._menu_buttons[battle_index].configure(command=self._start_battle)

    def _render_screen(self) -> None:
        if self.screen.startswith("battle_"):
            self.actions.clear()
            self.board.clear()
            self.board.mark_buttons(set())
            self._render_battle_screen()
            return
        super()._render_screen()

    def _window_resized(self, width: int, height: int) -> None:
        if self.screen.startswith("battle_") and self.screen != "battle_setup":
            self._layout_battle_screen(width, height)
            return
        super()._window_resized(width, height)

    def _key(self, key: str) -> None:
        if (str(key).lower() == "escape" and not self.board.fullscreen
                and self.screen.startswith("battle_")):
            self._to_menu()
            return
        super()._key(key)

    def _to_menu(self) -> None:
        if self.battle is not None and not self.battle.game_over:
            if not messagebox.askyesno("End battle?",
                                       "Leave the current battle and lose its progress?",
                                       parent=self.board._root):
                return
        self.battle = None
        super()._to_menu()

    def _clear_overlay(self, *, destroy: bool = True) -> None:
        if self._battle_refresh_id is not None:
            self.board._root.after_cancel(self._battle_refresh_id)
            self._battle_refresh_id = None
        super()._clear_overlay(destroy=destroy)
        self._battle_canvas = None
        self._battle_scrollbar = None
        self._battle_inner = None
        self._battle_window = None
        self._battle_wraps = []
        self._battle_hand_frame = None
        self._battle_hand_buttons = []
        self._battle_panel_frame = None
        self._battle_panels = []
        self._battle_columns = (0, 0)

    # ==================================================================
    # Battle Mode screens
    # ==================================================================
    # same colours as Battle_Mode.pdf: red = ATTACK, blue = DEFENSE, purple = TRICK
    BATTLE_COLORS = {ATTACK: "#fde8e8", DEFENSE: "#e8eefd", TRICK: "#f1e6fd", SKIP: "#fff0b8"}
    BATTLE_TEXT = {ATTACK: "#c00000", DEFENSE: "#0000c0", TRICK: "#7a00cc", SKIP: PAPER_INK}

    def _start_battle(self) -> None:
        if not self._battle_name_vars:
            self._battle_name_vars = [
                tk.StringVar(master=self.board._root, value=f"Player {i + 1}")
                for i in range(2)]
        self.screen = "battle_setup"
        self.render()

    def _render_battle_setup_overlay(self) -> None:
        panel = self._new_overlay()
        style = {"bg": PAPER_RED, "fg": PAPER_GOLD}
        tk.Label(panel, text="BATTLE MODE", font=("Arial", 19, "bold"),
                 **style).grid(row=0, column=0, pady=(0, 4))
        tk.Label(panel, text="Battle of Imagination — 2 players",
                 font=("Arial", 13), **style).grid(row=1, column=0, pady=(0, 16))
        for i, var in enumerate(self._battle_name_vars):
            row = tk.Frame(panel, bg=PAPER_RED)
            tk.Label(row, text=f"Player {i + 1}", font=("Arial", 12), width=10,
                     anchor="w", **style).pack(side="left")
            entry = tk.Entry(row, textvariable=var, width=24, font=("Arial", 13),
                             bd=1, relief="solid")
            entry.pack(side="left", ipady=5, padx=(8, 0))
            entry.bind("<Return>", lambda _ev: self._submit_battle_setup())
            row.grid(row=2 + i, column=0, pady=5)
            if i == 0:
                entry.focus_set()
        self._battle_error = tk.Label(panel, text="", bg=PAPER_RED, fg="#a52626",
                                     font=("Arial", 11), wraplength=420)
        self._battle_error.grid(row=4, column=0, pady=(9, 3))
        footer = tk.Frame(panel, bg=PAPER_RED)
        footer.grid(row=5, column=0, pady=(6, 0))
        self._button(footer, "BACK", self._to_menu, width=11).pack(side="left", padx=9)
        self._button(footer, "START BATTLE", self._submit_battle_setup,
                     width=14).pack(side="left", padx=9)

    def _submit_battle_setup(self) -> None:
        try:
            names = [var.get() for var in self._battle_name_vars]
            self.battle = BattleGame(names, load_cards(ROOT / "cards.json"))
        except (ValueError, RuntimeError) as exc:
            if self._battle_error is not None:
                self._battle_error.config(text=str(exc))
            return
        self.screen = "battle_handoff"
        self.render()

    # ----- generic scrollable, centered page -----------------------------
    def _battle_page(self) -> tk.Frame:
        page = self._new_overlay(full_window=True)
        viewport = self._wallpaper_canvas(page)
        scrollbar = tk.Scrollbar(page, orient="vertical", command=viewport.yview)
        viewport.configure(yscrollcommand=scrollbar.set)
        viewport.pack(side="left", fill="both", expand=True)
        content = self._wallpaper_panel(viewport)
        self._battle_window = viewport.create_window(0, 0, anchor="n", window=content)
        content.grid_columnconfigure(0, weight=1)
        self._battle_canvas = viewport
        self._battle_scrollbar = scrollbar
        self._battle_inner = content
        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._character_wheel_binds[event_name] = self.board._root.bind(
                event_name, self._scroll_battle, add="+")
        viewport.bind("<Configure>", lambda event:
                      self._layout_battle_screen(event.width, event.height), add="+")
        viewport.bind("<Destroy>", self._battle_canvas_destroyed)
        return content

    def _battle_label(self, parent, text: str, *, size: int = 19, bold: bool = False,
                     wrap: float | None = 0.85, **grid) -> tk.Label:
        label = tk.Label(parent, text=text, bg=PAPER_RED, fg=PAPER_GOLD,
                         font=("Arial", size, "bold") if bold else ("Arial", size),
                         justify="center")
        if wrap is not None:
            self._battle_wraps.append((label, wrap))
        if grid:
            label.grid(column=0, **grid)
        return label

    def _battle_header(self, content: tk.Frame) -> int:
        """MAIN MENU, round, health and cards left. Returns next free row."""
        battle = self.battle
        assert battle is not None
        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(16, 18))
        p0, p1 = battle.players
        round_text = f"ROUND {battle.round_number}" if battle.round_number else "START"
        self._battle_label(content,
                           f"{round_text}    ·    {p0.name} ♥ {max(0, p0.health)}"
                           f"  —  {max(0, p1.health)} ♥ {p1.name}"
                           f"    ·    CARDS LEFT: {battle.cards_left()}",
                           size=18, row=1, pady=(0, 18))
        return 2

    def _battle_canvas_destroyed(self, event) -> None:
        if event.widget is self._battle_canvas and self._battle_refresh_id is not None:
            self.board._root.after_cancel(self._battle_refresh_id)
            self._battle_refresh_id = None

    def _scroll_battle(self, event) -> None:
        if not self.screen.startswith("battle_") or self._battle_canvas is None:
            return
        if getattr(event, "num", None) == 4:
            amount = -3
        elif getattr(event, "num", None) == 5:
            amount = 3
        else:
            delta = getattr(event, "delta", 0)
            amount = (-3 if delta > 0 else 3) if delta else 0
        if amount:
            self._battle_canvas.yview_scroll(amount, "units")

    def _layout_battle_screen(self, width: int, height: int) -> None:
        if (self._battle_canvas is None or self._battle_inner is None
                or self._battle_window is None):
            return
        width, height = max(1, width), max(1, height)
        content_width = max(320, int(width * 0.92))
        self._battle_canvas.itemconfigure(self._battle_window, width=content_width)
        panel_cols = 2 if width >= 860 else 1
        hand_cols = 3 if width >= 1100 else 2 if width >= 700 else 1
        hand_cols = min(hand_cols, max(1, len(self._battle_hand_buttons)))
        if (panel_cols, hand_cols) != self._battle_columns:
            self._battle_columns = (panel_cols, hand_cols)
            self._grid_battle_items(self._battle_panel_frame, self._battle_panels, panel_cols)
            self._grid_battle_items(self._battle_hand_frame, self._battle_hand_buttons, hand_cols)
        for widget, fraction in self._battle_wraps:
            if widget.winfo_exists():
                widget.configure(wraplength=max(150, int(content_width * fraction) - 30))

        if self._battle_refresh_id is not None:
            self.board._root.after_cancel(self._battle_refresh_id)
        self._battle_refresh_id = self.board._root.after_idle(
            self._refresh_battle_scrollregion)

    @staticmethod
    def _grid_battle_items(frame: tk.Frame | None, items: list, columns: int) -> None:
        if frame is None or not items:
            return
        for item in items:
            item.grid_forget()
        for col in range(max(3, columns)):
            frame.grid_columnconfigure(col, weight=1 if col < columns else 0,
                                       uniform="battle" if col < columns else "")
        for index, item in enumerate(items):
            row, col = divmod(index, columns)
            item.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    def _refresh_battle_scrollregion(self) -> None:
        self._battle_refresh_id = None
        viewport, content = self._battle_canvas, self._battle_inner
        if viewport is None or content is None or not viewport.winfo_exists():
            return
        viewport.update_idletasks()
        width = max(1, viewport.winfo_width())
        height = max(1, viewport.winfo_height())
        needed = content.winfo_reqheight()
        top = max(12, (height - needed) // 2)
        viewport.coords(self._battle_window, width // 2, top)
        self._align_wallpaper(content)
        viewport.configure(scrollregion=(0, 0, width, max(height, top + needed + 16)))
        bar = self._battle_scrollbar
        if bar is not None:
            if top + needed + 16 > height:
                if not bar.winfo_manager():
                    bar.pack(side="right", fill="y")
            elif bar.winfo_manager():
                bar.pack_forget()
                viewport.yview_moveto(0)

    # ----- screens ----------------------------------------------------------
    def _render_battle_screen(self) -> None:
        if self.screen == "battle_setup":
            self._render_battle_setup_overlay()
            return
        assert self.battle is not None
        builders = {
            "battle_handoff": self._build_battle_handoff,
            "battle_mulligan": self._build_battle_mulligan,
            "battle_choose": self._build_battle_choose,
            "battle_reveal": self._build_battle_reveal,
            "battle_end": self._build_battle_end,
        }
        if self.screen not in builders:
            raise RuntimeError(f"Unknown screen {self.screen}")
        content = self._battle_page()
        builders[self.screen](content)
        self._layout_battle_screen(self.board._canvas.winfo_width(),
                                   self.board._canvas.winfo_height())

    def _battle_role(self) -> str:
        battle = self.battle
        assert battle is not None
        if battle.phase == "mulligan":
            return "Look at your starting hand"
        if battle.phase == "defend":
            return "You are the DEFENDER"
        return "You are the ATTACKER"

    def _build_battle_handoff(self, content: tk.Frame) -> None:
        # Pass the computer: hides the previous player's hand.
        battle = self.battle
        assert battle is not None
        row = self._battle_header(content)
        if battle.phase == "attack" and battle.last_result:
            self._battle_label(content, "LAST ROUND", size=14, bold=True,
                               row=row, pady=(0, 4))
            self._battle_label(content, battle.last_result, size=16,
                               row=row + 1, padx=16, pady=(0, 24))
            row += 2
        self._battle_label(content, f"PASS TO: {battle.players[battle.actor].name}",
                           size=21, bold=True, row=row, pady=(0, 8))
        self._battle_label(content, self._battle_role(), size=16,
                           row=row + 1, pady=(0, 22))
        self._button(content, "REVEAL", self._battle_reveal_hand, width=18).grid(
            row=row + 2, column=0, pady=(0, 18))

    def _battle_reveal_hand(self) -> None:
        battle = self.battle
        assert battle is not None
        self.screen = "battle_mulligan" if battle.phase == "mulligan" else "battle_choose"
        self.render()

    def _battle_card_button(self, parent: tk.Frame, text: str, kind: str,
                            action) -> tk.Frame:
        # The card type is the main part (big and bold); the Attribute text is
        # only flavour (small, italic). Clicking anywhere on the card plays it.
        card = tk.Frame(parent, bg=self.BATTLE_COLORS[kind], bd=1, relief="solid",
                        cursor="hand2" if action else "arrow")
        main = tk.Label(card, text=kind, bg=self.BATTLE_COLORS[kind],
                        fg=self.BATTLE_TEXT[kind], font=("Arial", 22, "bold"))
        main.pack(padx=14, pady=(14, 4))
        flavor = tk.Label(card, text=f"“{text}”", bg=self.BATTLE_COLORS[kind],
                          fg="#555c68", font=("Arial", 12, "italic"),
                          justify="center", wraplength=300)
        flavor.pack(padx=14, pady=(0, 14))
        self._battle_wraps.append((flavor, 0.28))
        if action is not None:
            for widget in (card, main, flavor):
                widget.bind("<Button-1>", lambda _event: action())
        return card

    def _build_battle_mulligan(self, content: tk.Frame) -> None:
        battle = self.battle
        assert battle is not None
        pid = battle.actor
        row = self._battle_header(content)
        self._battle_label(content, f"{battle.players[pid].name.upper()}'S STARTING HAND",
                           size=17, bold=True, row=row, pady=(0, 6))
        self._battle_label(content, "Keep it, or take your one mulligan: the hand is "
                           "shuffled back and you draw the same number of cards.",
                           size=14, row=row + 1, padx=16, pady=(0, 10))
        hand = tk.Frame(content, bg=PAPER_RED)
        hand.grid(row=row + 2, column=0, padx=8, pady=(0, 8), sticky="ew")
        self._battle_hand_frame = hand
        for text, kind in battle.players[pid].hand:
            self._battle_hand_buttons.append(self._battle_card_button(hand, text, kind, None))
        choices = tk.Frame(content, bg=PAPER_RED)
        choices.grid(row=row + 3, column=0, pady=(10, 18))
        self._button(choices, "KEEP HAND", self._battle_keep, width=14).pack(
            side="left", padx=9)
        self._button(choices, "MULLIGAN", self._battle_mulligan, width=14).pack(
            side="left", padx=9)

    def _battle_keep(self) -> None:
        assert self.battle is not None
        self.battle.keep_hand(self.battle.actor)
        self.screen = "battle_handoff"
        self.render()

    def _battle_mulligan(self) -> None:
        assert self.battle is not None
        self.battle.mulligan(self.battle.actor)
        self.screen = "battle_handoff"
        self.render()

    def _battle_panel(self, parent: tk.Frame, pid: int) -> tk.Frame:
        battle = self.battle
        assert battle is not None
        player = battle.players[pid]
        role = "ATTACKER" if pid == battle.attacker else "DEFENDER"
        frame = tk.Frame(parent, bg=PAPER_RED, bd=3 if pid == battle.actor else 1,
                         relief="solid")
        tk.Label(frame, text=f"{player.name}  —  {role}", bg=PAPER_RED, fg=PAPER_GOLD,
                 font=("Arial", 17, "bold")).pack(pady=(12, 6))
        health = max(0, player.health)
        tk.Label(frame, text="HEALTH  " + "♥ " * health + "♡ " * (START_HEALTH - health),
                 bg=PAPER_RED, fg="#a32626", font=("Arial", 16)).pack(pady=2)
        tk.Label(frame, text=f"CARDS IN HAND: {len(player.hand)}", bg=PAPER_RED,
                 fg=PAPER_GOLD, font=("Arial", 14)).pack(pady=(2, 12))
        return frame

    def _build_battle_choose(self, content: tk.Frame) -> None:
        battle = self.battle
        assert battle is not None
        pid = battle.actor
        me = battle.players[pid]
        row = self._battle_header(content)
        panels = tk.Frame(content, bg=PAPER_RED)
        panels.grid(row=row, column=0, padx=8, pady=(0, 14), sticky="ew")
        self._battle_panel_frame = panels
        self._battle_panels = [self._battle_panel(panels, p) for p in (0, 1)]

        self._battle_label(content, f"{me.name.upper()}: {self._battle_role()} — "
                           "pick one card or SKIP", size=17, bold=True,
                           row=row + 1, pady=(4, 6))
        hand = tk.Frame(content, bg=PAPER_RED)
        hand.grid(row=row + 2, column=0, padx=8, pady=(0, 8), sticky="ew")
        self._battle_hand_frame = hand
        for index, (text, kind) in enumerate(me.hand):
            button = self._battle_card_button(
                hand, text, kind, lambda i=index: self._battle_choose(i))
            self._battle_hand_buttons.append(button)
        self._button(content, "SKIP", lambda: self._battle_choose(None), width=18).grid(
            row=row + 3, column=0, pady=(6, 18))

        self._battle_label(content, "BATTLE LOG (newest first)", size=14, bold=True,
                           row=row + 4, pady=(0, 4))
        for n, line in enumerate(battle.log):
            self._battle_label(content, line, size=13, row=row + 5 + n,
                               padx=16, pady=(0, 4))

    def _battle_choose(self, index: int | None) -> None:
        battle = self.battle
        assert battle is not None
        battle.choose(battle.actor, index)
        # after the attacker: pass to the defender; after the defender: reveal
        self.screen = "battle_handoff" if battle.phase == "defend" else "battle_reveal"
        self.render()

    def _build_battle_reveal(self, content: tk.Frame) -> None:
        battle = self.battle
        assert battle is not None
        row = self._battle_header(content)
        self._battle_label(content, f"ROUND {battle.round_number} — REVEAL", size=24,
                           bold=True, row=row, pady=(0, 16))
        cards = tk.Frame(content, bg=PAPER_RED)
        cards.grid(row=row + 1, column=0, padx=8, pady=(0, 12), sticky="ew")
        self._battle_hand_frame = cards
        played = ((battle.attacker, "ATTACKER", battle.attack_card),
                  (battle.defender, "DEFENDER", battle.defend_card))
        for pid, role, (text, kind) in played:
            box = tk.Frame(cards, bg=self.BATTLE_COLORS[kind], bd=1, relief="solid")
            tk.Label(box, text=f"{role}: {battle.players[pid].name}",
                     bg=self.BATTLE_COLORS[kind], fg=PAPER_GOLD,
                     font=("Arial", 15)).pack(padx=14, pady=(14, 4))
            tk.Label(box, text=kind, bg=self.BATTLE_COLORS[kind],
                     fg=self.BATTLE_TEXT[kind], font=("Arial", 24, "bold")).pack(pady=2)
            if kind != SKIP:
                flavor = tk.Label(box, text=f"“{text}”", bg=self.BATTLE_COLORS[kind],
                                  fg="#555c68", font=("Arial", 12, "italic"),
                                  justify="center", wraplength=300)
                flavor.pack(padx=14, pady=(0, 14))
                self._battle_wraps.append((flavor, 0.38))
            else:
                tk.Frame(box, height=12, bg=self.BATTLE_COLORS[kind]).pack()
            self._battle_hand_buttons.append(box)
        self._battle_label(content, battle.last_result, size=18, bold=True,
                           row=row + 2, padx=16, pady=(6, 20))
        if battle.game_over:
            self._button(content, "FINAL RESULT", self._battle_to_end, width=18).grid(
                row=row + 3, column=0, pady=(0, 18))
        else:
            self._button(content, "NEXT ROUND", self._battle_next_round, width=18).grid(
                row=row + 3, column=0, pady=(0, 18))

    def _battle_next_round(self) -> None:
        assert self.battle is not None
        self.battle.next_round()
        self.screen = "battle_handoff"
        self.render()

    def _battle_to_end(self) -> None:
        self.screen = "battle_end"
        self.render()

    def _build_battle_end(self, content: tk.Frame) -> None:
        battle = self.battle
        assert battle is not None
        winner = battle.winner()
        self._button(content, "MAIN MENU", self._to_menu, width=18).grid(
            row=0, column=0, pady=(18, 30))
        if winner is None:
            self._battle_label(content, "IT'S A TIE", size=26, bold=True,
                               row=1, pady=(0, 12))
        else:
            self._battle_label(content, "BATTLE WINNER", size=26, bold=True,
                               row=1, pady=(0, 12))
            self._battle_label(content, battle.players[winner].name, size=24, bold=True,
                               row=2, pady=(0, 10))
        reason = ("The deck ran out." if battle.deck_ended
                  and min(p.health for p in battle.players) > 0
                  else "A player reached 0 health.")
        p0, p1 = battle.players
        self._battle_label(content, f"{reason}\n{p0.name} ♥ {max(0, p0.health)}"
                           f"  —  {max(0, p1.health)} ♥ {p1.name}",
                           size=18, row=3, pady=(0, 24))
        self._button(content, "NEW BATTLE", self._start_battle, width=18).grid(
            row=4, column=0, pady=(12, 18))


if __name__ == "__main__":
    BattleGameApp().run()
