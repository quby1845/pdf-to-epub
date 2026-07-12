# PDF → EPUB Converter

Convert scanned PDF files to EPUB format with **90-95% accuracy** using AI-powered OCR — runs entirely locally on your machine.

Based on the [pdf-craft](https://github.com/oomol-lab/pdf-craft) library. No API keys, no tokens, no monthly fees. Free forever.

---

## ✨ Features

- 🤖 **DeepSeek-OCR** for high-accuracy AI text recognition
- 📐 **DocLayout-YOLO** for page layout analysis (headers/footers auto-removed)
- 🖼️ Images automatically embedded in EPUB
- ✂️ Line-end hyphenation automatically merged
- 🎨 Premium `style.css` for book-quality EPUB typography
- 🚀 CUDA GPU acceleration (NVIDIA)
- 🇹🇷 Full Turkish character support

---

## 🖥️ System Requirements

| Component | Minimum |
|-----------|---------|
| **OS** | Windows 10/11 |
| **GPU** | NVIDIA (min. 8GB VRAM) |
| **Python** | 3.10+ |
| **RAM** | 16GB recommended |
| **Disk** | ~10GB free (for AI models) |

> ⚠️ AMD GPU and CPU-only systems are not supported. NVIDIA GPU is required.

---

## 🚀 Installation

### 1. Clone the repository
```bash
git clone https://github.com/quby1845/pdf-to-epub.git
cd pdf-to-epub
```

### 2. Run the setup script (one-time)
Open PowerShell **as Administrator**:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

This script automatically installs:
- Python virtual environment (venv)
- PyTorch + CUDA support (~2.5 GB download)
- pdf-craft library
- Pandoc (via winget)
- Poppler (via winget)

### 3. Download AI models (automatic on first run)
```powershell
.\venv\Scripts\Activate.ps1
python -c "from pdf_craft import predownload_models; predownload_models(models_cache_path='models')"
```

---

## 📖 Usage

### Method 1: Double-click (Easy)
1. Drop your PDF into the `input/` folder
2. Double-click `baslat.bat`
3. Enter book details when prompted (title, author, etc.)
4. Wait — EPUB will appear in the `output/` folder

### Method 2: Terminal
```powershell
.\venv\Scripts\Activate.ps1

# Interactive mode
python convert.py

# One-liner
python convert.py input/book.pdf --title "Book Title" --author "Author Name" --publisher "Publisher"
```

---

## ⚙️ Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--title` | PDF filename | Book title |
| `--author` | Unknown | Author name |
| `--publisher` | (empty) | Publisher name |
| `--lang` | `tr` | Language code |
| `--ocr-size` | `gundam` | OCR quality: `tiny` `small` `base` `large` `gundam` |
| `--dpi` | `300` | Scan resolution |
| `-o` | auto | Output EPUB path |

> **OCR size:** `gundam` is the highest quality and works with 8GB VRAM. Use `large` or `base` for faster processing.

---

## ⏱️ Performance

| GPU | Time per Page |
|-----|--------------|
| RTX 4060 Ti 8GB | ~40-45 sec |
| RTX 4070 Ti 12GB | ~20-25 sec |
| RTX 4090 24GB | ~10-12 sec |
| Google Colab L4 | ~25-30 sec |

---

## 📁 Project Structure

```
pdf-to-epub/
├── convert.py      # Main conversion script
├── setup.ps1       # One-time setup script
├── baslat.bat      # Double-click launcher
├── style.css       # Premium EPUB stylesheet
├── input/          # Place your PDF files here
├── output/         # EPUB files are saved here
├── models/         # AI model cache (not in git)
└── venv/           # Python virtual environment (not in git)
```

---

## ⚠️ Known Limitations

- Low-quality scanned PDFs may produce OCR errors
- Complex table layouts may not convert perfectly
- Right-to-left languages (Arabic, Ottoman Turkish) may have issues

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `CUDA out of memory` | Use `--ocr-size large`, close your browser |
| `pandoc not found` | Restart terminal |
| `poppler not found` | Restart terminal |

---

## 🙏 Credits

- [pdf-craft](https://github.com/oomol-lab/pdf-craft) — PDF to Markdown conversion
- [DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) — OCR model
- [Pandoc](https://pandoc.org/) — Markdown to EPUB conversion
- [Poppler](https://poppler.freedesktop.org/) — PDF processing

---

## 📄 License

MIT License
