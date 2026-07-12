"""
PDF-to-EPUB Dönüştürücü
=======================
Bu script PDF dosyalarını yüksek kaliteli EPUB formatına dönüştürür.

Kullanım:
    python convert.py                          # interaktif mod
    python convert.py input.pdf                # tek dosya
    python convert.py input.pdf -o kitap.epub  # çıktı adı belirle
    python convert.py input.pdf --title "Kitap Adı" --author "Yazar" --publisher "Yayınevi"

Gereksinimler:
    - NVIDIA GPU (en az 8GB VRAM)
    - PyTorch (CUDA destekli)
    - pdf-craft
    - pandoc
    - poppler
"""

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# Sabİtler
# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
MODELS_DIR = SCRIPT_DIR / "models"
TEMP_DIR = SCRIPT_DIR / "temp"
INPUT_DIR = SCRIPT_DIR / "input"
OUTPUT_DIR = SCRIPT_DIR / "output"


# ============================================================
# Yardımcı fonksiyonlar
# ============================================================
def print_header(text: str) -> None:
    """Renkli başlık yazdır."""
    border = "=" * 50
    print(f"\n\033[96m{border}\033[0m")
    print(f"\033[96m  {text}\033[0m")
    print(f"\033[96m{border}\033[0m\n")


def print_step(step: int, total: int, text: str) -> None:
    """Adım bilgisi yazdır."""
    print(f"\033[92m[{step}/{total}]\033[0m {text}")


def print_warn(text: str) -> None:
    """Uyarı mesajı yazdır."""
    print(f"\033[93m[UYARI]\033[0m {text}")


def print_error(text: str) -> None:
    """Hata mesajı yazdır."""
    print(f"\033[91m[HATA]\033[0m {text}")


def print_success(text: str) -> None:
    """Başarı mesajı yazdır."""
    print(f"\033[92m[OK]\033[0m {text}")


def print_info(text: str) -> None:
    """Bilgi mesajı yazdır."""
    print(f"\033[90m     {text}\033[0m")


