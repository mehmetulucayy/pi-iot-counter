# Gerçek Zamanlı Yolcu Sayma Sistemi

YOLOv8 kişi tespiti ve DeepSORT nesne takibi kullanarak gerçek zamanlı video analizi için tasarlanmış yüksek performanslı, çok thread'li yolcu sayma sistemi. Opsiyonel bulut senkronizasyonu ile birlikte gelir.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Özellikler

- **Gerçek Zamanlı Tespit**: Yapılandırılabilir güven eşikleri ile YOLOv8 tabanlı kişi tespiti
- **Hassas Takip**: Sağlam çoklu nesne takibi için DeepSORT algoritması
- **Çizgi Geçiş Sayacı**: Çift yönlü destek ile yapılandırılabilir sayım çizgisi
- **Çok Thread'li Pipeline**: Kamera, tespit, takip ve kayıt için ayrı thread'lerle optimize edilmiş performans
- **Yerel Depolama**: Kalıcı sayım kayıtları için SQLite veritabanı
- **Günlük Kayıtlar**: Tarihe göre organize edilmiş otomatik metin logları
- **Opsiyonel Bulut Senkronizasyonu**: Uzaktan izleme için Firebase Realtime Database entegrasyonu
- **Canlı Görselleştirme**: Takip overlay'leri ve istatistikler ile gerçek zamanlı görüntüleme

## 🏗️ Mimari

Sistem aşağıdaki bileşenlerle **üretici-tüketici modeli** kullanır:

```
Kamera → Algılayıcı → Takipçi → [Ekran, Veritabanı, Logger, Firebase]
  ↓         ↓          ↓
Thread 1  Thread 2  Thread 3  → Thread 4-7
```

### Thread Pipeline

1. **CameraThread**: Kamera/dosyadan video karelerini yakalar
2. **DetectorThread**: Kişi tespiti için YOLOv8 çıkarımını çalıştırır
3. **TrackerThread**: DeepSORT takipçisini günceller ve çizgi geçişlerini sayar
4. **DBThread**: Sayım olaylarını SQLite veritabanına yazar
5. **DailyTextLoggerThread**: Günlük metin loglarını tutar
6. **FirebaseWriterThread**: Sayımları Firebase'e senkronize eder (opsiyonel)
7. **DisplayThread**: Gerçek zamanlı görselleştirme penceresi gösterir

## 📋 Gereksinimler

- Python 3.8+
- Webcam veya video dosyası kaynağı
- YOLOv8 model ağırlıkları

## 🚀 Kurulum

### 1. Repository'yi Klonlayın

```bash
git clone https://github.com/mehmetulucayy/pi-iot-counter.git
cd pi-iot-counter
```

### 2. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

**Firebase entegrasyonu için** (opsiyonel), `requirements.txt` içindeki satırın yorum işaretini kaldırın:
```bash
pip install firebase-admin
```

### 3. YOLOv8 Modelini İndirin

Bir YOLOv8 modeli indirin ve `models/` dizinine yerleştirin:

```bash
# YOLOv8 Nano (en hızlı, gerçek zamanlı için önerilir)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -P models/

# Veya YOLOv8 Small (daha doğru)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt -P models/
```

### 4. Uygulamayı Yapılandırın

Örnek yapılandırmayı kopyalayın:

```bash
cp config.example.yaml config.yaml
```

Kurulumunuza uyacak şekilde `config.yaml` dosyasını düzenleyin (kamera kaynağı, sayım çizgisi konumu, vb.)

## ⚙️ Yapılandırma

### Temel Yapılandırma (`config.yaml`)

```yaml
video:
  source: 0              # Webcam için 0, veya video dosyası yolu
  width: 1280
  height: 720
  show_window: true

counting:
  entry_line: [200, 500, 1080, 500]  # [x1, y1, x2, y2]
  direction: both                     # "up", "down", veya "both"
  recount_ttl_sec: 30                 # Aynı kişinin tekrar sayılmasını önle
```

### Opsiyonel: Firebase Kurulumu

Bulut senkronizasyonu istiyorsanız:

1. Environment template'ini kopyalayın:
   ```bash
   cp .env.example .env
   ```

2. Bir Firebase projesi oluşturun ve service account kimlik bilgilerini indirin

3. `.env` dosyasını düzenleyin:
   ```env
   ENABLE_FIREBASE=true
   FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com/
   FIREBASE_CREDENTIALS_FILE=firebase_credentials.json
   ```

4. `firebase_credentials.json` dosyanızı proje kök dizinine yerleştirin

### 🔑 Cihaz Kodu Sistemi

Sistem, **her cihaz için otomatik olarak benzersiz bir kod üretir**. İlk çalıştırmada:

1. 6 karakterlik rastgele bir cihaz kodu oluşturulur (örn: `A1B2C3`)
2. Bu kod `device_code.txt` dosyasına kaydedilir
3. Aynı kod sonraki tüm çalıştırmalarda kullanılır

**Neden önemli?**
- Her cihaz Firebase'de kendi verilerini **ayrı bir ID altında** saklar
- Birden fazla sayaç cihazını aynı Firebase projesinde kullanabilirsiniz
- Her cihazın sayımları birbirinden bağımsızdır: `kisi_sayimi/{device_code}/`

**Örnek Firebase yapısı (3 farklı cihaz):**
```
kisi_sayimi/
  ├── A1B2C3/              # Cihaz 1
  │   ├── anlik_sayi: 42
  │   └── daily_totals/...
  ├── D4E5F6/              # Cihaz 2
  │   ├── anlik_sayi: 28
  │   └── daily_totals/...
  └── G7H8I9/              # Cihaz 3
      ├── anlik_sayi: 15
      └── daily_totals/...
```

