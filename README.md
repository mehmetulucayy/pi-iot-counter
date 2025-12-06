# Real-Time Passenger Counting System

A high-performance, multi-threaded passenger counting system using YOLOv8 for person detection and DeepSORT for object tracking. Designed for real-time video analysis with optional cloud synchronization.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **Real-Time Detection**: YOLOv8-based person detection with configurable confidence thresholds
- **Accurate Tracking**: DeepSORT algorithm for robust multi-object tracking
- **Line Crossing Counter**: Configurable counting line with bidirectional support
- **Multi-Threaded Pipeline**: Optimized performance with separate threads for camera, detection, tracking, and logging
- **Local Storage**: SQLite database for persistent count records
- **Daily Logging**: Automatic text logs organized by date
- **Optional Cloud Sync**: Firebase Realtime Database integration for remote monitoring
- **Live Visualization**: Real-time display with tracking overlays and statistics

## 🏗️ Architecture

The system uses a **producer-consumer pattern** with the following components:

```
Camera → Detector → Tracker → [Display, Database, Logger, Firebase]
  ↓         ↓         ↓
Thread 1  Thread 2  Thread 3  → Threads 4-7
```

### Thread Pipeline

1. **CameraThread**: Captures video frames from camera/file
2. **DetectorThread**: Runs YOLOv8 inference for person detection
3. **TrackerThread**: Updates DeepSORT tracker and counts line crossings
4. **DBThread**: Writes count events to SQLite database
5. **DailyTextLoggerThread**: Maintains daily text logs
6. **FirebaseWriterThread**: Syncs counts to Firebase (optional)
7. **DisplayThread**: Shows real-time visualization window

## 📋 Requirements

- Python 3.8+
- Webcam or video file source
- YOLOv8 model weights

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd yolcu_sayma_deepsort_threaded
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**For Firebase integration** (optional), uncomment the line in `requirements.txt`:
```bash
pip install firebase-admin
```

### 3. Download YOLOv8 Model

Download a YOLOv8 model and place it in the `models/` directory:

```bash
# YOLOv8 Nano (fastest, recommended for real-time)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -P models/

# Or YOLOv8 Small (more accurate)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt -P models/
```

### 4. Configure the Application

Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to match your setup (camera source, counting line position, etc.)

## ⚙️ Configuration

### Basic Configuration (`config.yaml`)

```yaml
video:
  source: 0              # 0 for webcam, or path to video file
  width: 1280
  height: 720
  show_window: true

counting:
  entry_line: [200, 500, 1080, 500]  # [x1, y1, x2, y2]
  direction: both                     # "up", "down", or "both"
  recount_ttl_sec: 30                 # Prevent recounting same person
```

### Optional: Firebase Setup

If you want cloud synchronization:

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Create a Firebase project and download service account credentials

3. Edit `.env`:
   ```env
   ENABLE_FIREBASE=true
   FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com/
   FIREBASE_CREDENTIALS_FILE=firebase_credentials.json
   ```

4. Place your `firebase_credentials.json` file in the project root

## 🎯 Usage

### Basic Usage

```bash
python main_deepsort_threaded.py
```

### With Custom Configuration

```bash
python main_deepsort_threaded.py --config my_config.yaml
```

### With Video File

```bash
python main_deepsort_threaded.py --source video.mp4
```

### Keyboard Controls

- **ESC**: Stop the application

## 📊 Data Storage

### Local Database

Count events are stored in `db/passenger_count.db` with schema:

```sql
CREATE TABLE counts (
  id INTEGER PRIMARY KEY,
  ts INTEGER,           -- Unix timestamp
  track_id INTEGER,     -- Tracker ID
  direction TEXT        -- 'up' or 'down'
);
```

### Daily Logs

Text logs are saved in `logs/YYYY-MM-DD.txt`:

```
2025-12-06 14:23:45 - {"timestamp": 1733493825, "count": 15}
```

### Firebase Structure (if enabled)

```
kisi_sayimi/
  └── {device_code}/
      ├── anlik_sayi: 42              # Current count
      └── daily_totals/
          └── 2025-12-06: 156         # Daily total
```

## 🛠️ Customization

### Adjusting the Counting Line

1. Run the application and observe the video feed
2. Note the coordinates where you want the counting line
3. Update `entry_line` in `config.yaml`: `[x1, y1, x2, y2]`
4. People crossing this line will be counted

### Detection Parameters

- **conf_thres**: Higher = fewer false positives, may miss people (default: 0.35)
- **iou_thres**: Non-max suppression threshold (default: 0.45)

### Tracking Parameters

- **max_age**: Frames to keep a track without detection (default: 30)
- **n_init**: Detections needed to confirm a track (default: 3)
- **nn_budget**: Appearance feature database size (default: 100)

## 🔍 Troubleshooting

### Camera Not Opening

- Check `source` in config (try 0, 1, or 2 for different cameras)
- Verify camera permissions
- Test with: `python -c "import cv2; print(cv2.VideoCapture(0).read())"`

### Low Frame Rate

- Use a smaller YOLOv8 model (yolov8n.pt)
- Reduce video resolution in config
- Ensure CPU is not overloaded

### Incorrect Counts

- Adjust counting line position
- Increase `recount_ttl_sec` to prevent duplicate counts
- Tune `conf_thres` for better detection

### Firebase Connection Issues

- Verify `ENABLE_FIREBASE=true` in `.env`
- Check credentials file path and database URL
- Ensure Firebase Realtime Database rules allow writes

## 📁 Project Structure

```
yolcu_sayma_deepsort_threaded/
├── main_deepsort_threaded.py    # Main application entry point
├── firebase_manager.py           # Firebase integration (optional)
├── config.yaml                   # Configuration file
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore patterns
├── db/
│   ├── sqlite_logger.py         # Database handler
│   └── passenger_count.db       # SQLite database (created at runtime)
├── tracker/
│   └── deep_sort_tracker.py     # DeepSORT wrapper
├── utils/
│   ├── pipeline.py              # Thread pipeline components
│   ├── zone_counter.py          # Line crossing counter logic
│   └── draw.py                  # Visualization utilities
├── models/
│   └── yolov8n.pt              # YOLOv8 model (download separately)
└── logs/                        # Daily text logs (created at runtime)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection
- [DeepSORT](https://github.com/nwojke/deep_sort) - Multi-object tracking
- [deep-sort-realtime](https://github.com/levan92/deep_sort_realtime) - DeepSORT implementation

## 📧 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: This system is designed for counting people crossing a line. For occupancy counting or zone-based analytics, modifications to the counting logic will be needed.