def check_cuda() -> bool:
    """CUDA kullanılabilirliğini kontrol et."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print_success(f"CUDA aktif — {gpu_name} ({vram:.1f} GB VRAM)")
            return True
        else:
            print_warn("CUDA bulunamadı! İşlem CPU ile devam edecek (çok yavaş olabilir).")
            return False
    except ImportError:
        print_error("PyTorch kurulu değil! Önce setup.ps1 çalıştırın.")
        sys.exit(1)


def check_pandoc() -> bool:
    """Pandoc kurulumunu kontrol et."""
    if shutil.which("pandoc"):
        print_success("Pandoc bulundu.")
        return True
    else:
        print_error("Pandoc bulunamadı! Lütfen kurun: winget install JohnMacFarlane.Pandoc")
        return False


def find_pdf_files() -> list[Path]:
    """input/ klasöründeki PDF dosyalarını bul."""
    if not INPUT_DIR.exists():
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(INPUT_DIR.glob("*.pdf"))


def select_pdf_interactive() -> Path:
    """Kullanıcıdan PDF seçmesini iste."""
    pdf_files = find_pdf_files()

    if not pdf_files:
        print_error(f"'{INPUT_DIR}' klasöründe hiç PDF dosyası bulunamadı!")
        print_info("PDF dosyanızı şu klasöre koyun ve tekrar çalıştırın:")
        print_info(f"  {INPUT_DIR}")
        sys.exit(1)

    if len(pdf_files) == 1:
        print_success(f"PDF bulundu: {pdf_files[0].name}")
        return pdf_files[0]

    print("\nMevcut PDF dosyaları:")
    for i, pdf in enumerate(pdf_files, 1):
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  \033[96m{i}.\033[0m {pdf.name} ({size_mb:.1f} MB)")

    while True:
        try:
            choice = input(f"\nHangi PDF'i dönüştürmek istiyorsunuz? (1-{len(pdf_files)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(pdf_files):
                return pdf_files[idx]
        except (ValueError, IndexError):
            pass
        print_warn("Geçersiz seçim, tekrar deneyin.")


def get_metadata_interactive(pdf_name: str) -> dict:
    """Kullanıcıdan kitap bilgilerini al."""
    stem = Path(pdf_name).stem

    print("\n\033[96mKitap Bilgileri\033[0m (boş bırakırsanız varsayılan kullanılır):")

    title = input(f"  Kitap Adı [{stem}]: ").strip() or stem
    author = input("  Yazar [Bilinmiyor]: ").strip() or "Bilinmiyor"
    publisher = input("  Yayınevi []: ").strip() or ""
    lang = input("  Dil [tr]: ").strip() or "tr"

    return {
        "title": title,
        "author": author,
        "publisher": publisher,
        "lang": lang,
    }


# ============================================================
# Ana dönüşüm fonksiyonları
# ============================================================
def step_download_models() -> None:
    """OCR modellerini indir (ilk sefer uzun sürer)."""
    from pdf_craft import predownload_models

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print_info("Modeller indiriliyor/kontrol ediliyor...")
    print_info(f"Önbellek konumu: {MODELS_DIR}")
    predownload_models(models_cache_path=str(MODELS_DIR))
    print_success("Modeller hazır.")


def step_convert_to_markdown(pdf_path: Path, md_path: Path, images_dir: Path) -> None:
    """PDF'i Markdown'a dönüştür (ana OCR işlemi)."""
    from pdf_craft import transform_markdown

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Sayfa sayısını tahmin et
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        estimated_time = page_count * 27  # ~27 saniye/sayfa
        print_info(f"Toplam sayfa: {page_count}")
        print_info(f"Tahmini süre: ~{estimated_time // 60} dakika {estimated_time % 60} saniye")
    except ImportError:
        print_info("(Sayfa sayısı tahmin edilemiyor — PyMuPDF kurulu değil)")

    print_info("Her sayfa için ~25-30 saniye sürecek.")
    print_info("İşlem sırasında 'torch.Size' ve 'attention_mask' uyarıları normaldir.\n")

    start_time = time.time()

    transform_markdown(
        pdf_path=str(pdf_path),
        markdown_path=str(md_path),
        markdown_assets_path=str(images_dir),
        analysing_path=str(TEMP_DIR),
        ocr_size="gundam",  # en yüksek kalite (8GB VRAM yeterli)
        models_cache_path=str(MODELS_DIR),
        dpi=300,
    )

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print_success(f"Markdown dönüşümü tamamlandı! (Süre: {minutes}dk {seconds}sn)")


def step_fix_hyphenation(md_path: Path) -> None:
    """Satır sonu heceleme tirelerini düzelt.
    
    PDF'lerde satır sonunda kelime sığmadığında tire ile bölünür:
      'popu-\nlerliğini' → 'popülerliğini'
      'bi-\nlimkurgu'   → 'bilimkurgu'
    
    Bu fonksiyon bu tireleri tespit edip kelimeleri birleştirir.
    """
    if not md_path.exists():
        print_warn("Markdown dosyası bulunamadı, heceleme düzeltmesi atlandı.")
        return

    content = md_path.read_text(encoding="utf-8")
    original_length = len(content)

    # Satır sonundaki heceleme tirelerini düzelt:
    # Bir harf + tire + satır sonu + küçük harf → kelimeleri birleştir
    # Örn: "popu-\nlerliğini" → "popülerliğini"
    fixed = re.sub(
        r'(\w)-\n(\s*)(\w)',
        lambda m: m.group(1) + m.group(3) if m.group(3).islower() else m.group(0),
        content
    )

    # Ayrıca satır içi kırık tireleri de düzelt:
    # "popu- lerliğini" → "popülerliğini" (tire + boşluk + küçük harf)
    fixed = re.sub(
        r'(\w)- (\w)',
        lambda m: m.group(1) + m.group(2) if m.group(2).islower() else m.group(0),
        fixed
    )

    fix_count = content.count('-\n') - fixed.count('-\n')
    
    md_path.write_text(fixed, encoding="utf-8")
    print_success(f"Heceleme tireleri düzeltildi ({fix_count} düzeltme yapıldı).")


def step_copy_images(images_dir: Path, media_dir: Path) -> None:
    """Resimleri media klasörüne kopyala."""
    if media_dir.exists():
        shutil.rmtree(media_dir)

    if images_dir.exists() and any(images_dir.iterdir()):
        shutil.copytree(images_dir, media_dir)
        image_count = len(list(media_dir.glob("*")))
        print_success(f"Resimler media klasörüne kopyalandı ({image_count} dosya).")
    else:
        media_dir.mkdir(parents=True, exist_ok=True)
        print_warn("Resim bulunamadı (metin-ağırlıklı PDF olabilir).")


def step_create_epub(md_path: Path, epub_path: Path, media_dir: Path, metadata: dict) -> None:
    """Markdown'dan EPUB oluştur (Pandoc ile)."""
    style_css = SCRIPT_DIR / "style.css"
    style_args = []
    if style_css.exists():
        print_success("style.css şablonu bulundu, uygulanıyor.")
        style_args = [f"--css={style_css}"]
    else:
        print_info("style.css bulunamadı, standart EPUB üretilecek.")

    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(epub_path),
        "--toc",
        "--toc-depth=3",
        f"--metadata=title:{metadata['title']}",
        f"--metadata=author:{metadata['author']}",
        f"--metadata=lang:{metadata['lang']}",
    ] + style_args

    if metadata.get("publisher"):
        cmd.append(f"--metadata=publisher:{metadata['publisher']}")

    if media_dir.exists():
        cmd.append(f"--extract-media={media_dir}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print_error(f"Pandoc hatası: {result.stderr}")
        sys.exit(1)

    size_mb = epub_path.stat().st_size / (1024 * 1024)
    print_success(f"EPUB oluşturuldu: {epub_path.name} ({size_mb:.1f} MB)")


def step_cleanup(md_path: Path, images_dir: Path, media_dir: Path) -> None:
    """Geçici dosyaları temizle (isteğe bağlı)."""
    answer = input("\nGeçici dosyalar (markdown, resimler) silinsin mi? (e/h) [h]: ").strip().lower()
    if answer == "e":
        if md_path.exists():
            md_path.unlink()
        if images_dir.exists():
            shutil.rmtree(images_dir)
        if media_dir.exists():
            shutil.rmtree(media_dir)
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        print_success("Geçici dosyalar temizlendi.")
    else:
        print_info(f"Markdown dosyası korundu: {md_path}")


# ============================================================
# Ana program
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="PDF dosyalarını yüksek kaliteli EPUB formatına dönüştürür.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python convert.py                                    # interaktif mod
  python convert.py input/kitap.pdf                    # tek dosya
  python convert.py input/kitap.pdf -o output/kitap.epub
  python convert.py input/kitap.pdf --title "Kitap" --author "Yazar"
        """,
    )
    parser.add_argument("pdf", nargs="?", help="Dönüştürülecek PDF dosyasının yolu")
    parser.add_argument("-o", "--output", help="Çıktı EPUB dosyasının yolu")
    parser.add_argument("--title", help="Kitap adı")
    parser.add_argument("--author", help="Yazar adı")
    parser.add_argument("--publisher", help="Yayınevi adı")
    parser.add_argument("--lang", default="tr", help="Dil kodu (varsayılan: tr)")
    parser.add_argument(
        "--ocr-size",
        default="gundam",
        choices=["tiny", "small", "base", "large", "gundam"],
        help="OCR model boyutu (varsayılan: gundam — en yüksek kalite)",
    )
    parser.add_argument("--dpi", type=int, default=300, help="DPI değeri (varsayılan: 300)")
    parser.add_argument("--no-cleanup", action="store_true", help="Temizleme sorusu sorma")

    args = parser.parse_args()

    # Başlık
    print_header("PDF → EPUB Dönüştürücü")

    # Adım 0: Kontroller
    print_step(0, 5, "Sistem kontrolleri yapılıyor...")
    check_cuda()
    if not check_pandoc():
        sys.exit(1)

    # PDF seç
    if args.pdf:
        pdf_path = Path(args.pdf).resolve()
        if not pdf_path.exists():
            print_error(f"PDF bulunamadı: {pdf_path}")
            sys.exit(1)
    else:
        pdf_path = select_pdf_interactive()

    # Metadata belirle
    if args.title:
        metadata = {
            "title": args.title,
            "author": args.author or "Bilinmiyor",
            "publisher": args.publisher or "",
            "lang": args.lang,
        }
    else:
        metadata = get_metadata_interactive(pdf_path.name)

    # Çıktı yollarını belirle
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in metadata["title"]).strip()
    epub_filename = f"{safe_title} - {metadata['author']}.epub" if metadata["author"] != "Bilinmiyor" else f"{safe_title}.epub"

    if args.output:
        epub_path = Path(args.output).resolve()
    else:
        epub_path = OUTPUT_DIR / epub_filename

    md_path = OUTPUT_DIR / f"{pdf_path.stem}_output.md"
    images_dir = OUTPUT_DIR / f"{pdf_path.stem}_images"
    media_dir = OUTPUT_DIR / f"{pdf_path.stem}_media"

    # Bilgi özeti
    print(f"\n  PDF    : \033[97m{pdf_path.name}\033[0m ({pdf_path.stat().st_size / (1024*1024):.1f} MB)")
    print(f"  EPUB   : \033[97m{epub_path.name}\033[0m")
    print(f"  Başlık : {metadata['title']}")
    print(f"  Yazar  : {metadata['author']}")
    if metadata.get("publisher"):
        print(f"  Yayınevi: {metadata['publisher']}")
    print(f"  OCR    : {args.ocr_size} | DPI: {args.dpi}")

    input("\n  Devam etmek için Enter'a basın (iptal: Ctrl+C)... ")

    # Adım 1: Modelleri indir
    print()
    print_step(1, 5, "OCR modelleri indiriliyor/kontrol ediliyor...")
    step_download_models()

    # Adım 2: PDF → Markdown
    print()
    print_step(2, 5, f"PDF → Markdown dönüşümü başlıyor...")
    step_convert_to_markdown(pdf_path, md_path, images_dir)

    # Adım 3: Heceleme tirelerini düzelt
    print()
    print_step(3, 6, "Heceleme tireleri düzeltiliyor...")
    step_fix_hyphenation(md_path)

    # Adım 4: Resimleri kopyala
    print()
    print_step(4, 6, "Resimler düzenleniyor...")
    step_copy_images(images_dir, media_dir)

    # Adım 5: Markdown → EPUB
    print()
    print_step(5, 6, "EPUB oluşturuluyor...")
    step_create_epub(md_path, epub_path, media_dir, metadata)

    # Adım 6: Temizlik
    print()
    print_step(6, 6, "Temizlik...")
    if not args.no_cleanup:
        step_cleanup(md_path, images_dir, media_dir)
    else:
        print_info("Temizlik atlandı (--no-cleanup).")

    # Sonuç
    print_header("Dönüşüm Tamamlandı!")
    print(f"  📖 EPUB dosyanız hazır:")
    print(f"  \033[97m{epub_path}\033[0m")
    print()


if __name__ == "__main__":
    main()
