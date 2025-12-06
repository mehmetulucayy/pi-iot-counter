import time
import cv2

class LineCounter:
    def __init__(self, p1, p2, direction="both", recount_ttl_sec=30):
        self.p1 = (int(p1[0]), int(p1[1]))
        self.p2 = (int(p2[0]), int(p2[1]))
        self.direction = direction
        self.recount_ttl = int(recount_ttl_sec)
        self.track_last_side = {}
        self.counted_recent = {}
        self.total_up = 0
        self.total_down = 0

    @staticmethod
    def _side(p, a, b):
        return (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])

    def update(self, track_id, center_xy):
        now = int(time.time())
        if track_id in self.counted_recent and (now - self.counted_recent[track_id]) < self.recount_ttl:
            return False, None
        side_val = self._side(center_xy, self.p1, self.p2)
        side = 1 if side_val > 0 else (-1 if side_val < 0 else 0)
        prev_side = self.track_last_side.get(track_id, side)
        self.track_last_side[track_id] = side
        if prev_side != side and prev_side != 0 and side != 0:
            direction = "down" if prev_side > side else "up"
            if self.direction in ("both", direction):
                if direction == "up":
                    self.total_up += 1
                else:
                    self.total_down += 1
                self.counted_recent[track_id] = now
                return True, direction
        return False, None

    def draw(self, frame):
        cv2.line(frame, self.p1, self.p2, (255,255,0), 2)
        return frame
