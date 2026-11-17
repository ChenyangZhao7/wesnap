"""Vector icons drawn straight onto a Tk canvas."""

FONT = "Microsoft YaHei"


def draw_icon(canvas, name: str, rect, color: str = "#ffffff", tags=()) -> None:
    x0, y0 = rect.x + 7, rect.y + 7
    x1, y1 = rect.right - 7, rect.bottom - 7
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    width = 1.5

    if name == "rect":
        canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=width,
                                tags=tags)
    elif name == "ellipse":
        canvas.create_oval(x0, y0, x1, y1, outline=color, width=width,
                           tags=tags)
    elif name == "arrow":
        canvas.create_line(x0, y1, x1, y0, fill=color, width=width, tags=tags)
        canvas.create_polygon(x1, y0, x1 - 6, y0 + 1, x1 - 1, y0 + 6,
                              fill=color, outline=color, tags=tags)
    elif name == "pen":
        canvas.create_line(x0 + 1, y1 - 4, x1 - 4, y0 + 1, fill=color, width=2,
                           tags=tags)
        canvas.create_polygon(x0 - 1, y1 + 1, x0 + 3, y1 - 1, x0 + 1, y1 - 5,
                              fill=color, outline=color, tags=tags)
    elif name == "text":
        canvas.create_text(cx, cy, text="A", fill=color,
                           font=(FONT, -max(10, int(rect.h * 0.45)), "bold"),
                           tags=tags)
    elif name == "mosaic":
        step = (x1 - x0) / 3
        for row in range(3):
            for col in range(3):
                if (row + col) % 2 == 0:
                    bx = x0 + col * step
                    by = y0 + row * step
                    canvas.create_rectangle(bx, by, bx + step - 1, by + step - 1,
                                            fill=color, outline="", tags=tags)
    elif name == "undo":
        canvas.create_arc(x0, y0, x1, y1, start=20, extent=280, style="arc",
                          outline=color, width=width, tags=tags)
        canvas.create_polygon(x0 + 1, cy - 2, x0 + 6, cy - 4, x0 + 3, cy + 3,
                              fill=color, outline=color, tags=tags)
    elif name == "longshot":
        canvas.create_line(cx, y0, cx, y1, fill=color, width=width, tags=tags)
        canvas.create_polygon(cx, y0 - 1, cx - 4, y0 + 5, cx + 4, y0 + 5,
                              fill=color, outline=color, tags=tags)
        canvas.create_polygon(cx, y1 + 1, cx - 4, y1 - 5, cx + 4, y1 - 5,
                              fill=color, outline=color, tags=tags)
    elif name == "pin":
        canvas.create_oval(cx - 5, y0, cx + 5, y0 + 9, outline=color,
                           width=width, tags=tags)
        canvas.create_line(cx, y0 + 9, cx, y1, fill=color, width=width,
                           tags=tags)
        canvas.create_line(cx - 3, y1, cx + 3, y1, fill=color, width=width,
                           tags=tags)
    elif name == "save":
        canvas.create_line(cx, y0, cx, y1 - 4, fill=color, width=width,
                           tags=tags)
        canvas.create_polygon(cx, y1, cx - 5, y1 - 6, cx + 5, y1 - 6,
                              fill=color, outline=color, tags=tags)
        canvas.create_line(x0, y1, x1, y1, fill=color, width=width, tags=tags)
    elif name == "done":
        canvas.create_line(x0, cy, cx - 1, y1 - 2, x1, y0 + 2, fill=color,
                           width=2.5, tags=tags)
    elif name == "cancel":
        canvas.create_line(x0, y0, x1, y1, fill=color, width=2, tags=tags)
        canvas.create_line(x1, y0, x0, y1, fill=color, width=2, tags=tags)
    else:
        canvas.create_text(cx, cy, text="?", fill=color,
                           font=(FONT, -max(10, int(rect.h * 0.45)), "bold"),
                           tags=tags)
