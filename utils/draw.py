import cv2

def draw_tracks(frame, tracks):
    for t in tracks:
        if not t.is_confirmed() or t.time_since_update > 0:
            continue
        l, tt, r, b = [int(v) for v in t.to_ltrb()]
        cv2.rectangle(frame, (l, tt), (r, b), (0, 255, 0), 2)
        cv2.putText(frame, f"ID {t.track_id}", (l, max(0, tt-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    return frame

def draw_hud(frame, total_up, total_down, fps=0.0):
    cv2.rectangle(frame, (10, 10), (10+320, 10+40), (0,0,0), -1)
    cv2.putText(frame, f"UP:{total_up} DOWN:{total_down} FPS:{fps:.1f}", (20, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    return frame
