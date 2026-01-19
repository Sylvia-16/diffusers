# 代码规范指南 / Code Standards Guide

本文档说明如何保持代码符合 diffusers 项目的规范标准。

## 🚀 快速开始

### 1. 安装开发依赖

```bash
# 安装开发工具
pip install -r requirements-dev.txt

# 或者单独安装核心工具
pip install ruff pre-commit bandit
```

### 2. 安装 Pre-commit Hooks

```bash
# 激活 pre-commit hooks（只需执行一次）
pre-commit install

# 测试运行（可选）
pre-commit run --all-files
```

安装后，每次 `git commit` 时会自动检查代码规范！

---

## 📋 使用的工具

### 1. **Ruff** - 代码检查和格式化
- ⚡ 极快的 Python linter 和 formatter（比 Black + Flake8 快 10-100 倍）
- 🔧 自动修复大部分问题
- 📏 行长度限制：119 字符
- 🎯 替代 Black, isort, Flake8, pylint 等工具

### 2. **Pre-commit** - Git 提交前自动检查
- 🎣 在提交前自动运行代码检查
- 🛡️ 防止不规范代码进入仓库
- ⚙️ 自动修复简单问题

### 3. **Bandit** - 安全漏洞检查
- 🔒 检测常见的安全问题
- 🚨 警告不安全的代码模式

### 4. **其他工具**
- 检查 YAML/JSON/TOML 语法
- 检查文件末尾空白
- 检查合并冲突标记
- 拼写检查

---

## 🔧 日常使用

### 方式 1: 自动检查（推荐）

安装 pre-commit 后，每次提交时自动运行：

```bash
git add .
git commit -m "your message"
# ✅ 自动检查并修复代码！
```

如果检查失败：
1. 查看错误信息
2. 修复问题（很多问题会被自动修复）
3. 重新 `git add` 修改的文件
4. 再次 `git commit`

### 方式 2: 手动运行

#### 快速格式化（推荐用于日常开发）
```bash
# 最快 - 只用 Ruff 格式化代码（推荐！）
make format-only

# 或者只检查修改的文件
make modified_only_fixup
```

#### 完整格式化和检查
```bash
# 快速完整检查（跳过仓库结构验证）
make fixup-fast

# 完整检查（包含仓库结构验证）
make fixup

# 格式化所有文件
make style

# 快速格式化（不含文档）
make style-fast
```

#### 只检查不修复
```bash
make quality
```

#### 使用 Ruff 直接运行
```bash
# 检查代码
ruff check src/diffusers examples tests

# 检查并自动修复
ruff check src/diffusers examples tests --fix

# 格式化代码
ruff format src/diffusers examples tests
```

#### 检查特定文件
```bash
# 检查单个文件
ruff check path/to/your/file.py --fix
ruff format path/to/your/file.py
```

### 方式 3: Pre-commit 手动运行

```bash
# 检查所有文件
pre-commit run --all-files

# 只检查暂存的文件
pre-commit run

# 检查特定文件
pre-commit run --files path/to/file.py
```

---

## 📐 代码规范要点

### Python 代码风格

1. **行长度**: 最大 119 字符
2. **缩进**: 4 个空格（不使用 Tab）
3. **引号**: 优先使用双引号 `"`
4. **Import 顺序**:
   ```python
   # 1. 标准库
   import os
   import sys

   # 2. 第三方库
   import torch
   import numpy as np

   # 3. 本地导入
   from diffusers import UNet2DModel
   from diffusers.utils import logging
   ```

5. **命名规范**:
   - 类名: `PascalCase` (如 `DiffusionPipeline`)
   - 函数/变量: `snake_case` (如 `generate_image`)
   - 常量: `UPPER_SNAKE_CASE` (如 `MAX_BATCH_SIZE`)
   - 私有成员: `_leading_underscore` (如 `_internal_method`)

### 文档字符串

使用 Google 风格的 docstring：

```python
def sample_function(param1: int, param2: str) -> bool:
    """
    函数的简短描述。

    更详细的描述（如果需要）。

    Args:
        param1 (`int`):
            参数1的描述。
        param2 (`str`):
            参数2的描述。

    Returns:
        `bool`: 返回值描述。

    Examples:
        ```python
        >>> result = sample_function(42, "test")
        >>> print(result)
        True
        ```
    """
    return True
```

### 类型注解

尽可能添加类型注解：

