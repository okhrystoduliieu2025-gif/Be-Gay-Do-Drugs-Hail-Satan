from __future__ import annotations

import tkinter as tk

from game2dboard import Board


class ResizableBoard(Board):
    def __init__(self, rows: int, columns: int):
        self.fullscreen = False
        self._display_width: int | None = None
        self._display_height: int | None = None
        self._button_cells: set[tuple[int, int]] = set()
        self.resize_callback = None
        super().__init__(rows, columns)

    def _setupUI(self) -> None:
        super()._setupUI()

        self._root.resizable(True, True)
        self._root.minsize(720, 610)
        self._canvas.pack_configure(fill="both", expand=True)
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        self._update_layout(max(1, self._canvas.winfo_width()),
                            max(1, self._canvas.winfo_height()))
        self._apply_cell_style()

    def _on_canvas_resize(self, event) -> None:
        if event.width > 1 and event.height > 1:
            self._update_layout(event.width, event.height)
            if callable(self.resize_callback):
                self.resize_callback(event.width, event.height)

    def _update_layout(self, width: int, height: int) -> None:
        self._display_width = width
        self._display_height = height
        sx = width / self._canvas_width
        sy = height / self._canvas_height

        self._canvas.coords(
            self._bgrect,
            self.margin * sx, self.margin * sy,
            (self._canvas_width - self.margin) * sx,
            (self._canvas_height - self.margin) * sy,
        )
        for r in range(self.nrows):
            for c in range(self.ncols):
                self._position_cell(r, c, sx, sy)

    def mark_buttons(self, cells: set[tuple[int, int]]) -> None:
        self._button_cells = set(cells)
        self._apply_cell_style()

    def _apply_cell_style(self) -> None:
        self._canvas.itemconfigure(self._bgrect, fill="#ffffff", outline="#ffffff")
        self._canvas.configure(bg="#ffffff")
        for row in range(self.nrows):
            for col in range(self.ncols):
                cell = self._cells[row][col]
                if cell is None:
                    continue
                clickable = (row, col) in self._button_cells
                self._canvas.itemconfigure(
                    cell.id, fill="#ffffff", outline="#3b4252" if clickable else "#ffffff",
                    width=2 if clickable else 0)

                cell._text_color = "#202633"
                if cell._image_id is not None and self._canvas.type(cell._image_id) == "text":
                    self._canvas.itemconfigure(cell._image_id, fill="#202633")

    def _position_cell(self, row: int, col: int,
                       sx: float | None = None, sy: float | None = None) -> None:
        cell = self._cells[row][col]
        if cell is None or self._display_width is None or self._display_height is None:
            return
        if sx is None:
            sx = self._display_width / self._canvas_width
        if sy is None:
            sy = self._display_height / self._canvas_height
        base_width, base_height = self.cell_size
        x, y = cell.x, cell.y
        self._canvas.coords(cell.id, x * sx, y * sy,
                            (x + base_width) * sx, (y + base_height) * sy)
        content = cell._image_id
        if content is not None:
            self._canvas.coords(content,
                                (x + base_width / 2) * sx,
                                (y + base_height / 2) * sy)
            if self._canvas.type(content) == "text":
                font_size = max(8, min(36, round(12 * min(sx, sy))))
                wrap_width = max(24, round((base_width - 8) * sx))
                self._canvas.itemconfigure(content,
                                           font=("Arial", font_size),
                                           fill="#202633",
                                           width=wrap_width)

    def _notify_change(self, row: int, col: int, new_value) -> None:
        super()._notify_change(row, col, new_value)
        if self._display_width is not None and self._cells[row][col] is not None:
            self._position_cell(row, col)
            cell = self._cells[row][col]
            cell._text_color = "#202633"

    def _xy2rc(self, x, y):
        if self._display_width and self._display_height:
            x = x * self._canvas_width / self._display_width
            y = y * self._canvas_height / self._display_height
        return super()._xy2rc(x, y)

    def maximize_window(self) -> None:
        try:
            self._root.state("zoomed")
            return
        except tk.TclError:
            pass
        try:
            self._root.attributes("-zoomed", True)
            return
        except tk.TclError:
            self._root.geometry(
                f"{self._root.winfo_screenwidth()}x"
                f"{self._root.winfo_screenheight()}+0+0"
            )

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self._root.attributes("-fullscreen", self.fullscreen)
