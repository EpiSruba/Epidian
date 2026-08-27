import io
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\FJ2\Downloads\image3.jpeg")
OUT_DIR = ROOT / "assets" / "models"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TEXTURE_PATH = OUT_DIR / "epidian5-label.png"
GLB_PATH = OUT_DIR / "epidian5-can.glb"


def make_label_texture():
    photo = ImageOps.exif_transpose(Image.open(SOURCE)).convert("RGB")
    # Front label corners measured from the supplied reference photograph.
    quad = (895, 934, 1045, 3290, 2390, 3230, 2470, 900)
    front = photo.transform(
        (1180, 1700), Image.Transform.QUAD, quad,
        resample=Image.Resampling.BICUBIC,
    )
    front = ImageEnhance.Contrast(front).enhance(1.05)
    front = ImageEnhance.Color(front).enhance(0.92)
    front = front.crop((0, 0, 1060, 1700))
    texture = ImageOps.fit(
        front, (2048, 1024), method=Image.Resampling.LANCZOS,
        centering=(0.48, 0.47),
    )
    texture.save(TEXTURE_PATH, optimize=True)
    bio = io.BytesIO()
    texture.save(bio, format="PNG", optimize=True)
    return bio.getvalue()


positions = []
normals = []
uvs = []
indices = []
parts = []


def add_part(pos, norm, uv, idx, material):
    start_v = len(positions)
    start_i = len(indices)
    positions.extend(pos)
    normals.extend(norm)
    uvs.extend(uv)
    indices.extend([start_v + i for i in idx])
    parts.append((start_v, len(pos), start_i, len(idx), material))


def cylinder_side(radius, y0, y1, segments, material, inward=False, uv_offset=0.0):
    p, n, t, idx = [], [], [], []
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        x, z = radius * math.sin(a), radius * math.cos(a)
        nx, nz = math.sin(a), math.cos(a)
        if inward:
            nx, nz = -nx, -nz
        p += [(x, y0, z), (x, y1, z)]
        n += [(nx, 0, nz), (nx, 0, nz)]
        t += [(i / segments + uv_offset, 1), (i / segments + uv_offset, 0)]
    for i in range(segments):
        a, b, c, d = 2*i, 2*i+1, 2*i+2, 2*i+3
        idx += [a, b, c, c, b, d] if not inward else [a, c, b, c, d, b]
    add_part(p, n, t, idx, material)


def disk(radius, y, segments, material, up=True, inner=0.0):
    p, n, t, idx = [], [], [], []
    ny = 1 if up else -1
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        s, c = math.sin(a), math.cos(a)
        p += [(inner*s, y, inner*c), (radius*s, y, radius*c)]
        n += [(0, ny, 0), (0, ny, 0)]
        t += [(.5 + inner*s/(2*radius), .5 + inner*c/(2*radius)), (.5+s/2, .5+c/2)]
    for i in range(segments):
        a, b, c, d = 2*i, 2*i+1, 2*i+2, 2*i+3
        idx += [a, c, b, c, d, b] if up else [a, b, c, c, b, d]
    add_part(p, n, t, idx, material)


def torus(major, minor, y, major_segments, minor_segments, material):
    p, n, t, idx = [], [], [], []
    for i in range(major_segments + 1):
        a = 2 * math.pi * i / major_segments
        sa, ca = math.sin(a), math.cos(a)
        for j in range(minor_segments + 1):
            b = 2 * math.pi * j / minor_segments
            sb, cb = math.sin(b), math.cos(b)
            r = major + minor * cb
            p.append((r*sa, y + minor*sb, r*ca))
            n.append((cb*sa, sb, cb*ca))
            t.append((i/major_segments, j/minor_segments))
    row = minor_segments + 1
    for i in range(major_segments):
        for j in range(minor_segments):
            a = i*row+j; b = a+row; c = a+1; d = b+1
            idx += [a, b, c, c, b, d]
    add_part(p, n, t, idx, material)


def append_aligned(blob, data):
    while len(blob) % 4:
        blob.extend(b"\x00")
    offset = len(blob)
    blob.extend(data)
    return offset, len(data)


