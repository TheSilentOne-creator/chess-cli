# ♟️ Chess CLI - 命令行国际象棋

<div align="center">

**纯 Python · 零依赖 · 完整规则 · AI 对战**  

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/TheSilentOne-creator/chess-cli)](https://github.com/TheSilentOne-creator/chess-cli/stargazers)

**在终端里体验完整的国际象棋对局**  

</div>

---

## 📖 项目简介

一个纯 Python 编写的命令行国际象棋游戏，**100% 标准库，零第三方依赖**。你可以在任何有 Python 的终端里运行它——办公室、地铁、树莓派，甚至 SSH 连到服务器上玩。

### 为什么选择 Chess CLI？

- ✅ **完整的规则实现**：易位、过路兵、兵升变、50步规则、三次重复、子力不足
- ✅ **AI 对手**：基于极小极大搜索 + Alpha-Beta 剪枝，难度可调（2/3/4 层）
- ✅ **人人对战**：和朋友在同一台电脑上轮流走棋
- ✅ **PGN 导出**：对局自动记录，可导出为标准 PGN 格式
- ✅ **悔棋功能**：走错了？随时悔棋
- ✅ **伪装友好**：纯命令行界面，远看就是在敲代码 😎

---

## 🎮 功能特性

| 功能 | 说明 |
| :--- | :--- |
| 🧠 AI 对战 | 搜索深度 2/3/4 层可调，棋力从新手到业余 |
| 👥 人人对战 | 双人轮流，适合午休 PK |
| 👑 完整规则 | 王车易位、吃过路兵、兵升变（手动选择） |
| 🏁 胜负判定 | 将杀、逼和、三次重复、50步规则、子力不足 |
| 📝 PGN 导出 | 对局自动记录，可保存为 .pgn 文件 |
| ↩️ 悔棋 | 人机模式撤两步，人人模式撤一步 |
| 🎨 双样式 | 字母（KQ）和 Unicode（♔♚）可切换 |
| ⚙️ 设置持久化 | 样式和难度保存到 settings.json |

---

## 🚀 快速开始

**环境要求**  

- Python 3.6 及以上
- 不需要安装任何第三方库

**克隆并运行**  

```bash
git clone https://github.com/TheSilentOne-creator/chess-cli.git
cd chess-cli
python chess.py
```

**游戏界面预览**  

```text
=========== 国际象棋 ===========

    a  b  c  d  e  f  g  h

8   r  n  b  q  k  b  n  r   8
7   p  p  p  p  p  p  p  p   7
6   .  .  .  .  .  .  .  .   6
5   .  .  .  .  .  .  .  .   5
4   .  .  .  .  .  .  .  .   4
3   .  .  .  .  .  .  .  .   3
2   P  P  P  P  P  P  P  P   2
1   R  N  B  Q  K  B  N  R   1

    a  b  c  d  e  f  g  h

================================

当前回合: 白方
半步计数: 0/100 (50步规则)
【你的回合 - 白方】请输入走棋：e2e4
```

---

## ⌨️ 操作指南

**走法格式**  

```bash
e2e4     # 兵从 e2 走到 e4
e7e8q    # 兵走到 e8 升变为后
e1g1     # 白方王车短易位
e8g8     # 黑方王车短易位
```

支持带连字符：`e2-e4`、`e7-e8=q`

**交互命令**  

| 命令 | 功能 |
| :--- | :--- |
| `history` | 查看历史走法列表 |
| `save` | 保存当前对局为 PGN 文件 |
| `undo` | 悔棋（人机撤两步，人人撤一步） |
| `quit` | 退出当前对局，返回主菜单 |

---

## 📂 项目结构

```text
chess-cli/
├── Chess.py              # 主程序（单文件，即开即玩）
├── settings.json         # 用户设置（自动生成）
├── README.md
├── LICENSE
├── CONTRIBUTING.md
└── .gitignore
```

---

## 📜 开源协议

本项目采用 **MIT License**，简单说就是：

**✅ 你可以**  

- 免费使用（商业/个人/教育）
- 自由修改
- 重新发布
- 商用

**❗ 你必须**  

- **保留版权声明**
- **二创必须注明出处**：`基于 https://github.com/TheSilentOne-creator/chess-cli 修改`

---

## 🛠️ 如何贡献

欢迎提交 Issue、PR！

**可以贡献的方向**  

- 🐛 修 Bug
- 🚀 优化 AI 搜索（加入开局库、残局库）
- 🎨 更好的 TUI 界面（如 `curses` 支持鼠标点击）
- 📝 完善文档
- 🌐 多语言支持

**提交要求**  

1. 保持零依赖（只用 Python 标准库）
2. 代码风格遵循 PEP 8
3. 新功能需包含测试或使用说明

---

## 🏆 路线图

**v1.1.1 — 视觉与交互增强**  

- [x] **彩色输出** — ANSI 颜色区分黑白棋子
- [x] **走法建议/高亮合法走位** — 选中棋子后显示可走位置（替代走法动画，工作量更小但效果更好）

---

**v1.1.2 — AI 增强**  

- [x] **开局库** — 前 5 步预置开局，AI 秒响应
- [x] **AI 随机性** — 相同局面下 AI 走法略有不同
- [x] **AI 思考过程** — 显示每层深度的最佳走法和评估值

---

**Beta 1.1 — 引入面向对象思想**  

- [ ] 提取 `Board` 类（棋盘状态）
- [ ] 提取 `MoveGenerator` 类（走法生成）
- [ ] 提取 `GameController` 类（游戏流程）
- [ ] 合并 `play_ai` 和 `play_pvp`
- [ ] 提取 `Renderer` 类（棋盘显示）

---

**v1.1.3 — 用户体验提升**  

- [ ] **棋盘翻转** — 黑方视角（人机模式自动切换）
- [ ] **和棋检测增强** — 50步规则/三次重复提前警告
- [ ] **老板键升级** — `Ctrl+Shift+F` 一键伪装

---

**v1.2.0 — 数据持久化**  

- [ ] **保存/加载对局** — 从 PGN 文件恢复对局
- [ ] **对局统计** — 胜/负/和、最长对局、连胜纪录
- [ ] **走法回放/复盘** — 逐步回放已保存的对局

---

**v2.0.0 — 网络对战**  

- [ ] **局域网对战** — Socket 双人联机
- [ ] **AI 对战 AI** — 观赏模式
- [ ] **走法动画** — 逐格移动

---

## 🙏 致谢

- Python 标准库开发团队
- 所有贡献代码的棋友
- 国际象棋的发明者 🏛️

---

## 📧 联系与交流

- 📮 [GitHub Issues](https://github.com/TheSilentOne-creator/chess-cli/issues)
- 💬 [GitHub Discussions](https://github.com/TheSilentOne-creator/chess-cli/discussions)

---

<div align="center">

**⭐ 如果这个项目让你摸鱼更快乐，请点个 Star！**

**Happy Hacking, Happy Chess! ♟️**  

</div>
