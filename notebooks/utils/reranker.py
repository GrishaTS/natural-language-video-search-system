from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from sentence_transformers import CrossEncoder


def load_reranker(model_name: str, device: str) -> CrossEncoder:
    return CrossEncoder(model_name, device=device, trust_remote_code=True)


def extract_middle_frame(
    video_path: Path, start_sec: float, end_sec: float
) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    t = (start_sec + end_sec) / 2.0
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def rerank_segments(
    query: str,
    segments: pd.DataFrame,
    video_dir: Path,
    model: CrossEncoder,
    prompt: str = "Retrieve video segments relevant to the user's query.",
) -> pd.DataFrame:
    """
    Скорит сегменты через reranker.
    segments: DataFrame с колонками video_id, start_sec, end_sec, score.
    Возвращает тот же DataFrame с score = sigmoid(raw_score), отсортированный по score desc.
    Сегменты без доступного видеофайла пропускаются.
    """
    if segments.empty:
        return segments.copy()

    frames: list[np.ndarray] = []
    valid_indices: list[int] = []
    for i, (_, row) in enumerate(segments.iterrows()):
        video_path = video_dir / (row["video_id"] + ".mp4")
        frame = extract_middle_frame(video_path, row["start_sec"], row["end_sec"])
        if frame is not None:
            frames.append(frame)
            valid_indices.append(i)

    if not frames:
        return segments.copy()

    pairs = [(query, frame) for frame in frames]
    raw_scores = model.predict(pairs, prompt=prompt)
    sigmoid_scores = torch.sigmoid(
        torch.tensor(raw_scores, dtype=torch.float32)
    ).numpy()

    result = segments.iloc[valid_indices].copy()
    result["score"] = sigmoid_scores
    return result.sort_values("score", ascending=False).reset_index(drop=True)
