# tokenizer-json

xz-compressed `tokenizer.json` release assets for tools like [`token-actuary`](https://github.com/ljh-sh/token-actuary).

The actual data lives in the [`data` release](https://github.com/ljh-sh/tokenizer-json/releases/tag/data). This repository only tracks sync scripts and metadata.

## Tokenizers

| id | model_type | vocab_size | added_tokens | pre_tokenizer | raw | xz |
|---|---|---|---|---|---|---|
| `deepseek_v3` | BPE | 128000 | 818 | Sequence | 7.5 MB | 1.3 MB |
| `llama3` | BPE | 128000 | 256 | Sequence | 8.7 MB | 1.5 MB |
| `mistral_v3` | BPE | 32768 | 771 | Metaspace | 1.9 MB | 326 KB |
| `qwen2_5` | BPE | 151643 | 22 | Sequence | 6.7 MB | 1.3 MB |

See [`index.tsv`](index.tsv) for the machine-readable list.

## Download

```bash
# Get a single tokenizer
curl -L -o qwen2_5.tokenizer.json.xz \
  https://github.com/ljh-sh/tokenizer-json/releases/download/data/qwen2_5.tokenizer.json.xz
xz -d qwen2_5.tokenizer.json.xz
```

## Use with token-actuary

```bash
ta count --tokenizer qwen2_5.tokenizer.json
```

## Use in browser

```javascript
const res = await fetch(
  'https://github.com/ljh-sh/tokenizer-json/releases/download/data/qwen2_5.tokenizer.json.xz'
);
// Browser does not natively decompress xz; serve decompressed or use a WASM xz decoder.
```

## Add a tokenizer

```bash
./scripts/sync.sh <id> <huggingface-repo>

# Example
./scripts/sync.sh qwen2_5 Qwen/Qwen2.5-7B-Instruct
```

Requirements:
- `curl`, `xz`, `python3`
- `gh` CLI authenticated to upload release assets

## Data plan

See [`docs/data-plan.md`](docs/data-plan.md) for size projections, storage strategy, and scaling guidance.

## License

- Code and metadata in this repository: Apache 2.0.
- Each tokenizer file retains the license of its originating model. See `data/<id>.tokenizer.json.src` for source and license links.
