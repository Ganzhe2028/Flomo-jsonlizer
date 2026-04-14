# Migration — 从旧 schema 到新 schema

本文档记录从旧格式（flomo HTML 导出 / 带 frontmatter 的 Markdown）到新 JSONL schema 的字段映射规则。

---

## 1. 数据源：flomo HTML 导出

flomo 的 HTML 导出是唯一数据源。旧 schema 指的是 flomo HTML 中隐含的数据结构。

### 1.1 HTML 中的 memo 结构

flomo 导出 HTML 中，每条 memo 是一个 DOM 节点，包含：

| 旧字段（HTML 中）                          | 提取方式                      | 新 schema 字段        | 映射规则                                        |
| ------------------------------------------ | ----------------------------- | --------------------- | ----------------------------------------------- |
| 时间标签（`<div class="time">` 或类似）    | 解析日期时间文本              | `created_at`          | 转为 ISO 8601：`YYYY-MM-DDTHH:MM:SS`            |
| 正文内容（`<div class="content">` 或类似） | HTML → Markdown 转换          | `body_md`             | 去除 frontmatter，保留 Markdown 正文            |
| 图片引用（`<img>` 标签）                   | 提取 `src` 属性               | `images.jsonl` 记录   | 生成 `image_uid`，复制文件，记录相对路径        |
| —                                          | 从导出文件夹名和出现顺序生成  | `memo_uid`            | `flomo-{user}-{batch}--{ordinal}`               |
| —                                          | 从导出文件夹路径              | `source_export`       | 去掉 `raw/` 前缀的相对路径                      |
| —                                          | 从 HTML 文件路径              | `source_html`         | 去掉 `raw/` 前缀的相对路径                      |
| —                                          | 从 HTML 中的出现顺序          | `source_memo_ordinal` | 按出现顺序从 1 递增                             |
| —                                          | 统计正文中的 `<img>` 标签数量 | `image_count`         | 等于 images + missing_images 中该 memo 的记录数 |

### 1.2 图片路径映射

| 旧路径（HTML img src）                                         | 新字段           | 映射规则                                     |
| -------------------------------------------------------------- | ---------------- | -------------------------------------------- |
| `file/2026-03-04/1198733/146c43269a10922e56c749c7203e276c.png` | `source_relpath` | 拼接导出批次前缀：`{source_export}/file/...` |
| —                                                              | `image_relpath`  | `store/images/YYYY/YYYY-MM/{image_uid}.png`  |
| —                                                              | `image_uid`      | `{memo_uid}--{order}`                        |

---

## 2. 旧 Markdown 格式（带 frontmatter）的迁移

如果之前有将 flomo 导出转为带 frontmatter Markdown 的中间格式，以下是其字段映射。

### 2.1 旧 frontmatter 字段映射

| 旧 frontmatter 字段      | 新 schema 字段                  | 映射规则                                                                           |
| ------------------------ | ------------------------------- | ---------------------------------------------------------------------------------- |
| `uid` / `id`             | `memo_uid`                      | 如果格式一致则直接使用，否则重新生成                                               |
| `date` / `created`       | `created_at`                    | 确保转为 ISO 8601 无时区格式                                                       |
| `tags`                   | —                               | **不进入真值层**。tag 信息可从 `body_md` 中的 `#tag` 提取，但只在 analytics 层使用 |
| `source`                 | `source_export` + `source_html` | 拆分为两个字段                                                                     |
| `images` / `attachments` | `images.jsonl` 记录             | 每个图片生成独立记录，不再嵌入 memo 记录                                           |
| `title`                  | —                               | **不进入真值层**。flomo 无标题概念                                                 |

### 2.2 正文映射

| 旧格式                               | 新格式                      | 处理方式                     |
| ------------------------------------ | --------------------------- | ---------------------------- |
| frontmatter 块（`---...---`）        | 删除                        | 不保留，不进入 `body_md`     |
| Markdown 正文                        | `body_md`                   | 原样保留，去除 frontmatter   |
| 图片引用（相对路径或绝对路径）       | `images.jsonl` 中的独立记录 | 提取路径，生成 image 记录    |
| 绝对路径（如 `/Users/.../file.png`） | 转为相对路径                | 去除项目根前缀，保留相对路径 |

---

## 3. 关键迁移规则

### 3.1 路径转换

| 旧格式              | 新格式           | 规则                                       |
| ------------------- | ---------------- | ------------------------------------------ |
| 绝对路径            | 相对路径         | 去除项目根目录前缀，转为相对于项目根的路径 |
| `raw/` 开头的路径   | 去掉 `raw/` 前缀 | 真值层字段不包含 `raw/` 前缀               |
| Windows 路径（`\`） | Unix 路径（`/`） | 统一使用 `/` 作为路径分隔符                |

### 3.2 不迁移的内容

| 内容          | 原因                       | 去处                          |
| ------------- | -------------------------- | ----------------------------- |
| video / audio | 非核心实体                 | 不迁移                        |
| tag 统计      | 派生数据，不属于真值层     | analytics 层可从 body_md 提取 |
| URL 列表      | 派生数据，不属于真值层     | analytics 层可从 body_md 提取 |
| Obsidian 配置 | 外部工具配置，不属于数据层 | 不迁移                        |

### 3.3 UID 一致性

- 如果旧格式中已有符合新规则的 `uid`，直接复用，不重新生成。
- 如果旧 `uid` 格式不一致，按新规则重新生成，并在迁移日志中记录映射关系。

---

## 4. 迁移执行

迁移本质上就是 Phase 1 的 `import_raw.py` 脚本。不存在单独的迁移脚本——从 HTML 源重新导入就是最干净的迁移路径。

如果需要从旧 Markdown 格式迁移（而非从 HTML 源重新导入），需要额外编写迁移脚本，按上表映射字段，但这种方式**不被推荐**——应优先从 HTML 源重新导入。
