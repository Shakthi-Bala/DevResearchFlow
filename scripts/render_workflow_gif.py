#!/usr/bin/env python3
"""Animate the source SVG with sequential stage outlines; no model or API calls.

Run from any directory:
    uv run --with-requirements scripts/requirements-artwork.txt \
        python scripts/render_workflow_gif.py
"""
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/assets/research-workflow.svg'
OUTPUT = ROOT / 'docs/assets/research-workflow.gif'
WIDTH, HEIGHT = 1200, 744
PHASE_BOXES = [(40, 189, 390, 519), (425, 189, 775, 519), (810, 189, 1160, 519)]
PHASE_COLORS = [(94, 234, 212), (96, 165, 250), (196, 181, 253)]
REVIEW_COLOR = (251, 191, 36)
# title, explanation, phase, active box, review
STEPS = [
    ('Coordinator', 'Define the question, constraints, budget, and task contracts.', 0, (59, 273, 371, 326), False),
    ('Literature researcher', 'Read primary sources and preserve limitations and conflicting evidence.', 0, (59, 332, 371, 382), False),
    ('Hypothesis researcher', 'Propose competing explanations and conditions that would disprove them.', 0, (59, 332, 371, 382), False),
    ('Methodology designer', 'Specify baselines, metrics, controls, repetitions, and the experiment budget.', 0, (59, 389, 371, 438), False),
    ('Review 1 / Protocol', 'The verifier checks whether the experiment tests the intended hypothesis.', 0, (59, 450, 371, 496), True),
    ('Research engineer / Implement', 'Implement the reviewed protocol and check critical numerical behavior.', 1, (444, 273, 756, 326), False),
    ('Review 2 / Implementation', 'The verifier checks the equations, data flow, configuration, and evaluation.', 1, (444, 336, 756, 382), True),
    ('Research engineer / Execute', 'Run within the agreed budget; save commands, settings, logs, and outputs.', 1, (444, 395, 756, 499), False),
    ('Results analyst', 'Compute reproducible measurements and report failures and uncertainty.', 2, (829, 273, 1141, 326), False),
    ('Review 3 / Evidence', 'The verifier checks the conclusions against supporting and contradicting evidence.', 2, (829, 336, 1141, 382), True),
    ('Coordinator + you / Decide', 'Record a scoped outcome: continue, revise, reject, or leave unresolved.', 2, (829, 395, 1141, 499), False),
    ('Preserve the evidence trail', 'Keep sources, protocols, raw runs, reviews, and decisions with the project.', None, (39, 570, 1161, 620), False),
]


def build_base():
    svg = SOURCE.read_text()
    # Use one available font family for consistent SVG/Pillow text metrics.
    font_stack = 'Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif'
    svg = svg.replace(font_stack, 'DejaVu Sans')
    # A flat background avoids gradient banding in GIF's 256-color palette.
    svg = svg.replace('fill="url(#background)"', 'fill="#0c172b"')
    rendered = cairosvg.svg2png(bytestring=svg.encode(), output_width=WIDTH, output_height=650)
    base = Image.new('RGBA', (WIDTH, HEIGHT), '#0c172b')
    base.alpha_composite(Image.open(BytesIO(rendered)).convert('RGBA'))
    draw = ImageDraw.Draw(base)
    draw.line((40, 647, 1160, 647), fill='#304661', width=1)
    return base


def draw_frame(base, index, strength):
    title, explanation, phase, box, review = STEPS[index]
    phase_color = PHASE_COLORS[phase] if phase is not None else PHASE_COLORS[0]
    color = REVIEW_COLOR if review else phase_color
    frame = base.copy()
    glow = Image.new('RGBA', frame.size)
    glow_draw = ImageDraw.Draw(glow)
    if phase is not None:
        glow_draw.rounded_rectangle(PHASE_BOXES[phase], radius=16,
                                    outline=(*phase_color, round(110 * strength)), width=10)
    glow_draw.rounded_rectangle(box, radius=9, outline=(*color, round(150 * strength)), width=9)
    frame = Image.alpha_composite(frame, glow.filter(ImageFilter.GaussianBlur(7)))
    draw = ImageDraw.Draw(frame)
    if phase is not None:
        draw.rounded_rectangle(PHASE_BOXES[phase], radius=16,
                               outline=(*phase_color, round(220 * strength)), width=3)
    draw.rounded_rectangle(box, radius=9, outline=(*color, round(255 * strength)), width=3)
    font = ImageFont.truetype('DejaVuSans.ttf', 18)
    small = ImageFont.truetype('DejaVuSans.ttf', 14)
    draw.text((40, 660), f'{index + 1:02d} / {len(STEPS):02d}', font=small, fill=color)
    draw.text((125, 656), title, font=font, fill='#f8fafc')
    draw.text((125, 684), explanation, font=small, fill='#b8c9dc')
    # A stable progress strip complements the moving box outlines.
    for i in range(len(STEPS)):
        x = 40 + i * 94
        fill = color if i == index else ('#547282' if i < index else '#24374d')
        draw.rounded_rectangle((x, 721, x + 82, 725), radius=2, fill=fill)
    return frame.convert('RGB')


def main():
    base = build_base()
    # Shared colors across every frame prevent GIF palette flicker.
    representatives = [draw_frame(base, index, 1) for index in (0, 4, 5, 8)]
    montage = Image.new('RGB', (WIDTH, HEIGHT * len(representatives)))
    for i, frame in enumerate(representatives):
        montage.paste(frame, (0, HEIGHT * i))
    palette = montage.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    frames, durations = [], []
    for index in range(len(STEPS)):
        for strength, duration in [(0.55, 100), (0.8, 100), (1, 950), (0.8, 100)]:
            frame = draw_frame(base, index, strength)
            frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
            durations.append(duration if index != len(STEPS) - 1 else duration * 2)
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)
    # Preview the full-size layout and representative review/engineering states.
    preview = Image.new('RGB', (WIDTH, HEIGHT * 3))
    for row, index in enumerate((0, 4, 7)):
        preview.paste(draw_frame(base, index, 1), (0, HEIGHT * row))
    # A temporary preview is useful during editing without adding extra repo assets.
    import tempfile
    preview_path = Path(tempfile.gettempdir()) / 'devresearchflow-animation-preview.png'
    preview.save(preview_path)
    with Image.open(OUTPUT) as result:
        assert result.is_animated and result.n_frames >= len(STEPS)
        assert result.info.get('loop') == 0
        print(f'{OUTPUT.relative_to(ROOT)}: {result.n_frames} frames, '
              f'{OUTPUT.stat().st_size / 1024:.0f} KiB, {result.size[0]} x {result.size[1]}')
    print(f'Preview: {preview_path}')


if __name__ == '__main__':
    main()
