#!/usr/bin/env python3
"""Convert Anthropic's claude.json (tiktoken/lite format) to HuggingFace tokenizer.json.

Steps:
1. Use Node.js to dump the full id->bytes vocab from @anthropic-ai/tokenizer.
2. Run this script to generate merges and write tokenizer.json.
"""

import argparse
import base64
import json
import lzma
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


def bytes_to_unicode() -> Dict[int, str]:
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
    return "".join(BYTE_ENCODER[ch] for ch in b)


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


def dump_vocab(claude_json_path: str, output_path: str) -> None:
    """Call Node.js to dump the full vocab from a claude.json file."""
    script = """
const { Tiktoken } = require('tiktoken/lite');
const fs = require('fs');
const claude = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const t = new Tiktoken(claude.bpe_ranks, claude.special_tokens, claude.pat_str);
const n = claude.explicit_n_vocab;
const vocab = [];
for (let i = 0; i < n; i++) {
    const bytes = Buffer.from(t.decode([i]));
    vocab.push({ id: i, b64: bytes.toString('base64') });
}
fs.writeFileSync(process.argv[3], JSON.stringify({
    explicit_n_vocab: n,
    pat_str: claude.pat_str,
    special_tokens: claude.special_tokens,
    vocab: vocab
}));
t.free();
"""
    subprocess.run(
        ["node", "-e", script, claude_json_path, output_path],
        check=True,
    )


def convert(dump_path: str, output_path: str) -> None:
    data = json.load(open(dump_path, encoding="utf-8"))
    n = data["explicit_n_vocab"]
    special = data["special_tokens"]
    pat_str = data["pat_str"]

    # Build rank -> bytes and mergeable ranks.
    rank_to_bytes: Dict[int, bytes] = {}
    mergeable_ranks: Dict[bytes, int] = {}
    for item in data["vocab"]:
        rank = item["id"]
        b = base64.b64decode(item["b64"])
        rank_to_bytes[rank] = b
        if rank not in special.values():
            mergeable_ranks[b] = rank

    # Generate vocab and merges.
    vocab: Dict[str, int] = {}
    merges: List[str] = []
    for rank in range(n):
        b = rank_to_bytes[rank]
        vocab[token_bytes_to_string(b)] = rank
        if rank in special.values() or len(b) == 1:
            continue
        merged = tuple(bpe(mergeable_ranks, b, max_rank=rank))
        if len(merged) != 2:
            raise RuntimeError(f"expected merge of length 2 for rank {rank}, got {len(merged)}")
        merges.append(" ".join(token_bytes_to_string(m) for m in merged))

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
        for content, tid in special.items()
    ]

    tokenizer = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": added_tokens,
        "normalizer": None,
        "pre_tokenizer": {
            "type": "Sequence",
            "pretokenizers": [
                {
                    "type": "Split",
                    "pattern": {"Regex": pat_str},
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
        },
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

    print(f"wrote {output_path}: vocab={len(vocab)}, merges={len(merges)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("claude_json", help="Path to Anthropic claude.json")
    parser.add_argument("-o", "--output", default="data/claude.tokenizer.json", help="Output tokenizer.json path")
    parser.add_argument("--from-dump", metavar="DUMP", help="Skip Node.js dump and use existing dump JSON")
    args = parser.parse_args()

    dump_path = args.from_dump or "/tmp/anthropic_vocab_dump.json"
    if not args.from_dump:
        dump_vocab(args.claude_json, dump_path)
    convert(dump_path, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
