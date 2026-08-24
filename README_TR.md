# PDF to EPUB OCR — Türkçe kolay kullanım

Taranmış PDF kitapları; yazı boyutu değiştirilebilen EPUB, düzenlenebilir Markdown veya eski
Kindle cihazları için MOBI dosyalarına dönüştürür. OCR işlemi kendi bilgisayarınızda yapılır;
kitabın sayfaları bir metin API'sine gönderilmez.

> [!IMPORTANT]
> Program şu anda alfa sürümündedir. Oluşan EPUB'ı mutlaka kontrol edin ve kaynak PDF'yi
> saklayın. Yalnızca dönüştürme hakkınız bulunan belgeleri kullanın.

## Bilgisayarım uygun mu?

- Windows 10 veya Windows 11
- Python 3.11–3.13 (yoksa kolay kurulum yüklemeyi dener)
- Desteklenen NVIDIA CUDA veya AMD ROCm ekran kartı; pratik alt sınır 8 GB VRAM
- En az 16 GB RAM ve yaklaşık 20 GB boş alan
- İlk kurulum ve ilk model indirmesi için internet bağlantısı

Program CPU ile dönüşümü desteklemez. NVIDIA kartlar CUDA, desteklenen AMD kartlar ROCm kullanır.
6 GB kartlar mevcut sıkıştırılmamış modeli güvenilir biçimde çalıştıramaz. 8 GB kartlarda diğer
GPU uygulamalarını kapatmak gerekebilir; daha fazla VRAM daha
rahat çalışır. Arayüzdeki sayfa işleme modu 6,5 GB model indirmesinin ve ana modelin bellekteki
boyutunu değil, sayfaların işlenme çözünürlüğünü, kırpma yöntemini ve ek çalışma belleğini
değiştirir.

## Windows Setup ile üç adımda kurulum