def build_glb(png_bytes):
    # Dimensions are normalized from the reference: roughly 1 kg cylindrical can.
    cylinder_side(1.0, -1.28, 1.20, 128, 0)
    disk(0.965, 1.235, 128, 0, True)
    disk(0.98, -1.30, 128, 0, False)
    torus(0.93, 0.075, 1.24, 128, 16, 0)
    torus(1.00, 0.055, 1.17, 128, 12, 0)
    torus(0.96, 0.045, -1.28, 128, 12, 0)
    disk(0.78, 1.285, 128, 1, True)
    torus(0.78, 0.035, 1.285, 128, 10, 0)
    cylinder_side(1.006, -1.17, 1.08, 160, 2, uv_offset=0.5)

    pos = np.asarray(positions, dtype="<f4")
    nor = np.asarray(normals, dtype="<f4")
    tex = np.asarray(uvs, dtype="<f4")
    ind = np.asarray(indices, dtype="<u4")

    blob = bytearray()
    views = []
    def add_view(data, target=None):
        off, ln = append_aligned(blob, data)
        view = {"buffer": 0, "byteOffset": off, "byteLength": ln}
        if target: view["target"] = target
        views.append(view)
        return len(views)-1
    pos_view = add_view(pos.tobytes(), 34962)
    nor_view = add_view(nor.tobytes(), 34962)
    uv_view = add_view(tex.tobytes(), 34962)
    idx_view = add_view(ind.tobytes(), 34963)
    img_view = add_view(png_bytes)

    accessors = []
    def accessor(view, comp, count, typ, mins=None, maxs=None, byte_offset=0):
        a = {"bufferView": view, "byteOffset": byte_offset, "componentType": comp, "count": count, "type": typ}
        if mins is not None: a["min"] = [float(x) for x in mins]
        if maxs is not None: a["max"] = [float(x) for x in maxs]
        accessors.append(a)
        return len(accessors)-1
    pos_acc = accessor(pos_view, 5126, len(pos), "VEC3", pos.min(0), pos.max(0))
    nor_acc = accessor(nor_view, 5126, len(nor), "VEC3")
    uv_acc = accessor(uv_view, 5126, len(tex), "VEC2")

    primitives = []
    for start_v, count_v, start_i, count_i, material in parts:
        ia = accessor(idx_view, 5125, count_i, "SCALAR", [int(ind[start_i:start_i+count_i].min())], [int(ind[start_i:start_i+count_i].max())], start_i*4)
        primitives.append({"attributes": {"POSITION": pos_acc, "NORMAL": nor_acc, "TEXCOORD_0": uv_acc}, "indices": ia, "material": material})

    gltf = {
        "asset": {"version": "2.0", "generator": "Epidian product model builder"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Epidian 5 can"}],
        "meshes": [{"name": "Epidian 5 can", "primitives": primitives}],
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": accessors,
        "images": [{"bufferView": img_view, "mimeType": "image/png", "name": "Epidian 5 label"}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 33071}],
        "textures": [{"sampler": 0, "source": 0}],
        "materials": [
            {"name": "Brushed steel", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.72,0.74,0.74,1], "metallicFactor": 0.92, "roughnessFactor": 0.24}},
            {"name": "Lid steel", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.60,0.63,0.64,1], "metallicFactor": 0.96, "roughnessFactor": 0.18}},
            {"name": "Printed label", "doubleSided": True, "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0, "roughnessFactor": 0.72}},
        ],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(js) % 4: js += b" "
    while len(blob) % 4: blob += b"\x00"
    total = 12 + 8 + len(js) + 8 + len(blob)
    out = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    out += struct.pack("<I4s", len(js), b"JSON") + js
    out += struct.pack("<I4s", len(blob), b"BIN\x00") + blob
    GLB_PATH.write_bytes(out)
    return GLB_PATH


if __name__ == "__main__":
    png = make_label_texture()
    path = build_glb(png)
    print(path)
    print(f"{path.stat().st_size / 1024 / 1024:.2f} MB")
