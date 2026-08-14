# tokenizer-json

xz-compressed `tokenizer.json` release assets for tools like [`token-actuary`](https://github.com/ljh-sh/token-actuary).

The actual data lives in the [`data` release](https://github.com/ljh-sh/tokenizer-json/releases/tag/data). This repository only tracks sync scripts and metadata.

## Tokenizers

| id | family | algorithm | vocab_size | added_tokens | raw | xz |
|---|---|---|---|---|---|---|
| `qwen2_5` | Qwen 2.5 | BPE | 151643 | 22 | 6.7 MB | 1.3 MB |
| `qwen3` | Qwen 3 | BPE | 151643 | 26 | 11 MB | 1.4 MB |
| `deepseek_v3` | DeepSeek V3 | BPE | 128000 | 818 | 7.5 MB | 1.3 MB |
| `deepseek_v4` | DeepSeek V4 | BPE | 128000 | 1283 | 6.1 MB | 1.3 MB |
| `llama3` | Meta Llama 3 | BPE | 128000 | 256 | 8.7 MB | 1.5 MB |
| `mistral_v3` | Mistral | BPE | 32768 | 771 | 1.9 MB | 326 KB |
| `gpt_4o` | OpenAI GPT-4o / o1 / o3 | BPE | 200000 | 2 | 6.4 MB | 1.9 MB |
| `o200k_harmony` | OpenAI GPT-4o / o1 / o3 (harmonized) | BPE | 201089 | 1091 | 6.6 MB | 1.9 MB |
| `gpt_4` | OpenAI GPT-4 / GPT-3.5 | BPE | 100261 | 5 | 2.7 MB | 874 KB |
| `claude` | Anthropic Claude (legacy 2023) | BPE | 64739 | 5 | 1.8 MB | 551 KB |
| `glm` | Zhipu GLM-4 | BPE | 151329 | 14 | 19 MB | 2.0 MB |

See [`index.tsv`](index.tsv) for the machine-readable list.

### Notes

- **OpenAI**: converted from `tiktoken` encodings (`o200k_base`, `cl100k_base`) to HuggingFace `tokenizer.json` format. GPT-4 and GPT-3.5 share the same `cl100k_base` vocabulary but have different default context lengths.
- **DeepSeek**: V4 was released on 2026-04-24 (`deepseek-ai/DeepSeek-V4-Pro` and `deepseek-ai/DeepSeek-V4-Flash`). Its tokenizer shares the same 128K BPE vocabulary and merges as V3, but adds ~465 new special tokens (including `<think>`, `</think>`, `<dsml:`, `</dsml:`, and multimodal placeholders). For token counting, V3 and V4 produce identical ids for ordinary text; only the special-token set differs.
- **Anthropic**: converted from the legacy `@anthropic-ai/tokenizer` (2023) `claude.json`. This is the only publicly available Anthropic tokenizer artifact; newer Claude 3/3.5/4 tokenizers have not been officially released.
- **Grok**: xAI has not officially released a `tokenizer.json`. Grok-1 ships a `tokenizer.model` (SentencePiece); Grok-2/3 tokenizers are not public. We will add Grok once a reliable source or conversion is available.
- **GLM-4**: The original `THUDM/glm-4-9b` and `ZhipuAI/glm-4-9b-chat` repos ship a custom `tokenization_chatglm.py` + `tokenizer.model` rather than a standard `tokenizer.json`. We use the HF-compatible `ZhipuAI/glm-4-9b-chat-hf` release, which provides a canonical `tokenizer.json` that matches the original tokenization.

## Download

```bash
# Get a single tokenizer
curl -L -o qwen2_5.tokenizer.json.xz \
  https://github.com/ljh-sh/tokenizer-json/releases/download/data/qwen2_5.tokenizer.json.xz
xz -d qwen2_5.tokenizer.json.xz
```

## Use with token-actuary

```bash
token-actuary count --tokenizer qwen2_5.tokenizer.json
```

## Use in browser

```javascript
// xz is not natively decompressable in browsers; use a WASM xz decoder or
// decompress server-side. The asset is xz because it is smaller than gzip.
const res = await fetch(
  'https://github.com/ljh-sh/tokenizer-json/releases/download/data/qwen2_5.tokenizer.json.xz'
);
```

## Add a tokenizer

### Open-source HuggingFace model

```bash
./scripts/sync.sh <id> <huggingface-repo>

# Example
./scripts/sync.sh qwen2_5 Qwen/Qwen2.5-7B-Instruct
```

Some repos (e.g., Qwen3, GLM-4) serve `tokenizer.json` via Git LFS or are not directly fetchable from the default HF mirror. Use `--modelscope` to download from the ModelScope mirror:

```bash
./scripts/sync.sh --modelscope qwen3 Qwen/Qwen3-0.6B
./scripts/sync.sh --modelscope glm ZhipuAI/glm-4-9b-chat-hf
```

### OpenAI tiktoken encoding

```bash
python3 scripts/convert-tiktoken.py gpt-4o -o data/gpt_4o.tokenizer.json
```

### Anthropic legacy tokenizer

Requires `tiktoken` and `node` with `tiktoken` + `@anthropic-ai/tokenizer` installed:

```bash
python3 scripts/convert-anthropic.py /path/to/claude.json -o data/claude.tokenizer.json
```

## Data plan

See [`docs/data-plan.md`](docs/data-plan.md) for size projections, storage strategy, and scaling guidance.

## License

- Code and metadata in this repository: Apache 2.0.
- Each tokenizer file retains the license of its originating model. See `data/<id>.tokenizer.json.src` for source and license links.
