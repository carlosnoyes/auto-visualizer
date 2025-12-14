import json
import ezdxf
import math
from ezdxf import path
from ezdxf.colors import int2rgb
from pathlib import Path

# =============================================================
# CONFIG
# =============================================================

OUTPUT_DIR = Path("JSONs")
DXF_DIR = Path("DXFs")

FLATTEN_TOLERANCE = 0.05

# =============================================================
# UNIT MAP (Standard DXF Codes)
# =============================================================
DXF_UNITS = {
    0: "Unitless",
    1: "in",
    2: "ft",
    3: "mi",
    4: "mm",
    5: "cm",
    6: "m",
    7: "km",
    8: "µin",
    9: "mil",
    10: "yd",
    11: "Å",
    12: "nm",
    13: "µm",
    14: "dm",
    15: "dam",
    16: "hm",
    17: "Gm",
    18: "AU",
    19: "ly",
    20: "pc"
}


# =============================================================
# MATH HELPERS
# =============================================================
def calculate_length(vertices):
    if not vertices or len(vertices) < 2: return 0.0
    total_length = 0.0
    for i in range(len(vertices) - 1):
        x1, y1 = vertices[i]
        x2, y2 = vertices[i + 1]
        total_length += math.hypot(x2 - x1, y2 - y1)
    return round(total_length, 4)


def calculate_area(vertices):
    if not vertices or len(vertices) < 3: return 0.0
    area = 0.0
    n = len(vertices)
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return round(abs(area) / 2.0, 4)


# =============================================================
# DXF HELPERS
# =============================================================
def get_layer_hex(doc, layer_name):
    try:
        layer = doc.layers.get(layer_name)
    except ValueError:
        return "#000000"
    if layer.rgb:
        return "#{:02x}{:02x}{:02x}".format(*layer.rgb)
    return _aci_to_hex(layer.color)


def get_entity_hex(entity):
    if entity.dxf.hasattr("true_color"):
        rgb = int2rgb(entity.dxf.true_color)
        return "#{:02x}{:02x}{:02x}".format(*rgb)
    c = entity.dxf.color
    if c == 256: return None
    return _aci_to_hex(c)


def _aci_to_hex(aci):
    if aci < 0 or aci > 255: return "#000000"
    rgb = int2rgb(aci)
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def entity_to_json(entity, unit_name="Unitless"):
    """
    Now accepts unit_name to format keys dynamically.
    """
    dxftype = entity.dxftype()
    hex_color = get_entity_hex(entity)
    linetype = entity.dxf.get('linetype', 'Continuous')
    lineweight = entity.dxf.get('lineweight', -1)

    data = {
        "type": dxftype,
        "layer": entity.dxf.layer,
        "color_hex": hex_color,
        "linetype": linetype,
        "lineweight": lineweight,
        "id": entity.dxf.handle,
    }

    # --- TEXT ---
    if dxftype in ['TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF']:
        try:
            content = entity.plain_text() if dxftype == 'MTEXT' else entity.dxf.text
            insert = entity.dxf.insert
            rotation = entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0.0

            if not content or content.strip() == "": return None

            data.update({
                "text": content,
                "insert": [insert.x, insert.y],
                "rotation": rotation
            })
            return data
        except:
            return None

    # --- BLOCKS / INSERTS ---
    if dxftype == 'INSERT':
        sx = entity.dxf.get('xscale', 1.0)
        sy = entity.dxf.get('yscale', 1.0)
        sz = entity.dxf.get('zscale', 1.0)

        data.update({
            "block_name": entity.dxf.name,
            "insert": [entity.dxf.insert.x, entity.dxf.insert.y],
            "rotation": entity.dxf.rotation,
            "scale": [sx, sy, sz],
            "attributes": []
        })

        if entity.attribs:
            for attrib in entity.attribs:
                # Pass unit_name recursively
                attr_data = entity_to_json(attrib, unit_name)
                if attr_data: data["attributes"].append(attr_data)
        return data

    # --- GEOMETRY (Lines, Polylines, Hatches) ---
    try:
        p = path.make_path(entity)
        vertices = list(p.flattening(FLATTEN_TOLERANCE))
        v_list = [[v.x, v.y] for v in vertices]
        if not v_list: return None

        # --- DYNAMIC UNIT KEYS ---
        len_key = f"length ({unit_name})"
        area_key = f"area ({unit_name}^2)"

        data[len_key] = calculate_length(v_list)
        data[area_key] = calculate_area(v_list)
        # -------------------------

        data["vertices"] = v_list
        data["vertex_count"] = len(v_list)
        return data
    except:
        return None


