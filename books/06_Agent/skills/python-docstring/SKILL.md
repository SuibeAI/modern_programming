---
name: python-docstring
description: 为 Python 函数补充 Google 风格 docstring，并保持代码逻辑不变。
---

# Python Docstring Skill

当任务涉及“补充注释”“解释函数”“完善文档字符串”时，使用本 skill。

## 要求

- 使用 Google 风格 docstring；
- docstring 放在函数定义下一行；
- 包含 `Args`、`Returns`，必要时包含 `Raises`；
- 不改变函数原有逻辑；
- 修改后运行 `python3 -m py_compile 文件名` 检查语法。

## 示例

```python
def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The sum of `a` and `b`.
    """
    return a + b
```
