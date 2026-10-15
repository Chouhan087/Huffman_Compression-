import tempfile
import unittest
from pathlib import Path
from huffman import compress_file, decompress_file

class HuffmanTests(unittest.TestCase):
    def test_binary_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / "sample.bin"
            original.write_bytes(bytes(range(256)) * 4 + b"hello huffman" * 100)
            compressed = root / "sample.bin.huff"

            compress_file(original, compressed)
            restored, _ = decompress_file(compressed, root)

            self.assertEqual(original.read_bytes(), restored.read_bytes())

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / "empty.txt"
            original.write_bytes(b"")
            compressed = root / "empty.txt.huff"

            compress_file(original, compressed)
            restored, _ = decompress_file(compressed, root)

            self.assertEqual(restored.read_bytes(), b"")

if __name__ == "__main__":
    unittest.main()
