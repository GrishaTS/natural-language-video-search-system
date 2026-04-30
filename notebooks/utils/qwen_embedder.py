from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor


def _l2_normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-8, None)


class Embedder:
    """
    Обёртка над Qwen3-VL-Embedding-2B.
    Все методы возвращают L2-нормализованные float32 массивы shape (N, 2048).

    API: apply_chat_template + AutoProcessor.
    Эмбеддинг = last_hidden_state[:, -1, :] (EOS-токен).
    Image/video требуют chat template с {"type": "image"} / {"type": "video"}.
    Text обрабатывается напрямую без chat template.
    """

    def __init__(self, model_name: str, device: str = "cuda:2") -> None:
        self.device = device
        self.model = AutoModel.from_pretrained(
            model_name,
            trust_remote_code=True,
            dtype=torch.bfloat16,
            device_map=device,
        ).eval()
        self.processor = AutoProcessor.from_pretrained(
            model_name, trust_remote_code=True
        )

    def _forward(self, inputs: dict) -> np.ndarray:
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model(**inputs)
        emb = out.last_hidden_state[:, -1, :]
        return emb.float().cpu().numpy()

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        """
        Batch image embed.
        images: список PIL.Image
        Возвращает: L2-нормализованный np.ndarray (N, 2048), dtype float32
        """
        if not images:
            raise ValueError("images list is empty")
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": ""}]}]
        text_template = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        all_vecs = []
        for img in images:
            inputs = self.processor(
                text=[text_template],
                images=[img],
                return_tensors="pt",
            )
            vec = self._forward(inputs)
            all_vecs.append(vec)
        return _l2_normalize(np.vstack(all_vecs))

    def embed_windows(self, windows: list[list[Image.Image]]) -> np.ndarray:
        """
        Batch video embed. Каждое окно — список PIL.Image кадров.
        windows: list of list[PIL.Image], len(windows[i]) >= 1
        Возвращает: L2-нормализованный np.ndarray (N, 2048), dtype float32
        """
        if not windows:
            raise ValueError("windows list is empty")
        messages = [{"role": "user", "content": [{"type": "video"}, {"type": "text", "text": ""}]}]
        text_template = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        all_vecs = []
        for frames in windows:
            inputs = self.processor(
                text=[text_template],
                videos=[frames],
                return_tensors="pt",
            )
            vec = self._forward(inputs)
            all_vecs.append(vec)
        return _l2_normalize(np.vstack(all_vecs))

    def embed_text(self, texts: list[str]) -> np.ndarray:
        """
        Batch text embed.
        texts: список строк
        Возвращает: L2-нормализованный np.ndarray (N, 2048), dtype float32
        """
        if not texts:
            raise ValueError("texts list is empty")
        all_vecs = []
        for text in texts:
            inputs = self.processor(text=[text], return_tensors="pt")
            vec = self._forward(inputs)
            all_vecs.append(vec)
        return _l2_normalize(np.vstack(all_vecs))
