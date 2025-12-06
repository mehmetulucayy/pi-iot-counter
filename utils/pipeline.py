import threading, queue, time, cv2
from utils.draw import draw_tracks, draw_hud

class StopSignal:
    def __init__(self): self._ev = threading.Event()
    def set(self): self._ev.set()
    def is_set(self): return self._ev.is_set()

class CameraThread(threading.Thread):
    def __init__(self, cap, stop, max_q=5):
        super().__init__(daemon=True); self.cap=cap; self.stop=stop
        self.out_q = queue.Queue(maxsize=max_q)
    def run(self):
        while not self.stop.is_set():
            ret, frame = self.cap.read()
            if not ret: break
            try:
                self.out_q.put(frame, timeout=0.01)
            except queue.Full:
                try: _ = self.out_q.get_nowait()
                except queue.Empty: pass
                try: self.out_q.put(frame, timeout=0.01)
                except queue.Full: pass

class DetectorThread(threading.Thread):
    def __init__(self, model, stop, conf=0.35, iou=0.45, classes=[0], max_q=5):
        super().__init__(daemon=True); self.model=model; self.stop=stop
        self.in_q = queue.Queue(maxsize=max_q); self.out_q = queue.Queue(maxsize=max_q)
        self.conf=conf; self.iou=iou; self.classes=classes
    def run(self):
        while not self.stop.is_set():
            try: frame = self.in_q.get(timeout=0.05)
            except queue.Empty: continue
            yolo_results = self.model.predict(source=frame, verbose=False,
                                              conf=self.conf, iou=self.iou, classes=self.classes, device="cpu")
            detections = []
            if len(yolo_results)>0:
                r=yolo_results[0]
                if r.boxes is not None and len(r.boxes)>0:
                    for box in r.boxes:
                        xyxy = box.xyxy[0].cpu().numpy().astype(float)
                        conf = float(box.conf[0].cpu().numpy())
                        detections.append((xyxy, conf))
            try: self.out_q.put((frame, detections), timeout=0.01)
            except queue.Full:
                try: _ = self.out_q.get_nowait()
                except queue.Empty: pass
                try: self.out_q.put((frame, detections), timeout=0.01)
                except queue.Full: pass

class TrackerThread(threading.Thread):
    def __init__(self, tracker_impl, counter, stop, max_q=5):
        super().__init__(daemon=True)
        self.tracker = tracker_impl
        self.counter = counter
        self.stop = stop

        self.in_q = queue.Queue(maxsize=max_q)
        self.out_frame_q = queue.Queue(maxsize=max_q)
        self.out_db_q = queue.Queue(maxsize=max_q)
        self.out_txt_q = queue.Queue(maxsize=max_q)

        # 🔴 Firebase kuyruğu eklendi
        self.out_firebase_q = queue.Queue(maxsize=max_q)

        self._fps=0.0; self._last=time.time()

    def run(self):
        print("TrackerThread başlatılıyor...")
        while not self.stop.is_set():
            try:
                frame, detections = self.in_q.get(timeout=0.05)
            except queue.Empty:
                continue

            # Takip güncelle
            tracks = self.tracker.update_tracks(detections, frame=frame)

            # Sayaç güncelle
            events=[]
            for t in tracks:
                if not t.is_confirmed() or t.time_since_update>0: continue
                l,t0,r,b = t.to_ltrb(); cx=int((l+r)/2); cy=int((t0+b)/2)
                crossed, dirn = self.counter.update(t.track_id, (cx,cy))
                if crossed: events.append((int(time.time()), t.track_id, dirn))

            # DB kuyruğu
            for ev in events:
                try: self.out_db_q.put(ev, timeout=0.01)
                except queue.Full: pass

            # TXT log kuyruğu
            try:
                self.out_txt_q.put({"timestamp": int(time.time()),
                                    "count": self.counter.total_up + self.counter.total_down},
                                    timeout=0.01)
            except queue.Full: pass

            # Görsel çizim
            frame = draw_tracks(frame, tracks)
            frame = self.counter.draw(frame)

            # FPS + HUD
            now=time.time()
            self._fps=0.9*self._fps+0.1*(1.0/max(1e-6, now-self._last))
            self._last=now
            frame = draw_hud(frame, self.counter.total_up, self.counter.total_down, self._fps)

            # Görüntü kuyruğu
            try: self.out_frame_q.put(frame, timeout=0.01)
            except queue.Full: pass

            # 🔴 Firebase kuyruğu (anlık kişi sayısı)
            try:
                total_count = self.counter.total_up + self.counter.total_down
                print(f"Anlık kişi sayısı: {total_count}")
                self.out_firebase_q.put({
                    "total_count": total_count,
                    "timestamp": int(time.time())
                }, timeout=0.01)
            except queue.Full: pass

        print("TrackerThread durduruldu.")

class DBThread(threading.Thread):
    def __init__(self, db, stop, max_q=100):
        super().__init__(daemon=True); self.db=db; self.stop=stop; self.in_q=queue.Queue(maxsize=max_q)
    def run(self):
        while not self.stop.is_set():
            try: ts, tid, dirn = self.in_q.get(timeout=0.1)
            except queue.Empty: continue
            try: self.db.insert_count(ts, tid, dirn)
            except Exception as e: print("DB insert error:", e)

class DisplayThread(threading.Thread):
    def __init__(self, stop, show=True):
        super().__init__(daemon=True); self.stop=stop; self.in_frame_q=queue.Queue(maxsize=5); self.show=show
    def run(self):
        while not self.stop.is_set():
            try: frame = self.in_frame_q.get(timeout=0.1)
            except queue.Empty: continue
            if self.show:
                cv2.imshow("Deep SORT Threaded", frame)
                key = cv2.waitKey(1) & 0xFF
                if key==27: self.stop.set(); break
