"""Vertical scroll-capture stitching with sticky-header awareness."""

from dataclasses import dataclass

from PIL import Image, ImageChops, ImageStat


@dataclass
class StitchResult:
    image: Image.Image
    appended_rows: int
    offset: int
    header_skipped: int
    score: float
    status: str


def _to_gray(image: Image.Image, width: int) -> Image.Image:
    gray = image.convert("L")
    if width and gray.width > width:
        gray = gray.resize((width, gray.height), Image.Resampling.LANCZOS)
    return gray


def _mean_diff(a: Image.Image, b: Image.Image) -> float:
    return float(ImageStat.Stat(ImageChops.difference(a, b)).mean[0])


def frames_differ(a: Image.Image, b: Image.Image, samples: int = 200,
                  threshold: float = 2.0) -> bool:
    if a.size != b.size:
        b = b.resize(a.size)
    width = min(a.width, 64)
    return _mean_diff(_to_gray(a, width), _to_gray(b, width)) > threshold


def common_prefix_rows(prev: Image.Image, frame: Image.Image,
                       max_ratio: float = 0.25, tol: float = 2.0) -> int:
    width = min(prev.width, frame.width, 64)
    a = _to_gray(prev, width)
    b = _to_gray(frame, width)
    limit = min(int(frame.height * max_ratio), a.height, b.height)
    rows = 0
    for y in range(limit):
        diff = ImageChops.difference(a.crop((0, y, a.width, y + 1)),
                                     b.crop((0, y, b.width, y + 1)))
        if float(ImageStat.Stat(diff).mean[0]) > tol:
            break
        rows += 1
    return rows


def _score_at(canvas_gray: Image.Image, frame_gray: Image.Image,
              d: int, header: int) -> float:
    height = canvas_gray.height
    a = canvas_gray.crop((0, height - d, canvas_gray.width, height))
    b = frame_gray.crop((0, header, frame_gray.width, header + d))
    return _mean_diff(a, b)


def _best_offset(canvas_gray: Image.Image, frame_gray: Image.Image,
                 header: int, min_overlap: int, max_overlap: int):
    high = min(frame_gray.height - header, max_overlap)
    if high < 1:
        return None, 255.0
    best = None
    best_score = 255.0
    for d in range(1, min(min_overlap, high) + 1):
        score = _score_at(canvas_gray, frame_gray, d, header)
        if score < best_score:
            best, best_score = d, score
    for d in range(max(min_overlap, 1), high + 1, 4):
        score = _score_at(canvas_gray, frame_gray, d, header)
        if score < best_score:
            best, best_score = d, score
    if best is not None:
        for d in range(max(1, best - 4), min(high, best + 4) + 1):
            score = _score_at(canvas_gray, frame_gray, d, header)
            if score < best_score:
                best, best_score = d, score
    return best, best_score


def _row_signature(gray: Image.Image) -> bytes:
    return gray.resize((1, gray.height), Image.Resampling.BOX).tobytes()


def _contained_in_canvas(canvas_gray: Image.Image, frame_gray: Image.Image,
                         threshold: float) -> bool:
    height, frame_height = canvas_gray.height, frame_gray.height
    if frame_height > height:
        return False
    last = height - frame_height
    window = max(1200, frame_height * 4)
    start = max(0, last - window)
    canvas_sig = _row_signature(canvas_gray)
    frame_sig = _row_signature(frame_gray)
    candidates = []
    for y in range(start, last + 1):
        score = 0
        for row in range(0, frame_height, 4):
            score += abs(canvas_sig[y + row] - frame_sig[row])
        candidates.append((score, y))
    candidates.sort()
    for _score, y in candidates[:6]:
        for candidate in range(max(start, y - 2), min(last, y + 2) + 1):
            if _mean_diff(canvas_gray.crop((0, candidate, canvas_gray.width,
                                             candidate + frame_height)),
                          frame_gray) <= threshold:
                return True
    return False


def _append(canvas: Image.Image, piece: Image.Image) -> Image.Image:
    if piece.height <= 0:
        return canvas.copy()
    out = Image.new("RGB", (canvas.width, canvas.height + piece.height))
    out.paste(canvas, (0, 0))
    out.paste(piece, (0, canvas.height))
    return out


def stitch(canvas: Image.Image, frame: Image.Image, prev_frame=None,
           min_overlap: int = 16, max_overlap_ratio: float = 0.9,
           threshold: float = 12.0, match_width: int = 320,
           max_height: int = 30000) -> StitchResult:
    if canvas.height >= max_height:
        return StitchResult(canvas, 0, 0, 0, 255.0, "max_height")
    header = common_prefix_rows(prev_frame, frame) if prev_frame is not None else 0
    canvas_gray = _to_gray(canvas, match_width)
    frame_gray = _to_gray(frame, match_width)
    if canvas.height >= frame.height:
        tail = canvas.crop((0, canvas.height - frame.height,
                            canvas.width, canvas.height))
        if not frames_differ(tail, frame):
            return StitchResult(canvas, 0, 0, header, 0.0, "ignored")
    max_overlap = int(frame.height * max_overlap_ratio)
    offset, score = _best_offset(canvas_gray, frame_gray, header,
                                 min_overlap, max_overlap)
    if offset is not None and score <= threshold:
        piece = frame.crop((0, header + offset, frame.width, frame.height))
        return StitchResult(_append(canvas, piece), frame.height - header - offset,
                            offset, header, score, "appended")
    if _contained_in_canvas(canvas_gray, frame_gray, threshold):
        return StitchResult(canvas, 0, 0, header, score, "ignored")
    return StitchResult(_append(canvas, frame), frame.height, 0, header, 255.0,
                        "appended_full")
