# 现代程序设计：Bash、Git、Vibe Coding 与 Specification 编写

这是一个 16 课时、8 周、每周 2 课时的 Jupyter Notebook 课程仓库。课程面向希望系统掌握现代编程工作流的学习者，内容从命令行基础开始，逐步进入版本控制、AI 辅助编程（Vibe Coding）和 specification 编写机器。

## 仓库结构

- `books/`：课程 Notebook 与 Markdown 页面。
- `codes/`：课程示例代码与可复用脚本。
- `papers/`：参考论文、文章或外部资料。
- `slides/`：课堂讲义或演示材料。
- `_build/books/`：本地构建产物，由构建脚本生成。

## 课程主线

1. Bash：文件系统、管道、重定向、脚本与自动化。
2. Git：提交、分支、合并、冲突处理与协作工作流。
3. Vibe Coding：用 AI 进行探索式实现、调试、重构与验证。
4. Specification 编写机器：把需求、约束、验收标准和测试转化为可执行的软件规格。

## 构建与预览

构建静态书籍：

```bash
./book_generate.sh
```

本地预览：

```bash
./book_start.sh
```

默认预览地址为 `http://127.0.0.1:8000`。
