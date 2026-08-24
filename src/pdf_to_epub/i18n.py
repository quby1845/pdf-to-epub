"""Small, dependency-free translations for the desktop interface."""

from __future__ import annotations

from typing import Literal

UiLanguage = Literal["tr", "en"]
DEFAULT_UI_LANGUAGE: UiLanguage = "en"
LANGUAGE_NAMES: dict[UiLanguage, str] = {"tr": "Türkçe", "en": "English"}


_TEXT: dict[str, dict[UiLanguage, str]] = {
    "tagline": {
        "tr": "Yerel OCR ile sade, güvenli ve okunabilir e-kitaplar",
        "en": "Clean, private, readable e-books with local OCR",
    },
    "privacy": {"tr": "Yerel ve gizli", "en": "Local and private"},
    "light_theme": {"tr": "Açık tema", "en": "Light theme"},
    "dark_theme": {"tr": "Koyu tema", "en": "Dark theme"},
    "hero_badge": {"tr": "YEREL OCR DÖNÜŞTÜRÜCÜ", "en": "LOCAL OCR CONVERTER"},
    "hero_title": {
        "tr": "PDF kitabınızı akıcı bir EPUB'a dönüştürün.",
        "en": "Turn your PDF book into a reflowable e-book.",
    },
    "hero_body": {
        "tr": (
            "Taranmış sayfaları cihazınızda okuyup satır sonlarını ve kelime "
            "bölünmelerini e-kitaba uygun biçimde düzenler."
        ),
        "en": (
            "Reads scanned pages on your device and repairs line endings and split words "
            "for comfortable e-book reading."
        ),
    },
    "feature_private": {"tr": "Dosya yüklemez", "en": "No uploads"},
    "feature_gpu": {"tr": "GPU destekli", "en": "GPU accelerated"},
    "feature_reader": {"tr": "E-okuyucu uyumlu", "en": "E-reader ready"},
    "step": {"tr": "ADIM {number}", "en": "STEP {number}"},
    "file_title": {"tr": "PDF dosyasını seçin", "en": "Choose a PDF file"},
    "file_hint": {
        "tr": "Dosyanız bilgisayarınızdan çıkmaz; işlem tamamen yerel yapılır.",
        "en": "Your file never leaves your computer; processing is entirely local.",
    },
    "choose_pdf": {"tr": "PDF seç", "en": "Choose PDF"},
    "details_title": {
        "tr": "Kitap bilgilerini kontrol edin",
        "en": "Review the book details",
    },
    "details_hint": {
        "tr": "Bu bilgiler e-kitap çıktısında ve kitaplığınızda görünür.",
        "en": "These details will appear in the e-book and your library.",
    },
    "book_title": {"tr": "Kitap adı", "en": "Book title"},
    "author": {"tr": "Yazar", "en": "Author"},
    "book_language": {"tr": "Dil", "en": "Book language"},
    "processing_mode": {"tr": "Sayfa işleme modu", "en": "Page processing mode"},
    "output_format": {"tr": "Çıktı biçimi", "en": "Output format"},
    "output_location": {
        "tr": "Çıktı dosyasının kaydedileceği yer",
        "en": "Output file location",
    },
    "change": {"tr": "Değiştir", "en": "Change"},
    "convert_title": {"tr": "Dönüştürmeyi başlatın", "en": "Start the conversion"},
    "convert_hint": {
        "tr": "Süre; sayfa sayısı, tarama kalitesi ve ekran kartına göre değişir.",
        "en": "Duration depends on the page count, scan quality, and graphics card.",
    },
    "ready_title": {
        "tr": "Her şey hazır olduğunda tek tıkla başlayın",
        "en": "Start with one click when everything is ready",
    },
    "ready_hint": {
        "tr": "İlerlemeyi sayfa sayfa burada görebilirsiniz.",
        "en": "Follow the conversion page by page here.",
    },
    "convert": {"tr": "Dönüştür", "en": "Convert"},
    "converting": {"tr": "Dönüştürülüyor…", "en": "Converting…"},
    "pause": {"tr": "Duraklat", "en": "Pause"},
    "resume": {"tr": "Devam et", "en": "Resume"},
    "retry": {"tr": "Tekrar dene", "en": "Try again"},
    "stage_model": {"tr": "Model hazırlanıyor", "en": "Preparing model"},
    "stage_pages": {"tr": "Sayfalar okunuyor", "en": "Reading pages"},
    "stage_output": {"tr": "Çıktı hazırlanıyor", "en": "Building output"},
    "open_output": {"tr": "Çıktıyı aç", "en": "Open output"},
    "open_folder": {"tr": "Klasörü aç", "en": "Open folder"},
    "send_to_koreader": {"tr": "KOReader'a gönder", "en": "Send to KOReader"},
    "send_file_to_koreader": {"tr": "Dosya gönder", "en": "Send a file"},
    "select_send_file_title": {
        "tr": "KOReader'a gönderilecek dosyayı seçin",
        "en": "Choose a file to send to KOReader",
    },
    "all_files": {"tr": "Tüm dosyalar", "en": "All files"},
    "koreader_title": {"tr": "KOReader'a gönder", "en": "Send to KOReader"},
    "koreader_body": {
        "tr": (
            "KOReader'da PDF to EPUB Receiver eklentisini başlatın. Aynı Wi-Fi ağındaki cihazlar "
            "otomatik olarak burada görünecektir. Her tür normal dosya aktarılabilir."
        ),
        "en": (
            "Start PDF to EPUB Receiver in KOReader. Devices on the same Wi-Fi network "
            "will appear here automatically. Any regular file can be transferred."
        ),
    },
    "koreader_selected_file": {
        "tr": "Gönderilecek dosya: {name} • {size}",
        "en": "File to send: {name} • {size}",
    },
    "koreader_devices": {"tr": "Bulunan cihazlar", "en": "Discovered devices"},
    "koreader_scanning": {"tr": "Cihazlar aranıyor…", "en": "Looking for devices…"},
    "koreader_none": {
        "tr": (
            "Henüz cihaz bulunamadı. KOReader'da PDF to EPUB Receiver'ı başlatıp yeniden tarayın."
        ),
        "en": "No device found yet. Start PDF to EPUB Receiver in KOReader, then scan again.",
    },
    "koreader_found": {"tr": "{count} cihaz bulundu.", "en": "Found {count} device(s)."},
    "koreader_manual": {"tr": "Elle IP adresi", "en": "Manual IP address"},
    "koreader_manual_hint": {"tr": "örn. 192.168.1.50", "en": "e.g. 192.168.1.50"},
    "koreader_pin": {"tr": "PIN (isteğe bağlı)", "en": "PIN (optional)"},
    "koreader_rescan": {"tr": "Yeniden tara", "en": "Scan again"},
    "koreader_plugin_help": {"tr": "Eklentiyi indir", "en": "Download plugin"},
    "koreader_send": {"tr": "Dosyayı gönder", "en": "Send file"},
    "koreader_close": {"tr": "Kapat", "en": "Close"},
    "koreader_select": {
        "tr": "Bir cihaz seçin veya IP adresini girin.",
        "en": "Select a device or enter its IP address.",
    },
    "koreader_connecting": {"tr": "KOReader'a bağlanılıyor…", "en": "Connecting to KOReader…"},
    "koreader_waiting": {
        "tr": "KOReader ekranındaki aktarım isteğini onaylayın…",
        "en": "Approve the transfer request on the KOReader screen…",
    },
    "koreader_sending": {
        "tr": "Dosya gönderiliyor… {percent}%",
        "en": "Sending file… {percent}%",
    },
    "koreader_sent": {
        "tr": "{name}, {device} cihazına başarıyla gönderildi.",
        "en": "Sent {name} to {device} successfully.",
    },
    "koreader_error": {"tr": "KOReader aktarım hatası", "en": "KOReader transfer error"},
    "initial_status": {"tr": "Bir PDF seçerek başlayın.", "en": "Start by choosing a PDF."},
    "no_pdf": {"tr": "Henüz PDF seçilmedi", "en": "No PDF selected yet"},
    "no_pdf_detail": {
        "tr": "Bilgisayarınızdan dönüştürmek istediğiniz kitabı seçin.",
        "en": "Choose the book you want to convert from your computer.",
    },
    "unknown_author": {"tr": "Bilinmiyor", "en": "Unknown"},
    "select_pdf_title": {
        "tr": "Dönüştürülecek PDF'yi seçin",
        "en": "Choose the PDF to convert",
    },
    "pdf_files": {"tr": "PDF dosyaları", "en": "PDF files"},
    "pdf_ready": {
        "tr": "PDF hazır. Kitap bilgilerini kontrol edip dönüştürmeyi başlatın.",
        "en": "PDF ready. Review the book details and start the conversion.",
    },
    "save_output": {"tr": "Çıktı dosyasını kaydet", "en": "Save output file"},
    "epub_files": {"tr": "EPUB dosyaları", "en": "EPUB files"},
    "markdown_files": {"tr": "Markdown dosyaları", "en": "Markdown files"},
    "mobi_files": {"tr": "MOBI dosyaları", "en": "MOBI files"},
    "missing_info": {"tr": "Eksik bilgi", "en": "Missing information"},
    "file_exists_title": {"tr": "Dosya zaten var", "en": "File already exists"},
    "file_exists_body": {
        "tr": "Aynı isimde bir çıktı dosyası var. Üzerine yazılsın mı?",
        "en": "An output file with the same name already exists. Overwrite it?",
    },
    "checking_system": {
        "tr": "Sistem gereksinimleri kontrol ediliyor…",
        "en": "Checking system requirements…",
    },
    "warning_prefix": {"tr": "Uyarı: {message}", "en": "Warning: {message}"},
    "low_vram": {"tr": "Düşük ekran kartı belleği", "en": "Low graphics memory"},
    "paused_status": {
        "tr": "Dönüştürme duraklatıldı. Devam et düğmesiyle aynı yerden sürdürebilirsiniz.",
        "en": "Conversion paused. Select Resume to continue from the same place.",
    },
    "success": {
        "tr": "Hazır! {format} {minutes:.1f} dakikada oluşturuldu.",
        "en": "Done! {format} was created in {minutes:.1f} minutes.",
    },
    "failed_status": {
        "tr": "Dönüştürme tamamlanamadı: {message}",
        "en": "Conversion failed: {message}",
    },
    "log_hint": {"tr": "Ayrıntılı günlük: {path}", "en": "Detailed log: {path}"},
    "conversion_error": {"tr": "Dönüştürme hatası", "en": "Conversion error"},
}


def normalize_ui_language(value: str) -> UiLanguage:
    """Return a supported language code with a stable English fallback."""
    normalized = value.strip().casefold()
    return "tr" if normalized.startswith("tr") else "en"


def translate(language: str, key: str, **values: object) -> str:
    """Translate a desktop string and interpolate named values."""
    normalized = normalize_ui_language(language)
    translated = _TEXT[key][normalized]
    return translated.format(**values) if values else translated