> **Not**: Cihaz kodunu manuel olarak değiştirmek isterseniz, `device_code.txt` dosyasını silin. Program yeni bir kod oluşturacaktır.


## 🎯 Kullanım

### Temel Kullanım

```bash
python main_deepsort_threaded.py
```

### Özel Yapılandırma ile

```bash
python main_deepsort_threaded.py --config my_config.yaml
```

### Video Dosyası ile

```bash
python main_deepsort_threaded.py --source video.mp4
```

### Klavye Kontrolleri

- **ESC**: Uygulamayı durdur

## 📊 Veri Depolama

### Yerel Veritabanı

Sayım olayları şu şema ile `db/passenger_count.db` içinde saklanır:

```sql
CREATE TABLE counts (
  id INTEGER PRIMARY KEY,
  ts INTEGER,           -- Unix zaman damgası
  track_id INTEGER,     -- Takip ID'si
  direction TEXT        -- 'up' veya 'down'
);
```

### Günlük Loglar

Metin logları `logs/YYYY-MM-DD.txt` formatında kaydedilir:

```
2025-12-06 14:23:45 - {"timestamp": 1733493825, "count": 15}
```

### Firebase Yapısı (etkinse)

```
kisi_sayimi/
  └── {device_code}/
      ├── anlik_sayi: 42              # Mevcut sayım
      └── daily_totals/
          └── 2025-12-06: 156         # Günlük toplam
```

## 🛠️ Özelleştirme

### Sayım Çizgisini Ayarlama

1. Uygulamayı çalıştırın ve video akışını gözlemleyin
2. Sayım çizgisini istediğiniz koordinatları not edin
3. `config.yaml` içinde `entry_line` değerini güncelleyin: `[x1, y1, x2, y2]`
4. Bu çizgiyi geçen kişiler sayılacaktır

### Algılama Parametreleri

- **conf_thres**: Yüksek = daha az yanlış pozitif, kişileri kaçırabilir (varsayılan: 0.35)
- **iou_thres**: Non-max suppression eşiği (varsayılan: 0.45)

### Takip Parametreleri

- **max_age**: Algılama olmadan bir takibi tutma süresi (kare sayısı) (varsayılan: 30)
- **n_init**: Bir takibi onaylamak için gereken algılama sayısı (varsayılan: 3)
- **nn_budget**: Görünüm özelliği veritabanı boyutu (varsayılan: 100)

## 🔍 Sorun Giderme

### Kamera Açılmıyor

- Config'deki `source` değerini kontrol edin (farklı kameralar için 0, 1, veya 2 deneyin)
- Kamera izinlerini doğrulayın
- Şununla test edin: `python -c "import cv2; print(cv2.VideoCapture(0).read())"`

### Düşük Kare Hızı

- Daha küçük bir YOLOv8 modeli kullanın (yolov8n.pt)
- Config'de video çözünürlüğünü azaltın
- CPU'nun aşırı yüklenmediğinden emin olun

### Yanlış Sayımlar

- Sayım çizgisi konumunu ayarlayın
- Tekrarlanan sayımları önlemek için `recount_ttl_sec` değerini artırın
- Daha iyi algılama için `conf_thres` değerini ayarlayın

### Firebase Bağlantı Sorunları

- `.env` içinde `ENABLE_FIREBASE=true` olduğunu doğrulayın
- Kimlik bilgileri dosya yolunu ve veritabanı URL'sini kontrol edin
- Firebase Realtime Database kurallarının yazma işlemine izin verdiğinden emin olun

## 📁 Proje Yapısı

```
pi-iot-counter/
├── main_deepsort_threaded.py    # Ana uygulama giriş noktası
├── firebase_manager.py           # Firebase entegrasyonu (opsiyonel)
├── config.yaml                   # Yapılandırma dosyası
├── requirements.txt              # Python bağımlılıkları
├── .env.example                  # Environment değişkenleri şablonu
├── .gitignore                    # Git ignore kalıpları
├── db/
│   ├── sqlite_logger.py         # Veritabanı işleyicisi
│   └── passenger_count.db       # SQLite veritabanı (çalışma zamanında oluşturulur)
├── tracker/
│   └── deep_sort_tracker.py     # DeepSORT wrapper
├── utils/
│   ├── pipeline.py              # Thread pipeline bileşenleri
│   ├── zone_counter.py          # Çizgi geçiş sayacı mantığı
│   └── draw.py                  # Görselleştirme araçları
├── models/
│   └── yolov8n.pt              # YOLOv8 modeli (ayrı olarak indirilir)
└── logs/                        # Günlük metin logları (çalışma zamanında oluşturulur)
```

## 🤝 Katkıda Bulunma

Katkılar memnuniyetle karşılanır! Lütfen bir Pull Request göndermekten çekinmeyin.

## 📝 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır - detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 🙏 Teşekkürler

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Nesne algılama
- [DeepSORT](https://github.com/nwojke/deep_sort) - Çoklu nesne takibi
- [deep-sort-realtime](https://github.com/levan92/deep_sort_realtime) - DeepSORT implementasyonu

## 📧 Destek

Sorunlar ve sorular için lütfen GitHub'da bir issue açın.

---

**Not**: Bu sistem bir çizgiyi geçen kişileri saymak için tasarlanmıştır. Doluluk sayımı veya bölge tabanlı analizler için sayım mantığında değişiklikler gerekecektir.
