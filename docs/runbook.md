# Runbook — 操作手册

本文档定义从原始 flomo 导出到全量重建的完整操作流程。每个步骤对应一个脚本或一组命令，按顺序执行即可。

---

## 1. 前置条件

- Python 3.11+
- 依赖已安装：`pip install -e ".[dev]"`
- `raw/` 目录中已放置 flomo 导出文件夹

### raw/ 目录结构预期

```
raw/
└── YYYY/
    └── flomo@{User}-{YYYYMMDD}/
        ├── {User}的笔记.html
        └── file/
            └── YYYY-MM-DD/
                └── {hash_id}/
                    └── {filename}.png
```

每个导出批次是一个顶层文件夹，内含一个 HTML 文件和一个 `file/` 目录（存放图片）。

---

## 2. Step 1 — 原始导入（raw → store）

### 命令

```bash
python scripts/import_raw.py --raw-dir raw/ --store-dir store/
```

### 行为

1. 扫描 `raw/` 下所有 `flomo@*/` 文件夹
2. 解析每个 HTML 文件，提取所有 memo（按 HTML 中的出现顺序编号）
3. 对每个 memo：
   - 生成 `memo_uid`：`flomo-{user}-{export_batch}--{ordinal}`
   - 提取 `created_at`（从 HTML 中的时间标签）
   - 将 HTML 正文转为 Markdown 写入 `body_md`（去除 frontmatter）
   - 统计正文中引用的图片数量，写入 `image_count`
4. 对每个图片引用：
   - 在 `raw/` 中查找对应物理文件
   - 文件存在 → 写入 `images.jsonl`，复制文件到 `store/images/YYYY/YYYY-MM/{image_uid}.png`
   - 文件缺失 → 写入 `missing_images.jsonl`
5. 追加写入 `memos.jsonl`、`images.jsonl`、`missing_images.jsonl`

### 前置条件

- `raw/` 目录结构符合预期
- `store/` 目录已创建（项目骨架已包含）

### 输出

- `store/memos.jsonl` — 所有 memo 记录
- `store/images.jsonl` — 所有图片记录
- `store/missing_images.jsonl` — 所有缺失图片记录
- `store/images/YYYY/YYYY-MM/*.png` — 归档后的图片文件

### 注意

- 此步骤会覆盖已有的 JSONL 文件（全量模式，非增量）
- `raw/` 中的文件不会被修改

---

## 3. Step 2 — 真值层校验

### 命令

```bash
python scripts/validate_store.py --store-dir store/
```

### 行为

逐条检查 schema.md 中定义的 C1–C11 约束，输出校验报告。

### 校验项

| 编号 | 检查内容                                                      | 严重级别 |
| ---- | ------------------------------------------------------------- | -------- |
| C1   | `memo_uid` 唯一性                                             | ERROR    |
| C2   | `image_uid` 唯一性                                            | ERROR    |
| C3   | `image_count` 与实际关联记录数一致                            | ERROR    |
| C4   | `images.jsonl.memo_uid` 引用完整性                            | ERROR    |
| C5   | `missing_images.jsonl.memo_uid` 引用完整性                    | ERROR    |
| C6   | 同一 `image_uid` 不在 images 和 missing_images 中同时出现     | ERROR    |
| C7   | 所有路径字段为相对路径                                        | ERROR    |
| C8   | `image_relpath` 指向的文件存在                                | WARNING  |
| C9   | `source_relpath` 在 images 中存在、在 missing_images 中不存在 | WARNING  |
| C10  | `created_at` 格式合法                                         | ERROR    |
| C11  | `body_md` 不含 frontmatter                                    | WARNING  |

### 输出

- 终端输出校验报告摘要
- 如有 ERROR 级别违规，脚本以非零退出码退出

### 成功标准

- 0 个 ERROR
- WARNING 需列在报告中，但不阻塞流程

---

## 4. Step 3 — Analytics 构建（store → analytics）

### 命令

```bash
python scripts/build_analytics.py --store-dir store/ --analytics-dir analytics/
```

### 行为

1. 读取 `memos.jsonl` 和 `images.jsonl`
2. 转换为 Parquet 格式：
   - `analytics/memos.parquet`
   - `analytics/images.parquet`
3. 创建 DuckDB 数据库 `analytics/warehouse.duckdb`：
   - 导入 Parquet 文件为表
   - 创建常用视图（按月统计、按图片数分布等）

### 输出

- `analytics/memos.parquet`
- `analytics/images.parquet`
- `analytics/warehouse.duckdb`

### 注意

- analytics 层是纯派生，可从 store 完全重建
- 每次构建会覆盖已有文件

---

## 5. Step 4 — Preview 构建（store → preview）

### 命令

```bash
python scripts/build_preview.py --store-dir store/ --preview-dir preview/
```

### 行为

1. 读取 `memos.jsonl`
2. 按 `created_at` 的年月分组
3. 每个月生成一个 Markdown 文件，包含该月所有 memo

### 输出

- `preview/monthly_markdown/YYYY-MM.md`

### 注意

- preview 层是纯派生，可从 store 完全重建
- 生成文件仅供人工浏览，不作为任何脚本的数据源

---

## 6. 全量重建

当 store 层数据需要完全重建时，按以下顺序执行：

```bash
# 1. 清理 store 和 analytics（保留 raw/ 不动）
rm -f store/memos.jsonl store/images.jsonl store/missing_images.jsonl
rm -rf store/images/
rm -rf analytics/
rm -rf preview/

# 2. 重建空目录
mkdir -p store/images analytics preview/monthly_markdown

# 3. 从 raw 重新导入
python scripts/import_raw.py --raw-dir raw/ --store-dir store/

# 4. 校验
python scripts/validate_store.py --store-dir store/

# 5. 构建 analytics
python scripts/build_analytics.py --store-dir store/ --analytics-dir analytics/

# 6. 构建 preview
python scripts/build_preview.py --store-dir store/ --preview-dir preview/
```

### 重建原则

- `raw/` 是唯一的数据源头，永不动
- `store/` 可从 `raw/` 完全重建
- `analytics/` 可从 `store/` 完全重建
- `preview/` 可从 `store/` 完全重建
- 重建顺序：raw → store → analytics/preview（后两者可并行）

---

## 7. 故障排查

| 现象                           | 可能原因                    | 处理方式                            |
| ------------------------------ | --------------------------- | ----------------------------------- |
| 校验报 C3 不通过               | 导入时 image_count 计算错误 | 重新运行 import_raw.py              |
| 校验报 C8 图片文件不存在       | 复制图片时目标路径错误      | 检查 `image_relpath` 格式，重新导入 |
| 校验报 C9 source 文件缺失      | raw/ 中确实缺文件           | 确认是否应归入 missing_images.jsonl |
| DuckDB 查询结果与 JSONL 不一致 | Parquet 构建有误            | 重新运行 build_analytics.py         |
