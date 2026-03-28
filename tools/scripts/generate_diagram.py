"""Generate an animated GIF showing cross-prompt flag coordination.

Shows how a single flag toggle controls different sections across
multiple prompts simultaneously — the core value proposition.

Usage:
    python -m tools.scripts.generate_diagram
"""

from PIL import Image, ImageDraw, ImageFont
import math

WIDTH = 900
HEIGHT = 520
BG = "#0d1117"
CARD_BG = "#161b22"
CARD_BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED = "#484f58"
FLAG_ON_BG = "#1a7f37"
FLAG_ON_BORDER = "#2ea043"
FLAG_OFF_BG = "#6e2b2b"
FLAG_OFF_BORDER = "#da3633"
SECTION_ON = "#1f6feb"
SECTION_ON_BORDER = "#388bfd"
SECTION_OFF = "#21262d"
SECTION_OFF_BORDER = "#30363d"
SECTION_ON_TEXT = "#e6edf3"
SECTION_OFF_TEXT = "#484f58"
ACCENT = "#58a6ff"
CONNECTOR = "#30363d"
TITLE_COLOR = "#58a6ff"


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font at the given size."""
    for path in [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/SF-Mono-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: str,
    outline: str | None = None,
    width: int = 1,
) -> None:
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_frame(flag_on: bool, frame_idx: int, total_frames: int) -> Image.Image:
    """Draw a single frame of the animation."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    font_title = get_font(20)
    font_heading = get_font(15)
    font_body = get_font(12)
    font_small = get_font(11)
    font_flag = get_font(14)

    # Title
    draw.text(
        (WIDTH // 2, 24),
        "One Flag, Multiple Prompts — Coordinated Behavior",
        fill=TITLE_COLOR,
        font=font_title,
        anchor="mt",
    )

    # Flag toggle box (centered at top)
    flag_w, flag_h = 260, 48
    flag_x = (WIDTH - flag_w) // 2
    flag_y = 56
    flag_bg = FLAG_ON_BG if flag_on else FLAG_OFF_BG
    flag_border = FLAG_ON_BORDER if flag_on else FLAG_OFF_BORDER
    rounded_rect(draw, (flag_x, flag_y, flag_x + flag_w, flag_y + flag_h), 10, flag_bg, flag_border, 2)

    flag_label = "chain_of_thought: ON" if flag_on else "chain_of_thought: OFF"
    toggle_icon = "●" if flag_on else "○"
    draw.text(
        (WIDTH // 2, flag_y + flag_h // 2),
        f"  {toggle_icon}  {flag_label}",
        fill=TEXT_PRIMARY,
        font=font_flag,
        anchor="mm",
    )

    # Connector lines from flag to cards
    connector_y_start = flag_y + flag_h
    connector_y_end = 140
    mid_y = (connector_y_start + connector_y_end) // 2

    # Left connector
    left_card_center = 235
    draw.line([(WIDTH // 2, connector_y_start), (WIDTH // 2, mid_y)], fill=CONNECTOR, width=2)
    draw.line([(WIDTH // 2, mid_y), (left_card_center, mid_y)], fill=CONNECTOR, width=2)
    draw.line([(left_card_center, mid_y), (left_card_center, connector_y_end)], fill=CONNECTOR, width=2)

    # Right connector
    right_card_center = WIDTH - 235
    draw.line([(WIDTH // 2, mid_y), (right_card_center, mid_y)], fill=CONNECTOR, width=2)
    draw.line([(right_card_center, mid_y), (right_card_center, connector_y_end)], fill=CONNECTOR, width=2)

    # Small arrows
    arrow_size = 5
    for cx in [left_card_center, right_card_center]:
        draw.polygon(
            [(cx, connector_y_end), (cx - arrow_size, connector_y_end - arrow_size * 2), (cx + arrow_size, connector_y_end - arrow_size * 2)],
            fill=CONNECTOR,
        )

    # --- Prompt Cards ---
    card_w = 380
    card_h = 340
    card_y = 148
    gap = 40
    left_x = (WIDTH - 2 * card_w - gap) // 2
    right_x = left_x + card_w + gap

    # ---- Generator Prompt Card ----
    rounded_rect(draw, (left_x, card_y, left_x + card_w, card_y + card_h), 12, CARD_BG, CARD_BORDER, 1)
    draw.text((left_x + 20, card_y + 14), "Generator Prompt", fill=TEXT_PRIMARY, font=font_heading)
    draw.text((left_x + 20, card_y + 36), "bucket: generator  /  prompt: coding", fill=TEXT_SECONDARY, font=font_small)

    # Sections
    sec_x = left_x + 16
    sec_w = card_w - 32
    sec_h = 72

    # Section 1: identity (always on)
    sec1_y = card_y + 62
    rounded_rect(draw, (sec_x, sec1_y, sec_x + sec_w, sec1_y + sec_h), 8, SECTION_ON, SECTION_ON_BORDER, 1)
    draw.text((sec_x + 12, sec1_y + 8), "identity", fill=ACCENT, font=font_body)
    draw.text((sec_x + sec_w - 12, sec1_y + 8), "always on", fill=TEXT_MUTED, font=font_small, anchor="rt")
    draw.text((sec_x + 12, sec1_y + 28), '"You are a coding assistant."', fill=SECTION_ON_TEXT, font=font_body)
    draw.text((sec_x + 12, sec1_y + 48), "priority: 1", fill=TEXT_MUTED, font=font_small)

    # Section 2: reasoning (flag controlled)
    sec2_y = sec1_y + sec_h + 10
    s2_bg = SECTION_ON if flag_on else SECTION_OFF
    s2_border = SECTION_ON_BORDER if flag_on else SECTION_OFF_BORDER
    s2_text = SECTION_ON_TEXT if flag_on else SECTION_OFF_TEXT
    rounded_rect(draw, (sec_x, sec2_y, sec_x + sec_w, sec2_y + sec_h), 8, s2_bg, s2_border, 1)
    draw.text((sec_x + 12, sec2_y + 8), "reasoning", fill=ACCENT if flag_on else TEXT_MUTED, font=font_body)
    flag_tag_color = FLAG_ON_BORDER if flag_on else FLAG_OFF_BORDER
    draw.text((sec_x + sec_w - 12, sec2_y + 8), "flag: chain_of_thought", fill=flag_tag_color, font=font_small, anchor="rt")

    gen_text = '"Think step by step. Show your'
    gen_text2 = ' reasoning before the final answer."'
    if flag_on:
        draw.text((sec_x + 12, sec2_y + 28), gen_text, fill=s2_text, font=font_body)
        draw.text((sec_x + 12, sec2_y + 44), gen_text2, fill=s2_text, font=font_body)
    else:
        draw.text((sec_x + 12, sec2_y + 34), "— section disabled —", fill=TEXT_MUTED, font=font_body)
    draw.text((sec_x + 12, sec2_y + 58), "priority: 10", fill=TEXT_MUTED, font=font_small)

    # Section 3: format (always on)
    sec3_y = sec2_y + sec_h + 10
    rounded_rect(draw, (sec_x, sec3_y, sec_x + sec_w, sec3_y + sec_h), 8, SECTION_ON, SECTION_ON_BORDER, 1)
    draw.text((sec_x + 12, sec3_y + 8), "format", fill=ACCENT, font=font_body)
    draw.text((sec_x + sec_w - 12, sec3_y + 8), "always on", fill=TEXT_MUTED, font=font_small, anchor="rt")
    draw.text((sec_x + 12, sec3_y + 28), '"Return your answer as JSON with', fill=SECTION_ON_TEXT, font=font_body)
    draw.text((sec_x + 12, sec3_y + 44), ' keys: answer, confidence."', fill=SECTION_ON_TEXT, font=font_body)
    draw.text((sec_x + 12, sec3_y + 58), "priority: 20", fill=TEXT_MUTED, font=font_small)

    # ---- Reviewer Prompt Card ----
    rounded_rect(draw, (right_x, card_y, right_x + card_w, card_y + card_h), 12, CARD_BG, CARD_BORDER, 1)
    draw.text((right_x + 20, card_y + 14), "Reviewer Prompt", fill=TEXT_PRIMARY, font=font_heading)
    draw.text((right_x + 20, card_y + 36), "bucket: reviewer  /  prompt: code_review", fill=TEXT_SECONDARY, font=font_small)

    sec_rx = right_x + 16

    # Section 1: identity (always on)
    rounded_rect(draw, (sec_rx, sec1_y, sec_rx + sec_w, sec1_y + sec_h), 8, SECTION_ON, SECTION_ON_BORDER, 1)
    draw.text((sec_rx + 12, sec1_y + 8), "identity", fill=ACCENT, font=font_body)
    draw.text((sec_rx + sec_w - 12, sec1_y + 8), "always on", fill=TEXT_MUTED, font=font_small, anchor="rt")
    draw.text((sec_rx + 12, sec1_y + 28), '"You are a code reviewer."', fill=SECTION_ON_TEXT, font=font_body)
    draw.text((sec_rx + 12, sec1_y + 48), "priority: 1", fill=TEXT_MUTED, font=font_small)

    # Section 2: check_reasoning (flag controlled — DIFFERENT TEXT)
    rounded_rect(draw, (sec_rx, sec2_y, sec_rx + sec_w, sec2_y + sec_h), 8, s2_bg, s2_border, 1)
    draw.text((sec_rx + 12, sec2_y + 8), "check_reasoning", fill=ACCENT if flag_on else TEXT_MUTED, font=font_body)
    draw.text((sec_rx + sec_w - 12, sec2_y + 8), "flag: chain_of_thought", fill=flag_tag_color, font=font_small, anchor="rt")

    rev_text = '"Verify each reasoning step is'
    rev_text2 = ' sound and the conclusion follows."'
    if flag_on:
        draw.text((sec_rx + 12, sec2_y + 28), rev_text, fill=s2_text, font=font_body)
        draw.text((sec_rx + 12, sec2_y + 44), rev_text2, fill=s2_text, font=font_body)
    else:
        draw.text((sec_rx + 12, sec2_y + 34), "— section disabled —", fill=TEXT_MUTED, font=font_body)
    draw.text((sec_rx + 12, sec2_y + 58), "priority: 10", fill=TEXT_MUTED, font=font_small)

    # Section 3: check_json (always on)
    rounded_rect(draw, (sec_rx, sec3_y, sec_rx + sec_w, sec3_y + sec_h), 8, SECTION_ON, SECTION_ON_BORDER, 1)
    draw.text((sec_rx + 12, sec3_y + 8), "check_json", fill=ACCENT, font=font_body)
    draw.text((sec_rx + sec_w - 12, sec3_y + 8), "always on", fill=TEXT_MUTED, font=font_small, anchor="rt")
    draw.text((sec_rx + 12, sec3_y + 28), '"Verify the response is valid JSON', fill=SECTION_ON_TEXT, font=font_body)
    draw.text((sec_rx + 12, sec3_y + 44), ' with required keys."', fill=SECTION_ON_TEXT, font=font_body)
    draw.text((sec_rx + 12, sec3_y + 58), "priority: 20", fill=TEXT_MUTED, font=font_small)

    # Bottom caption
    if flag_on:
        caption = "Both prompts include their reasoning sections — different text, same toggle"
    else:
        caption = "Both reasoning sections removed simultaneously — prompts stay in sync"
    draw.text((WIDTH // 2, HEIGHT - 16), caption, fill=TEXT_SECONDARY, font=font_small, anchor="mb")

    return img


def generate_gif(output_path: str) -> None:
    """Generate the animated GIF."""
    frames: list[Image.Image] = []

    # ON state: hold for 2.5 seconds (25 frames at 100ms)
    on_frame = draw_frame(True, 0, 1)
    for _ in range(25):
        frames.append(on_frame.copy())

    # OFF state: hold for 2.5 seconds
    off_frame = draw_frame(False, 0, 1)
    for _ in range(25):
        frames.append(off_frame.copy())

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=True,
    )
    print(f"Generated {output_path} ({len(frames)} frames)")  # noqa: T201


if __name__ == "__main__":
    generate_gif("docs/assets/cross-prompt-flags.gif")
