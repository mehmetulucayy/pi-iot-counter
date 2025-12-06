from deep_sort_realtime.deepsort_tracker import DeepSort

class DeepSortWrapper:
    def __init__(self, max_age=30, n_init=3, nn_budget=100):
        self.tracker = DeepSort(max_age=max_age, n_init=n_init, nn_budget=nn_budget)
    def update_tracks(self, detections, frame):
        ds_inputs = []
        for (xyxy, conf) in detections:
            x1,y1,x2,y2 = xyxy
            w = x2 - x1
            h = y2 - y1
            ds_inputs.append(((x1, y1, w, h), conf, 'person'))
        return self.tracker.update_tracks(ds_inputs, frame=frame)
