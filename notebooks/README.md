# Natural Language Video Search — Notebooks

___
## About
*Research notebooks for evaluating natural language video moment retrieval on the QVHighlights benchmark. Each notebook implements a full pipeline — indexing → search → evaluation — for a different model approach.*

Models covered:
- **Qwen3-VL-Embedding (2B / 8B)** — multimodal dense retrieval (frame-level and window-level indexing), with optional **Qwen3-VL-Reranker-2B** cross-encoder reranking
- **CLIP ViT-L/14** — image-text retrieval with frame and sliding-window indexing
- **X-CLIP** — video-text retrieval with temporal window indexing
- **CG-DETR (lighthouse)** — transformer-based moment detection, direct grounding and cross-encoder saliency pipelines

___
## Notebooks

| # | File | Description |
|---|------|-------------|
| 00 | `00_dataset.ipynb` | QVHighlights dataset download and EDA |
| 01 | `01 qwen3.ipynb` | Full pipeline with Qwen3-VL-Embedding (2B / 8B), with optional Qwen3-VL-Reranker-2B |
| 02 | `02 clip.ipynb` | Full pipeline with CLIP ViT-L/14 |
| 03 | `03 xclip.ipynb` | Full pipeline with X-CLIP |
| 04 | `04 momentdetr_direct.ipynb` | CG-DETR direct grounding pipeline |
| 05 | `05 momentdetr_cross.ipynb` | CG-DETR cross-encoder saliency pipeline |

___
## Project Structure

<details open>
  <summary>📂 notebooks/</summary>
  <ul>
    <li>📄 <code>config.py</code> — Paths, model names, and hyperparameters for all notebooks</li>
    <li>📄 <code>requirements.txt</code> — Python dependencies</li>
    <li>📄 <code>clearml.yml</code> — ClearML experiment tracking configuration</li>
    <li>📄 <code>00_dataset.ipynb</code> — QVHighlights dataset download and EDA</li>
    <li>📄 <code>01 qwen3.ipynb</code> — Full pipeline with Qwen3-VL-Embedding (2B / 8B), with optional Qwen3-VL-Reranker-2B</li>
    <li>📄 <code>02 clip.ipynb</code> — Full pipeline with CLIP ViT-L/14</li>
    <li>📄 <code>03 xclip.ipynb</code> — Full pipeline with X-CLIP</li>
    <li>📄 <code>04 momentdetr_direct.ipynb</code> — CG-DETR direct grounding pipeline</li>
    <li>📄 <code>05 momentdetr_cross.ipynb</code> — CG-DETR cross-encoder saliency pipeline</li>
    <details>
      <summary>📂 utils/</summary>
      <ul>
        <li>📄 <code>download.py</code> — Dataset and annotation download helpers</li>
        <li>📄 <code>frames.py</code> — Video frame extraction utilities</li>
        <li>📄 <code>clip_embedder.py</code> — CLIP and X-CLIP embedding wrappers</li>
        <li>📄 <code>qwen_embedder.py</code> — Qwen3-VL-Embedding (2B / 8B) embedding wrapper</li>
        <li>📄 <code>reranker.py</code> — Qwen3-VL-Reranker-2B reranking wrapper</li>
        <li>📄 <code>indexing.py</code> — Vector index construction and persistence</li>
        <li>📄 <code>search.py</code> — Candidate retrieval and segment merging</li>
        <li>📄 <code>metrics.py</code> — Evaluation metrics (mAP, R1@0.5, R1@0.7)</li>
        <li>📄 <code>clearml_logger.py</code> — ClearML experiment logging helpers</li>
      </ul>
    </details>
  </ul>
</details>

___
## Results

