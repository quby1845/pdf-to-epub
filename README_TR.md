# PDF to EPUB OCR — Türkçe kolay kullanım

Taranmış PDF kitapları, yazı boyutu değiştirilebilen ve e-kitap okuyucularda rahat kullanılan
EPUB dosyalarına dönüştürür. OCR işlemi kendi bilgisayarınızda yapılır; kitabın sayfaları bir
metin API'sine gönderilmez.

> [!IMPORTANT]
> Program şu anda alfa sürümündedir. Oluşan EPUB'ı mutlaka kontrol edin ve kaynak PDF'yi
> saklayın. Yalnızca dönüştürme hakkınız bulunan belgeleri kullanın.

## Bilgisayarım uygun mu?

- Windows 10 veya Windows 11
- Python 3.11–3.13 (yoksa kolay kurulum yüklemeyi dener)
- NVIDIA ekran kartı; `gundam` modeli için 8 GB VRAM önerilir
- En az 16 GB RAM ve yaklaşık 10 GB boş alan
- İlk kurulum ve ilk model indirmesi için internet bağlantısı

NVIDIA ekran kartınız yoksa dönüşüm çok yavaş olabilir veya hiç çalışmayabilir. Bu sürümde CPU
ile dönüşüm resmî olarak desteklenmemektedir.

## Üç adımda kurulum

1. [Son sürüm sayfasını](https://github.com/quby1845/pdf-to-epub/releases/latest) açın ve adı
   **`windows-easy-start.zip`** ile biten dosyayı indirin.
2. ZIP dosyasına sağ tıklayıp **Tümünü ayıkla** seçeneğini kullanın. Programı ZIP'in içinden
   çalıştırmayın.
3. Ayıklanan klasörde **`KURULUM.bat`** dosyasına çift tıklayın.

Windows koruma uyarısı gösterirse yalnızca bu GitHub deposundan indirdiğinizi doğruladıktan sonra
**Daha fazla bilgi → Yine de çalıştır** yolunu kullanın. Kurulum; Python, CUDA destekli PyTorch,
Pandoc, Poppler ve programın bağımlılıklarını hazırlar. İnternet hızına göre 10–30 dakika
sürebilir; masaüstüne ve Başlat menüsüne **PDF to EPUB OCR** kısayolu ekler.

## Docker ile kurulum (isteğe bağlı)

Docker; Python, CUDA kütüphaneleri, Pandoc, Poppler ve programı tek bir yalıtılmış ortamda kurar.
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

## EPUB oluşturma

1. Masaüstündeki veya Başlat menüsündeki **PDF to EPUB OCR** kısayolunu açın. Kurulumdan sonra
   komut penceresi görünmez; program normal bir Windows uygulaması olarak açılır.
2. **PDF seç** düğmesiyle kitabınızı seçin.
3. Kitap adı, yazar ve dili kontrol edin.
4. OCR modeli olarak önce **large — dengeli** seçeneğini deneyin.
5. **EPUB'a Dönüştür** düğmesine basın.

Sağ üstteki **Koyu tema** düğmesiyle görünümü değiştirebilirsiniz. Seçiminiz hatırlanır ve program
bir sonraki açılışta aynı temayı kullanır. Dönüşüm sürerken yanlışlıkla arayüzü yenilememek için
tema düğmesi işlem bitene kadar geçici olarak kilitlenir.

Modern arayüzde her adım ve işlem için açık/koyu temaya uyumlu simgeler bulunur. PDF seçildiğinde
dosya adı, boyutu ve bulunduğu klasör tek bakışta gösterilir. Bu simgeler programla birlikte gelir;
arayüz açılırken internetten hiçbir görsel indirilmez.

İlk dönüşümde OCR modeli indirileceği için ilerleme bir süre aynı yerde görünebilir. Program
bittiğinde EPUB varsayılan olarak PDF'nin bulunduğu klasöre kaydedilir. Sayfa okuma başlayınca
program toplam sayfa sayısını, o anda okunan sayfayı ve tamamlanma yüzdesini canlı gösterir.

Program PDF'de satır sonunda bölünmüş `bit-miş` gibi Türkçe kelimeleri EPUB oluşturulurken
otomatik olarak birleştirir. Gerçek tireli `e-posta` benzeri sözcükleri korumaya çalışır; OCR
sonucu belgeye göre değişebileceği için oluşan EPUB'ı yine de gözden geçirin.

## Hangi OCR modelini seçmeliyim?

| Model | Ne zaman kullanılır? |
| --- | --- |
| `small` | Düşük ekran kartı belleği; kalite daha düşük olabilir |
| `base` | Bellek hatası alan bilgisayarlar |
| `large` | Çoğu kullanıcı için dengeli ve önerilen başlangıç |
| `gundam` | 8 GB veya daha fazla VRAM ile en yüksek kalite |

## Sorun yaşarsanız

| Sorun | Çözüm |
| --- | --- |
| Kurulum yarıda kaldı | `KURULUM.bat` dosyasını yeniden çalıştırın |
| Ekran kartı belleği hatası | Modeli `base` veya `small` seçin; diğer GPU uygulamalarını kapatın |
| Pandoc/PyTorch bulunamadı | Kurulumu yeniden çalıştırın ve bilgisayarı yeniden başlatın |
| EPUB zaten var | Farklı kayıt adı seçin veya üzerine yazmayı onaylayın |
| OCR hataları var | Daha temiz tarama veya daha güçlü model deneyin |

Devam eden bir sorun için [hata bildirimi açabilirsiniz](https://github.com/quby1845/pdf-to-epub/issues/new/choose).
Telifli ya da özel PDF dosyalarını hata bildirimine yüklemeyin; sorunu tarif edin veya herkese açık
küçük bir örnek kullanın.

## Gizlilik

PDF içeriği bilgisayarınızda işlenir. İlk kullanımda model dosyaları indirilebilir; bu indirme
belgenizin içeriğini göndermez. Kullanılan açık kaynak bileşenler ve ayrıntılı teknik bilgiler için
[ana README dosyasına](README.md) bakabilirsiniz.
