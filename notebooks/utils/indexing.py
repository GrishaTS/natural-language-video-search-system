from pathlib import Path

import faiss
import numpy as np
import pandas as pd


def build_index(vectors: np.ndarray) -> faiss.IndexFlatIP:
    """
    Строит FAISS IndexFlatIP из L2-нормализованных векторов.
    Dot product нормализованных векторов = косинусное сходство.
    vectors: shape (N, D), dtype float32, должны быть L2-нормализованы.
    """
    d = vectors.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(vectors)
    return index


def save_index(
    index: faiss.IndexFlatIP,
    metadata_df: pd.DataFrame,
    index_dir: Path,
) -> None:
    """Сохраняет index.faiss и metadata.parquet в index_dir."""
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "index.faiss"))
    metadata_df.to_parquet(index_dir / "metadata.parquet", index=False)


def load_index(index_dir: Path) -> tuple[faiss.IndexFlatIP, pd.DataFrame]:
    """Загружает index.faiss и metadata.parquet из index_dir."""
    index = faiss.read_index(str(index_dir / "index.faiss"))
    metadata = pd.read_parquet(index_dir / "metadata.parquet")
    return index, metadata
