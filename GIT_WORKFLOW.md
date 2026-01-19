# Git Fork 开发工作流程

## 仓库配置
- **origin**: https://github.com/Sylvia-16/diffusers.git (你的 fork)
- **upstream**: https://github.com/huggingface/diffusers.git (上游仓库)

## 日常开发流程

### 1. 同步上游最新代码
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main

# 同步后建议运行格式检查
make format-only
```

### 2. 创建新功能分支
```bash
# 确保在最新的 main 分支
git checkout main
git pull origin main

# 创建新分支
git checkout -b feature/your-feature-name
```

### 3. 开发和提交
```bash
# 修改代码后
git add .
git commit -m "feat: 描述你的功能"

# 推送到你的 fork
git push origin feature/your-feature-name
```

### 4. 保持功能分支最新
```bash
# 在功能分支上
git fetch upstream

# 方法1: rebase (保持提交历史清晰)
git rebase upstream/main
git push origin feature/your-feature-name --force-with-lease

# 方法2: merge (保留完整历史)
git merge upstream/main
git push origin feature/your-feature-name
```

### 5. 完成功能开发
```bash
# 合并回你的 main 分支（如果需要）
git checkout main
git merge feature/your-feature-name
git push origin main

# 删除功能分支
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## 提交信息规范

使用约定式提交（Conventional Commits）：

- `feat:` 新功能
- `fix:` 错误修复
- `docs:` 文档更改
- `style:` 代码格式（不影响代码运行）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

示例：
```
feat: 添加新的扩散模型支持
fix: 修复采样器的内存泄漏问题
docs: 更新 README 中的安装说明
```

## 最佳实践

1. **保持 main 分支干净**: 不要直接在 main 分支上开发
2. **定期同步**: 至少每周同步一次上游更新
3. **小而频繁的提交**: 每个提交应该是一个逻辑单元
4. **描述性的分支名**: `feature/add-lora-support` 而不是 `feature/new`
5. **提交前测试**: 确保代码可以正常运行
6. **使用 .gitignore**: 不要提交临时文件、编译文件等

## 常见问题解决

### 冲突解决
```bash
# 如果合并或 rebase 时遇到冲突
# 1. 手动编辑冲突文件
# 2. 标记为已解决
git add <冲突文件>
# 3. 继续操作
git rebase --continue  # 如果是 rebase
git commit             # 如果是 merge
```

### 撤销本地更改
```bash
# 撤销未暂存的更改
git checkout -- <文件名>

# 撤销已暂存的更改
git reset HEAD <文件名>

# 撤销最后一次提交（保留更改）
git reset --soft HEAD^

# 撤销最后一次提交（丢弃更改）
git reset --hard HEAD^
```

### 查看状态
```bash
# 查看当前状态
git status

# 查看远程分支
git remote -v

# 查看所有分支
git branch -a

# 查看提交历史
git log --oneline --graph --all
```

## 工作流程图

```
┌─────────────────────────────────────────────────────────────┐
│  upstream (huggingface/diffusers)                           │
│  上游仓库 - 只读                                             │
└───────────────────┬─────────────────────────────────────────┘
                    │ fetch/pull
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  origin/main (Sylvia-16/diffusers)                          │
│  你的 fork 主分支 - 与上游保持同步                            │
└───────────────────┬─────────────────────────────────────────┘
                    │ checkout -b
        ┌───────────┼───────────┐
        ↓           ↓           ↓
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ feature/ │ │  fix/    │ │ experiment/│
  │ branch-A │ │ branch-B │ │ branch-C │
  └──────────┘ └──────────┘ └──────────┘
   功能分支     修复分支     实验分支
```

## 定期维护任务

### 每周
- [ ] 同步上游 main 分支
- [ ] 检查并合并/删除已完成的功能分支

### 开始新功能前
- [ ] 从最新的 main 分支创建新分支
- [ ] 确保 main 已与上游同步

### 提交代码前
- [ ] 运行测试
- [ ] 检查代码风格
- [ ] 写清楚提交信息
- [ ] 检查没有调试代码残留

---

*创建日期: 2026-01-19*
