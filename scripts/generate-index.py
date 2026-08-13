#!/usr/bin/env python3
"""Generate index.tsv from xz-compressed tokenizer.json release assets."""

import json
import lzma
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
INDEX_PATH = REPO_ROOT / "index.tsv"


def analyze(path: Path) -> dict:
    raw = lzma.open(path, "rb").read()
    data = json.loads(raw)

    model = data.get("model", {})
    model_type = model.get("type", "unknown")

    vocab = model.get("vocab", [])
    if isinstance(vocab, dict):
        vocab_size = len(vocab)
    elif isinstance(vocab, list):
        vocab_size = len(vocab)
    else:
        vocab_size = 0

    added = data.get("added_tokens", [])
    added_count = len(added)

    pre_tokenizer = data.get("pre_tokenizer")
    pre_type = "none"
    if isinstance(pre_tokenizer, dict):
        pre_type = pre_tokenizer.get("type", "unknown")
    elif isinstance(pre_tokenizer, list) and pre_tokenizer:
        pre_type = pre_tokenizer[0].get("type", "unknown")

    return {
        "id": path.stem.replace(".tokenizer.json", ""),
        "model_type": model_type,
        "vocab_size": vocab_size,
        "added_tokens": added_count,
        "pre_tokenizer": pre_type,
        "size_raw": len(raw),
        "size_xz": path.stat().st_size,
    }


def main() -> int:
    rows = []
    for xz_path in sorted(DATA_DIR.glob("*.tokenizer.json.xz")):
        try:
            rows.append(analyze(xz_path))
        except Exception as e:
            print(f"error analyzing {xz_path}: {e}", file=sys.stderr)
            return 1

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write("id\tmodel_type\tvocab_size\tadded_tokens\tpre_tokenizer\tsize_raw\tsize_xz\n")
        for r in rows:
            f.write(
                f"{r['id']}\t{r['model_type']}\t{r['vocab_size']}\t{r['added_tokens']}\t"
                f"{r['pre_tokenizer']}\t{r['size_raw']}\t{r['size_xz']}\n"
            )

    print(f"wrote {INDEX_PATH} with {len(rows)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
