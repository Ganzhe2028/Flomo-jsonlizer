# Runbook — 操作手册

本文档定义从原始 flomo 导出到全量重建的完整操作流程。每个步骤对应一个脚本或一组命令，按顺序执行即可。

---

## 1. 前置条件

- Python 3.11+
- 依赖已安装：`pip install -e ".[dev]"`
- 推荐先使用 `examples/raw/` 中的匿名示例数据验证流程

### 示例数据目录结构（推荐）

```text
examples/raw/
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
python scripts/build_store.py --raw-root examples/raw --store-root tmp/example-store
```

### 行为

1. 扫描 `examples/raw/` 下所有 `flomo@*/` 文件夹
2. 解析每个 HTML 文件，提取所有 memo（按 HTML 中的出现顺序编号）
3. 对每个 memo：
   - 生成 `memo_uid`：`flomo-{user}-{export_batch}--{ordinal}`
   - 提取 `created_at`（从 HTML 中的时间标签）
   - 将 HTML 正文转为 Markdown 写入 `body_md`（去除 frontmatter）
   - 统计正文中引用的图片数量，写入 `image_count`
4. 对每个图片引用：
   - 在 `examples/raw/` 中查找对应物理文件
   - 文件存在 → 写入 `images.jsonl`，复制文件到 `{store-root}/images/YYYY/YYYY-MM/{image_uid}.png`
   - 文件缺失 → 写入 `missing_images.jsonl`
5. 输出 `memos.jsonl`、`images.jsonl`、`missing_images.jsonl`

### 前置条件

- `examples/raw/` 目录结构符合预期
- `tmp/example-store/` 可由脚本自动创建

### 输出

- `tmp/example-store/memos.jsonl` — 所有 memo 记录
- `tmp/example-store/images.jsonl` — 所有图片记录
- `tmp/example-store/missing_images.jsonl` — 所有缺失图片记录
- `tmp/example-store/images/YYYY/YYYY-MM/*` — 归档后的图片文件

### 注意

- 此步骤会覆盖已有的 JSONL 文件（全量模式，非增量）
- `examples/raw/` 中的文件不会被修改

---

## 3. Step 2 — 真值层校验

### 命令

```bash
python scripts/validate_store.py --store-root tmp/example-store
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
python scripts/build_analytics.py --store-root tmp/example-store --analytics-dir tmp/example-analytics
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

- `tmp/example-analytics/memos.parquet`
- `tmp/example-analytics/images.parquet`
- `tmp/example-analytics/warehouse.duckdb`

### 注意

- analytics 层是纯派生，可从 store 完全重建
- 每次构建会覆盖已有文件

---

## 5. Step 4 — Preview 构建（store → preview）

### 命令

```bash
python scripts/build_preview.py --store-root tmp/example-store --preview-dir tmp/example-preview
```

### 行为

1. 读取 `memos.jsonl`
2. 按 `created_at` 的年月分组
3. 每个月生成一个 Markdown 文件，包含该月所有 memo

### 输出

- `tmp/example-preview/monthly_markdown/YYYY-MM.md`

### 注意

- preview 层是纯派生，可从 store 完全重建
- 生成文件仅供人工浏览，不作为任何脚本的数据源

---

## 6. 全量重建

当 store 层数据需要完全重建时，按以下顺序执行：

```bash
# 1. 清理示例输出目录（保留 examples/raw/ 不动）
rm -rf tmp/example-store tmp/example-analytics tmp/example-preview

# 2. 从示例数据重新导入
python scripts/build_store.py --raw-root examples/raw --store-root tmp/example-store

# 3. 校验
python scripts/validate_store.py --store-root tmp/example-store

# 4. 构建 analytics
python scripts/build_analytics.py --store-root tmp/example-store --analytics-dir tmp/example-analytics

# 5. 构建 preview
python scripts/build_preview.py --store-root tmp/example-store --preview-dir tmp/example-preview
```

### 重建原则

- `examples/raw/` 是示例数据源头，永不动
- `tmp/example-store/` 可从 `examples/raw/` 完全重建
- `tmp/example-analytics/` 可从 `tmp/example-store/` 完全重建
- `tmp/example-preview/` 可从 `tmp/example-store/` 完全重建
- 重建顺序：examples/raw → example-store → example-analytics/example-preview（后两者可并行）

---

## 7. macOS Launcher — Memo Sync

Spotlight 可搜索并启动的 GUI 工具，一键执行 validate → build 流程。

### 依赖

- [swiftDialog](https://swiftdialog.app/) — GUI 状态窗
- Python 3.11+ 及项目依赖（beautifulsoup4 等）

### 安装 swiftDialog

```bash
brew install swiftdialog
```

### 编译 Launcher App

```bash
tools/apple/build_app.sh
# 或指定输出目录：
tools/apple/build_app.sh ~/Applications
```

默认输出到 `~/Applications/Memo Sync.app`。

### 通过 Spotlight 启动

1. 打开 Spotlight（⌘ + Space）
2. 输入 "Memo Sync"
3. 回车启动

### 行为流程

1. 弹出 swiftDialog 状态窗
2. 自动运行 `validate_store.py --store-root store`
3. 校验通过 → 自动运行 `build_store.py --raw-root raw --store-root store`
4. 校验失败 → Build 跳过，窗口显示失败日志尾部
5. 完成后可点击按钮：
   - **Open Cursor** → 用 Cursor 打开项目目录（无 Cursor 则降级为 Finder）
   - **Open Finder** → 用 Finder 打开项目目录

### 文件结构

```
scripts/launch_memo_sync.sh   # Shell helper：执行 pipeline + 更新 GUI
tools/apple/
  Memo Sync.applescript        # AppleScript 源码
  build_app.sh                 # 编译 .app 的脚本
```

### 注意

- Shell helper 根据自身位置推导项目根目录，不需要手写绝对路径
- swiftDialog 未安装时会弹出错误提示，不会静默失败
- 项目路径变更后需要重新编译 .app（`build_app.sh` 会注入路径）

---

## 8. 故障排查

| 现象                           | 可能原因                    | 处理方式                            |
| ------------------------------ | --------------------------- | ----------------------------------- |
| 校验报 C3 不通过               | 导入时 image_count 计算错误 | 重新运行 build_store.py             |
| 校验报 C8 图片文件不存在       | 复制图片时目标路径错误      | 检查 `image_relpath` 格式，重新导入 |
| 校验报 C9 source 文件缺失      | examples/raw/ 中确实缺文件  | 确认是否应归入 missing_images.jsonl |
| DuckDB 查询结果与 JSONL 不一致 | Parquet 构建有误            | 重新运行 build_analytics.py         |
