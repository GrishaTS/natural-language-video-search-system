import json
import tarfile
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm


def parse_annotation_line(line: str) -> Optional[dict]:
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def extract_youtube_id(vid: str) -> str:
    # vid format: "<youtube_id>_<start_sec>_<end_sec>"
    # last two underscore-separated parts are float timestamps
    parts = vid.split("_")
    return "_".join(parts[:-2])


def load_annotations(jsonl_path: Path) -> list[dict]:
    annotations = []
    with open(jsonl_path) as f:
        for line in f:
            item = parse_annotation_line(line)
            if item is not None:
                annotations.append(item)
    return annotations


def download_annotations(urls: dict[str, str], annotations_dir: Path) -> None:
    annotations_dir.mkdir(parents=True, exist_ok=True)
    for split, url in urls.items():
        dest = annotations_dir / f"{split}.jsonl"
        if dest.exists():
            print(f"Уже скачан: {dest.name}")
            continue
        print(f"Скачиваем {split}.jsonl...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_text(resp.text)
        lines = resp.text.strip().count("\n") + 1
        print(f"  → {dest} ({lines:,} примеров)")


class _StreamingIO:
    """Оборачивает streaming HTTP response в file-like объект для tarfile."""

    def __init__(self, resp: requests.Response, chunk_size: int = 1024 * 1024):
        self._iter = resp.iter_content(chunk_size=chunk_size)
        self._buf = b""

    def read(self, n: int = -1) -> bytes:
        while n < 0 or len(self._buf) < n:
            try:
                self._buf += next(self._iter)
            except StopIteration:
                break
        if n < 0:
            data, self._buf = self._buf, b""
        else:
            data, self._buf = self._buf[:n], self._buf[n:]
        return data

    def readable(self) -> bool:
        return True


def download_videos(
    url: str,
    video_dir: Path,
    wanted_vids: Optional[set[str]] = None,
    limit: Optional[int] = None,
) -> set[str]:
    """
    Стримит архив QVHighlights и извлекает только нужные видео.

    wanted_vids — множество vid из аннотаций (фильтр по имени файла).
                  None = брать всё подряд.
    limit       — итоговое количество видео на диске. Уже скачанные
                  засчитываются: если на диске уже >= limit, архив не качается.

    Возвращает множество vid (не более limit), которые есть на диске.
    """
    video_dir.mkdir(parents=True, exist_ok=True)

    # Считаем, что уже есть на диске из нужных нам vid
    existing_vids: set[str] = {
        p.stem
        for p in video_dir.iterdir()
        if p.is_file() and (wanted_vids is None or p.stem in wanted_vids)
    }

    if limit and len(existing_vids) >= limit:
        result = set(list(existing_vids)[:limit])
        print(f"На диске уже {len(existing_vids)} видео — лимит {limit} достигнут, скачивание не нужно")
        return result

    need_new = (limit - len(existing_vids)) if limit else None

    print(f"Стримим архив с {url}")
    if wanted_vids:
        print(f"Ищем {len(wanted_vids)} видео из аннотаций")
    if need_new is not None:
        print(f"На диске: {len(existing_vids)}, нужно докачать: {need_new}")

    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    extracted = 0
    skipped_unwanted = 0
    new_vids: set[str] = set()

    with tarfile.open(fileobj=_StreamingIO(resp), mode="r|gz") as tar:
        with tqdm(desc="Извлекаем видео", unit="файл", total=need_new) as bar:
            for member in tar:
                if not member.isfile():
                    continue
                name = Path(member.name).stem  # vid без расширения
                if wanted_vids is not None and name not in wanted_vids:
                    skipped_unwanted += 1
                    tar.members = []
                    continue
                if name in existing_vids:
                    tar.members = []
                    continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                out_path = video_dir / Path(member.name).name
                out_path.write_bytes(f.read())
                new_vids.add(name)
                extracted += 1
                bar.update(1)
                bar.set_postfix(extracted=extracted)
                if need_new and extracted >= need_new:
                    break

    result = existing_vids | new_vids
    if limit:
        result = set(list(result)[:limit])
    print(f"Готово: извлечено {extracted} новых, было на диске {len(existing_vids)}, итого {len(result)}")
    return result
