from __future__ import annotations

import numpy as np
import pandas as pd


def search_index(
    index,
    metadata: pd.DataFrame,
    query_vec: np.ndarray,
    k: int = 100,
) -> pd.DataFrame:
    """
    Возвращает top-K хитов как DataFrame с колонками index_type.
    query_vec: shape (1, D), L2-нормализован.
    """
    import faiss  # noqa: F401 — lazy import, not needed by group_segments
    scores, ids = index.search(query_vec, k)
    scores, ids = scores[0], ids[0]
    mask = ids >= 0
    hits = metadata.iloc[ids[mask]].copy()
    hits["score"] = scores[mask].astype(float)
    return hits.reset_index(drop=True)


def group_segments(
    hits: pd.DataFrame,
    gap_sec: float = 1.0,
) -> pd.DataFrame:
    """
    Склеивает соседние хиты одного видео в сегменты.
    Зазор между концом предыдущего и началом следующего <= gap_sec → один сегмент.
    Возвращает DataFrame (video_id, start_sec, end_sec, score), отсортированный по score desc.
    """
    if hits.empty:
        return pd.DataFrame(columns=["video_id", "start_sec", "end_sec", "score"])

    segments = []
    for video_id, group in hits.groupby("video_id"):
        group = group.sort_values("start_sec")
        seg_start = seg_end = seg_score = None

        for _, row in group.iterrows():
            if seg_start is None:
                seg_start, seg_end, seg_score = row["start_sec"], row["end_sec"], row["score"]
            elif row["start_sec"] - seg_end <= gap_sec:
                seg_end = max(seg_end, row["end_sec"])
                seg_score = max(seg_score, row["score"])
            else:
                segments.append({"video_id": video_id, "start_sec": seg_start, "end_sec": seg_end, "score": seg_score})
                seg_start, seg_end, seg_score = row["start_sec"], row["end_sec"], row["score"]

        segments.append({"video_id": video_id, "start_sec": seg_start, "end_sec": seg_end, "score": seg_score})

    return (
        pd.DataFrame(segments)
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
    )
