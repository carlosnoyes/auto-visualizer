# renderer.py

import json
import base64
import io
import numpy as np

import matplotlib
# Use a non-interactive backend for servers (no GUI)
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection


def render_filtered_view_base64(json_path_or_data, filters=None, show_background=True):
    """
    Returns a base64 PNG image of the filtered CAD JSON view.

    PARAMETERS
    ----------
    json_path_or_data : str | dict
        Path to JSON file or already-loaded JSON dict.

    filters : dict
        {
            "layers": [...],
            "types": [...],
            "ids": [...]
        }

    show_background : bool
        If True: draw all non-text, non-insert, non-hatch geometry in gray.

    RETURNS
    -------
    { "image_base64": <string> }
    """

    # Load JSON if needed
    if isinstance(json_path_or_data, dict):
        data = json_path_or_data
    else:
        with open(json_path_or_data, "r") as f:
            data = json.load(f)

    entities = data.get("entities", [])

    # Prepare filters
    filters = filters or {}
    filter_layers = set(filters.get("layers", []))
    filter_types = set(filters.get("types", []))
    filter_ids = set(filters.get("ids", []))

    def is_filtered(e):
        """True if entity matches ANY filter provided."""
        ok_layer = (not filter_layers) or (e.get("layer") in filter_layers)
        ok_type  = (not filter_types)  or (e.get("type") in filter_types)
        ok_id    = (not filter_ids)    or (str(e.get("id")) in filter_ids)
        return ok_layer and ok_type and ok_id

    # Create figure off-screen
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_aspect("equal")
    ax.axis("off")

    # ======================================================
    # BACKGROUND (gray)
    # ======================================================
    if show_background:
        bg_segs = []
        for e in entities:
            if e.get("type") in ("INSERT", "HATCH", "MTEXT", "TEXT"):
                continue

            verts = e.get("vertices")
            if verts and len(verts) > 1:
                bg_segs.append(np.array(verts))

        if bg_segs:
            lc_bg = LineCollection(bg_segs, colors="#888888", linewidths=1, alpha=0.5)
            ax.add_collection(lc_bg)

    # ======================================================
    # FOREGROUND (filtered, red)
    # ======================================================
    fg_segs = []
    hatch_regions = []

    for e in entities:
        if not is_filtered(e):
            continue

        if e.get("type") == "HATCH" and "vertices" in e:
            hatch_regions.append(np.array(e["vertices"]))
            continue

        verts = e.get("vertices")
        if verts and len(verts) > 1:
            fg_segs.append(np.array(verts))

    if fg_segs:
        lc_fg = LineCollection(fg_segs, colors="red", linewidths=1.2)
        ax.add_collection(lc_fg)

    if hatch_regions:
        pc = PolyCollection(hatch_regions, facecolors="red", edgecolors="none", alpha=0.3)
        ax.add_collection(pc)

    ax.autoscale()

    # ======================================================
    # Convert figure → PNG → base64
    # ======================================================
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=False)
    plt.close(fig)

    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "image_base64": image_base64
    }
