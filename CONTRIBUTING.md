# 贡献指南

感谢你对 Chess CLI 的兴趣！以下是我们的小小要求：

## 🐛 报告 Bug

1. 检查 [Issues](https://github.com/TheSilentOne-creator/chess-cli/issues) 是否已有人报告
2. 提供复现步骤 + 预期结果 + 实际结果
3. 附上你的 Python 版本和操作系统

## 💡 提交功能建议

1. 先开一个 Issue 讨论，避免白写代码
2. 说明使用场景和设计思路

## 🚀 提交 Pull Request

1. Fork 本仓库
2. 从 `main` 分支拉 `feature/xxx` 分支
3. 保持单文件？还是拆模块？——**建议先保持单文件**，除非改动特别大
4. 保持零依赖（只用 Python 标准库）
5. 代码风格：PEP 8
6. 提交前自测：

   ```bash
   python chess.py
   # 测试人机 + 人人模式各走几步
   ```

## 📝 提交信息格式

```bash
<类型>: <简短描述>

类型：
- feat: 新功能
- fix: 修 Bug
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- chore: 构建/工具
```

---

**Happy Coding! ♟️**  
