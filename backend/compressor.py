"""
Smart adaptive compressor.

- General files: custom Huffman + Min Heap + Greedy algorithm.
- Images: format-aware Pillow compression.
- Already compressed image formats are converted only when a size benefit
  is actually found.
- Huffman decompression is lossless and restores exact original bytes.
"""

from pathlib import Path
import heapq
import struct
import time
import shutil
from PIL import Image

MAGIC = b"HUF2"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PRECOMPRESSED = {".jpg", ".jpeg", ".webp", ".png", ".gif"}

class Node:
    __slots__ = ("freq", "symbol", "left", "right")
    def __init__(self, freq, symbol=None, left=None, right=None):
        self.freq, self.symbol, self.left, self.right = freq, symbol, left, right
    def leaf(self):
        return self.symbol is not None

def build_tree(freqs):
    heap, counter = [], 0
    for symbol, freq in enumerate(freqs):
        if freq:
            heapq.heappush(heap, (freq, counter, Node(freq, symbol)))
            counter += 1
    if not heap:
        return None
    while len(heap) > 1: #BUilds the tree
        f1, _, a = heapq.heappop(heap)
        f2, _, b = heapq.heappop(heap)
        parent = Node(f1 + f2, left=a, right=b)
        heapq.heappush(heap, (parent.freq, counter, parent))
        counter += 1
    return heap[0][2]

def build_codes(root): #builds the tree into binary code
    if root is None:
        return {}
    if root.leaf():
        return {root.symbol: "0"}
    codes = {}
    stack = [(root, "")]
    while stack:
        node, prefix = stack.pop()
        if node.leaf():
            codes[node.symbol] = prefix
        else:
            stack.append((node.right, prefix + "1"))
            stack.append((node.left, prefix + "0"))
    return codes

def pack_bits(data, codes): #packs the bits into actual byte 
    out = bytearray()
    acc = 0
    nbits = 0
    for value in data:
        code = codes[value]
        for ch in code:
            acc = (acc << 1) | (ch == "1")
            nbits += 1
            if nbits == 8:
                out.append(acc)
                acc = 0
                nbits = 0
    padding = (8 - nbits) % 8
    if nbits:
        out.append(acc << padding)
    return bytes(out), padding