# =============================================================
# MAIN PARSER
# =============================================================
def parse_dxf(filepath):
    print(f"Reading {filepath.name}...")
    try:
        doc = ezdxf.readfile(filepath)
    except Exception as e:
        print(f"Error: {e}")
        return None

    # --- CAPTURE UNITS ---
    unit_code = doc.header.get("$INSUNITS", 0)
    unit_name = DXF_UNITS.get(unit_code, "Unitless")

    # 1. Layers
    layers = {}
    for layer in doc.layers:
        layers[layer.dxf.name] = {
            "color": get_layer_hex(doc, layer.dxf.name),
            "frozen": layer.is_frozen(),
            "locked": layer.is_locked()
        }

    # 2. Blocks
    blocks = {}
    for block in doc.blocks:
        if block.name.startswith("*"): continue

        block_entities = []
        for e in block:
            # PASS UNIT NAME
            e_data = entity_to_json(e, unit_name)
            if e_data: block_entities.append(e_data)

        if block_entities: blocks[block.name] = block_entities

    # 3. Modelspace
    msp = doc.modelspace()
    entities = []
    for e in msp:
        # PASS UNIT NAME
        e_data = entity_to_json(e, unit_name)
        if e_data: entities.append(e_data)

    # 4. Offset Calculation
    all_x, all_y = [], []
    for e in entities:
        if "vertices" in e:
            for x, y in e["vertices"]:
                all_x.append(x);
                all_y.append(y)
        elif "insert" in e:
            all_x.append(e["insert"][0]);
            all_y.append(e["insert"][1])

    offset = {"x": 0, "y": 0}
    if all_x:
        cx = (min(all_x) + max(all_x)) / 2
        cy = (min(all_y) + max(all_y)) / 2
        offset = {"x": -cx, "y": -cy}

    # 5. Apply Offset
    for e in entities:
        if "vertices" in e:
            e["vertices"] = [[x + offset["x"], y + offset["y"]] for x, y in e["vertices"]]
        if "insert" in e:
            e["insert"][0] += offset["x"]
            e["insert"][1] += offset["y"]
        if e["type"] == "INSERT" and "attributes" in e:
            for attr in e["attributes"]:
                attr["insert"][0] += offset["x"]
                attr["insert"][1] += offset["y"]

    return {
        "filename": filepath.name,
        "units": unit_name,
        "unit_code": unit_code,
        "offset": offset,
        "layers": layers,
        "blocks": blocks,
        "entities": entities
    }


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)

    dxf_files = sorted(DXF_DIR.glob("*.dxf"))

    if not dxf_files:
        print("No DXF files found in DXFs/")
        exit(0)

    converted = 0
    skipped = 0
    failed = 0

    for dxf_path in dxf_files:
        json_path = OUTPUT_DIR / f"{dxf_path.stem}.json"

        if json_path.exists():
            print(f"⏭  Skipping (already exists): {json_path.name}")
            skipped += 1
            continue

        try:
            data = parse_dxf(dxf_path)
            if not data:
                print(f"❌ Failed to parse: {dxf_path.name}")
                failed += 1
                continue

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            print(f"✅ Saved: {json_path.name}")
            converted += 1

        except Exception as e:
            print(f"❌ Error processing {dxf_path.name}: {e}")
            failed += 1

    print("\n--- Summary ---")
    print(f"Converted: {converted}")
    print(f"Skipped:   {skipped}")
    print(f"Failed:    {failed}")
