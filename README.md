# 现代智能编程开发实践

本仓库是“现代智能编程开发实践”课程的 Jupyter Notebook 书稿。课程用 8 周、16 课时讲解现代软件开发的基础工作流：先掌握 Shell、Git、VSCode 和 Python 环境，再学习如何把 AI 工具纳入理解、实现、调试、重构和验证过程。

## 课程目标

- 能在命令行中完成文件、文本、进程和项目管理任务。
- 能用 Git 组织个人开发历史，并处理基础协作场景。
- 能配置 VSCode、Python 环境和远程开发工作流。
- 能把 AI 工具用于读代码、写代码、调试、重构和补测试。
- 能编写清晰、可验证、可迭代的 specification，并连接到代码实现和验收测试。

## 课程主线

- Shell 入门：WSL 安装、Shell 命令、文件系统、文件查看与编辑、管道与重定向、环境变量、Shell 脚本。
- VSCode：VSCode 安装、基础配置、插件管理、SSH 远程访问。
- Python 环境管理：Python、Conda、虚拟环境、`PYTHONPATH`、依赖安装。
- Git 版本管理：提交、分支、合并、冲突、远程协作、代码审查。
- 大模型简介：大模型基本原理、API 调用、在 Python 中调用大模型。
- AI Agent：从零开始构建一个简单 AI Agent。
- AI Coding Agent：用 AI 辅助读代码、写代码、调试、重构和补测试。
- 项目实战：从需求、specification、实现到验证的完整小项目。

## 仓库结构

- `books/`：课程正文、Notebook、章节说明和补充阅读材料。
- `codes/`：课程代码示例或课堂练习代码。
- `slides/`：课程幻灯片素材。
- `papers/`：大模型或 AI Agent 章节需要参考的论文和资料。
- `book_generate.sh`：生成 Jupyter Book 聚合源或静态网站。
- `book_start.sh`：启动本地预览服务。

## 构建与预览

生成静态网站：

```bash
./book_generate.sh
```

只生成聚合源，不构建 HTML：

```bash
./book_generate.sh ./books ./_build/books source
```

本地预览：

```bash
./book_start.sh
```

默认预览地址为 `http://127.0.0.1:8000`。Shell 入门章节可访问 `http://127.0.0.1:8000/books/shell`。