def unpack_bits(payload, root, padding, original_size): #unpacks the bits back to orignal size 
    if original_size == 0:
        return b""
    if root.leaf():
        return bytes([root.symbol]) * original_size
    result = bytearray()
    node = root
    total_bits = len(payload) * 8 - padding
    for i in range(total_bits):
        bit = (payload[i // 8] >> (7 - i % 8)) & 1
        node = node.right if bit else node.left
        if node.leaf():
            result.append(node.symbol)
            if len(result) == original_size:
                break
            node = root
    if len(result) != original_size:
        raise ValueError("Corrupt Huffman stream")
    return bytes(result)

def huffman_compress(source, destination):
    start = time.perf_counter()
    data = Path(source).read_bytes()
    freqs = [0] * 256
    for b in data:
        freqs[b] += 1

    root = build_tree(freqs)
    codes = build_codes(root)
    payload, padding = pack_bits(data, codes)
    name = Path(source).name.encode("utf-8")

    with Path(destination).open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<QHB", len(data), len(name), padding))
        f.write(name)
        f.write(struct.pack("<256I", *freqs))
        f.write(payload)

    elapsed = (time.perf_counter() - start) * 1000
    size = Path(destination).stat().st_size
    return {
        "method": "Huffman Coding",
        "algorithm": "Huffman + Greedy Algorithm + Min Heap",
        "original_size": len(data),
        "compressed_size": size,
        "compression_ratio": round(size / len(data), 4) if data else 0,
        "space_saved_percent": round((1 - size / len(data)) * 100, 2) if data else 0,
        "processing_time_ms": round(elapsed, 3),
        "unique_symbols": sum(x > 0 for x in freqs),
    }

def huffman_decompress(compressed, output_dir):
    start = time.perf_counter()
    with Path(compressed).open("rb") as f:
        if f.read(4) != MAGIC:
            raise ValueError("Not a valid HUF2 file")
        original_size, name_len, padding = struct.unpack("<QHB", f.read(11))
        name = f.read(name_len).decode("utf-8")
        freqs = list(struct.unpack("<256I", f.read(1024)))
        payload = f.read()

    root = build_tree(freqs)
    restored = unpack_bits(payload, root, padding, original_size) if root else b""
    output = Path(output_dir) / ("restored_" + Path(name).name)
    output.write_bytes(restored)
    return output, {"decompression_time_ms": round((time.perf_counter()-start)*1000, 3),
                     "restored_size": len(restored)}

def image_compress(source, destination, quality=75):
    """
    Format-aware image compression.
    We try several quality levels and keep the smallest acceptable result.
    PNG is tested as optimized PNG and as JPEG when it has no transparency.
    The output extension reflects the actual codec.
    """
    start = time.perf_counter()
    image = Image.open(source)
    original_size = Path(source).stat().st_size
    suffix = Path(source).suffix.lower()
    candidates = []

    # Keep transparency safe: JPEG cannot represent alpha.
    has_alpha = "A" in image.getbands() or "transparency" in image.info

    if suffix in {".jpg", ".jpeg"}:
        rgb = image.convert("RGB")
        for q in (85, 75, 65, 55, 45, 35):
            out = Path(destination) / f"{Path(source).stem}_compressed_q{q}.jpg"
            rgb.save(out, "JPEG", quality=q, optimize=True, progressive=True)
            candidates.append((out, q))
    elif suffix == ".png":
        out = Path(destination) / f"{Path(source).stem}_optimized.png"
        image.save(out, "PNG", optimize=True, compress_level=9)
        candidates.append((out, 100))
        if not has_alpha:
            rgb = image.convert("RGB")
            for q in (85, 75, 65, 55, 45):
                out2 = Path(destination) / f"{Path(source).stem}_compressed_q{q}.jpg"
                rgb.save(out2, "JPEG", quality=q, optimize=True, progressive=True)
                candidates.append((out2, q))
    elif suffix in {".webp", ".bmp", ".tif", ".tiff"}:
        rgb_or_rgba = image.convert("RGBA" if has_alpha else "RGB")
        for q in (85, 75, 65, 55, 45):
            out = Path(destination) / f"{Path(source).stem}_compressed_q{q}.webp"
            rgb_or_rgba.save(out, "WEBP", quality=q, method=6, lossless=False)
            candidates.append((out, q))
        if suffix in {".bmp", ".tif", ".tiff"}:
            out = Path(destination) / f"{Path(source).stem}_optimized.png"
            image.save(out, "PNG", optimize=True, compress_level=9)
            candidates.append((out, 100))
    else:
        raise ValueError("Unsupported image format")

    best, quality = min(candidates, key=lambda x: x[0].stat().st_size)
    best_size = best.stat().st_size

    # For already-compressed images, never claim success if larger.
    if best_size >= original_size:
        fallback = Path(destination) / Path(source).name
        shutil.copy2(source, fallback)
        chosen = fallback
        note = "No smaller image encoding found; original retained."
    else:
        chosen = best
        note = f"Format-aware image compression, quality/level {quality}."

    for p, _ in candidates:
        if p != chosen:
            try: p.unlink()
            except OSError: pass

    return {
        "method": "Image-aware compression",
        "algorithm": "Format-aware JPEG/WebP/PNG encoding",
        "original_size": original_size,
        "compressed_size": chosen.stat().st_size,
        "compression_ratio": round(chosen.stat().st_size / original_size, 4),
        "space_saved_percent": round((1 - chosen.stat().st_size / original_size) * 100, 2),
        "processing_time_ms": round((time.perf_counter()-start)*1000, 3),
        "compressed_name": chosen.name,
        "note": note,
        "lossless": suffix == ".png" and chosen.suffix.lower() == ".png"
    }

def compress_any(source, job):
    suffix = Path(source).suffix.lower()
    if suffix in IMAGE_EXTS:
        return image_compress(source, job)
    destination = Path(job) / (Path(source).name + ".huff")
    result = huffman_compress(source, destination)
    result["compressed_name"] = destination.name
    result["note"] = "Lossless: original bytes can be reconstructed exactly."
    result["lossless"] = True
    return result

def decompress_huff(compressed, output_dir):
    return huffman_decompress(compressed, output_dir)
