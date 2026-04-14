# Schema 定义

本文档定义 JSONL 真值层的完整 schema。所有导入脚本、校验器、分析仓构建都必须遵守此规范。

---

## 1. 核心实体

真值层只允许两种核心实体：

| 实体  | 文件                 | 说明              |
| ----- | -------------------- | ----------------- |
| memo  | `store/memos.jsonl`  | 一条 flomo 笔记   |
| image | `store/images.jsonl` | memo 中的一张图片 |

异常实体：

| 实体          | 文件                         | 说明               |
| ------------- | ---------------------------- | ------------------ |
| missing_image | `store/missing_images.jsonl` | 图片文件缺失的记录 |

---

## 2. memos.jsonl

每行一个 JSON 对象，代表一条 memo。

### 字段定义

| 字段                  | 类型      | 必填 | 约束                                                                      |
| --------------------- | --------- | ---- | ------------------------------------------------------------------------- |
| `memo_uid`            | `string`  | 是   | 主键。格式：`flomo-{user}-{export_batch}--{ordinal}`                      |
| `created_at`          | `string`  | 是   | ISO 8601 日期时间，无时区后缀。格式：`YYYY-MM-DDTHH:MM:SS`                |
| `source_export`       | `string`  | 是   | 相对路径，指向 raw/ 下的导出批次根目录。格式：`YYYY/flomo@{User}-{batch}` |
| `source_html`         | `string`  | 是   | 相对路径，指向 raw/ 下的 HTML 源文件                                      |
| `source_memo_ordinal` | `integer` | 是   | 该 memo 在源 HTML 中的出现顺序，从 1 开始                                 |
| `body_md`             | `string`  | 是   | Markdown 正文。不包含 frontmatter，不包含 UID 行                          |
| `image_count`         | `integer` | 是   | 必须等于 `images.jsonl` 中该 `memo_uid` 的关联记录数（见约束 C3）         |

### 示例

```json
{
  "memo_uid": "flomo-exampleuser-20260301--0255",
  "created_at": "2026-03-04T13:06:44",
  "source_export": "2026/flomo@ExampleUser-20260301",
  "source_html": "2026/flomo@ExampleUser-20260301/ExampleUser的笔记.html",
  "source_memo_ordinal": 255,
  "body_md": "今天读到一段话很有感触……",
  "image_count": 2
}
```

---

## 3. images.jsonl

每行一个 JSON 对象，代表 memo 中的一张图片。

### 字段定义

| 字段             | 类型      | 必填 | 约束                                                                                           |
| ---------------- | --------- | ---- | ---------------------------------------------------------------------------------------------- |
| `image_uid`      | `string`  | 是   | 主键。格式：`{memo_uid}--{order}`，order 两位零填充                                            |
| `memo_uid`       | `string`  | 是   | 外键，指向 `memos.jsonl.memo_uid`                                                              |
| `order_in_memo`  | `integer` | 是   | 图片在 memo 正文中出现的顺序，从 1 开始                                                        |
| `image_relpath`  | `string`  | 是   | 相对路径，指向 `store/images/` 下的物理文件。格式：`store/images/YYYY/YYYY-MM/{image_uid}.png` |
| `source_relpath` | `string`  | 是   | 相对路径，指向 raw/ 下的原始图片文件                                                           |

### 示例

```json
{
  "image_uid": "flomo-exampleuser-20260301--0255--01",
  "memo_uid": "flomo-exampleuser-20260301--0255",
  "order_in_memo": 1,
  "image_relpath": "store/images/2026/2026-03/flomo-exampleuser-20260301--0255--01.png",
  "source_relpath": "2026/flomo@ExampleUser-20260301/file/2026-03-04/1198733/146c43269a10922e56c749c7203e276c.png"
}
```

---

## 4. missing_images.jsonl

每行一个 JSON 对象，记录原始导出中引用但文件不存在的图片。

### 字段定义

| 字段             | 类型     | 必填 | 约束                                                  |
| ---------------- | -------- | ---- | ----------------------------------------------------- |
| `memo_uid`       | `string` | 是   | 外键，指向 `memos.jsonl.memo_uid`                     |
| `image_uid`      | `string` | 是   | 预分配的 image UID（格式同 `images.jsonl.image_uid`） |
| `source_relpath` | `string` | 是   | 相对路径，指向 raw/ 下应当存在但缺失的文件            |
| `reason`         | `string` | 是   | 枚举值：`source_file_missing`                         |

### 示例

```json
{
  "memo_uid": "flomo-exampleuser-20250101--0042",
  "image_uid": "flomo-exampleuser-20250101--0042--01",
  "source_relpath": "2025/flomo@ExampleUser-20250101/file/2025-01-03/55321/abcdef1234567890.png",
  "reason": "source_file_missing"
}
```

---

## 5. 主键与外键关系

```text
memos.jsonl
  memo_uid  ←── 主键

images.jsonl
  image_uid ←── 主键
  memo_uid  ←── 外键 → memos.jsonl.memo_uid

missing_images.jsonl
  (memo_uid, image_uid) ←── 联合唯一
  memo_uid  ←── 外键 → memos.jsonl.memo_uid
```

