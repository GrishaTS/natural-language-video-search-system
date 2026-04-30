from pathlib import Path

from decord import VideoReader, cpu
from PIL import Image


def extract_frames(
    video_path: Path,
    fps: float = 1.0,
) -> list[tuple[float, Image.Image]]:
    """
    Равномерно семплирует кадры из видео по 1 кадру на интервал 1/fps секунд.
    Возвращает список (timestamp_sec, PIL.Image), где timestamp — середина интервала.
    Кадры возвращаются в RAM, на диск не пишутся.
    """
    vr = VideoReader(str(video_path), ctx=cpu(0))
    native_fps = vr.get_avg_fps()
    total_frames = len(vr)
    duration_sec = total_frames / native_fps

    interval = 1.0 / fps
    n_intervals = int(duration_sec / interval)

    result: list[tuple[float, Image.Image]] = []
    for i in range(n_intervals):
        ts = i * interval + interval / 2.0  # середина интервала
        frame_idx = min(int(ts * native_fps), total_frames - 1)
        frame_np = vr[frame_idx].asnumpy()  # (H, W, 3) uint8 RGB
        pil_img = Image.fromarray(frame_np)
        result.append((ts, pil_img))

    return result
