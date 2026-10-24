# Workflow artwork

- `research-workflow.svg`: editable static diagram.
- `research-workflow.gif`: looping illustration of the normal workflow. Colored
  outlines follow the active step; amber outlines identify independent reviews.
  The footer names each step and shows progress through the sequence.

The main README embeds the GIF and links to the static SVG for readers who prefer
an image without motion. Review corrections are described in the diagram; the
animation illustrates the normal forward path, not live agent execution.

## Rebuild the animation

From the repository root:

```bash
uv run --with-requirements scripts/requirements-artwork.txt \
  python scripts/render_workflow_gif.py
```

Rendering uses CairoSVG, Pillow, the system Cairo library, and the DejaVu Sans
font. These are optional artwork dependencies, separate from the research tools.
The renderer uses the SVG as its base. If its layout changes, update the step
outline coordinates in `scripts/render_workflow_gif.py` before regenerating.
