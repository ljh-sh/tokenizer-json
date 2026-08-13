#!/usr/bin/env python3
"""Convert OpenAI tiktoken encodings to HuggingFace tokenizer.json format.

Only depends on `tiktoken` and the Python standard library.
"""

import argparse
import json
import lzma
import os
import sys
from typing import Dict, List, Optional, Tuple

import tiktoken


def bytes_to_unicode() -> Dict[int, str]:
    """Returns the same mapping as transformers' bytes_to_unicode."""
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b)
            cs.append(2**8 + n)
            n += 1
    cs = [chr(c) for c in cs]
    return dict(zip(bs, cs))


BYTE_ENCODER = bytes_to_unicode()


def token_bytes_to_string(b: bytes) -> str:
    return "".join(BYTE_ENCODER[ord(ch)] for ch in b.decode("latin-1"))


def bpe(mergeable_ranks: Dict[bytes, int], token: bytes, max_rank: Optional[int] = None) -> List[bytes]:
    parts = [bytes([b]) for b in token]
    while True:
        min_idx = None
        min_rank = None
        for i, pair in enumerate(zip(parts[:-1], parts[1:])):
            rank = mergeable_ranks.get(pair[0] + pair[1])
            if rank is not None and (min_rank is None or rank < min_rank):
                min_idx = i
                min_rank = rank
        if min_rank is None or (max_rank is not None and min_rank >= max_rank):
            break
        assert min_idx is not None
        parts = parts[:min_idx] + [parts[min_idx] + parts[min_idx + 1]] + parts[min_idx + 2 :]
    return parts


def generate_vocab_and_merges(encoder) -> Tuple[Dict[str, int], List[str]]:
    mergeable_ranks = encoder._mergeable_ranks
    merges: List[str] = []
    vocab: Dict[str, int] = {}
    for token, rank in mergeable_ranks.items():
        vocab[token_bytes_to_string(token)] = rank
        if len(token) == 1:
            continue
        merged = tuple(bpe(mergeable_ranks, token, max_rank=rank))
        assert len(merged) == 2, f"expected merge of length 2, got {len(merged)}"
        merges.append(" ".join(token_bytes_to_string(m) for m in merged))
    vocab.update(encoder._special_tokens)
    return vocab, merges


ENCODING_MAP = {
    "gpt2": {"encoding": "r50k_base", "model_max_length": 1024},
    "davinci": {"encoding": "r50k_base", "model_max_length": 2048},
    "text-davinci-002": {"encoding": "p50k_base", "model_max_length": 4096},
    "text-davinci-003": {"encoding": "p50k_base", "model_max_length": 4096},
    "gpt-3.5-turbo": {"encoding": "cl100k_base", "model_max_length": 4096},
    "gpt-4": {"encoding": "cl100k_base", "model_max_length": 8192},
    "gpt-4o": {"encoding": "o200k_base", "model_max_length": 128000},
    "gpt-4o-mini": {"encoding": "o200k_base", "model_max_length": 128000},
}


def convert(encoding_name: str, model_max_length: int, output_path: str) -> None:
    encoder = tiktoken.get_encoding(encoding_name)
    vocab, merges = generate_vocab_and_merges(encoder)

    added_tokens = [
        {
            "id": tid,
            "content": content,
            "single_word": False,
            "lstrip": False,
            "rstrip": False,
            "normalized": False,
            "special": True,
        }
        for content, tid in encoder._special_tokens.items()
    ]

    if encoding_name in ("cl100k_base", "o200k_base"):
        pre_tokenizer = {
            "type": "Sequence",
            "pretokenizers": [
                {
                    "type": "Split",
                    "pattern": {
                        "Regex": "(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\\r\\n\\p{L}\\p{N}]?\\p{L}+|\\p{N}{1,3}| ?[^\\s\\p{L}\\p{N}]+[\\r\\n]*|\\s*[\\r\\n]+|\\s+(?!\\S)|\\s+"
                    },
                    "behavior": "Removed",
                    "invert": True,
                },
                {
                    "type": "ByteLevel",
                    "add_prefix_space": False,
                    "trim_offsets": True,
                    "use_regex": False,
                },
            ],
        }
    else:
        pre_tokenizer = {
            "type": "ByteLevel",
            "add_prefix_space": False,
            "trim_offsets": True,
            "use_regex": True,
        }

    tokenizer = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": added_tokens,
        "normalizer": None,
        "pre_tokenizer": pre_tokenizer,
        "post_processor": None,
        "decoder": {
            "type": "ByteLevel",
            "add_prefix_space": True,
            "trim_offsets": True,
            "use_regex": True,
        },
        "model": {
            "type": "BPE",
            "dropout": None,
            "unk_token": None,
            "continuing_subword_prefix": "",
            "end_of_word_suffix": "",
            "fuse_unk": False,
            "byte_fallback": False,
            "vocab": vocab,
            "merges": merges,
        },
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if output_path.endswith(".xz"):
        with lzma.open(output_path, "wt", encoding="utf-8") as fp:
            json.dump(tokenizer, fp, ensure_ascii=False, separators=(",", ":"))
    else:
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump(tokenizer, fp, ensure_ascii=False, separators=(",", ":"))

    print(f"wrote {output_path}: vocab={len(vocab)}, merges={len(merges)}, max_len={model_max_length}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert tiktoken encodings to tokenizer.json")
    parser.add_argument("id", choices=list(ENCODING_MAP.keys()), help="Model identifier")
    parser.add_argument("-o", "--output", help="Output path (default: data/<id>.tokenizer.json)")
    args = parser.parse_args()

    info = ENCODING_MAP[args.id]
    output = args.output or f"data/{args.id}.tokenizer.json"
    convert(info["encoding"], info["model_max_length"], output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