Evaluated on the [QVHighlights](https://github.com/jayleicn/moment_detr) benchmark (val split).

| Metric | CG-DETR / saliency | CG-DETR / direct | Qwen3-VL-8B / w6s3 | Qwen3-VL-8B / w4s1 | Qwen3-VL-8B / w2s1 | Qwen3-VL-8B / w4s2 | X-CLIP / window | CLIP-L/14 / window | CLIP-L/14 / frame | Qwen3-VL-8B / frame+reranker | Qwen3-VL-8B / w2s2+reranker | Qwen3-VL-8B / frame | Qwen3-VL-8B / w2s2 | Qwen3-VL-2B / frame | Qwen3-VL-2B / w2s2 | Qwen3-VL-2B / frame+reranker | Qwen3-VL-2B / w2s2+reranker |
|--------|-------------------|-----------------|--------------------|--------------------|--------------------|--------------------|-----------------|-------------------|-------------------|------------------------------|-------------------------------|---------------------|----------------------|---------------------|----------------------|------------------------------|-------------------------------|
| mean_iou@top5 | 0.630 | 0.840 | 0.591 | 0.647 | 0.679 | 0.650 | 0.370 | 0.551 | 0.492 | 0.574 | 0.626 | 0.645 | 0.681 | 0.579 | 0.664 | 0.496 | 0.637 |
| mean_iou@top1 | 0.602 | 0.865 | 0.511 | 0.574 | 0.606 | 0.556 | 0.452 | 0.559 | 0.448 | 0.486 | 0.580 | 0.603 | 0.598 | 0.498 | 0.611 | 0.435 | 0.579 |
| mean_iou | 0.624 | 0.767 | 0.599 | 0.637 | 0.670 | 0.639 | 0.334 | 0.553 | 0.456 | 0.623 | 0.663 | 0.623 | 0.663 | 0.553 | 0.646 | 0.553 | 0.646 |
| MR@IoU≥0.3 | 0.720 | 0.607 | 0.794 | 0.860 | 0.822 | 0.822 | 0.308 | 0.682 | 0.579 | 0.757 | 0.794 | 0.776 | 0.832 | 0.673 | 0.785 | 0.654 | 0.757 |
| MR@IoU≥0.5 | 0.589 | 0.570 | 0.654 | 0.673 | 0.673 | 0.645 | 0.215 | 0.542 | 0.383 | 0.626 | 0.636 | 0.636 | 0.654 | 0.570 | 0.645 | 0.570 | 0.617 |
| MR@IoU≥0.7 | 0.364 | 0.458 | 0.411 | 0.439 | 0.486 | 0.458 | 0.103 | 0.336 | 0.280 | 0.458 | 0.495 | 0.467 | 0.505 | 0.402 | 0.514 | 0.393 | 0.495 |
| moment_mrr@iou03 | 0.504 | 0.167 | 0.632 | 0.698 | 0.675 | 0.667 | 0.202 | 0.478 | 0.411 | 0.529 | 0.561 | 0.649 | 0.666 | 0.484 | 0.614 | 0.444 | 0.537 |
| moment_mrr@iou05 | 0.400 | 0.164 | 0.507 | 0.533 | 0.553 | 0.504 | 0.136 | 0.350 | 0.271 | 0.439 | 0.471 | 0.531 | 0.518 | 0.420 | 0.508 | 0.383 | 0.451 |
| moment_mrr@iou07 | 0.258 | 0.138 | 0.302 | 0.331 | 0.389 | 0.345 | 0.077 | 0.226 | 0.202 | 0.297 | 0.359 | 0.361 | 0.395 | 0.275 | 0.387 | 0.263 | 0.355 |
| video_map | 0.582 | 0.169 | 0.668 | 0.676 | 0.648 | 0.656 | 0.243 | 0.455 | 0.434 | 0.592 | 0.564 | 0.595 | 0.608 | 0.526 | 0.564 | 0.569 | 0.562 |
| video_mrr | 0.618 | 0.169 | 0.835 | 0.809 | 0.809 | 0.812 | 0.380 | 0.623 | 0.628 | 0.756 | 0.733 | 0.775 | 0.800 | 0.697 | 0.762 | 0.733 | 0.714 |
| Video Recall@K | 0.860 | 0.636 | 0.953 | 0.953 | 0.944 | 0.944 | 0.664 | 0.935 | 0.907 | 0.944 | 0.944 | 0.916 | 0.935 | 0.907 | 0.944 | 0.935 | 0.944 |
| video_f1@5 | 0.326 | 0.087 | 0.412 | 0.470 | 0.509 | 0.431 | 0.261 | 0.374 | 0.420 | 0.526 | 0.432 | 0.525 | 0.476 | 0.510 | 0.455 | 0.527 | 0.453 |
| Video F1@K | 0.123 | 0.061 | 0.173 | 0.214 | 0.263 | 0.186 | 0.155 | 0.225 | 0.297 | 0.344 | 0.231 | 0.321 | 0.231 | 0.316 | 0.233 | 0.342 | 0.242 |
| ndcg@10 | 0.850 | 0.209 | 1.201 | 1.403 | 1.545 | 1.234 | 0.728 | 1.142 | 1.366 | 1.749 | 1.316 | 1.720 | 1.389 | 1.676 | 1.341 | 1.770 | 1.355 |
| Video nDCG@K | 0.870 | 0.262 | 1.270 | 1.490 | 1.733 | 1.325 | 0.845 | 1.310 | 1.716 | 2.110 | 1.459 | 2.018 | 1.547 | 1.938 | 1.507 | 2.080 | 1.513 |

___
## Technologies Used
![PyTorch](https://img.shields.io/badge/Framework-PyTorch-EE4C2C?logo=pytorch) ![Transformers](https://img.shields.io/badge/Models-Transformers-FF4C7B?logo=huggingface) ![Qwen3--VL](https://img.shields.io/badge/Embedding-Qwen3--VL-0064FF) ![CLIP](https://img.shields.io/badge/Model-CLIP-FF8C00) ![X--CLIP](https://img.shields.io/badge/Model-X--CLIP-FF6B00) ![CG--DETR](https://img.shields.io/badge/Model-CG--DETR-6A5ACD) ![FAISS](https://img.shields.io/badge/Index-FAISS-00599C) ![ClearML](https://img.shields.io/badge/Tracking-ClearML-FF6F00) ![Pandas](https://img.shields.io/badge/Data-Pandas-150458?logo=pandas) ![NumPy](https://img.shields.io/badge/Numerics-NumPy-013243?logo=numpy)