```python
from typing import Optional, Union, List, Dict

def process_data(
    data: Union[List[int], Dict[str, int]],
    threshold: float = 0.5,
    device: Optional[str] = None,
) -> torch.Tensor:
    """Process the data."""
    ...
```

---

## 🚫 常见错误和修复

### 错误 1: 行太长
```python
# ❌ 错误
result = some_very_long_function_name(argument1, argument2, argument3, argument4, argument5, argument6)

# ✅ 正确
result = some_very_long_function_name(
    argument1,
    argument2,
    argument3,
    argument4,
    argument5,
    argument6,
)
```

### 错误 2: Import 顺序错误
```python
# ❌ 错误
from diffusers import UNet2DModel
import torch
import os

# ✅ 正确（Ruff 会自动修复）
import os

import torch

from diffusers import UNet2DModel
```

### 错误 3: 未使用的导入
```python
# ❌ 错误
import numpy as np
import torch  # 未使用

def process(data):
    return np.array(data)

# ✅ 正确（Ruff 会自动删除）
import numpy as np

def process(data):
    return np.array(data)
```

---

## 🔍 编辑器集成

### VS Code / Cursor

在 `.vscode/settings.json` 中添加：

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.enable": true,
  "ruff.fixAll": true,
  "ruff.organizeImports": true,
  "ruff.lint.run": "onSave"
}
```

安装 Ruff 扩展：
- 打开扩展市场
- 搜索 "Ruff"
- 安装 Charlie Marsh 的 Ruff 扩展

### PyCharm

1. 安装 Ruff 插件：File → Settings → Plugins → 搜索 "Ruff"
2. 配置：File → Settings → Tools → Ruff
3. 启用 "Run on save"

### Vim/Neovim

使用 ALE 或 null-ls 插件配置 Ruff。

---

## 🧪 提交前检查清单

在提交代码前，确保：

- [ ] 代码已通过 `make fixup` 或 `make style`
- [ ] 没有调试代码（如 `print()`, `breakpoint()`）
- [ ] 添加了必要的文档字符串
- [ ] 添加了类型注解（如果可能）
- [ ] 测试通过（如果修改了核心代码）
- [ ] 提交信息清晰描述了更改

---

## 📊 CI/CD 检查

当你提交 Pull Request 时，GitHub Actions 会自动运行：

1. **代码质量检查**: Ruff linting
2. **格式检查**: Ruff formatting
3. **安全检查**: Bandit
4. **测试**: Pytest
5. **文档检查**: Doc-builder

确保所有检查都通过！❌ → ✅

---

## 🛠️ 故障排除

### Pre-commit 太慢？

```bash
# 跳过 pre-commit（不推荐）
git commit --no-verify -m "message"

# 更新 pre-commit hooks
pre-commit autoupdate
```

### Ruff 报告太多错误？

```bash
# 只修复安全和简单问题
ruff check --fix --select E,F

# 逐个修复
ruff check --fix path/to/file.py
```

### 与 main 分支冲突？

```bash
# 同步 main 分支后重新运行
git fetch upstream
git rebase upstream/main
make fixup
```

---

## 📚 相关资源

- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Pre-commit 文档](https://pre-commit.com/)
- [diffusers CONTRIBUTING.md](./CONTRIBUTING.md)
- [PEP 8 - Python 代码风格](https://pep8.org/)
- [Google Python 风格指南](https://google.github.io/styleguide/pyguide.html)

---

## ❓ 常见问题

### Q: 我需要每次都运行 `make style` 吗？

A: 不需要！安装 pre-commit 后会自动检查。但在提交大量更改前运行一次是个好习惯。

### Q: Pre-commit 修改了我的文件怎么办？

A: 这是正常的！它自动修复了代码规范问题。重新 `git add` 修改的文件，然后再次提交即可。

### Q: 我可以跳过某些检查吗？

A: 可以，但不推荐。如果必须：
```python
# ruff: noqa: E501  # 忽略这行的行长度检查
very_long_line_that_cannot_be_broken = "..."
```

### Q: 如何检查单个文件？

A:
```bash
ruff check path/to/file.py --fix
ruff format path/to/file.py
```

### Q: Ruff 和 Black 有什么区别？

A: Ruff 更快（10-100倍），功能更全，可以替代 Black + isort + Flake8 + 更多工具。

---

**最后提醒**: 保持代码规范不仅让代码更易读，也让团队协作更顺畅！🎉
