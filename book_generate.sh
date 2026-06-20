#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOKS_DIR="${1:-"$SCRIPT_DIR/books"}"
OUTPUT_DIR="${2:-"$SCRIPT_DIR/_build/books"}"
BUILD_MODE="${3:-directory}"
GENERATED_ROOT="$SCRIPT_DIR/.jupyter-book-generated"
AGGREGATE_SOURCE_DIR="$GENERATED_ROOT/books-directory"
DEFAULT_MYST_TEMPLATE_DIR="$SCRIPT_DIR/.myst-templates/book-theme"
LOCAL_MYST_TEMPLATE_DIR="${MYST_SITE_TEMPLATE_DIR:-"$DEFAULT_MYST_TEMPLATE_DIR"}"
ANNBOOK_BOOK_TITLE="${ANNBOOK_BOOK_TITLE:-现代智能编程开发实践}"
ANNBOOK_BOOK_AUTHOR="${ANNBOOK_BOOK_AUTHOR:-Modern Programming Course}"

usage() {
  cat <<'EOF'
Usage: ./book_generate.sh [BOOKS_DIR] [OUTPUT_DIR] [MODE]

MODE:
  directory  Build one Jupyter Book that contains all notebooks under BOOKS_DIR.
  source     Generate the aggregate Jupyter Book source only; do not build HTML.
  books      Build each direct child directory under BOOKS_DIR as a separate book.

Defaults:
  BOOKS_DIR  ./books
  OUTPUT_DIR ./_build/books
  MODE       directory

Environment:
  ANNBOOK_BOOK_TITLE   Book title for aggregate directory/source builds.
  ANNBOOK_BOOK_AUTHOR  Author name written into generated MyST config.
  MYST_SITE_TEMPLATE_DIR
                        Local MyST template directory. Defaults to
                        ./.myst-templates/book-theme.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if command -v jupyter-book >/dev/null 2>&1; then
  JB_CMD=(jupyter-book)
elif python3 -c 'import jupyter_book' >/dev/null 2>&1; then
  JB_CMD=(python3 -m jupyter_book)
else
  echo "Error: jupyter-book is not installed." >&2
  echo "Install it with: python3 -m pip install -U jupyter-book" >&2
  exit 1
fi

if [[ ! -d "$BOOKS_DIR" ]]; then
  echo "Error: books directory not found: $BOOKS_DIR" >&2
  exit 1
fi

site_template_for() {
  local book_dir="$1"

  if [[ ! -f "$LOCAL_MYST_TEMPLATE_DIR/template.yml" ]]; then
    echo "Error: local MyST template not found: $LOCAL_MYST_TEMPLATE_DIR/template.yml" >&2
    echo "Set MYST_SITE_TEMPLATE_DIR to a directory containing template.yml." >&2
    exit 1
  fi

  python3 - "$LOCAL_MYST_TEMPLATE_DIR" "$book_dir" <<'PY'
from pathlib import Path
import os
import sys

template_dir = Path(sys.argv[1]).resolve()
book_dir = Path(sys.argv[2]).resolve()
print(Path(os.path.relpath(template_dir, book_dir)).as_posix())
PY
}

generate_aggregate_source() {
  local source_dir="$AGGREGATE_SOURCE_DIR"
  local site_template

  rm -rf "$source_dir"
  mkdir -p "$source_dir"
  cp -R "$BOOKS_DIR" "$source_dir/books"

  site_template="$(site_template_for "$source_dir")"
  echo "Using local MyST template: $LOCAL_MYST_TEMPLATE_DIR" >&2

  python3 - "$source_dir" "$site_template" "$ANNBOOK_BOOK_TITLE" "$ANNBOOK_BOOK_AUTHOR" <<'PY'
from collections import defaultdict
from pathlib import Path
import json
import shutil
import sys

source_dir = Path(sys.argv[1])
site_template = sys.argv[2]
book_title = sys.argv[3]
book_author = sys.argv[4]
books_dir = source_dir / "books"

alias_titles = {}
page_order = {}

def copy_with_rewritten_links(src: Path, dest: Path, link_map: dict[str, str]) -> None:
    data = json.loads(src.read_text(encoding="utf-8"))
    for cell in data.get("cells", []):
        source = cell.get("source")
        if not isinstance(source, list):
            continue
        rewritten = []
        for line in source:
            for old, new in link_map.items():
                line = line.replace(old, new)
            rewritten.append(line)
        cell["source"] = rewritten
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

def create_shell_aliases() -> list[Path]:
    src_dir = books_dir / "01_Shell入门"
    if not src_dir.exists():
        return []

    dest_dir = books_dir / "shell"
    shutil.rmtree(dest_dir, ignore_errors=True)

    def ignore_notebooks(_dir: str, names: list[str]) -> list[str]:
        return [name for name in names if Path(name).suffix.lower() in {".ipynb", ".md", ".rst"}]

    shutil.copytree(src_dir, dest_dir, ignore=ignore_notebooks)

    file_map = {
        "01_概览.ipynb": "index.ipynb",
        "02_WSL安装.ipynb": "wsl.ipynb",
        "03_Shell命令.ipynb": "commands.ipynb",
        "04_文件系统.ipynb": "filesystem.ipynb",
        "05_文件查看与编辑.ipynb": "file-view-edit.ipynb",
        "06_管道与重定向.ipynb": "pipes-redirection.ipynb",
        "07_环境变量.ipynb": "environment.ipynb",
        "08_Shell脚本.ipynb": "scripts.ipynb",
    }

    asset_map = {
        "figures/01_01_windows功能设置.png": "figures/windows-features.png",
        "figures/01_02_Windows商店安装Ubuntu.png": "figures/windows-store-ubuntu.png",
    }

    for old_name, new_name in asset_map.items():
        src = src_dir / old_name
        dest = dest_dir / new_name
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    link_map = {**file_map, **asset_map}
    created = []
    for old_name, new_name in file_map.items():
        src = src_dir / old_name
        if not src.exists():
            continue
        dest = dest_dir / new_name
        copy_with_rewritten_links(src, dest, link_map)
        rel = dest.relative_to(source_dir).as_posix()
        alias_titles[rel] = Path(old_name).stem
        page_order[rel] = len(created)
        created.append(dest)
    return created

def create_vscode_aliases() -> list[Path]:
    src_dir = books_dir / "02_VSCode"
    if not src_dir.exists():
        return []

    dest_dir = books_dir / "vscode"
    shutil.rmtree(dest_dir, ignore_errors=True)

    def ignore_notebooks(_dir: str, names: list[str]) -> list[str]:
        return [name for name in names if Path(name).suffix.lower() in {".ipynb", ".md", ".rst"}]

    shutil.copytree(src_dir, dest_dir, ignore=ignore_notebooks)

    file_map = {
        "01_概览.ipynb": "index.ipynb",
        "02_VSCode安装.ipynb": "install.ipynb",
        "03_第一个项目.ipynb": "first-project.ipynb",
        "04_VSCode配置.ipynb": "settings.ipynb",
        "05_VSCode插件.ipynb": "extensions.ipynb",
        "06_Copilot编程插件.ipynb": "copilot.ipynb",
        "07_ClaudeCode编程插件.ipynb": "claude-code.ipynb",
        "08_SSH远程开发.ipynb": "ssh.ipynb",
    }

    created = []
    for old_name, new_name in file_map.items():
        src = src_dir / old_name
        if not src.exists():
            continue
        dest = dest_dir / new_name
        copy_with_rewritten_links(src, dest, file_map)
        rel = dest.relative_to(source_dir).as_posix()
        alias_titles[rel] = Path(old_name).stem
        page_order[rel] = len(created)
        created.append(dest)
    return created

def create_python_aliases() -> list[Path]:
    src_dir = books_dir / "03_Python"
    if not src_dir.exists():
        return []

    dest_dir = books_dir / "python"
    shutil.rmtree(dest_dir, ignore_errors=True)

    def ignore_notebooks(_dir: str, names: list[str]) -> list[str]:
        return [name for name in names if Path(name).suffix.lower() in {".ipynb", ".md", ".rst"}]

    shutil.copytree(src_dir, dest_dir, ignore=ignore_notebooks)

    file_map = {
        "01_概览.ipynb": "index.ipynb",
        "02_Python解释器与包.ipynb": "interpreter-packages.ipynb",
        "03_pip依赖安装.ipynb": "pip.ipynb",
        "04_虚拟环境.ipynb": "venv.ipynb",
        "05_Conda.ipynb": "conda.ipynb",
        "06_uv.ipynb": "uv.ipynb",
        "07_Python调试.ipynb": "debugging.ipynb",
        "08_Jupyter.ipynb": "jupyter.ipynb",
    }

    created = []
    for old_name, new_name in file_map.items():
        src = src_dir / old_name
        if not src.exists():
            continue
        dest = dest_dir / new_name
        copy_with_rewritten_links(src, dest, file_map)
        rel = dest.relative_to(source_dir).as_posix()
        alias_titles[rel] = Path(old_name).stem
        page_order[rel] = len(created)
        created.append(dest)
    return created

def create_git_aliases() -> list[Path]:
    src_dir = books_dir / "04_版本控制Git"
    if not src_dir.exists():
        return []

    dest_dir = books_dir / "git"
    shutil.rmtree(dest_dir, ignore_errors=True)

    def ignore_notebooks(_dir: str, names: list[str]) -> list[str]:
        return [name for name in names if Path(name).suffix.lower() in {".ipynb", ".md", ".rst"}]

    shutil.copytree(src_dir, dest_dir, ignore=ignore_notebooks)

    file_map = {
        "01_概览.ipynb": "index.ipynb",
        "02_Git基本原理与分支.ipynb": "basics.ipynb",
        "03_工作区暂存区与提交.ipynb": "commit.ipynb",
        "04_查看修改与回退.ipynb": "diff-restore.ipynb",
        "05_远程仓库与协作.ipynb": "remote.ipynb",
        "07_AI_Coding_Agent与Git.ipynb": "ai-agent-git.ipynb",
        "08_更多内容.ipynb": "advanced.ipynb",
    }

    created = []
    for old_name, new_name in file_map.items():
        src = src_dir / old_name
        if not src.exists():
            continue
        dest = dest_dir / new_name
        copy_with_rewritten_links(src, dest, file_map)
        rel = dest.relative_to(source_dir).as_posix()
        alias_titles[rel] = Path(old_name).stem
        page_order[rel] = len(created)
        created.append(dest)
    return created

alias_pages = create_shell_aliases() + create_vscode_aliases() + create_python_aliases() + create_git_aliases()

pages = sorted(
    p for p in books_dir.rglob("*")
    if p.suffix.lower() in {".ipynb", ".md", ".rst"}
    and not any(part.startswith((".", "_")) for part in p.relative_to(books_dir).parts)
    and not (
        p.relative_to(books_dir).parts
        and p.relative_to(books_dir).parts[0] in {"01_Shell入门", "02_VSCode", "03_Python", "04_版本控制Git"}
    )
)

if not pages:
    raise SystemExit(f"No notebooks or markdown pages found under {books_dir}")

groups = defaultdict(list)
for page in pages:
    rel_parent = page.parent.relative_to(books_dir)
    groups[rel_parent.as_posix() if rel_parent.parts else "books"].append(page)

group_titles = {
    "shell": "Shell 入门",
    "vscode": "VSCode",
    "python": "Python 环境管理",
    "git": "Git 版本管理",
}

group_order = {
    "shell": 0,
    "vscode": 1,
    "python": 2,
    "git": 3,
    "books": 4,
}

def group_sort_key(group_name: str) -> tuple[int, str]:
    return (group_order.get(group_name, 100), group_name)

def page_sort_key(page: Path) -> tuple[int, str]:
    rel_page = page.relative_to(source_dir).as_posix()
    return (page_order.get(rel_page, 1000), rel_page)

index_lines = [
    f"# {book_title} 目录",
    "",
    "本页自动汇总 `books/` 目录下的课程 Notebook。左侧目录保留原始文件夹层次，便于同时浏览多个 annotated notebook。",
    "",
]

for group_name in sorted(groups, key=group_sort_key):
    index_lines.extend([f"## {group_titles.get(group_name, group_name)}", ""])
    for page in sorted(groups[group_name], key=page_sort_key):
        rel = page.relative_to(source_dir).as_posix()
        index_lines.append(f"- [{alias_titles.get(rel, page.stem)}]({rel})")
    index_lines.append("")

(source_dir / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

def rel(path: Path) -> str:
    return path.relative_to(source_dir).as_posix()

myst = [
    "version: 1",
    "project:",
    f"  title: {book_title}",
    "  authors:",
    f"    - name: {book_author}",
    "  toc:",
    "    - file: index.md",
]

for group_name in sorted(groups, key=group_sort_key):
    myst.append(f"    - title: {group_titles.get(group_name, group_name)}")
    myst.append("      children:")
    for page in sorted(groups[group_name], key=page_sort_key):
        myst.append(f"        - file: {rel(page)}")

myst.extend([
    "site:",
    "  options:",
    "    folders: true",
    f"  template: {site_template}",
    "",
])

(source_dir / "myst.yml").write_text("\n".join(myst), encoding="utf-8")
PY

  printf '%s\n' "$source_dir"
}

build_site() {
  local source_dir="$1"
  local output_dir="$2"

  (
    cd "$source_dir"
    "${JB_CMD[@]}" build --html --force
  )

  rm -rf "$output_dir"
  mkdir -p "$output_dir"
  cp -R "$source_dir/_build/html"/. "$output_dir"
}

generate_single_book_source() {
  local book_dir="$1"
  local book_name="$2"
  local source_dir="$GENERATED_ROOT/$book_name"
  local site_template

  rm -rf "$source_dir"
  mkdir -p "$GENERATED_ROOT"
  cp -R "$book_dir" "$source_dir"

  site_template="$(site_template_for "$source_dir")"

  python3 - "$source_dir" "$book_name" "$site_template" "$ANNBOOK_BOOK_AUTHOR" <<'PY'
from pathlib import Path
import sys

book_dir = Path(sys.argv[1])
book_name = sys.argv[2]
site_template = sys.argv[3]
book_author = sys.argv[4]

pages = sorted(
    p for p in book_dir.rglob("*")
    if p.suffix.lower() in {".ipynb", ".md", ".rst"}
    and not any(part.startswith(("_", ".")) for part in p.relative_to(book_dir).parts)
)

if not pages:
    raise SystemExit(f"No notebook or markdown pages found in {book_dir}")

myst = [
    "version: 1",
    "project:",
    f"  title: {book_name}",
    "  authors:",
    f"    - name: {book_author}",
    "  toc:",
]

for page in pages:
    myst.append(f"    - file: {page.relative_to(book_dir).as_posix()}")

myst.extend([
    "site:",
    "  options:",
    "    folders: true",
    f"  template: {site_template}",
    "",
])

(book_dir / "myst.yml").write_text("\n".join(myst), encoding="utf-8")
PY

  printf '%s\n' "$source_dir"
}

case "$BUILD_MODE" in
  directory)
    source_dir="$(generate_aggregate_source)"
    echo "Building notebook directory ..."
    build_site "$source_dir" "$OUTPUT_DIR"
    echo "Done. HTML output is under: $OUTPUT_DIR"
    ;;
  source)
    source_dir="$(generate_aggregate_source)"
    echo "Done. Jupyter Book source is under: $source_dir"
    ;;
  books)
    shopt -s nullglob
    book_dirs=("$BOOKS_DIR"/*/)

    if (( ${#book_dirs[@]} == 0 )); then
      echo "Error: no book directories found under $BOOKS_DIR" >&2
      exit 1
    fi

    for book_dir in "${book_dirs[@]}"; do
      book_dir="${book_dir%/}"
      book_name="$(basename "$book_dir")"
      source_dir="$(generate_single_book_source "$book_dir" "$book_name")"

      echo "Building $book_name ..."
      build_site "$source_dir" "$OUTPUT_DIR/$book_name"
    done

    echo "Done. HTML output is under: ${2:-"$SCRIPT_DIR/_build/books"}"
    ;;
  *)
    echo "Error: unknown build mode: $BUILD_MODE" >&2
    usage >&2
    exit 1
    ;;
esac
