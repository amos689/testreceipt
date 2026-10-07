"""Render the README's logo and static badges as SVG files in docs/assets/.

    uv run --with pillow python docs/assets/make_brand.py

Text widths are measured with the real fonts (Verdana for badges, Arial Bold for the wordmark), so
the shapes fit the text. Live badges (CI, release) are linked from their services instead.
"""

# ruff: noqa: E501  (the SVG templates are clearer as one line per element)

from __future__ import annotations

from html import escape
from pathlib import Path

from PIL import ImageFont

HERE = Path(__file__).resolve().parent
FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype"), Path("/Library/Fonts")]


def _font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for folder in FONT_DIRS:
        for name in names:
            hits = list(folder.rglob(name)) if folder.exists() else []
            if hits:
                return ImageFont.truetype(str(hits[0]), size)
    raise SystemExit(f"none of {names} found")


VERDANA = _font(["verdana.ttf", "DejaVuSans.ttf"], 11)
ARIAL_BOLD = _font(["arialbd.ttf", "DejaVuSans-Bold.ttf"], 72)

# Mid-tone colours that read on white and on dark pages, so one logo serves every theme.
SQUARE, PAPER, LINE, CHECK = "#263845", "#fffdf8", "#cfd8dc", "#2da44e"
INK, ACCENT = "#5c7080", "#d9822b"
DISPLAY_WIDTH = 420


def mark(x: int, y: int) -> str:
    """A till receipt with a torn (zigzag) bottom edge, printed lines and a green check."""
    left, right, top, bottom = x + 34, x + 94, y + 16, y + 104
    teeth = 6
    step = (right - left) / teeth
    zigzag = " ".join(
        f"L{right - step * (i + 0.5):g} {bottom - 7 if i % 2 == 0 else bottom:g}"
        for i in range(teeth)
    )
    edge = f"M{left} {top + 6}A6 6 0 0 1 {left + 6} {top}H{right - 6}A6 6 0 0 1 {right} {top + 6}V{bottom} {zigzag} L{left} {bottom}Z"
    rows = []
    for i, (length, total) in enumerate(((26, 12), (20, 16), (30, 10), (16, 18))):
        line_y = y + 32 + i * 14
        rows.append(
            f'<rect x="{left + 9}" y="{line_y}" width="{length}" height="6" rx="3" fill="{LINE}"/>'
            f'<rect x="{right - 9 - total}" y="{line_y}" width="{total}" height="6" rx="3" fill="{INK}"/>'
        )
    return "\n  ".join(
        [
            f'<rect x="{x}" y="{y}" width="128" height="128" rx="32" fill="{SQUARE}"/>',
            f'<path d="{edge}" fill="{PAPER}"/>',
            *rows,
            f'<circle cx="{x + 94}" cy="{y + 96}" r="22" fill="{CHECK}" stroke="{SQUARE}" stroke-width="6"/>',
            f'<path d="M{x + 84} {y + 96.5}L{x + 91.5} {y + 104}L{x + 104.5} {y + 89}" fill="none" stroke="#ffffff" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>',
        ]
    )


def logo() -> str:
    first, second = "test", "receipt"
    tracking = -2
    width = int(
        174
        + ARIAL_BOLD.getlength(first)
        + ARIAL_BOLD.getlength(second)
        + tracking * len(first + second)
        + 24
    )
    height = round(160 * DISPLAY_WIDTH / width)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{DISPLAY_WIDTH}" height="{height}" viewBox="0 0 {width} 160" role="img" aria-labelledby="title desc">
  <title id="title">testreceipt</title>
  <desc id="desc">A till receipt with a green check mark, beside the testreceipt wordmark.</desc>
  {mark(16, 16)}
  <text x="174" y="106" fill="{INK}" font-family="Arial, Helvetica, sans-serif" font-size="72" font-weight="700" letter-spacing="{tracking}">{first}<tspan fill="{ACCENT}">{second}</tspan></text>
</svg>
"""


def mark_only() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160" role="img" aria-label="testreceipt">
  <title>testreceipt</title>
  {mark(16, 16)}
</svg>
"""


def badge(label: str, value: str, color: str) -> str:
    left = round(VERDANA.getlength(label) + 16)
    right = round(VERDANA.getlength(value) + 16)
    total = left + right
    title = escape(f"{label}: {value}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="22" viewBox="0 0 {total} 22" role="img" aria-label="{title}">
  <title>{title}</title>
  <clipPath id="r"><rect width="{total}" height="22" rx="3"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{total}" height="22" fill="#3b4a5a"/>
    <rect x="{left}" width="{right}" height="22" fill="{color}"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana, Geneva, DejaVu Sans, sans-serif" font-size="11">
    <text x="{left / 2:g}" y="15">{escape(label)}</text>
    <text x="{left + right / 2:g}" y="15">{escape(value)}</text>
  </g>
</svg>
"""


BADGES = {
    "license": ("license", "MIT", "#2da44e"),
    "python": ("Python", "3.11–3.14", "#346c97"),
    "study": ("study", "2025 → 2026 agent PRs", "#d9822b"),
    "action": ("GitHub Action", "report-only by default", "#2f6fb0"),
    "hook": ("Claude Code", "Stop hook", "#6f52c8"),
    "platforms": ("platforms", "Windows / Linux / macOS", "#4f6d8a"),
}


def main() -> None:
    (HERE / "brand").mkdir(parents=True, exist_ok=True)
    (HERE / "badges").mkdir(parents=True, exist_ok=True)
    (HERE / "brand" / "testreceipt-logo.svg").write_text(logo(), encoding="utf-8")
    (HERE / "brand" / "testreceipt-mark.svg").write_text(mark_only(), encoding="utf-8")
    for name, (label, value, color) in BADGES.items():
        (HERE / "badges" / f"{name}.svg").write_text(badge(label, value, color), encoding="utf-8")
    print(f"wrote 2 logo files and {len(BADGES)} badges")


if __name__ == "__main__":
    main()
