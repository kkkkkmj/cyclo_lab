"""Bounded asynchronous encoding of recorded simulation RGB, never desktop capture."""
import json
from pathlib import Path
import queue
import threading
import time

import imageio_ffmpeg
import numpy as np
from PIL import Image
from preview_encoding import compose_native_preview

CAMERAS = ('head_cam', 'left_wrist_cam', 'right_wrist_cam')


class EpisodeVideo:
    def __init__(self, directory, episode_id, dt, capacity=32):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.episode_id = episode_id
        self.dt = dt
        self.queue = queue.Queue(maxsize=capacity)
        self.stopping = threading.Event()
        self.error = None
        self.submitted = self.dropped = self.encoded = 0
        self.closed = False
        self.thread = threading.Thread(target=self._encode, daemon=True)
        self.thread.start()

    def submit(self, images, sample_index, wall_time, simulation_time):
        """Called only for complete recorder rows, before any terminal reset."""
        self.submitted += 1
        if self.error or self.queue.full():
            self.dropped += 1
            return
        # Camera readback/copy remains on the simulation thread; no encoding or pipe writes here.
        frames = [np.array(images[name], copy=True) for name in CAMERAS]
        row = dict(sample_index=sample_index, wall_monotonic=wall_time,
                   simulation_time=simulation_time, enqueued_monotonic=time.monotonic())
        try:
            self.queue.put_nowait((frames, row))
        except queue.Full:
            self.dropped += 1

    def _encode(self):
        writer = None
        previous = previous_readback = None
        try:
            with (self.directory/'frames.jsonl').open('x') as timestamps:
                while not self.stopping.is_set() or not self.queue.empty():
                    try:
                        frames, row = self.queue.get(timeout=.05)
                    except queue.Empty:
                        continue
                    if writer is None:
                        writer = imageio_ffmpeg.write_frames(
                            str(self.directory/'video.mp4'), (768, 256), fps=1/self.dt,
                            codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p',
                            macro_block_size=1, output_params=['-crf', '22', '-preset', 'veryfast',
                                                             '-threads', '2', '-movflags', '+faststart'])
                        writer.send(None)
                    writer.send(np.asarray(compose_native_preview([Image.fromarray(f) for f in frames])))
                    row.update(video_frame=self.encoded, presentation_time=self.encoded*self.dt,
                               observation_sample_interval_s=None if previous is None else row['wall_monotonic']-previous,
                               capture_interval_s=None if previous_readback is None else row['enqueued_monotonic']-previous_readback)
                    previous = row['wall_monotonic']
                    previous_readback = row['enqueued_monotonic']
                    timestamps.write(json.dumps(row)+'\n')
                    self.encoded += 1
        except Exception as error:
            self.error = repr(error)
        finally:
            if writer is not None:
                try:
                    writer.close()
                except Exception as error:
                    self.error = repr(error)

    def close(self):
        if not self.closed:
            self.stopping.set()
            self.thread.join()  # Episode boundary only; never in the active control loop.
            self.closed = True
            report = dict(episode_id=self.episode_id, source='simulation_camera_pre_action_observations',
                          cameras=CAMERAS, fps=1/self.dt, time_basis='simulation_time',
                          playback='constant_fps; dropped samples omitted, consult frames.jsonl for gaps',
                          wall_time='wall_monotonic: pre-action sample; enqueued_monotonic: CPU readback; neither is sensor exposure time',
                          submitted=self.submitted, encoded=self.encoded,
                          dropped=self.submitted-self.encoded, queue_dropped=self.dropped,
                          error=self.error, playable=bool(self.encoded and not self.error))
            (self.directory/'video.json').write_text(json.dumps(report, indent=2)+'\n')
            self.report = report
        return self.report
