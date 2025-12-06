import argparse
import time
import cv2
import yaml
from datetime import datetime, date
from utils.pipeline import (
    CameraThread, DetectorThread, TrackerThread, DBThread, DisplayThread, StopSignal
)
from db.sqlite_logger import SQLiteLogger
from utils.zone_counter import LineCounter
from tracker.deep_sort_tracker import DeepSortWrapper
from ultralytics import YOLO
import threading
import queue
import os

from firebase_manager import FirebaseWriterThread, initialize_firebase, get_device_code

# ------------------ Günlük TXT Logger ------------------
class DailyTextLoggerThread(threading.Thread):
    def __init__(self, in_q, stop, folder="logs"):
        super().__init__()
        self.in_q = in_q
        self.stop = stop
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.current_date = date.today()
        self.file = open(self._get_filename(), "a", encoding="utf-8")

    def _get_filename(self):
        return os.path.join(self.folder, f"{self.current_date}.txt")

    def run(self):
        while not self.stop.is_set():
            try:
                data = self.in_q.get(timeout=0.1)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.file.write(f"{now} - {data}\n")
                self.file.flush()
                if date.today() != self.current_date:
                    self.file.close()
                    self.current_date = date.today()
                    self.file = open(self._get_filename(), "a", encoding="utf-8")
            except queue.Empty:
                continue
        self.file.close()


# ------------------ Config Yükleme ------------------
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="config.yaml")
    ap.add_argument("--source", type=str, default=None)
    return ap.parse_args()


# ------------------ Ana Fonksiyon ------------------
def main():
    args = parse_args()
    cfg = load_config(args.config)

    # Initialize Firebase (optional)
    firebase_enabled = initialize_firebase()

    # Get device code
    device_code = get_device_code()
    print(f"📌 Device pairing code: {device_code}")

    # Kamera ve model hazırlığı
    src = args.source if args.source is not None else cfg["video"]["source"]
    cap = cv2.VideoCapture(int(src) if str(src).isdigit() else src)
    if cfg["video"].get("width"):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["video"]["width"])
    if cfg["video"].get("height"):
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["video"]["height"])

    model = YOLO(cfg["yolo"]["weights"])
    tracker_impl = DeepSortWrapper(
        max_age=cfg["deepsort"]["max_age"],
        n_init=cfg["deepsort"]["n_init"],
        nn_budget=cfg["deepsort"]["nn_budget"],
    )
    x1, y1, x2, y2 = cfg["counting"]["entry_line"]
    counter = LineCounter(
        (x1, y1), (x2, y2),
        direction=cfg["counting"]["direction"],
        recount_ttl_sec=int(cfg["counting"]["recount_ttl_sec"])
    )

    db_logger = SQLiteLogger(cfg["database"]["path"])
    db_logger.init_schema()

    stop = StopSignal()

    # Kuyruklar
    txt_log_q = queue.Queue()
    firebase_q = queue.Queue()

    # Threadler
    cam_t = CameraThread(cap, stop)
    det_t = DetectorThread(
        model, stop,
        conf=float(cfg["yolo"]["conf_thres"]),
        iou=float(cfg["yolo"]["iou_thres"]),
        classes=cfg["yolo"]["classes"]
    )
    trk_t = TrackerThread(tracker_impl, counter, stop)
    sqlite_db_t = DBThread(db_logger, stop)
    txt_logger_t = DailyTextLoggerThread(txt_log_q, stop, folder="logs")
    disp_t = DisplayThread(stop, show=cfg["video"].get("show_window", True))

    # Firebase Writer (writes to fixed device code if enabled)
    firebase_writer_t = FirebaseWriterThread(firebase_q, stop, device_code, enabled=firebase_enabled)

    # Kuyruk bağlantıları
    cam_t.out_q = det_t.in_q
    det_t.out_q = trk_t.in_q
    trk_t.out_frame_q = disp_t.in_frame_q
    trk_t.out_db_q = sqlite_db_t.in_q
    trk_t.out_txt_q = txt_log_q
    trk_t.out_firebase_q = firebase_q

    # Threadleri başlat
    cam_t.start(); det_t.start(); trk_t.start()
    sqlite_db_t.start(); txt_logger_t.start(); disp_t.start()
    firebase_writer_t.start()

    try:
        while not stop.is_set():
            time.sleep(0.1)
            if not all(t.is_alive() for t in (
                cam_t, det_t, trk_t, sqlite_db_t, txt_logger_t, disp_t, firebase_writer_t
            )):
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for t in (cam_t, det_t, trk_t, sqlite_db_t, txt_logger_t, disp_t, firebase_writer_t):
            t.join()
        cap.release()
        db_logger.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