关系说明：

- 一个 memo 可以有 0~N 张图片（1 对多）
- 一个 memo 可以有 0~N 条 missing_image 记录
- 同一个 `image_uid` 不能同时出现在 `images.jsonl` 和 `missing_images.jsonl` 中
- `images.jsonl` 和 `missing_images.jsonl` 中同一 `memo_uid` 的记录总数，应与 `memos.jsonl` 中该 memo 的 `image_count` 一致

---

## 6. UID 命名规则

### memo_uid

```text
flomo-{user}-{export_batch}--{ordinal}
```

| 片段           | 说明                                       | 示例       |
| -------------- | ------------------------------------------ | ---------- |
| `user`         | flomo 用户名，lowercase，空格去除          | `exampleuser` |
| `export_batch` | 导出批次标识，通常为 `YYYYMMDD`            | `20260301` |
| `ordinal`      | memo 在该批次中的顺序号，零填充至至少 4 位 | `0255`     |

分隔符：`--`（双连字符）分隔批次前缀与序号。

### image_uid

```text
{memo_uid}--{order}
```

| 片段    | 说明                                                   | 示例 |
| ------- | ------------------------------------------------------ | ---- |
| `order` | 图片在 memo 中的出现顺序，从 1 开始，零填充至至少 2 位 | `01` |

---

## 7. 路径规则

### 7.1 总则

- **真值层所有路径均为相对路径**，相对于项目根目录 `memo_system/`。
- **绝对路径禁止进入真值层**。任何脚本不得将绝对路径写入 JSONL 文件。

### 7.2 source_export / source_html / source_relpath

- 以 `raw/` 下的相对路径为基准，但字段值不包含 `raw/` 前缀。
- 示例：源文件位于 `raw/2026/flomo@ExampleUser-20260301/`，则 `source_export` 值为 `2026/flomo@ExampleUser-20260301`。

### 7.3 image_relpath

- 物理文件存放于 `store/images/YYYY/YYYY-MM/` 目录下。
- 文件名与 `image_uid` 一致，扩展名为 `.png`。
- 示例：`store/images/2026/2026-03/flomo-exampleuser-20260301--0255--01.png`

### 7.4 raw/ 目录

- `raw/` 目录下的文件永远只读，任何脚本不得修改、删除、移动 `raw/` 中的文件。
- 如果需要修正原始数据，在 `store/` 层处理，`raw/` 保持原样。

---

## 8. 硬约束（C 系列编号，用于校验器引用）

| 编号 | 约束                                                                                                                                                                                           |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1   | `memo_uid` 在 `memos.jsonl` 中唯一                                                                                                                                                             |
| C2   | `image_uid` 在 `images.jsonl` 中唯一                                                                                                                                                           |
| C3   | `memos.image_count` == `images.jsonl` 中该 `memo_uid` 的记录数 + `missing_images.jsonl` 中该 `memo_uid` 的记录数。`image_count` 统计的是 memo 在原始 HTML 中引用的图片总数，无论源文件是否存在 |
| C4   | `images.jsonl.memo_uid` 必须在 `memos.jsonl` 中存在（引用完整性）                                                                                                                              |
| C5   | `missing_images.jsonl.memo_uid` 必须在 `memos.jsonl` 中存在（引用完整性）                                                                                                                      |
| C6   | 同一 `image_uid` 不能同时出现在 `images.jsonl` 和 `missing_images.jsonl` 中                                                                                                                    |
| C7   | 真值层所有路径字段均为相对路径，不含绝对路径                                                                                                                                                   |
| C8   | `images.jsonl.image_relpath` 指向的物理文件必须存在                                                                                                                                            |
| C9   | `images.jsonl.source_relpath` 或 `missing_images.jsonl.source_relpath` 指向的 raw/ 文件：前者必须存在，后者必须不存在                                                                          |
| C10  | `created_at` 必须符合 ISO 8601 格式 `YYYY-MM-DDTHH:MM:SS`，无时区后缀                                                                                                                          |
| C11  | `body_md` 不包含 frontmatter 块（`---` 分隔的 YAML 头部）                                                                                                                                      |

---

## 9. 非目标与禁止事项

### 9.1 不进入真值层的内容

以下内容只能存在于派生层（analytics/ 或 preview/），不得写入 JSONL 真值层：

- `month`、`year` 等时间维度字段（从 `created_at` 派生）
- URL 列表或域名统计（从 `body_md` 提取）
- Obsidian 配置、导航页、模板
- 任何绝对路径
- video / audio 文件引用

### 9.2 真值层格式禁止

- 禁止使用带 frontmatter 的 Markdown 作为真值格式
- 禁止为了"单条文件好看"（如每条 memo 一个 `.md` 文件）而污染 schema
- 禁止在 JSONL 中存储非核心实体的数据（如 tag 统计、链接图等）

### 9.3 不支持的功能

- video / audio 作为核心实体
- 增量导入（当前为全量重建模式）
- 多用户合并（当前按导出批次隔离）
