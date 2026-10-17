
# Intelligent Data Compression — Adaptive v2


### General data
TXT, CSV, JSON, DOCX, PDF, and other files are processed as raw bytes using:
- Frequency analysis
- Min Heap
- Greedy Huffman tree construction
- Lossless Huffman encoding

### Images
PNG/JPEG/WebP/BMP/TIFF are handled by a format-aware image compressor using Pillow. Several quality/encoding settings are tested and the smallest result is selected. For already-compressed images, if no smaller result exists, the original is retained.

This is intentionally adaptive: Huffman is the DAA core, while image codecs are used where they are more effective.

## Run backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Run frontend
```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally http://localhost:5173.

## Important
Image compression is generally lossy when JPEG/WebP quality is reduced. General-file Huffman compression is lossless. PNG→optimized PNG is lossless when that is the selected result.
