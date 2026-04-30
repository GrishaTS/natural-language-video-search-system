from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor, XCLIPModel, XCLIPProcessor


def _l2_normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return (vecs / np.clip(norms, 1e-8, None)).astype(np.float32)


class CLIPEmbedder:
    """
    CLIP ViT-L/14 embedder для frame- и window-режимов.

    pooling='frame'  — embed_images / embed_text
    pooling='window' — embed_windows (mean pool кадров) / embed_text
    """

    def __init__(self, model_name: str, device: str, pooling: str = "frame") -> None:
        if pooling not in ("frame", "window"):
            raise ValueError(f"pooling must be 'frame' or 'window', got {pooling!r}")
        self.device = device
        self.pooling = pooling
        self.model = CLIPModel.from_pretrained(model_name).eval().to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        """(N, 768) L2-нормализованный float32."""
        inputs = self.processor(images=images, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)
        with torch.no_grad():
            vision_out = self.model.vision_model(pixel_values=pixel_values)
            feats = self.model.visual_projection(vision_out.pooler_output)
        return _l2_normalize(feats.float().cpu().numpy())

    def embed_windows(self, windows: list[list[Image.Image]]) -> np.ndarray:
        """(N, 768) L2-нормализованный float32. Требует pooling='window'."""
        if self.pooling != "window":
            raise ValueError("embed_windows requires pooling='window'")
        vecs = [self.embed_images(frames).mean(axis=0) for frames in windows]
        return _l2_normalize(np.vstack(vecs))

    def embed_text(self, texts: list[str]) -> np.ndarray:
        """(N, 768) L2-нормализованный float32."""
        inputs = self.processor(
            text=texts, return_tensors="pt", padding=True, truncation=True
        )
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)
        with torch.no_grad():
            text_out = self.model.text_model(input_ids=input_ids, attention_mask=attention_mask)
            feats = self.model.text_projection(text_out.pooler_output)
        return _l2_normalize(feats.float().cpu().numpy())


class XCLIPEmbedder:
    """
    Microsoft X-CLIP embedder для window-режима.
    Всегда ресэмплирует кадры окна до NUM_FRAMES=8.
    """

    NUM_FRAMES = 8

    def __init__(self, model_name: str, device: str) -> None:
        self.device = device
        self.model = XCLIPModel.from_pretrained(model_name).eval().to(device)
        self.processor = XCLIPProcessor.from_pretrained(model_name)

    def _resample(self, frames: list[Image.Image]) -> list[Image.Image]:
        n = len(frames)
        idxs = np.linspace(0, n - 1, self.NUM_FRAMES, dtype=int)
        return [frames[i] for i in idxs]

    def embed_windows(self, windows: list[list[Image.Image]]) -> np.ndarray:
        """(N, 512) L2-нормализованный float32."""
        resampled = [self._resample(w) for w in windows]
        inputs = self.processor(images=resampled, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)
        with torch.no_grad():
            feats = self.model.get_video_features(pixel_values=pixel_values).pooler_output
        return _l2_normalize(feats.float().cpu().numpy())

    def embed_text(self, texts: list[str]) -> np.ndarray:
        """(N, 512) L2-нормализованный float32."""
        inputs = self.processor(
            text=texts, return_tensors="pt", padding=True, truncation=True
        )
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)
        with torch.no_grad():
            feats = self.model.get_text_features(input_ids=input_ids, attention_mask=attention_mask).pooler_output
        return _l2_normalize(feats.float().cpu().numpy())