1. [Son sürüm sayfasını](https://github.com/quby1845/pdf-to-epub/releases/latest) açın ve adı
   **`windows-setup.exe`** ile biten dosyayı indirin.
2. Setup dosyasını açıp İngilizce kurulum sihirbazındaki adımları izleyin.
3. Kurulum bitince masaüstünden veya Başlat menüsünden **PDF to EPUB OCR** uygulamasını açın.

Windows koruma uyarısı gösterirse yalnızca bu GitHub deposundan indirdiğinizi doğruladıktan sonra
**Daha fazla bilgi → Yine de çalıştır** yolunu kullanın. Kurulum; Python, CUDA destekli PyTorch,
Pandoc, Poppler, MOBI için Calibre ve programın bağımlılıklarını hazırlar. İnternet hızına göre
10–30 dakika
sürebilir; masaüstüne ve Başlat menüsüne **PDF to EPUB OCR** kısayolu ekler. Python ortamı
`%LOCALAPPDATA%\PDF-to-EPUB-OCR\venv` konumuna kurulur. Kurulum yarıda kalırsa Başlat menüsündeki
**PDF to EPUB OCR Maintenance** aracından **Repair** seçeneğini kullanın. Araç bozuk ortamı gerçek
içe aktarma ve GPU testiyle algılayıp yeniden oluşturur. Aynı merkezden SHA-256 doğrulamalı
güncelleme kontrolü ve kaldırma işlemi de yapılabilir.
RTX 50 serisinde `sm_120` destekli CUDA 13 paketi otomatik seçilir; çalışan RTX 30/40 kurulumu
gereksiz yere değiştirilmez.

AMD desteği şimdilik beta durumundadır. Windows 11, Python 3.12 ve Radeon sürücüsü 26.2.2
gerektirir. Resmi Windows ROCm 7.2.1 listesinde şu kartlar bulunur: RX 9070, RX 9070 XT,
AI PRO R9700, RX 9060 XT, RX 7900 XTX, PRO W7900, PRO W7900 Dual Slot ve RX 7700. Kurulum ekran
kartını otomatik algılar; listede olmayan AMD kartta yanlış paket kurmak yerine anlaşılır hata
verir. PyTorch AMD'de de `torch.cuda` ad alanını kullandığı için bu isim loglarda görülebilir.
Kurulum, gerçek GPU tensörü çalıştırmadan tamamlandı sayılmaz. Güncel liste için AMD'nin
[Windows uyumluluk tablosuna](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html)
bakabilirsiniz.

## Docker ile kurulum (isteğe bağlı)

Docker; Python, CUDA kütüphaneleri, Pandoc, Poppler, Calibre ve programı tek bir yalıtılmış
ortamda kurar.
Bu yöntem masaüstü arayüzünü değil, komut satırı sürümünü çalıştırır. Normal Windows kullanıcısı
için yukarıdaki `KURULUM.bat` yöntemi daha kolaydır.

Gerekenler:

- Güncel sürücülü bir NVIDIA ekran kartı
- Windows'ta WSL 2 altyapısıyla çalışan Docker Desktop veya Linux'ta Docker Engine ve NVIDIA
  Container Toolkit
- Docker Compose v2 ve en az 10 GB boş alan

Önce projeyi indirip Docker imajını bir kez oluşturun:

```powershell
git clone https://github.com/quby1845/pdf-to-epub.git
cd pdf-to-epub
docker compose build
```

PDF dosyanızı projenin `input` klasörüne koyun. Rehberli kullanım için şu komutu çalıştırın:

```powershell
docker compose run --rm converter
```

Tek komutla doğrudan dönüştürmek isterseniz:

```powershell
docker compose run --rm converter `
  "input/kitap.pdf" `
  --output "output/kitap.epub" `
  --title "Kitap Adı" `
  --author "Yazar Adı" `
  --lang tr `
  --ocr-size large `
  --yes
```

Oluşan EPUB bilgisayarınızdaki `output` klasörüne yazılır. OCR modeli Docker'ın kalıcı `models`
alanında saklandığı için her dönüşümde yeniden indirilmez. GPU'nun container içinde görüldüğünü
şöyle kontrol edebilirsiniz:

```powershell
docker compose run --rm --entrypoint python converter `
  -c "import torch; print('CUDA kullanılabilir:', torch.cuda.is_available())"
```

`docker compose down` model önbelleğini silmez. İndirilen modelleri de özellikle kaldırmak
isterseniz `docker compose down --volumes` kullanın.

## EPUB, Markdown veya MOBI oluşturma

1. Masaüstündeki veya Başlat menüsündeki **PDF to EPUB OCR** kısayolunu açın. Kurulumdan sonra
   komut penceresi görünmez; program normal bir Windows uygulaması olarak açılır.
2. **PDF seç** düğmesiyle kitabınızı seçin.
3. Kitap adı, yazar ve dili kontrol edin.
4. **Çıktı biçimi** alanından EPUB, Markdown veya MOBI seçin.
5. **Sayfa işleme modu** olarak önce **large — dengeli** seçeneğini deneyin.
6. **Dönüştür** düğmesine basın.

EPUB çoğu telefon, tablet ve güncel e-kitap okuyucu için önerilen biçimdir. Markdown seçildiğinde
düzenlenebilir `.md` dosyası ile görseller için aynı klasörde `<kitap_adı>_assets` klasörü
oluşturulur. MOBI, eski Kindle cihazları veya eski iş akışları içindir ve Calibre bileşenini
kullanır. EPUB ve MOBI çıktılarında PDF'nin ilk sayfası kırpılmadan, tam sayfa kapak olarak
eklenir.

Sağ üstteki **Koyu tema** düğmesiyle görünümü değiştirebilirsiniz. Seçiminiz hatırlanır ve program
bir sonraki açılışta aynı temayı kullanır. Dönüşüm sürerken yanlışlıkla arayüzü yenilememek için
tema düğmesi işlem bitene kadar geçici olarak kilitlenir.

Üst bölümdeki **English / Türkçe** düğmesi arayüzün tamamını anında değiştirir. Dosya pencereleri,
model açıklamaları, ilerleme bilgileri ve hata mesajları da seçilen dile çevrilir. Dil seçimi
hatırlanır ve uygulama bir sonraki açılışta aynı dili kullanır. Yeni kurulumlar küresel kullanım
için İngilizce arayüzle başlar; Türkçe düğmeyle anında seçilebilir.

Modern arayüzde her adım ve işlem için açık/koyu temaya uyumlu simgeler bulunur. PDF seçildiğinde
dosya adı, boyutu ve bulunduğu klasör tek bakışta gösterilir. Bu simgeler programla birlikte gelir;
arayüz açılırken internetten hiçbir görsel indirilmez.

İlk dönüşümde OCR modeli indirileceği için ilerleme bir süre aynı yerde görünebilir. Program
bittiğinde seçilen çıktı varsayılan olarak PDF'nin bulunduğu klasöre kaydedilir. Sayfa okuma başlayınca
program toplam sayfa sayısını, o anda okunan sayfayı ve tamamlanma yüzdesini canlı gösterir.
İlk sayfada PDF hazırlama, modelin GPU'ya yüklenmesi ve OCR aşamaları ayrı mesajlarla belirtilir.
Üç sayfa tamamlandıktan sonra tahmini kalan süre de gösterilir ve her sayfada yeniden hesaplanır.
Bir hata olursa pencere ayrıntılı tanı günlüğünün konumunu da gösterir.

Sayfa okunurken **Duraklat** düğmesi kullanılabilir. Program çalışan kısa OCR adımının güvenli
noktasında beklemeye geçer; tamamlanan sayfalar silinmez ve model ekran kartı belleğinde kalır.
**Devam et** düğmesine basınca aynı dönüşüm kaldığı yerden sürer. Duraklatılan süre, tahmini kalan
süre hesabına eklenmez. Bu özellik özellikle uzun kitaplarda bilgisayara soğuma fırsatı vermek
içindir; duraklatma sırasında VRAM boşaltılmaz.

Program PDF'de satır sonunda bölünmüş `bit-miş` gibi Türkçe kelimeleri EPUB oluşturulurken
otomatik olarak birleştirir. Gerçek tireli `e-posta` benzeri sözcükleri korumaya çalışır; OCR
sonucu belgeye göre değişebileceği için oluşan EPUB'ı yine de gözden geçirin.

OCR normal bir paragrafı yanlışlıkla çoğu hücresi boş veya `None` olan bir tabloya dönüştürürse
program bu belirgin hatayı düz metne çevirir. Gerçek veri tabloları korunur; karmaşık sayfa düzenleri
için son çıktıyı yine de kontrol edin.

## Hangi sayfa işleme modunu seçmeliyim?

| Model | İşleme boyutu | Tahmini toplam VRAM | Ne zaman kullanılır? |
| --- | ---: | ---: | --- |
| `tiny` | 512 px | ≈7 GB | En hızlı deneme; küçük yazılarda kalite düşebilir |
| `small` | 640 px | ≈7,5 GB | Temiz ve kolay taramalarda daha hızlı seçenek |
| `base` | 1024 px | ≈8 GB | Temiz taramalar ve 8 GB kartlar için güvenli seçim |
| `large` | 1280 px | ≈8 GB+ | Çoğu kullanıcı için dengeli ve önerilen başlangıç |
| `gundam` | 1024/640 px, kırpma | ≈10 GB+ | Zor sayfalarda yüksek kalite; tüketim değişkendir |

Bu rakamlar kesin ölçüm değil, seçim yapmayı kolaylaştıran yaklaşık tepe tüketim tahminleridir.
Beş seçenek de yaklaşık 6,5 GB'lık aynı ana modeli kullanır. Sayfa içeriği, kırpma sayısı, diğer
GPU programları, PyTorch ve sürücü sürümü gerçek tüketimi değiştirebilir.

## Sorun yaşarsanız

| Sorun | Çözüm |
| --- | --- |
| Kurulum yarıda kaldı | Maintenance Center içinden **Repair** seçin |
| `[WinError 206]` | Ortam kısa kullanıcı yoluna kurulur; Maintenance Center içinden **Repair** seçin |
| `[WinError 1314]` | Son sürüm model cache'inde symlink yerine normal kopya kullanır; yönetici/Developer Mode gerekmez |
| RTX 50 / `no kernel image` | **Repair** seçin; kurulum CUDA 13 + `sm_120` paketini seçer |
| Desteklenmeyen AMD ekran kartı | Kartınızı AMD'nin Windows ROCm 7.2.1 uyumluluk listesinde kontrol edin |
| AMD ROCm kurulumu başarısız | Windows 11, Python 3.12 ve Radeon sürücüsü 26.2.2 kullandığınızı doğrulayın |
| 6 GB VRAM | Mevcut 6,5 GB ana model sığmaz; Tiny/Small bunu küçültmez |
| 8 GB ve üzeri bellek hatası | Diğer GPU uygulamalarını kapatın; sayfa yükü için `base` veya `small` deneyin |
| Pandoc/PyTorch bulunamadı | Kurulumu yeniden çalıştırın ve bilgisayarı yeniden başlatın |
| MOBI için Calibre bulunamadı | Maintenance Center içinden **Repair** seçin |
| `Failed to extract page 1 layout at stage 1` | Son sürümü kurun; gösterilen ayrıntılı CUDA hatasıyla birlikte ekran kartı modeli ve VRAM miktarını bildirin |
| Çıktı zaten var | Farklı kayıt adı seçin veya üzerine yazmayı onaylayın |
| OCR hataları var | Daha temiz tarama veya daha güçlü model deneyin |

Devam eden bir sorun için [hata bildirimi açabilirsiniz](https://github.com/quby1845/pdf-to-epub/issues/new/choose).
Telifli ya da özel PDF dosyalarını hata bildirimine yüklemeyin; sorunu tarif edin veya herkese açık
küçük bir örnek kullanın.

## Gizlilik

PDF içeriği bilgisayarınızda işlenir. İlk kullanımda 6,5 GB model dosyası indirilir ve sonraki
denemelerde önbellekten kullanılır. `snapshots` ve `blobs` klasörleri aynı önbellek dosyasını iki
farklı görünümde gösterebilir; bunları elle değiştirmeyin. Windows'ta snapshot dosyaları normal
kopya olarak hazırlanır; `.ipynb_checkpoints` ve `README-checkpoint.md` gibi model için gereksiz
dosyalar dönüşüm ön koşulu değildir. Bu indirme belgenizin içeriğini göndermez.
Kullanılan açık kaynak bileşenler ve ayrıntılı teknik bilgiler için
[ana README dosyasına](README.md) bakabilirsiniz.
