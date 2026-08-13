# tokenizer-json 数据规划

> 本仓库专门收录开源 LLM 的 `tokenizer.json`，供 `token-actuary` 等工具按需加载。

## 1. 当前规模

| 模型 | 文件 | 原始大小 | gzip 后 |
|---|---|---|---|
| Qwen2.5-7B-Instruct | `qwen2_5.tokenizer.json` | 6.7 MB | ~1.7 MB |
| DeepSeek-V3 | `deepseek_v3.tokenizer.json` | 7.5 MB | ~1.9 MB |
| Meta-Llama-3-8B (via NousResearch) | `llama3.tokenizer.json` | 8.7 MB | ~2.2 MB |
| Mistral-7B-Instruct-v0.3 | `mistral_v3.tokenizer.json` | 1.9 MB | ~0.5 MB |
| **合计** | | **~24.8 MB** | **~6.3 MB** |

## 2. 增长预测

### 2.1 单文件大小

- 小型 tokenizer（BPE/WordPiece，vocab 32K–64K）：1–3 MB
- 中型 tokenizer（vocab 100K–128K）：5–8 MB
- 大型 tokenizer（vocab 200K+，含大量 added tokens）：8–15 MB

### 2.2 收录数量

| 阶段 | 模型数量 | 原始数据估算 | gzip 后估算 |
|---|---|---|---|
| 当前 | 4 | 25 MB | 6 MB |
| 短期（10 个主流模型） | 10 | 60–80 MB | 15–20 MB |
| 中期（30 个模型/系列） | 30 | 200–300 MB | 50–80 MB |
| 长期（100+ 模型/版本） | 100 | 700 MB–1.5 GB | 200–400 MB |

## 3. 存储策略

### 3.1 原始文件存仓库（当前方案）

用户要求：`data/<model>.tokenizer.json` 直接同步在仓库中。

**优点**：
- 简单直接，用户/CI 可直接 `git clone` 获取。
- 与模型版本一一对应，便于审计和溯源。

**风险**：
- Git 仓库体积随历史提交线性增长。
- 如果 tokenizer 文件更新（如新版模型修正 added_tokens），旧版本仍保留在 git 历史中。
- GitHub 对普通仓库没有硬性大小限制，但建议控制在 1 GB 以下；超过 5 GB 会收到警告。

### 3.2 压缩发布（推荐）

**Release assets**：每次更新时，通过 GitHub Actions 生成并上传：
- `tokenizers.tar.gz`：所有 tokenizer.json 的 gzip 压缩包
- 或每个模型单独发布 `<model>.tokenizer.json.gz`

**优点**：
- 仓库本身保持较小（仅保留原始文件）。
- 下游工具/前端可直接下载压缩包，减少传输。
- 适合 `token-actuary` WASM 场景：前端 fetch `.gz` 后浏览器解压。

### 3.3 Git LFS（备选）

如果仓库原始数据超过 200 MB，建议启用 Git LFS：
- `data/*.tokenizer.json` 走 LFS。
- 仓库本身只保留指针文件，克隆更快。

**缺点**：
- 增加使用复杂度（需要安装 git-lfs）。
- GitHub LFS 有带宽和存储配额限制。

## 4. 命名与目录规范

```
data/
├── <model>.tokenizer.json          # 原始 tokenizer.json
├── <model>.tokenizer.json.sha256   # 校验和（可选）
└── <model>.tokenizer.json.src       # 来源说明（可选）
```

命名规则：
- 使用小写字母、数字、下划线。
- 格式：`<model_family>_<version>.tokenizer.json`
- 示例：`qwen2_5.tokenizer.json`, `llama3.tokenizer.json`, `deepseek_v3.tokenizer.json`

## 5. 同步与校验

### 5.1 同步脚本

提供 `scripts/sync.sh`，记录来源并自动下载：

```bash
./scripts/sync.sh qwen2_5 https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct/raw/main/tokenizer.json
```

### 5.2 CI 校验

每次 PR 检查：
- 所有 `.tokenizer.json` 是合法 JSON。
- 能被 `tokenizers.Tokenizer.from_file()` 加载。
- 文件大小不超过 20 MB。
- 新增文件必须附带 `SOURCE` 行（说明来源和许可证）。

## 6. 推荐演进路线

| 阶段 | 数据量 | 策略 |
|---|---|---|
| 现在 | < 50 MB | 原始文件直接存仓库，同时用 Release 发布 gzip 包 |
| 50–200 MB | 开启 Release assets 为主，原始文件仍存仓库 |
| > 200 MB | 评估 Git LFS；或拆分按模型家族拆分子仓库 |
| > 1 GB | 必须拆分子仓库 / 用 LFS / 仅保留 Release assets |

## 7. 与 token-actuary 的集成

```bash
# 用户可以直接从 release 下载
curl -L https://github.com/ljh-sh/tokenizer-json/releases/latest/download/qwen2_5.tokenizer.json.gz \
  | gunzip > qwen2_5.tokenizer.json

# WASM 前端直接 fetch .gz 并在浏览器解压
fetch('https://github.com/ljh-sh/tokenizer-json/releases/latest/download/qwen2_5.tokenizer.json.gz')
```

## 8. 版权与许可证

每个 `data/<model>.tokenizer.json` 必须附带来源说明。tokenizer 文件通常遵循对应模型的许可证：
- Qwen2.5: Tongyi Qianwen License / Apache-2.0
- DeepSeek-V3: DeepSeek License
- Llama3: Llama 3 Community License
- Mistral: Apache-2.0

本仓库不修改原始 tokenizer 内容，仅做镜像收录。
