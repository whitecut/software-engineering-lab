# 软件工程实验二 · 酒店预订系统（Git 记录）

本仓库用于记录实验二从 **AI 生成稿** 到 **人工修改稿** 的变化，便于检查和对比。

## 分支与标签

- 分支：`lab2`
- `lab2-ai-draft`：AI 生成的报告初稿（含 4 张 UML 图、12 张 UI 界面）
- `lab2-final`：人工修改后的最终版本

## 查看人工修改

```bash
git diff lab2-ai-draft lab2-final -- 实验报告.md
```

或查看统计：

```bash
git diff --stat lab2-ai-draft lab2-final
```

## 仓库内容

| 内容 | 路径 |
|---|---|
| 实验报告（Markdown） | `实验报告.md` |
| UML 图（4 张，.puml + .png） | `UML/` |
| UI 界面（12 张） | `UI界面/` |
| 最终提交压缩包 | `实验2_241220081_刘子健.zip` |

## 说明

- AI 初稿由 DeepSeek + PlantUML + HTML/CSS 生成（2026-11-13）。
- 人工修改集中在：报告标题与署名、第 1.1/1.2/3.1 节措辞、第 4 章 AI 使用说明的重写、删除第 5 章与附录，以及少量表格用词调整。
- 具体差异以 `git diff lab2-ai-draft lab2-final` 为准。
