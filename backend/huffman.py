import heapq
import json
import os
import struct
import time
from pathlib import Path

MAGIC = b"HUF1"

class Node:
    __slots__ = ("freq", "symbol", "left", "right")
    def __init__(self, freq, symbol=None, left=None, right=None):
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right

    def is_leaf(self):
        return self.symbol is not None

def build_tree(freqs):
    heap = []
    counter = 0
    for symbol, freq in enumerate(freqs):
        if freq:
            heapq.heappush(heap, (freq, counter, Node(freq, symbol)))
            counter += 1

    if not heap:
        return None

    while len(heap) > 1:
        f1, _, a = heapq.heappop(heap)
        f2, _, b = heapq.heappop(heap)
        parent = Node(f1 + f2, left=a, right=b)
        heapq.heappush(heap, (parent.freq, counter, parent))
        counter += 1
    return heap[0][2]

def build_codes(root):
    codes = {}
    if root is None:
        return codes
    if root.is_leaf():
        codes[root.symbol] = "0"
        return codes

    def walk(node, prefix):
        if node.is_leaf():
            codes[node.symbol] = prefix
            return
        walk(node.left, prefix + "0")
        walk(node.right, prefix + "1")

    walk(root, "")
    return codes

def pack_bits(data, codes):
    out = bytearray()
    current = 0
    count = 0
    for byte in data:
        for bit in codes[byte]:
            current = (current << 1) | (bit == "1")
            count += 1
            if count == 8:
                out.append(current)
                current = 0
                count = 0
    padding = (8 - count) % 8
    if count:
        current <<= padding
        out.append(current)
    return bytes(out), padding

def unpack_bits(data, root, padding):
    if root is None:
        return b""
    if root.is_leaf():
        # The header stores original size, so caller handles the exact length.
        return b""

    result = bytearray()
    node = root
    total_bits = len(data) * 8 - padding
    for i in range(total_bits):
        bit = (data[i // 8] >> (7 - (i % 8))) & 1
        node = node.right if bit else node.left
        if node.is_leaf():
            result.append(node.symbol)
            node = root
    return bytes(result)

def serialize_freqs(freqs):
    return struct.pack("<256I", *freqs)

def deserialize_freqs(raw):
    if len(raw) != 1024:
        raise ValueError("Invalid Huffman frequency table")
    return list(struct.unpack("<256I", raw))

def compress_file(source, destination):
    start = time.perf_counter()
    source = Path(source)
    destination = Path(destination)

    data = source.read_bytes()
    freqs = [0] * 256
    for b in data:
        freqs[b] += 1

    root = build_tree(freqs)
    codes = build_codes(root)
    encoded, padding = pack_bits(data, codes)

    name_bytes = source.name.encode("utf-8")
    if len(name_bytes) > 65535:
        raise ValueError("Filename is too long")

    # Header:
    # magic 4 | original size Q | filename length H | padding B | filename | 1024-byte freq table | payload
    with destination.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<QHB", len(data), len(name_bytes), padding))
        f.write(name_bytes)
        f.write(serialize_freqs(freqs))
        f.write(encoded)

    elapsed = time.perf_counter() - start
    compressed_size = destination.stat().st_size
    original_size = len(data)

    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": round(compressed_size / original_size, 4) if original_size else 0,
        "space_saved_percent": round((1 - compressed_size / original_size) * 100, 2) if original_size else 0,
        "processing_time_ms": round(elapsed * 1000, 3),
        "unique_symbols": sum(1 for x in freqs if x),
        "algorithm": "Huffman Coding (Greedy + Min Heap)"
    }

def decompress_file(compressed, output_dir):
    start = time.perf_counter()
    compressed = Path(compressed)
    output_dir = Path(output_dir)

    with compressed.open("rb") as f:
        if f.read(4) != MAGIC:
            raise ValueError("Not a valid .huff file")

        original_size, name_len, padding = struct.unpack("<QHB", f.read(11))
        name = f.read(name_len).decode("utf-8")
        freqs = deserialize_freqs(f.read(1024))
        payload = f.read()

    root = build_tree(freqs)

    if original_size == 0:
        restored = b""
    elif root is not None and root.is_leaf():
        restored = bytes([root.symbol]) * original_size
    else:
        restored = unpack_bits(payload, root, padding)
        if len(restored) != original_size:
            raise ValueError("Corrupted or invalid compressed file")

    safe_name = Path(name).name
    output = output_dir / ("restored_" + safe_name)
    output.write_bytes(restored)

    elapsed = time.perf_counter() - start
    return output, {
        "decompression_time_ms": round(elapsed * 1000, 3),
        "restored_size": len(restored)
    }
