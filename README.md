# PDF → EPUB Dönüştürücü 🇹🇷

Taranmış PDF dosyalarını **%90-95 doğrulukla** EPUB formatına dönüştüren, tamamen yerel çalışan Python aracı.

Google Colab üzerinden yapılan [pdf-craft](https://github.com/oomol-lab/pdf-craft) tabanlı dönüşümün **Windows bilgisayarında yerel** olarak çalışan versiyonudur. Token harcamaz, API gerektirmez, ücretsizdir.

---

## ✨ Özellikler

- 🤖 **DeepSeek-OCR** ile AI destekli yüksek doğruluklu metin tanıma
- 📐 **DocLayout-YOLO** ile sayfa düzeni analizi (header/footer otomatik temizlenir)
- 🖼️ Görseller EPUB'a otomatik dahil edilir
- ✂️ Satır sonu heceleme tireleri otomatik birleştirilir
- 🎨 Premium `style.css` ile kitap kalitesinde EPUB dizgisi
- 🚀 CUDA destekli GPU hızlandırması (NVIDIA)
- 🇹🇷 Türkçe karakter desteği

---

## 🖥️ Sistem Gereksinimleri

| Bileşen | Minimum |
|---------|---------|
| **İşletim Sistemi** | Windows 10/11 |
| **GPU** | NVIDIA (min. 8GB VRAM) |
| **Python** | 3.10+ |
| **RAM** | 16GB önerilir |
| **Disk** | ~10GB boş alan (modeller için) |

> ⚠️ AMD ekran kartı ve sadece CPU ile çalışmaz. NVIDIA zorunludur.

---

## 🚀 Kurulum

### 1. Depoyu klonla
```bash
git clone https://github.com/KULLANICI_ADIN/pdf-to-epub.git
cd pdf-to-epub
```

### 2. Kurulum scriptini çalıştır (tek seferlik)
PowerShell'i **Yönetici olarak** aç:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

Bu script otomatik olarak şunları kurar:
- Python sanal ortamı (venv)
- PyTorch + CUDA desteği (~2.5 GB)
- pdf-craft kütüphanesi
- Pandoc (winget ile)
- Poppler (winget ile)

### 3. AI modellerini indir (ilk seferde otomatik yapılır)
```powershell
.\venv\Scripts\Activate.ps1
python -c "from pdf_craft import predownload_models; predownload_models(models_cache_path='models')"
```

---

## 📖 Kullanım

### Yöntem 1: Çift Tıkla (Kolay)
1. PDF dosyasını `input/` klasörüne koy
2. `baslat.bat` dosyasına çift tıkla
3. Soruları yanıtla (kitap adı, yazar vb.)
4. Bekle — EPUB `output/` klasöründe oluşacak

### Yöntem 2: Terminal
```powershell
.\venv\Scripts\Activate.ps1

# İnteraktif mod
python convert.py

# Tek satırda
python convert.py input/kitap.pdf --title "Kitap Adı" --author "Yazar" --publisher "Yayınevi"
```

---

## ⚙️ Parametreler

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `--title` | PDF adı | Kitap başlığı |
| `--author` | Bilinmiyor | Yazar adı |
| `--publisher` | (boş) | Yayınevi |
| `--lang` | `tr` | Dil kodu |
| `--ocr-size` | `gundam` | OCR kalitesi: `tiny` `small` `base` `large` `gundam` |
| `--dpi` | `300` | Tarama çözünürlüğü |
| `-o` | otomatik | Çıktı EPUB yolu |

> **OCR boyutu:** `gundam` en yüksek kalitedir ve 8GB VRAM ile çalışır. Daha hızlı işlem için `large` veya `base` kullanılabilir.

---

## ⏱️ Performans

| GPU | Sayfa Başına Süre |
|-----|-----------------|
| RTX 4060 Ti 8GB | ~40-45 sn |
| RTX 4070 Ti 12GB | ~20-25 sn |
| RTX 4090 24GB | ~10-12 sn |
| Google Colab L4 | ~25-30 sn |

---

## 📁 Proje Yapısı

```
pdf-to-epub/
├── convert.py      # Ana dönüşüm scripti
├── setup.ps1       # Tek seferlik kurulum
├── baslat.bat      # Çift tıkla başlat
├── style.css       # Premium EPUB stil şablonu
├── input/          # PDF dosyalarını buraya koy
├── output/         # EPUB çıktıları burada oluşur
├── models/         # AI model önbelleği (git'e dahil değil)
└── venv/           # Python sanal ortamı (git'e dahil değil)
```

---

## ⚠️ Bilinen Sınırlamalar

- Düşük kaliteli taranmış PDF'lerde OCR hataları olabilir
- Çok karmaşık tablo yapıları tam doğrulukla dönüştürülemeyebilir
- Arapça/Osmanlıca gibi sağdan sola dillerde sorunlar yaşanabilir

---

## 🔧 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `CUDA out of memory` | `--ocr-size large` kullan, tarayıcıyı kapat |
| `pandoc not found` | Terminal'i yeniden başlat |
| `poppler not found` | Terminal'i yeniden başlat |

---

## 🙏 Kullanılan Kütüphaneler

- [pdf-craft](https://github.com/oomol-lab/pdf-craft) — PDF → Markdown dönüşümü
- [DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) — OCR modeli
- [Pandoc](https://pandoc.org/) — Markdown → EPUB dönüşümü
- [Poppler](https://poppler.freedesktop.org/) — PDF işleme

---

## 📄 Lisans

MIT License
