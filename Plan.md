## 一、项目总目标

目标不是做一个“好看的笔记系统”，而是做一个：

- 以 `JSONL（JSON Lines，每行一个 JSON 对象）` 为真值层
- 以 `memo + image` 为唯一核心实体
- 以 `DuckDB（本地分析引擎） + Parquet（列式分析文件）` 为分析仓
- 可从原始 flomo 导出稳定重建
- 对脚本、LLM（Large Language Model，大语言模型）、人工抽查都低摩擦

非目标：

- 不保留 video / audio 为核心实体
- 不兼容旧的重 frontmatter（文档头元数据）Markdown 作为真值层
- 不把 Obsidian（黑曜石笔记软件）配置和导航页纳入核心层
- 不保留绝对路径
- 不为了“单条文件好看”污染 schema

---

## 二、目标目录结构

这是整个项目的固定目标，后面所有 prompt 都围绕它。

```text
memo_system/
├── raw/
│   └── <original flomo export folders>
├── store/
│   ├── memos.jsonl
│   ├── images.jsonl
│   ├── missing_images.jsonl
│   └── images/
│       └── YYYY/YYYY-MM/*.png
├── analytics/
│   ├── memos.parquet
│   ├── images.parquet
│   └── warehouse.duckdb
├── preview/
│   └── monthly_markdown/
├── scripts/
├── tests/
├── docs/
│   ├── schema.md
│   ├── migration.md
│   └── runbook.md
└── pyproject.toml
```

---

## 三、核心 schema

这是整个项目最重要的约束。
先定死，不然后面会越写越乱。

### 1) `memos.jsonl`

每行一条 memo。

```json
{
  "memo_uid": "flomo-isaacbao-20260301--0255",
  "created_at": "2026-03-04T13:06:44",
  "source_export": "2026/flomo@IsaacBao-20260301",
  "source_html": "2026/flomo@IsaacBao-20260301/IsaacBao的笔记.html",
  "source_memo_ordinal": 255,
  "body_md": "memo markdown body here",
  "image_count": 2
}
```

### 2) `images.jsonl`

每行一张图片。

```json
{
  "image_uid": "flomo-isaacbao-20260301--0255--01",
  "memo_uid": "flomo-isaacbao-20260301--0255",
  "order_in_memo": 1,
  "image_relpath": "store/images/2026/2026-03/flomo-isaacbao-20260301--0255--01.png",
  "source_relpath": "2026/flomo@IsaacBao-20260301/file/2026-03-04/1198733/146c43269a10922e56c749c7203e276c.png"
}
```

### 3) `missing_images.jsonl`

只记录异常。

```json
{
  "memo_uid": "flomo-isaacbao-20250101--0042",
  "image_uid": "flomo-isaacbao-20250101--0042--01",
  "source_relpath": "2025/flomo@IsaacBao-20250101/file/...",
  "reason": "source_file_missing"
}
```

### 4) 硬规则

- 真值层只允许相对路径
- 真值层只允许 `memo` 和 `image` 两种核心实体
- `month`、`year`、URL 列表、Obsidian 文件、绝对路径都只能派生，不能进真值层
- `body_md` 保留 Markdown 正文，但不保留旧 frontmatter
- `image_count` 必须等于 `images.jsonl` 中该 `memo_uid` 的关联记录数，除非存在 `missing_images.jsonl` 例外

---

## 四、开发计划总览

| 阶段    | 目标                   | 输出                                                |
| ------- | ---------------------- | --------------------------------------------------- |
| Phase 0 | 先写规范，不写业务代码 | `docs/schema.md`                                    |
| Phase 1 | 导入 raw 到 store      | `memos.jsonl` `images.jsonl` `missing_images.jsonl` |
| Phase 2 | 做校验器               | `validate_store.py` + 报告                          |
