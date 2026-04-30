from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "qvhighlights"
VIDEO_DIR = DATA_DIR / "videos"
ANNOTATIONS_DIR = DATA_DIR / "annotations"

SPLITS = ["train", "val"]

ANNOTATIONS_URLS = {
    "train": "https://raw.githubusercontent.com/jayleicn/moment_detr/main/data/highlight_train_release.jsonl",
    "val": "https://raw.githubusercontent.com/jayleicn/moment_detr/main/data/highlight_val_release.jsonl",
}

VIDEOS_URL = "https://nlp.cs.unc.edu/data/jielei/qvh/qvhilights_videos.tar.gz"

# --- Indexing ---
INDEX_FRAME_DIR = DATA_DIR / "index_frame"
INDEX_WINDOW_DIR = DATA_DIR / "index_window"

# --- Embedding model ---
EMBED_MODEL_NAME = "Qwen/Qwen3-VL-Embedding-2B"
EMBED_DEVICE = "cuda:2"
EMBED_BATCH_SIZE_FRAMES = 16   # кадров за один forward pass (01_1)
EMBED_BATCH_SIZE_WINDOWS = 8   # окон за один forward pass (01_2)

# --- Frame sampling ---
SAMPLE_FPS = 1.0               # кадров в секунду (для extract_frames)
WINDOW_SIZE_SEC = 2            # длина окна в секундах (01_2)
WINDOW_STEP_SEC = 2            # шаг окна (= WINDOW_SIZE_SEC → без overlap)

# --- Search ---
SEARCH_K         = 100         # кандидатов из индекса
GAP_FRAME_SEC    = 1.0         # зазор склейки для frame-индекса (сек)
GAP_WINDOW_SEC   = 2.0         # зазор склейки для window-индекса (сек)
RESULTS_DIR      = DATA_DIR / "results"

# --- Reranker ---
RERANKER_MODEL_NAME = "Qwen/Qwen3-VL-Reranker-2B"
RERANKER_DEVICE     = "cuda:2"

# --- CLIP ---
CLIP_MODEL_NAME        = "openai/clip-vit-large-patch14"
CLIP_DEVICE            = "cuda:2"
CLIP_BATCH_SIZE        = 64   # изображений за один forward pass

# --- X-CLIP ---
XCLIP_MODEL_NAME       = "microsoft/xclip-base-patch32"
XCLIP_DEVICE           = "cuda:2"
XCLIP_BATCH_SIZE       = 8    # окон за один forward pass

INDEX_CLIP_FRAME_DIR   = DATA_DIR / "index_clip_frame"
INDEX_CLIP_WINDOW_DIR  = DATA_DIR / "index_clip_window"
INDEX_XCLIP_DIR        = DATA_DIR / "index_xclip"

# --- CG-DETR (lighthouse) ---
CGDETR_CKPT          = BASE_DIR / "checkpoints" / "cgdetr_clip_qvhighlights.ckpt"
CGDETR_DEVICE        = "cuda:2"
FEATS_CGDETR_DIR     = DATA_DIR / "feats_cgdetr"
