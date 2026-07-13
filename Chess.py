#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chess.py - 命令行国际象棋

版本: v Beta 1.0
作者: TheSilentOne-creator
License: MIT
Repository: https://github.com/TheSilentOne-creator/chess-cli

完整功能: 
- 人机对战（AI 难度 2/3/4 层可调）
- 人人对战
- 完整规则（易位、过路兵、升变、50步、三次重复、子力不足）
- PGN 对局导出
- 悔棋
- 棋子样式切换（字母 / Unicode）
- 走法历史显示（可开关）
- AI 思考耗时显示
- 走法高亮
- 彩色输出（可开关）
- 走法建议/合法走位高亮（可开关）
- 传统走法模式（走法建议关闭时）
- 类型注解
- 增强错误处理
"""

import random
import subprocess
import os
import copy
import json
from datetime import datetime
from collections import defaultdict
import time
from typing import List, Tuple, Optional, Dict, Any, Union

# ---------------------- 自定义异常 ----------------------
class ChessError(Exception):
    """国际象棋基础异常"""
    pass

class InvalidMoveError(ChessError):
    """非法走法异常"""
    pass

class InvalidInputError(ChessError):
    """无效输入异常"""
    pass

class GameStateError(ChessError):
    """游戏状态异常"""
    pass

# ---------------------- 类型别名 ----------------------
# 位置类型:  (row, col)
Position = Tuple[int, int]

# 走法类型:  ((from_row, from_col), (to_row, to_col))
MoveType = Tuple[Position, Position]

# 棋盘类型:  8x8 字符串列表
BoardType = List[List[str]]

# 易位状态类型
CastlingState = Dict[str, bool]

# 走法记录类型
MoveRecord = Dict[str, Any]

# ---------------------- 全局设置 ----------------------
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    'piece_style': 'letter',      # 'letter' 或 'unicode'
    'ai_depth': 3,                # AI搜索深度: 2=简单, 3=中等, 4=困难
    'show_history': True,         # 是否在棋盘旁显示走法历史
    'use_colors': True,           # 是否使用彩色输出
    'show_suggestions': True,     # 是否显示走法建议
}

SETTINGS = DEFAULT_SETTINGS.copy()

# ---------------------- 棋盘常量 ----------------------
BOARD_SIZE = 8
FIRST_ROW = 0
LAST_ROW = 7
FIRST_COL = 0
LAST_COL = 7

# ---------------------- 王车易位常量 ----------------------
WHITE_KING_ROW = 7
BLACK_KING_ROW = 0
KING_COL = 4
KING_SIDE_CASTLE_COL = 6      # 短易位目标列
QUEEN_SIDE_CASTLE_COL = 2     # 长易位目标列

# ---------------------- 兵常量 ----------------------
PAWN_DIR_WHITE = -1
PAWN_DIR_BLACK = 1
PAWN_START_ROW_WHITE = 6
PAWN_START_ROW_BLACK = 1
PAWN_DOUBLE_STEP = 2

# ---------------------- AI 常量 ----------------------
MATE_SCORE = 100000

# ---------------------- UI 常量 ----------------------
MAX_HISTORY_DISPLAY = 20
BOARD_WIDTH = 35

# ---------------------- 设置持久化 ----------------------
def load_settings() -> None:
    """从文件加载设置"""
    global SETTINGS
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            SETTINGS.update(loaded)
    except FileNotFoundError:
        save_settings()
        print("📝 已创建默认设置文件")
    except json.JSONDecodeError as e:
        print(f"⚠️  设置文件损坏 ({e}), 使用默认设置")
        try:
            backup_name = f"{SETTINGS_FILE}.backup"
            os.rename(SETTINGS_FILE, backup_name)
            print(f"📁 已备份损坏的设置文件为: {backup_name}")
        except Exception:
            pass
        save_settings()
    except PermissionError:
        print("⚠️  无法读取设置文件（权限不足）, 使用默认设置")
    except Exception as e:
        print(f"⚠️  加载设置时出错 ({e}), 使用默认设置")

def save_settings() -> None:
    """保存设置到文件"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, indent=2, ensure_ascii=False)
    except PermissionError:
        print("⚠️  无法保存设置（权限不足）")
        input("\n回车继续...")
    except OSError as e:
        print(f"⚠️  无法保存设置 ({e})")
        input("\n回车继续...")
    except Exception as e:
        print(f"⚠️  保存设置时出错 ({e})")
        input("\n回车继续...")

# ---------------------- ANSI 颜色代码 ----------------------
class Colors:
    """ANSI 颜色代码, 跨平台兼容"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    @staticmethod
    def disable() -> None:
        """禁用所有颜色"""
        Colors.RESET = ''
        Colors.BOLD = ''
        Colors.BLACK = Colors.RED = Colors.GREEN = Colors.YELLOW = ''
        Colors.BLUE = Colors.MAGENTA = Colors.CYAN = Colors.WHITE = ''
        Colors.BRIGHT_BLACK = Colors.BRIGHT_RED = Colors.BRIGHT_GREEN = ''
        Colors.BRIGHT_YELLOW = Colors.BRIGHT_BLUE = Colors.BRIGHT_MAGENTA = ''
        Colors.BRIGHT_CYAN = Colors.BRIGHT_WHITE = ''
        Colors.BG_BLACK = Colors.BG_RED = Colors.BG_GREEN = ''
        Colors.BG_YELLOW = Colors.BG_BLUE = Colors.BG_MAGENTA = ''
        Colors.BG_CYAN = Colors.BG_WHITE = ''

# ---------------------- Unicode 国际象棋符号 ----------------------
UNICODE_PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
    '.': '·'
}

PIECE_COLORS = {
    'K': 'white', 'Q': 'white', 'R': 'white', 'B': 'white', 'N': 'white', 'P': 'white',
    'k': 'black', 'q': 'black', 'r': 'black', 'b': 'black', 'n': 'black', 'p': 'black'
}

# ---------------------- 清屏函数 ----------------------
def clear_terminal() -> None:
    subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)

# ---------------------- 棋子常量定义 ----------------------
EMPTY = "."
WK, WQ, WR, WB, WN, WP = "K", "Q", "R", "B", "N", "P"
BK, BQ, BR, BB, BN, BP = "k", "q", "r", "b", "n", "p"

PIECE_NAMES = {
    'K': 'K', 'Q': 'Q', 'R': 'R', 'B': 'B', 'N': 'N', 'P': '',
    'k': 'K', 'q': 'Q', 'r': 'R', 'b': 'B', 'n': 'N', 'p': ''
}

# ---------------------- 棋子价值（用于AI评估） ----------------------
PIECE_VALUES = {
    'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000,
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000
}

PAWN_TABLE = [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5,  5, 10, 25, 25, 10,  5,  5],
    [0,  0,  0, 20, 20,  0,  0,  0],
    [5, -5,-10,  0,  0,-10, -5,  5],
    [5, 10, 10,-20,-20, 10, 10,  5],
    [0,  0,  0,  0,  0,  0,  0,  0]
]

def evaluate_piece(piece: str, row: int, col: int, turn: str) -> int:
    """获取棋子价值（包含位置加成）"""
    if piece == EMPTY:
        return 0
    
    base_value = PIECE_VALUES.get(piece, 0)
    
    if piece.upper() == 'P':
        if turn == 'white':
            pawn_row = 7 - row
        else:
            pawn_row = row
        pawn_col = col
        return base_value + PAWN_TABLE[pawn_row][pawn_col]
    
    if piece.upper() in ('N', 'B'):
        center = (BOARD_SIZE - 1) / 2
        center_dist = abs(row - center) + abs(col - center)
        center_bonus = (BOARD_SIZE - 1 - center_dist) * 5
        return base_value + center_bonus
    
    return base_value

# ---------------------- 初始化棋盘 + 易位状态 + 过路兵 ----------------------
def init_board() -> Tuple[BoardType, CastlingState, Optional[Position]]:
    """初始化棋盘, 返回 (棋盘, 易位状态, 过路兵目标)"""
    board = [
        ["r", "n", "b", "q", "k", "b", "n", "r"],
        ["p", "p", "p", "p", "p", "p", "p", "p"],
        [".", ".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", ".", "."],
        ["P", "P", "P", "P", "P", "P", "P", "P"],
        ["R", "N", "B", "Q", "K", "B", "N", "R"],
    ]
    castling_state = {
        "w_king": False, "w_r_left": False, "w_r_right": False,
        "b_king": False, "b_r_left": False, "b_r_right": False
    }
    en_passant_target = None
    return board, castling_state, en_passant_target

# ---------------------- 输入验证辅助函数 ----------------------

def safe_input(prompt: str, allow_empty: bool = False) -> str:
    """
    安全的输入函数, 处理 KeyboardInterrupt
    """
    try:
        user_input = input(prompt).strip()
        if not allow_empty and not user_input:
            return ""
        return user_input
    except KeyboardInterrupt:
        print("\n\n检测到中断, 返回主菜单...")
        return "quit"
    except EOFError:
        print("\n\n检测到输入结束, 返回主菜单...")
        return "quit"

def validate_coordinate(coord: str) -> bool:
    """
    验证坐标格式（如 'e2'）
    """
    if len(coord) != 2:
        return False
    if not ('a' <= coord[0].lower() <= 'h'):
        return False
    if not ('1' <= coord[1] <= '8'):
        return False
    return True

def parse_move_input(user_input: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析走法输入, 返回 (from_pos, to_pos) 或 (None, None)
    """
    user_input = user_input.replace(' ', '').replace('-', '').lower()
    
    if len(user_input) == 4:
        return user_input[:2], user_input[2:]
    
    if len(user_input) == 5 and user_input[2] == '=':
        return user_input[:2], user_input[2:4]
    
    return None, None

# ---------------------- 棋盘渲染辅助函数 ----------------------

def _render_piece(piece: str, symbol: str, is_highlight: bool, is_selected: bool, use_colors: bool) -> str:
    """
    渲染单个棋子（含颜色/高亮/选中效果）
    返回渲染后的字符串（含颜色代码）
    """
    if is_selected and piece != EMPTY:
        if use_colors:
            if piece.isupper():
                return f" {Colors.BG_BLUE}{Colors.BRIGHT_WHITE}{symbol}{Colors.RESET} "
            else:
                return f" {Colors.BG_BLUE}{Colors.RED}{symbol}{Colors.RESET} "
        else:
            return f"({symbol}) "
    
    if is_highlight and piece != EMPTY:
        if use_colors:
            if piece.isupper():
                return f" {Colors.BG_YELLOW}{Colors.BLACK}{symbol}{Colors.RESET} "
            else:
                return f" {Colors.BG_YELLOW}{Colors.BLACK}{symbol}{Colors.RESET} "
        else:
            return f" {symbol} "
    
    if use_colors:
        if piece == EMPTY:
            return f" {Colors.BRIGHT_BLACK}·{Colors.RESET} "
        elif piece.isupper():
            return f" {Colors.BRIGHT_WHITE}{symbol}{Colors.RESET} "
        else:
            return f" {Colors.RED}{symbol}{Colors.RESET} "
    else:
        return f" {symbol} "

def _build_board_lines(
    board: BoardType,
    last_move: Optional[MoveType],
    candidate_moves: Optional[List[Position]],
    selected_pos: Optional[Position]
) -> List[str]:
    """
    构建棋盘的行列表
    返回: List[str] 棋盘各行
    """
    use_colors = SETTINGS.get('use_colors', True)
    show_suggestions = SETTINGS.get('show_suggestions', True)
    
    lines = []
    lines.append("=========== 国际象棋 ===========")
    
    if SETTINGS['piece_style'] == 'unicode':
        lines.append("    a  b  c  d  e  f  g  h")
    else:
        lines.append("    a  b  c  d  e  f  g  h")
    
    # 上一步走法高亮
    highlight_from = None
    highlight_to = None
    if last_move:
        (fr, fc), (tr, tc) = last_move
        highlight_from = (fr, fc)
        highlight_to = (tr, tc)
    
    for row_idx in range(BOARD_SIZE):
        line_num = BOARD_SIZE - row_idx
        row_str = f"{line_num}  "
        for col_idx in range(BOARD_SIZE):
            piece = board[row_idx][col_idx]
            
            # 检查是否在候选走法列表中
            is_candidate = show_suggestions and candidate_moves and (row_idx, col_idx) in candidate_moves
            
            # 检查是否被选中
            is_selected = selected_pos and (row_idx, col_idx) == selected_pos
            
            # 检查是否高亮（上一步走法）
            is_highlight = False
            if highlight_from and (row_idx, col_idx) == highlight_from:
                is_highlight = True
            elif highlight_to and (row_idx, col_idx) == highlight_to:
                is_highlight = True
            
            # 获取符号
            if SETTINGS['piece_style'] == 'unicode':
                symbol = UNICODE_PIECES.get(piece, ' ')
            else:
                symbol = piece
            
            # 候选走法显示（绿色圆点）
            if is_candidate and piece == EMPTY:
                if use_colors:
                    row_str += f" {Colors.GREEN}·{Colors.RESET} "
                else:
                    row_str += f" * "
                continue
            
            # 渲染棋子
            row_str += _render_piece(piece, symbol, is_highlight, is_selected, use_colors)
        
        row_str += f"  {line_num}"
        lines.append(row_str)
    
    if SETTINGS['piece_style'] == 'unicode':
        lines.append("    a  b  c  d  e  f  g  h")
    else:
        lines.append("    a  b  c  d  e  f  g  h")
    lines.append("=================================")
    
    return lines

def _build_history_lines(move_history: Optional['GameRecorder']) -> List[str]:
    """
    构建走法历史行列表
    返回: List[str] 历史各行
    """
    lines = []
    
    if SETTINGS['show_history'] and move_history and move_history.moves:
        lines.append("")
        lines.append("📜 走法历史")
        lines.append("")
        
        max_moves = len(move_history.moves)
        num_width = len(str(max_moves))
        start_idx = max(0, max_moves - MAX_HISTORY_DISPLAY)
        
        for i in range(start_idx, max_moves):
            move = move_history.moves[i]
            move_num = move['move_num']
            white = move['white']
            black = move['black']
            
            if black:
                lines.append(f"{move_num:>{num_width}}. {white:<6} {black:<6}")
            else:
                lines.append(f"{move_num:>{num_width}}. {white:<6}")
        
        if max_moves > MAX_HISTORY_DISPLAY:
            lines.append("")
            lines.append(f"... 共 {max_moves} 步")
    else:
        lines.append("")
        lines.append("  (历史已关闭)")
    
    return lines

def _print_board_merged(board_lines: List[str], history_lines: List[str]) -> None:
    """
    合并打印棋盘和历史（棋盘左侧, 历史右侧）
    """
    max_lines = max(len(board_lines), len(history_lines))
    
    for i in range(max_lines):
        board_line = board_lines[i] if i < len(board_lines) else ""
        history_line = history_lines[i] if i < len(history_lines) else ""
        print(f"{board_line:<{BOARD_WIDTH}}  {history_line}")

def print_board(
    board: BoardType,
    last_move: Optional[MoveType] = None,
    move_history: Optional['GameRecorder'] = None,
    candidate_moves: Optional[List[Position]] = None,
    selected_pos: Optional[Position] = None
) -> None:
    """
    打印棋盘, 支持: 
    - 走法历史显示在右侧
    - 彩色输出
    - 走法建议（绿色圆点标记合法走位）
    - 选中棋子高亮
    """
    board_lines = _build_board_lines(board, last_move, candidate_moves, selected_pos)
    history_lines = _build_history_lines(move_history)
    _print_board_merged(board_lines, history_lines)

# ---------------------- 坐标转换 a1 -> (行,列) ----------------------
def pos_to_row_col(pos: str) -> Position:
    """将坐标字符串（如 'e2'）转换为 (行, 列)"""
    if not validate_coordinate(pos):
        raise InvalidInputError(f"无效坐标: {pos}")
    
    col = ord(pos[0].lower()) - ord("a")
    row = BOARD_SIZE - int(pos[1])
    return row, col

def row_col_to_pos(row: int, col: int) -> str:
    """将 (行, 列) 转换为坐标字符串（如 'e2'）"""
    return f"{chr(col + ord('a'))}{BOARD_SIZE - row}"

# ---------------------- 阵营判断 ----------------------
def is_same_side(piece: str, turn: str) -> bool:
    """判断棋子是否属于 turn 方"""
    if piece == EMPTY:
        return False
    if turn == "white":
        return piece.isupper()
    return piece.islower()

def is_enemy(piece: str, turn: str) -> bool:
    """判断棋子是否是 turn 方的敌人"""
    if piece == EMPTY:
        return False
    return not is_same_side(piece, turn)

# ---------------------- 王车易位辅助 ----------------------
def is_row_empty_between(board: BoardType, row: int, col_start: int, col_end: int) -> bool:
    """检查从 col_start 到 col_end 之间（不含两端）是否全空"""
    step = 1 if col_end > col_start else -1
    col = col_start + step
    while col != col_end:
        if board[row][col] != EMPTY:
            return False
        col += step
    return True

# ---------------------- 检查某个位置是否被攻击 ----------------------
def is_square_attacked(board: BoardType, row: int, col: int, by_turn: str) -> bool:
    """检查 (row, col) 是否被 by_turn 阵营攻击"""
    for attacker_row in range(BOARD_SIZE):
        for attacker_col in range(BOARD_SIZE):
            piece = board[attacker_row][attacker_col]
            if piece == EMPTY:
                continue
            if is_same_side(piece, by_turn):
                moves = get_raw_moves(board, attacker_row, attacker_col, by_turn, None, None)
                if (row, col) in moves:
                    return True
    return False

# ---------------------- 走法生成辅助函数 ----------------------

def _handle_castling_moves(
    board: BoardType,
    row: int,
    col: int,
    turn: str,
    castling_state: CastlingState,
    moves: List[Position]
) -> None:
    """
    处理王车易位走法, 添加到 moves 列表中
    前置条件: 当前棋子是王, 且 castling_state 不为 None
    """
    if turn == "white" and row == WHITE_KING_ROW and col == KING_COL:
        if not castling_state["w_king"] and not is_square_attacked(board, WHITE_KING_ROW, KING_COL, "black"):
            # 短易位（王翼）
            if (not castling_state["w_r_right"] and 
                is_row_empty_between(board, WHITE_KING_ROW, KING_COL, LAST_COL) and
                not is_square_attacked(board, WHITE_KING_ROW, KING_COL + 1, "black") and
                not is_square_attacked(board, WHITE_KING_ROW, KING_SIDE_CASTLE_COL, "black")):
                moves.append((WHITE_KING_ROW, KING_SIDE_CASTLE_COL))
            # 长易位（后翼）
            if (not castling_state["w_r_left"] and 
                is_row_empty_between(board, WHITE_KING_ROW, KING_COL, FIRST_COL) and
                not is_square_attacked(board, WHITE_KING_ROW, KING_COL - 1, "black") and
                not is_square_attacked(board, WHITE_KING_ROW, QUEEN_SIDE_CASTLE_COL, "black")):
                moves.append((WHITE_KING_ROW, QUEEN_SIDE_CASTLE_COL))
    
    elif turn == "black" and row == BLACK_KING_ROW and col == KING_COL:
        if not castling_state["b_king"] and not is_square_attacked(board, BLACK_KING_ROW, KING_COL, "white"):
            # 短易位（王翼）
            if (not castling_state["b_r_right"] and 
                is_row_empty_between(board, BLACK_KING_ROW, KING_COL, LAST_COL) and
                not is_square_attacked(board, BLACK_KING_ROW, KING_COL + 1, "white") and
                not is_square_attacked(board, BLACK_KING_ROW, KING_SIDE_CASTLE_COL, "white")):
                moves.append((BLACK_KING_ROW, KING_SIDE_CASTLE_COL))
            # 长易位（后翼）
            if (not castling_state["b_r_left"] and 
                is_row_empty_between(board, BLACK_KING_ROW, KING_COL, FIRST_COL) and
                not is_square_attacked(board, BLACK_KING_ROW, KING_COL - 1, "white") and
                not is_square_attacked(board, BLACK_KING_ROW, QUEEN_SIDE_CASTLE_COL, "white")):
                moves.append((BLACK_KING_ROW, QUEEN_SIDE_CASTLE_COL))

# ---------------------- 获取原始走法（不检查将军） ----------------------
def get_raw_moves(
    board: BoardType,
    row: int,
    col: int,
    turn: str,
    castling_state: Optional[CastlingState],
    en_passant_target: Optional[Position]
) -> List[Position]:
    """获取不考虑将军的走法"""
    piece = board[row][col]
    moves = []
    piece_type = piece.upper()

    # 车、象、后: 长距离走法
    if piece_type in ("R", "B", "Q"):
        sliding_dirs = {
            'R': [(-1, 0), (1, 0), (0, -1), (0, 1)],
            'B': [(-1, -1), (-1, 1), (1, -1), (1, 1)],
            'Q': [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)],
        }
        for delta_row, delta_col in sliding_dirs[piece_type]:
            next_row, next_col = row + delta_row, col + delta_col
            while FIRST_ROW <= next_row < BOARD_SIZE and FIRST_COL <= next_col < BOARD_SIZE:
                target = board[next_row][next_col]
                if target == EMPTY:
                    moves.append((next_row, next_col))
                elif is_enemy(target, turn):
                    moves.append((next_row, next_col))
                    break
                else:
                    break
                next_row += delta_row
                next_col += delta_col

    # 马: 跳跃走法
    elif piece_type == "N":
        knight_moves = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)
        ]
        for delta_row, delta_col in knight_moves:
            next_row, next_col = row + delta_row, col + delta_col
            if FIRST_ROW <= next_row < BOARD_SIZE and FIRST_COL <= next_col < BOARD_SIZE:
                target = board[next_row][next_col]
                if target == EMPTY or is_enemy(target, turn):
                    moves.append((next_row, next_col))

    # 王: 一步走法 + 易位
    elif piece_type == "K":
        king_moves = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]
        for delta_row, delta_col in king_moves:
            next_row, next_col = row + delta_row, col + delta_col
            if FIRST_ROW <= next_row < BOARD_SIZE and FIRST_COL <= next_col < BOARD_SIZE:
                target = board[next_row][next_col]
                if target == EMPTY or is_enemy(target, turn):
                    moves.append((next_row, next_col))

        # 王车易位
        if castling_state is not None:
            _handle_castling_moves(board, row, col, turn, castling_state, moves)

    # 兵: 直走 + 斜吃 + 过路兵
    elif piece_type == "P":
        direction = PAWN_DIR_WHITE if turn == "white" else PAWN_DIR_BLACK
        start_row = PAWN_START_ROW_WHITE if turn == "white" else PAWN_START_ROW_BLACK

        # 直走
        next_row = row + direction
        if FIRST_ROW <= next_row < BOARD_SIZE and board[next_row][col] == EMPTY:
            moves.append((next_row, col))
            # 开局双走两格
            if row == start_row:
                next_row2 = row + direction * PAWN_DOUBLE_STEP
                if board[next_row2][col] == EMPTY:
                    moves.append((next_row2, col))

        # 斜吃
        for delta_col in (-1, 1):
            next_col = col + delta_col
            next_row = row + direction
            if FIRST_ROW <= next_row < BOARD_SIZE and FIRST_COL <= next_col < BOARD_SIZE and is_enemy(board[next_row][next_col], turn):
                moves.append((next_row, next_col))

        # 吃过路兵
        if en_passant_target is not None:
            ep_row, ep_col = en_passant_target
            for delta_col in (-1, 1):
                if (row + direction, col + delta_col) == (ep_row, ep_col):
                    moves.append((ep_row, ep_col))

    return moves

# ---------------------- 获取合法走法（考虑将军） ----------------------
def get_legal_moves(
    board: BoardType,
    row: int,
    col: int,
    turn: str,
    castling_state: Optional[CastlingState],
    en_passant_target: Optional[Position]
) -> List[Position]:
    """获取合法走法（不能导致己方王被将军）"""
    raw_moves = get_raw_moves(board, row, col, turn, castling_state, en_passant_target)
    legal_moves = []

    for to_row, to_col in raw_moves:
        temp_board = copy.deepcopy(board)
        temp_castling = copy.deepcopy(castling_state) if castling_state else None

        piece = temp_board[row][col]
        temp_board[to_row][to_col] = piece
        temp_board[row][col] = EMPTY

        # 处理易位（模拟车移动）
        if piece.upper() == "K":
            if piece == "K" and row == WHITE_KING_ROW and col == KING_COL and to_row == WHITE_KING_ROW and to_col == KING_SIDE_CASTLE_COL:
                temp_board[WHITE_KING_ROW][KING_COL + 1] = temp_board[WHITE_KING_ROW][LAST_COL]
                temp_board[WHITE_KING_ROW][LAST_COL] = EMPTY
            elif piece == "K" and row == WHITE_KING_ROW and col == KING_COL and to_row == WHITE_KING_ROW and to_col == QUEEN_SIDE_CASTLE_COL:
                temp_board[WHITE_KING_ROW][KING_COL - 1] = temp_board[WHITE_KING_ROW][FIRST_COL]
                temp_board[WHITE_KING_ROW][FIRST_COL] = EMPTY
            elif piece == "k" and row == BLACK_KING_ROW and col == KING_COL and to_row == BLACK_KING_ROW and to_col == KING_SIDE_CASTLE_COL:
                temp_board[BLACK_KING_ROW][KING_COL + 1] = temp_board[BLACK_KING_ROW][LAST_COL]
                temp_board[BLACK_KING_ROW][LAST_COL] = EMPTY
            elif piece == "k" and row == BLACK_KING_ROW and col == KING_COL and to_row == BLACK_KING_ROW and to_col == QUEEN_SIDE_CASTLE_COL:
                temp_board[BLACK_KING_ROW][KING_COL - 1] = temp_board[BLACK_KING_ROW][FIRST_COL]
                temp_board[BLACK_KING_ROW][FIRST_COL] = EMPTY

        # 处理过路兵
        if piece.upper() == "P" and abs(to_col - col) == 1 and temp_board[to_row][to_col] == EMPTY:
            temp_board[row][to_col] = EMPTY

        if not is_king_in_check(temp_board, turn):
            legal_moves.append((to_row, to_col))

    return legal_moves

# ---------------------- 检查王是否被将军 ----------------------
def is_king_in_check(board: BoardType, turn: str) -> bool:
    """检查 turn 方的王是否被将军"""
    king = 'K' if turn == 'white' else 'k'
    king_pos = None
    
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] == king:
                king_pos = (row, col)
                break
        if king_pos:
            break
    
    if not king_pos:
        return True
    
    row, col = king_pos
    enemy = 'black' if turn == 'white' else 'white'
    
    for attacker_row in range(BOARD_SIZE):
        for attacker_col in range(BOARD_SIZE):
            piece = board[attacker_row][attacker_col]
            if piece == EMPTY:
                continue
            if is_enemy(piece, turn):
                moves = get_raw_moves(board, attacker_row, attacker_col, enemy, None, None)
                if (row, col) in moves:
                    return True
    return False

# ---------------------- 获取全部合法走法 ----------------------
def get_all_legal_moves(
    board: BoardType,
    turn: str,
    castling_state: Optional[CastlingState],
    en_passant_target: Optional[Position]
) -> List[MoveType]:
    """获取当前方所有合法走法"""
    all_steps = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            piece = board[row][col]
            if is_same_side(piece, turn):
                legal = get_legal_moves(board, row, col, turn, castling_state, en_passant_target)
                for to_row, to_col in legal:
                    all_steps.append(((row, col), (to_row, to_col)))
    return all_steps

# ---------------------- 兵升变选择函数 ----------------------
def promotion_select(is_white: bool, auto: bool = False) -> str:
    """
    兵升变选择
    参数:
        is_white: 是否为白方
        auto: 是否自动选择（AI 使用）, True 时直接升后
    """
    if auto:
        return WQ if is_white else BQ
    
    while True:
        print("\n兵到达底线, 请选择升变棋子: ")
        print("1 - 后(Q/q) | 2 - 车(R/r) | 3 - 象(B/b) | 4 - 马(N/n)")
        sel = safe_input("输入数字: ")
        
        if sel == "quit":
            return WQ if is_white else BQ
        
        if sel == "1":
            return WQ if is_white else BQ
        elif sel == "2":
            return WR if is_white else BR
        elif sel == "3":
            return WB if is_white else BB
        elif sel == "4":
            return WN if is_white else BN
        else:
            print("❌ 输入无效, 请输入1/2/3/4! ")

# ---------------------- 落子逻辑辅助函数 ----------------------

def _handle_pawn_moves(
    board: BoardType,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    piece: str,
    turn: str
) -> Tuple[Optional[Position], Optional[Position], bool, bool]:
    """
    处理兵的移动相关逻辑
    返回: (new_ep, en_passant_captured, is_capture, is_en_passant)
    """
    new_ep = None
    en_passant_captured = None
    is_capture = False
    is_en_passant = False
    
    dr_abs = abs(to_row - from_row)
    dc_abs = abs(to_col - from_col)
    
    # 吃过路兵
    if piece.upper() == "P" and dc_abs == 1 and board[to_row][to_col] == EMPTY:
        en_passant_captured = (from_row, to_col)
        board[from_row][to_col] = EMPTY
        is_capture = True
        is_en_passant = True
    
    # 兵一次走两格, 记录过路兵坐标
    if piece.upper() == "P" and dr_abs == PAWN_DOUBLE_STEP:
        ep_row = (from_row + to_row) // 2
        new_ep = (ep_row, to_col)
    
    return new_ep, en_passant_captured, is_capture, is_en_passant

def _handle_castling_execution(
    board: BoardType,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    piece: str
) -> Tuple[bool, str]:
    """
    执行王车易位（移动车）
    返回: (is_castling, moved_piece)
    """
    is_castling = False
    moved_piece = piece
    
    if piece == "K":
        if from_row == WHITE_KING_ROW and from_col == KING_COL and to_row == WHITE_KING_ROW and to_col == KING_SIDE_CASTLE_COL:
            board[WHITE_KING_ROW][KING_COL + 1] = board[WHITE_KING_ROW][LAST_COL]
            board[WHITE_KING_ROW][LAST_COL] = EMPTY
            moved_piece = "K"
            is_castling = True
        elif from_row == WHITE_KING_ROW and from_col == KING_COL and to_row == WHITE_KING_ROW and to_col == QUEEN_SIDE_CASTLE_COL:
            board[WHITE_KING_ROW][KING_COL - 1] = board[WHITE_KING_ROW][FIRST_COL]
            board[WHITE_KING_ROW][FIRST_COL] = EMPTY
            moved_piece = "K"
            is_castling = True
    
    elif piece == "k":
        if from_row == BLACK_KING_ROW and from_col == KING_COL and to_row == BLACK_KING_ROW and to_col == KING_SIDE_CASTLE_COL:
            board[BLACK_KING_ROW][KING_COL + 1] = board[BLACK_KING_ROW][LAST_COL]
            board[BLACK_KING_ROW][LAST_COL] = EMPTY
            moved_piece = "k"
            is_castling = True
        elif from_row == BLACK_KING_ROW and from_col == KING_COL and to_row == BLACK_KING_ROW and to_col == QUEEN_SIDE_CASTLE_COL:
            board[BLACK_KING_ROW][KING_COL - 1] = board[BLACK_KING_ROW][FIRST_COL]
            board[BLACK_KING_ROW][FIRST_COL] = EMPTY
            moved_piece = "k"
            is_castling = True
    
    return is_castling, moved_piece

def _update_castling_flags(
    castling_state: CastlingState,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    piece: str
) -> None:
    """
    更新易位状态标记
    """
    # 王移动标记
    if piece == "K":
        castling_state["w_king"] = True
    elif piece == "k":
        castling_state["b_king"] = True
    
    # 车移动标记
    if piece == "R":
        if from_col == FIRST_COL:
            castling_state["w_r_left"] = True
        if from_col == LAST_COL:
            castling_state["w_r_right"] = True
    elif piece == "r":
        if from_col == FIRST_COL:
            castling_state["b_r_left"] = True
        if from_col == LAST_COL:
            castling_state["b_r_right"] = True
    
    # 车被吃标记
    if to_row == WHITE_KING_ROW and to_col == FIRST_COL:
        castling_state["w_r_left"] = True
    if to_row == WHITE_KING_ROW and to_col == LAST_COL:
        castling_state["w_r_right"] = True
    if to_row == BLACK_KING_ROW and to_col == FIRST_COL:
        castling_state["b_r_left"] = True
    if to_row == BLACK_KING_ROW and to_col == LAST_COL:
        castling_state["b_r_right"] = True

def _handle_promotion(
    board: BoardType,
    to_row: int,
    to_col: int,
    turn: str,
    auto: bool = False
) -> Optional[str]:
    """
    处理兵升变
    参数:
        auto: 是否自动选择（AI 使用）, True 时直接升后
    返回: promotion_piece 或 None
    """
    piece = board[to_row][to_col]
    if piece not in ("P", "p"):
        return None
    
    if turn == "white" and to_row == FIRST_ROW:
        new_piece = promotion_select(True, auto)
        board[to_row][to_col] = new_piece
        return new_piece
    elif turn == "black" and to_row == LAST_ROW:
        new_piece = promotion_select(False, auto)
        board[to_row][to_col] = new_piece
        return new_piece
    
    return None

# ---------------------- 落子逻辑 ----------------------
def make_move(
    board: BoardType,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    castling_state: CastlingState,
    turn: str,
    en_passant_target: Optional[Position],
    auto_promotion: bool = False
) -> Tuple[Optional[Position], MoveRecord]:
    """
    执行走法
    参数:
        auto_promotion: 是否自动升变（AI 使用）, True 时 AI 自动升后
    返回: (new_ep, move_record)
    """
    piece = board[from_row][from_col]
    captured_piece = board[to_row][to_col]
    
    # 保存当前状态（用于悔棋）
    old_en_passant = en_passant_target
    old_castling = copy.deepcopy(castling_state)
    
    # 1. 处理兵相关逻辑（过路兵、双走）
    new_ep, en_passant_captured, is_capture, is_en_passant = _handle_pawn_moves(
        board, from_row, from_col, to_row, to_col, piece, turn
    )
    if captured_piece != EMPTY:
        is_capture = True
    
    # 2. 执行王车易位（移动车）
    is_castling, moved_piece = _handle_castling_execution(
        board, from_row, from_col, to_row, to_col, piece
    )
    
    # 3. 更新易位状态标记
    _update_castling_flags(castling_state, from_row, from_col, to_row, to_col, piece)
    
    # 4. 基础移动
    board[to_row][to_col] = board[from_row][from_col]
    board[from_row][from_col] = EMPTY
    
    # 5. 处理兵升变
    promotion_piece = _handle_promotion(board, to_row, to_col, turn, auto_promotion)
    
    # 6. 构建走法记录
    move_record = {
        'from_row': from_row, 'from_col': from_col,
        'to_row': to_row, 'to_col': to_col,
        'piece': piece,
        'captured': captured_piece,
        'castling_state': old_castling,
        'old_en_passant': old_en_passant,
        'new_ep': new_ep,
        'is_capture': is_capture,
        'is_en_passant': is_en_passant,
        'is_castling': is_castling,
        'promotion_piece': promotion_piece,
        'en_passant_captured': en_passant_captured,
        'turn': turn
    }
    
    return new_ep, move_record

# ---------------------- 悔棋函数 ----------------------
def undo_move(
    board: BoardType,
    castling_state: CastlingState,
    move_record: MoveRecord
) -> Optional[Position]:
    """撤销一步走法, 返回之前的过路兵目标"""
    from_row, from_col = move_record['from_row'], move_record['from_col']
    to_row, to_col = move_record['to_row'], move_record['to_col']
    piece = move_record['piece']
    captured = move_record['captured']
    is_castling = move_record['is_castling']
    is_en_passant = move_record['is_en_passant']
    en_passant_captured = move_record.get('en_passant_captured')
    promotion_piece = move_record.get('promotion_piece')
    
    board[from_row][from_col] = piece
    
    if is_en_passant and en_passant_captured:
        ep_row, ep_col = en_passant_captured
        board[ep_row][ep_col] = 'p' if piece.islower() else 'P'
        board[to_row][to_col] = EMPTY
    elif is_castling:
        if piece == "K":
            board[to_row][to_col] = EMPTY
            if to_col == KING_SIDE_CASTLE_COL:
                board[WHITE_KING_ROW][LAST_COL] = 'R'
                board[WHITE_KING_ROW][KING_COL + 1] = EMPTY
            else:
                board[WHITE_KING_ROW][FIRST_COL] = 'R'
                board[WHITE_KING_ROW][KING_COL - 1] = EMPTY
        else:
            board[to_row][to_col] = EMPTY
            if to_col == KING_SIDE_CASTLE_COL:
                board[BLACK_KING_ROW][LAST_COL] = 'r'
                board[BLACK_KING_ROW][KING_COL + 1] = EMPTY
            else:
                board[BLACK_KING_ROW][FIRST_COL] = 'r'
                board[BLACK_KING_ROW][KING_COL - 1] = EMPTY
    else:
        board[to_row][to_col] = captured
        if captured != EMPTY:
            board[to_row][to_col] = captured
        if promotion_piece:
            board[from_row][from_col] = piece
    
    castling_state.update(move_record['castling_state'])
    return move_record['old_en_passant']

# ---------------------- 走法描述生成 ----------------------
def generate_move_description(
    board: BoardType,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    turn: str,
    move_record: MoveRecord
) -> str:
    """生成走法的PGN描述"""
    if move_record['is_castling']:
        if to_col > from_col:
            return "O-O"
        else:
            return "O-O-O"
    
    piece = move_record['piece']
    piece_type = piece.upper()
    captured = move_record['captured']
    is_capture = move_record['is_capture']
    is_en_passant = move_record['is_en_passant']
    promotion = move_record['promotion_piece']
    
    if piece_type == "P":
        move_str = ""
        if is_capture or is_en_passant:
            move_str += row_col_to_pos(from_row, from_col)[0] + "x"
        move_str += row_col_to_pos(to_row, to_col)
        if promotion:
            move_str += f"={promotion.upper()}"
        return move_str
    
    move_str = piece_type
    if is_capture:
        move_str += "x"
    move_str += row_col_to_pos(to_row, to_col)
    return move_str

# ---------------------- 胜负判定 ----------------------
def get_board_hash(board: BoardType) -> str:
    return ''.join(''.join(row) for row in board)

def check_threefold_repetition(position_history: List[str]) -> bool:
    if len(position_history) < 6:
        return False
    
    position_count = defaultdict(int)
    for pos_hash in position_history:
        position_count[pos_hash] += 1
        if position_count[pos_hash] >= 3:
            return True
    return False

def check_fifty_move_rule(halfmove_clock: int) -> bool:
    return halfmove_clock >= 100

def check_insufficient_material(board: BoardType) -> bool:
    pieces = {'white': [], 'black': []}
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            piece = board[row][col]
            if piece != EMPTY:
                if piece.isupper():
                    pieces['white'].append(piece)
                else:
                    pieces['black'].append(piece)
    
    white_pieces = [p for p in pieces['white'] if p != 'K']
    black_pieces = [p for p in pieces['black'] if p != 'k']
    
    if not white_pieces and not black_pieces:
        return True
    
    if len(white_pieces) == 1 and white_pieces[0] == 'N' and not black_pieces:
        return True
    if len(black_pieces) == 1 and black_pieces[0] == 'n' and not white_pieces:
        return True
    
    if len(white_pieces) == 1 and white_pieces[0] == 'B' and not black_pieces:
        return True
    if len(black_pieces) == 1 and black_pieces[0] == 'b' and not white_pieces:
        return True
    
    if len(white_pieces) == 1 and white_pieces[0] == 'B' and len(black_pieces) == 1 and black_pieces[0] == 'b':
        white_bishop_pos = None
        black_bishop_pos = None
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if board[row][col] == 'B':
                    white_bishop_pos = (row, col)
                elif board[row][col] == 'b':
                    black_bishop_pos = (row, col)
        if white_bishop_pos and black_bishop_pos:
            if (white_bishop_pos[0] + white_bishop_pos[1]) % 2 == (black_bishop_pos[0] + black_bishop_pos[1]) % 2:
                return True
    
    return False

def is_game_over(
    board: BoardType,
    turn: str,
    castling_state: Optional[CastlingState],
    en_passant_target: Optional[Position],
    position_history: List[str],
    halfmove_clock: int
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    检查游戏是否结束
    返回: (is_end, result, reason)
    """
    moves = get_all_legal_moves(board, turn, castling_state, en_passant_target)
    
    if not moves:
        if is_king_in_check(board, turn):
            winner = "1-0" if turn == "black" else "0-1"
            return True, winner, "将杀"
        else:
            return True, "1/2-1/2", "逼和"
    
    if check_threefold_repetition(position_history):
        return True, "1/2-1/2", "三次重复局面"
    
    if check_fifty_move_rule(halfmove_clock):
        return True, "1/2-1/2", "50步规则"
    
    if check_insufficient_material(board):
        return True, "1/2-1/2", "子力不足"
    
    return False, None, None

# ---------------------- 走法记录类 ----------------------
class GameRecorder:
    def __init__(self) -> None:
        self.moves: List[Dict] = []
        self.move_records: List[MoveRecord] = []
        self.position_history: List[str] = []
        self.halfmove_clock: int = 0
        self.result: Optional[str] = None
        self.start_time: datetime = datetime.now()
        self.white_player: str = "Player"
        self.black_player: str = "AI"
        self.game_type: str = "AI"
    
    def add_move(self, move_num: int, white_move: str, black_move: Optional[str] = None, move_record: Optional[MoveRecord] = None) -> None:
        if black_move is None:
            self.moves.append({
                'move_num': move_num,
                'white': white_move,
                'black': '',
                'fen': ''
            })
            if move_record:
                self.move_records.append(move_record)
                if move_record['is_capture'] or move_record['piece'].upper() == 'P':
                    self.halfmove_clock = 0
                else:
                    self.halfmove_clock += 1
        else:
            if len(self.moves) >= move_num:
                self.moves[move_num - 1]['black'] = black_move
                if move_record:
                    self.move_records.append(move_record)
                    if move_record['is_capture'] or move_record['piece'].upper() == 'P':
                        self.halfmove_clock = 0
                    else:
                        self.halfmove_clock += 1
            else:
                self.moves.append({
                    'move_num': move_num,
                    'white': white_move,
                    'black': black_move,
                    'fen': ''
                })
                if move_record:
                    self.move_records.append(move_record)
                    if move_record['is_capture'] or move_record['piece'].upper() == 'P':
                        self.halfmove_clock = 0
                    else:
                        self.halfmove_clock += 1
    
    def add_position(self, board: BoardType) -> None:
        self.position_history.append(get_board_hash(board))
    
    def undo_last_move(self) -> Optional[MoveRecord]:
        if self.move_records:
            self.halfmove_clock = 0
            if self.position_history:
                self.position_history.pop()
            return self.move_records.pop()
        return None
    
    def remove_last_move_from_history(self) -> None:
        if self.moves:
            last_move = self.moves[-1]
            if last_move['black']:
                self.moves.pop()
                if self.moves and not self.moves[-1]['black']:
                    self.moves.pop()
            else:
                self.moves.pop()
    
    def set_result(self, result: str) -> None:
        self.result = result
    
    def get_pgn(self) -> str:
        if not self.moves:
            return ""
        
        pgn = f'[Event "Casual Game"]\n'
        pgn += f'[Site "Chess AI"]\n'
        pgn += f'[Date "{self.start_time.strftime("%Y.%m.%d")}"]\n'
        pgn += f'[Round "1"]\n'
        pgn += f'[White "{self.white_player}"]\n'
        pgn += f'[Black "{self.black_player}"]\n'
        pgn += f'[Result "{self.result if self.result else "*"}"]\n'
        pgn += f'[GameType "{self.game_type}"]\n\n'
        
        for move in self.moves:
            move_num = move['move_num']
            white_move = move['white']
            black_move = move['black']
            
            if black_move:
                pgn += f"{move_num}. {white_move} {black_move} "
            else:
                pgn += f"{move_num}. {white_move} "
        
        pgn += f"{self.result if self.result else '*'}\n"
        return pgn
    
    def save_pgn(self, filename: Optional[str] = None) -> str:
        """保存PGN文件, 带错误处理"""
        if filename is None:
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"chess_game_{timestamp}.pgn"
        
        if not filename.endswith('.pgn'):
            filename += '.pgn'
        
        base_name = filename[:-4]
        counter = 1
        while os.path.exists(filename):
            filename = f"{base_name}_{counter}.pgn"
            counter += 1
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.get_pgn())
            return filename
        except PermissionError:
            print(f"❌ 无法保存PGN文件（权限不足）")
            raise
        except OSError as e:
            print(f"❌ 无法保存PGN文件 ({e})")
            raise
    
    def display_history(self) -> None:
        if not self.moves:
            print("\n📜 暂无走法记录")
            return
        
        print("\n" + "="*50)
        print("📜 走法历史")
        print("="*50)
        
        max_moves = len(self.moves)
        num_width = len(str(max_moves))
        
        for move in self.moves:
            move_num = move['move_num']
            white = move['white']
            black = move['black']
            
            if black:
                print(f"{move_num:>{num_width}}. {white:<10} {black:<10}")
            else:
                print(f"{move_num:>{num_width}}. {white:<10} {'...':<10}")
        
        if self.result:
            print("\n" + "="*50)
            print(f"结果: {self.result}")
        print("="*50)

# ---------------------- AI评估函数 ----------------------
def evaluate_board(board: BoardType) -> int:
    score = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            piece = board[row][col]
            if piece == EMPTY:
                continue
            if piece.isupper():
                score += evaluate_piece(piece, row, col, 'white')
            else:
                score -= evaluate_piece(piece, row, col, 'black')
    return score

# ---------------------- AI极小极大搜索 ----------------------
def minimax(
    board: BoardType,
    depth: int,
    alpha: float,
    beta: float,
    is_maximizing: bool,
    castling_state: CastlingState,
    en_passant_target: Optional[Position]
) -> Tuple[float, Optional[MoveType]]:
    if depth == 0:
        return evaluate_board(board), None
    
    turn = "white" if is_maximizing else "black"
    moves = get_all_legal_moves(board, turn, castling_state, en_passant_target)
    
    if not moves:
        if is_king_in_check(board, turn):
            return -MATE_SCORE + depth if is_maximizing else MATE_SCORE - depth, None
        else:
            return 0, None
    
    best_move = random.choice(moves) if moves else None
    
    if is_maximizing:
        max_eval = float('-inf')
        for move in moves:
            temp_board = copy.deepcopy(board)
            temp_castling = copy.deepcopy(castling_state)
            from_row, from_col = move[0]
            to_row, to_col = move[1]
            new_ep, _ = make_move(temp_board, from_row, from_col, to_row, to_col, temp_castling, turn, en_passant_target, auto_promotion=True)
            eval, _ = minimax(temp_board, depth - 1, alpha, beta, False, temp_castling, new_ep)
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in moves:
            temp_board = copy.deepcopy(board)
            temp_castling = copy.deepcopy(castling_state)
            from_row, from_col = move[0]
            to_row, to_col = move[1]
            new_ep, _ = make_move(temp_board, from_row, from_col, to_row, to_col, temp_castling, turn, en_passant_target, auto_promotion=True)
            eval, _ = minimax(temp_board, depth - 1, alpha, beta, True, temp_castling, new_ep)
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

# ---------------------- AI走棋 ---------------------
def get_ai_move(
    board: BoardType,
    castling_state: CastlingState,
    en_passant_target: Optional[Position],
    depth: int
) -> Optional[MoveType]:
    all_moves = get_all_legal_moves(board, "black", castling_state, en_passant_target)
    if not all_moves:
        return None
    
    _, best_move = minimax(board, depth, float('-inf'), float('inf'), False, 
                           castling_state, en_passant_target)
    
    if best_move is None:
        best_move = random.choice(all_moves)
    
    return best_move

# ---------------------- 游戏流程辅助函数 ----------------------

def _handle_game_end(
    board: BoardType,
    last_move_info: Optional[MoveType],
    recorder: GameRecorder,
    result: str,
    reason: str,
    turn: str
) -> None:
    """处理游戏结束"""
    clear_terminal()
    print_board(board, last_move_info, recorder)
    print(f"\n🏁 游戏结束! 原因: {reason}")
    
    if result == "1-0":
        print("🎉 白方胜利! ")
    elif result == "0-1":
        print("🎉 黑方胜利! ")
    else:
        print("🤝 和棋! ")
    
    recorder.set_result(result)
    recorder.display_history()
    
    save_choice = safe_input("\n是否保存PGN文件? (y/n): ").strip().lower()
    if save_choice == 'y':
        try:
            filename = recorder.save_pgn()
            print(f"✅ 已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存失败: {e}")
    
    input("\n回车返回菜单...")

def _handle_common_commands(
    user_input: str,
    recorder: GameRecorder,
    board: BoardType,
    castling_state: CastlingState,
    en_passant_target: Optional[Position]
) -> Tuple[bool, Optional[Position], bool]:
    """
    处理通用命令（history/save/undo/quit）
    返回: (handled, new_en_passant, should_quit)
    """
    if user_input == "quit":
        clear_terminal()
        print("返回主菜单...")
        return True, en_passant_target, True
    
    if user_input == "history":
        recorder.display_history()
        input("\n回车继续...")
        return True, en_passant_target, False
    
    if user_input == "save":
        if recorder.moves:
            try:
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            except Exception as e:
                print(f"❌ 保存失败: {e}")
        else:
            print("❌ 还没有走法可以保存")
        input("\n回车继续...")
        return True, en_passant_target, False
    
    if user_input == "undo":
        return True, en_passant_target, False  # 具体处理由调用者完成
    
    return False, en_passant_target, False

def _process_suggestion_mode_input(
    board: BoardType,
    turn: str,
    castling_state: CastlingState,
    en_passant_target: Optional[Position],
    recorder: GameRecorder,
    last_move_info: Optional[MoveType],
    move_count: int
) -> Tuple[Optional[bool], Optional[Position], Optional[MoveType], int, bool]:
    """
    处理走法建议模式的用户输入
    返回: (move_executed, new_en_passant, new_last_move_info, new_move_count, should_return)
    """
    selected_pos = None
    candidate_moves = None
    
    while True:
        clear_terminal()
        print_board(board, last_move_info, recorder, candidate_moves, selected_pos)
        
        print(f"\n当前回合: {turn}")
        print(f"半步计数: {recorder.halfmove_clock}/100 (50步规则)")
        
        if is_king_in_check(board, turn):
            print(f"⚠️  注意: {turn}方的王被将军了! ")
        
        if selected_pos:
            row, col = selected_pos
            piece = board[row][col]
            print(f"\n已选中棋子: {row_col_to_pos(row, col)} ({piece})")
            print(f"合法走法数: {len(candidate_moves) if candidate_moves else 0}")
            print("请输入目标位置（如 e4）, 或输入 'cancel' 取消")
        else:
            print(f"\n【{turn}方回合】请选择要移动的棋子（如 e2）")
        
        print("输入 'history'、'save'、'undo'、'quit' 执行操作")
        
        user_input = safe_input(">>> ")
        if not user_input:
            continue
        
        # 处理通用命令
        handled, new_ep, should_quit = _handle_common_commands(
            user_input, recorder, board, castling_state, en_passant_target
        )
        if should_quit:
            return None, en_passant_target, None, move_count, True
        if handled:
            continue
        
        # 处理 undo
        if user_input == "undo":
            return None, en_passant_target, None, move_count, False
        
        # 处理 cancel
        if user_input == "cancel":
            if selected_pos:
                selected_pos = None
                candidate_moves = None
                print("✅ 已取消选中")
                input("\n回车继续...")
            continue
        
        # 选择棋子
        if len(user_input) == 2 and not selected_pos:
            try:
                row, col = pos_to_row_col(user_input)
                piece = board[row][col]
                if is_same_side(piece, turn):
                    selected_pos = (row, col)
                    candidate_moves = get_legal_moves(board, row, col, turn, castling_state, en_passant_target)
                    if not candidate_moves:
                        print("❌ 这个棋子没有合法走法! ")
                        selected_pos = None
                        candidate_moves = None
                        input("\n回车继续...")
                        continue
                else:
                    print(f"❌ 这不是 {turn} 方的棋子! ")
                    input("\n回车继续...")
                    continue
            except InvalidInputError as e:
                print(f"❌ {e}")
                input("\n回车继续...")
                continue
            except Exception as e:
                print(f"❌ 无效坐标: {e}")
                input("\n回车继续...")
                continue
        
        # 执行走法
        elif len(user_input) == 4 and selected_pos:
            try:
                from_pos, to_pos = parse_move_input(user_input)
                if from_pos is None or to_pos is None:
                    print("❌ 格式错误! 示例: e4 或 e2-e4")
                    input("\n回车继续...")
                    continue
                
                to_row, to_col = pos_to_row_col(to_pos)
                from_row, from_col = selected_pos
                
                if candidate_moves and (to_row, to_col) not in candidate_moves:
                    print("❌ 非法走法! 请选择绿色圆点标记的位置")
                    input("\n回车继续...")
                    continue
                
                en_passant_target, move_record = make_move(
                    board, from_row, from_col, to_row, to_col, 
                    castling_state, turn, en_passant_target,
                    auto_promotion=False  # 玩家手动选择
                )
                move_count += 1
                last_move_info = ((from_row, from_col), (to_row, to_col))
                
                recorder.add_position(board)
                move_desc = generate_move_description(board, from_row, from_col, to_row, to_col, turn, move_record)
                move_num = (move_count + 1) // 2
                recorder.add_move(move_num, move_desc, move_record=move_record)
                
                return True, en_passant_target, last_move_info, move_count, False
                
            except InvalidInputError as e:
                print(f"❌ {e}")
                input("\n回车继续...")
                continue
            except Exception as e:
                print(f"❌ 无效目标: {e}")
                input("\n回车继续...")
                continue
        else:
            if not selected_pos:
                print("❌ 请先选择棋子（如 e2）")
            else:
                print("❌ 请输入目标位置（如 e4）或 'cancel' 取消")
            input("\n回车继续...")
            continue

def _process_traditional_mode_input(
    board: BoardType,
    turn: str,
    castling_state: CastlingState,
    en_passant_target: Optional[Position],
    recorder: GameRecorder,
    last_move_info: Optional[MoveType],
    move_count: int
) -> Tuple[Optional[bool], Optional[Position], Optional[MoveType], int, bool]:
    """
    处理传统模式的用户输入（直接输入完整走法）
    返回: (move_executed, new_en_passant, new_last_move_info, new_move_count, should_quit)
    """
    tip = "【白方回合 大写棋子】" if turn == "white" else "【黑方回合 小写棋子】"
    user_input = safe_input(f"{tip} 输入走棋: ")
    if not user_input:
        return False, en_passant_target, last_move_info, move_count, False
    
    # 处理通用命令
    handled, new_ep, should_quit = _handle_common_commands(
        user_input, recorder, board, castling_state, en_passant_target
    )
    if should_quit:
        return None, en_passant_target, None, move_count, True
    if handled:
        return False, en_passant_target, last_move_info, move_count, False
    
    # 处理 undo
    if user_input == "undo":
        return None, en_passant_target, None, move_count, False
    
    # 解析走法
    from_pos, to_pos = parse_move_input(user_input)
    if from_pos is None or to_pos is None:
        print("❌ 格式错误! 示例: e2e4 或 e2-e4")
        input("\n回车继续...")
        return False, en_passant_target, last_move_info, move_count, False
    
    try:
        from_row, from_col = pos_to_row_col(from_pos)
        to_row, to_col = pos_to_row_col(to_pos)
    except InvalidInputError as e:
        print(f"❌ {e}")
        input("\n回车继续...")
        return False, en_passant_target, last_move_info, move_count, False
    except Exception as e:
        print(f"❌ 坐标无效: {e}")
        input("\n回车继续...")
        return False, en_passant_target, last_move_info, move_count, False
    
    piece = board[from_row][from_col]
    if not is_same_side(piece, turn):
        print(f"❌ 当前回合不能移动该棋子! ")
        input("\n回车继续...")
        return False, en_passant_target, last_move_info, move_count, False
    
    legal = get_legal_moves(board, from_row, from_col, turn, castling_state, en_passant_target)
    if (to_row, to_col) not in legal:
        print("❌ 非法走棋! ")
        input("\n回车继续...")
        return False, en_passant_target, last_move_info, move_count, False
    
    en_passant_target, move_record = make_move(
        board, from_row, from_col, to_row, to_col, 
        castling_state, turn, en_passant_target,
        auto_promotion=False  # 玩家手动选择
    )
    move_count += 1
    last_move_info = ((from_row, from_col), (to_row, to_col))
    
    recorder.add_position(board)
    move_desc = generate_move_description(board, from_row, from_col, to_row, to_col, turn, move_record)
    move_num = (move_count + 1) // 2
    recorder.add_move(move_num, move_desc, move_record=move_record)
    
    return True, en_passant_target, last_move_info, move_count, False

def _handle_player_turn(
    board: BoardType,
    turn: str,
    castling_state: CastlingState,
    en_passant_target: Optional[Position],
    recorder: GameRecorder,
    last_move_info: Optional[MoveType],
    move_count: int,
    show_suggestions: bool,
    is_ai_mode: bool
) -> Tuple[str, Optional[str], Optional[str], Optional[Position], Optional[MoveType], int, Optional[bool]]:
    """
    处理玩家走棋
    返回: (status, result, reason, new_en_passant, new_last_move_info, new_move_count, should_return)
    status: 'game_over', 'quit', 'undo', 'ok', 'invalid'
    """
    # 检查游戏是否该结束
    is_end, result, reason = is_game_over(
        board, turn, castling_state, en_passant_target,
        recorder.position_history, recorder.halfmove_clock
    )
    if is_end:
        return "game_over", result, reason, en_passant_target, last_move_info, move_count, None
    
    # 显示将军提示
    if is_king_in_check(board, turn):
        print(f"⚠️  注意: {turn}方的王被将军了! ")
    
    # 处理玩家走法
    if show_suggestions:
        move_executed, en_passant_target, last_move_info, move_count, should_quit = \
            _process_suggestion_mode_input(
                board, turn, castling_state, en_passant_target,
                recorder, last_move_info, move_count
            )
    else:
        move_executed, en_passant_target, last_move_info, move_count, should_quit = \
            _process_traditional_mode_input(
                board, turn, castling_state, en_passant_target,
                recorder, last_move_info, move_count
            )
    
    if should_quit:
        return "quit", None, None, en_passant_target, last_move_info, move_count, None
    
    # 处理 undo（走法建议模式返回 None 表示需要撤销）
    if move_executed is None and show_suggestions:
        return "undo", None, None, en_passant_target, last_move_info, move_count, None
    
    # 如果走法未执行, 返回 'invalid' 状态
    if move_executed is False:
        return "invalid", None, None, en_passant_target, last_move_info, move_count, None
    
    return "ok", None, None, en_passant_target, last_move_info, move_count, None

def _handle_ai_turn(
    board: BoardType,
    castling_state: CastlingState,
    en_passant_target: Optional[Position],
    recorder: GameRecorder,
    last_move_info: Optional[MoveType],
    move_count: int
) -> Tuple[Optional[Position], Optional[MoveType], int, bool]:
    """
    处理 AI 走棋
    返回: (new_en_passant, new_last_move_info, new_move_count, should_return)
    """
    print("\n✅ 落子成功, AI思考中...", end="", flush=True)
    
    start_time = time.time()
    best_move = get_ai_move(board, castling_state, en_passant_target, SETTINGS['ai_depth'])
    elapsed = time.time() - start_time
    print(f" 完成! ({elapsed:.2f}s)")
    
    if best_move is None:
        # AI无走法
        if is_king_in_check(board, "black"):
            clear_terminal()
            print_board(board, last_move_info, recorder)
            print("\n🎉 将杀! 你赢了! ")
            recorder.set_result("1-0")
        else:
            clear_terminal()
            print_board(board, last_move_info, recorder)
            print("\n🤝 逼和! ")
            recorder.set_result("1/2-1/2")
        
        recorder.display_history()
        save_choice = safe_input("\n是否保存PGN文件? (y/n): ").strip().lower()
        if save_choice == 'y':
            try:
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            except Exception as e:
                print(f"❌ 保存失败: {e}")
        input("\n回车返回菜单...")
        return en_passant_target, last_move_info, move_count, True
    
    # 执行AI走法（自动升变）
    (from_row, from_col), (to_row, to_col) = best_move
    en_passant_target, ai_record = make_move(
        board, from_row, from_col, to_row, to_col,
        castling_state, "black", en_passant_target,
        auto_promotion=True  # AI 自动升变
    )
    move_count += 1
    last_move_info = ((from_row, from_col), (to_row, to_col))
    
    ai_move_desc = generate_move_description(board, from_row, from_col, to_row, to_col, "black", ai_record)
    recorder.add_position(board)
    
    move_num = (move_count + 1) // 2
    if len(recorder.moves) >= move_num:
        recorder.moves[move_num - 1]['black'] = ai_move_desc
        recorder.move_records.append(ai_record)
        if ai_record['is_capture'] or ai_record['piece'].upper() == 'P':
            recorder.halfmove_clock = 0
        else:
            recorder.halfmove_clock += 1
    else:
        recorder.add_move(move_num, "", ai_move_desc, move_record=ai_record)
    
    # 检查AI是否被将杀
    if is_king_in_check(board, "black"):
        ai_moves = get_all_legal_moves(board, "black", castling_state, en_passant_target)
        if not ai_moves:
            clear_terminal()
            print_board(board, last_move_info, recorder)
            print("\n🎉 将杀! 你赢了! ")
            recorder.set_result("1-0")
            recorder.display_history()
            save_choice = safe_input("\n是否保存PGN文件? (y/n): ").strip().lower()
            if save_choice == 'y':
                try:
                    filename = recorder.save_pgn()
                    print(f"✅ 已保存到: {filename}")
                except Exception as e:
                    print(f"❌ 保存失败: {e}")
            input("\n回车返回菜单...")
            return en_passant_target, last_move_info, move_count, True
    
    # 检查游戏是否结束
    is_end, result, reason = is_game_over(
        board, "white", castling_state, en_passant_target,
        recorder.position_history, recorder.halfmove_clock
    )
    if is_end:
        _handle_game_end(board, last_move_info, recorder, result, reason, "white")
        return en_passant_target, last_move_info, move_count, True
    
    return en_passant_target, last_move_info, move_count, False

# ---------------------- 人机对战 ----------------------
def play_ai() -> None:
    """人机对战, 带错误处理"""
    try:
        board, castling_state, en_passant_target = init_board()
        recorder = GameRecorder()
        recorder.white_player = "You"
        recorder.black_player = "AI"
        recorder.game_type = "AI"
        
        recorder.add_position(board)
        
        move_count = 0
        last_move_info = None
        show_suggestions = SETTINGS.get('show_suggestions', True)
        
        print("=========== 简易国际象棋人机对战 ===========")
        print("操作说明: ")
        print("  1. 你操控白方大写, AI黑方小写")
        print("  2. 王车易位: e1g1(短) / e1c1(长)")
        print("  3. 吃过路兵: 敌方兵双走后斜一格吃掉, 仅限下一回合")
        print("  4. 兵走到底线可升变后/车/象/马")
        
        if show_suggestions:
            print("  5. 走法方式: 先输入棋子位置(如 e2), 再输入目标位置(如 e4)")
            print("  6. 输入 'cancel' 取消选中棋子")
            print("  7. 输入 'quit' 返回菜单")
            print("  8. 输入 'history' 查看历史走法")
            print("  9. 输入 'save' 保存PGN文件")
            print("  10. 输入 'undo' 悔棋（撤销上一步）")
            print("  11. AI难度: 深度{SETTINGS['ai_depth']}层\n")
        else:
            print("  5. 走法方式: 直接输入完整走法（如 e2e4 或 e2-e4）")
            print("  6. 输入 'quit' 返回菜单")
            print("  7. 输入 'history' 查看历史走法")
            print("  8. 输入 'save' 保存PGN文件")
            print("  9. 输入 'undo' 悔棋（撤销上一步）")
            print("  10. AI难度: 深度{SETTINGS['ai_depth']}层\n")
        
        while True:
            clear_terminal()
            print_board(board, last_move_info, recorder)
            print(f"\n当前回合: 白方")
            print(f"半步计数: {recorder.halfmove_clock}/100 (50步规则)")
            
            # 玩家回合
            status, result, reason, en_passant_target, last_move_info, move_count, _ = \
                _handle_player_turn(board, "white", castling_state, en_passant_target,
                                    recorder, last_move_info, move_count, show_suggestions, True)
            
            if status == "game_over":
                _handle_game_end(board, last_move_info, recorder, result, reason, "white")
                break
            elif status == "quit":
                break
            elif status == "invalid":
                # 非法走法, 继续等待玩家输入
                continue
            elif status == "undo":
                if len(recorder.move_records) < 2:
                    print("❌ 没有足够的走法可以悔棋! ")
                    input("\n回车继续...")
                    continue
                
                # 撤销AI走法
                ai_record = recorder.undo_last_move()
                if ai_record:
                    en_passant_target = undo_move(board, castling_state, ai_record)
                    recorder.remove_last_move_from_history()
                
                # 撤销玩家走法
                player_record = recorder.undo_last_move()
                if player_record:
                    en_passant_target = undo_move(board, castling_state, player_record)
                    recorder.remove_last_move_from_history()
                
                move_count -= 2
                last_move_info = None
                print("✅ 已悔棋")
                input("\n回车继续...")
                continue
            
            # 检查AI是否被将杀
            if is_king_in_check(board, "black"):
                ai_moves = get_all_legal_moves(board, "black", castling_state, en_passant_target)
                if not ai_moves:
                    clear_terminal()
                    print_board(board, last_move_info, recorder)
                    print("\n🎉 将杀! 你赢了! ")
                    recorder.set_result("1-0")
                    recorder.display_history()
                    save_choice = safe_input("\n是否保存PGN文件? (y/n): ").strip().lower()
                    if save_choice == 'y':
                        try:
                            filename = recorder.save_pgn()
                            print(f"✅ 已保存到: {filename}")
                        except Exception as e:
                            print(f"❌ 保存失败: {e}")
                    input("\n回车返回菜单...")
                    break
            
            # 检查游戏是否结束
            is_end, result, reason = is_game_over(
                board, "black", castling_state, en_passant_target,
                recorder.position_history, recorder.halfmove_clock
            )
            if is_end:
                _handle_game_end(board, last_move_info, recorder, result, reason, "black")
                break
            
            # AI回合
            en_passant_target, last_move_info, move_count, should_return = \
                _handle_ai_turn(board, castling_state, en_passant_target, recorder,
                               last_move_info, move_count)
            
            if should_return:
                break
            
            input("\n回车下一回合...")
    
    except KeyboardInterrupt:
        print("\n\n游戏被中断, 返回主菜单...")
        input("回车继续...")
    except Exception as e:
        print(f"\n❌ 游戏发生错误: {e}")
        input("回车继续...")
        raise

# ---------------------- 人人对战 ----------------------
def play_pvp() -> None:
    """人人对战, 带错误处理"""
    try:
        board, castling_state, en_passant_target = init_board()
        turn = "white"
        recorder = GameRecorder()
        recorder.white_player = "Player1"
        recorder.black_player = "Player2"
        recorder.game_type = "PVP"
        
        recorder.add_position(board)
        last_move_info = None
        move_count = 0
        
        show_suggestions = SETTINGS.get('show_suggestions', True)
        
        print("=========== 人人对战 ===========")
        print("白先行, 支持易位、过路兵、兵升变")
        
        if show_suggestions:
            print("走法方式: 先输入棋子位置, 再输入目标位置")
            print("输入 'cancel' 取消选中棋子")
        else:
            print("走法方式: 直接输入完整走法（如 e2e4 或 e2-e4）")
        
        print("输入 'history' 查看历史走法")
        print("输入 'save' 保存PGN文件")
        print("输入 'undo' 悔棋")
        print("输入 'quit' 返回菜单\n")
        
        while True:
            clear_terminal()
            print_board(board, last_move_info, recorder)
            print(f"半步计数: {recorder.halfmove_clock}/100 (50步规则)")
            
            # 检查游戏是否该结束
            is_end, result, reason = is_game_over(
                board, turn, castling_state, en_passant_target,
                recorder.position_history, recorder.halfmove_clock
            )
            if is_end:
                _handle_game_end(board, last_move_info, recorder, result, reason, turn)
                break
            
            # 检查是否无走法
            all_moves = get_all_legal_moves(board, turn, castling_state, en_passant_target)
            if not all_moves:
                if is_king_in_check(board, turn):
                    winner = "黑方" if turn == "white" else "白方"
                    print(f"💀 将杀! {winner}获胜! ")
                    recorder.set_result("0-1" if turn == "white" else "1-0")
                else:
                    print("🤝 逼和! ")
                    recorder.set_result("1/2-1/2")
                
                recorder.display_history()
                save_choice = safe_input("\n是否保存PGN文件? (y/n): ").strip().lower()
                if save_choice == 'y':
                    try:
                        filename = recorder.save_pgn()
                        print(f"✅ 已保存到: {filename}")
                    except Exception as e:
                        print(f"❌ 保存失败: {e}")
                input("\n回车返回菜单...")
                break
            
            # 玩家回合（人人模式, 无AI, turn 由玩家控制）
            status, result, reason, en_passant_target, last_move_info, move_count, _ = \
                _handle_player_turn(board, turn, castling_state, en_passant_target,
                                    recorder, last_move_info, move_count, show_suggestions, False)
            
            if status == "game_over":
                _handle_game_end(board, last_move_info, recorder, result, reason, turn)
                break
            elif status == "quit":
                break
            elif status == "invalid":
                # 非法走法, 继续等待玩家输入
                continue
            elif status == "undo":
                if len(recorder.move_records) < 1:
                    print("❌ 没有走法可以悔棋! ")
                    input("\n回车继续...")
                    continue
                
                last_record = recorder.undo_last_move()
                if last_record:
                    en_passant_target = undo_move(board, castling_state, last_record)
                    recorder.remove_last_move_from_history()
                    if recorder.position_history:
                        recorder.position_history.pop()
                    move_count -= 1
                    turn = last_record['turn']
                    last_move_info = None
                    print("✅ 已悔棋")
                input("\n回车继续...")
                continue
            
            # 切换回合
            turn = "black" if turn == "white" else "white"
            print("✅ 落子完成, 切换对手")
            input("\n回车切换棋盘...")
    
    except KeyboardInterrupt:
        print("\n\n游戏被中断, 返回主菜单...")
        input("回车继续...")
    except Exception as e:
        print(f"\n❌ 游戏发生错误: {e}")
        input("回车继续...")
        raise

# ---------------------- 帮助界面 ----------------------
def show_help() -> None:
    clear_terminal()
    print("==================== 游戏帮助 ====================")
    print("1.菜单选项: 1人机 2人人 3帮助 4设置 5退出")
    print("2.走法方式（由设置中的'走法建议'控制）: ")
    print("   ✅ 开启: 两步走法, 先选棋子再选目标, 显示合法走位")
    print("   ❌ 关闭: 传统模式, 直接输入完整走法（如 e2e4）")
    print("3.棋子: 白大写 KQRNBP | 黑小写 kqrnbp")
    print("4.特殊规则: ")
    print("   ① 王车易位: 王、车未移动, 中间无棋子")
    print("     白短e1g1 / 白长e1c1 | 黑短e8g8 / 黑长e8c8")
    print("   ② 吃过路兵: 敌方兵一步两格, 斜一格吃掉")
    print("   ③ 兵升变: 兵走到底线, 可选后/车/象/马; AI自动升后")
    print("5.交互命令: ")
    print("   · 'history' 查看历史走法")
    print("   · 'save' 保存PGN文件")
    print("   · 'undo' 悔棋")
    print("   · 'quit' 返回主菜单")
    print("   · 'cancel' 取消选中棋子（走法建议模式）")
    print("6.设置功能: ")
    print("   · 切换棋子显示样式（字母 ↔ Unicode符号）")
    print("   · 调整AI难度（2=简单 / 3=中等 / 4=困难）")
    print("   · 走法历史显示（开启/关闭）")
    print("   · 彩色输出（开启/关闭）")
    print("   · 走法建议（开启/关闭）⭐")
    print("==================================================")
    input("\n回车返回菜单...")

# ---------------------- 设置界面 ----------------------
def show_settings() -> None:
    while True:
        clear_terminal()
        print("\n==================== 设置 ====================")
        print("当前设置(输入数字进行对应设置): ")
        print("  0. 返回主菜单")
        print(f"  1. 棋子样式: {'Unicode符号 ♔♚' if SETTINGS['piece_style'] == 'unicode' else '字母 KQ'}")
        print(f"  2. AI难度: 深度 {SETTINGS['ai_depth']} 层 "
              f"({'简单' if SETTINGS['ai_depth'] <= 2 else '中等' if SETTINGS['ai_depth'] == 3 else '困难'})")
        print(f"  3. 走法历史: {'✅ 开启' if SETTINGS['show_history'] else '❌ 关闭'}")
        print(f"  4. 彩色输出: {'✅ 开启' if SETTINGS.get('use_colors', True) else '❌ 关闭'}")
        print(f"  5. 走法建议: {'✅ 开启' if SETTINGS.get('show_suggestions', True) else '❌ 关闭'} ")
        print("==============================================")
        
        choice = safe_input("请输入数字选择: ")
        if choice == "quit":
            save_settings()
            break
        
        if choice == "0":
            save_settings()
            break
        elif choice == "1":
            if SETTINGS['piece_style'] == 'letter':
                SETTINGS['piece_style'] = 'unicode'
                print("\n✅ 已切换到 Unicode 符号样式(警告, 部分老旧终端可能无法显示)")
            else:
                SETTINGS['piece_style'] = 'letter'
                print("\n✅ 已切换到 字母 样式")
            
            print("\n预览效果: ")
            print("  字母样式: K Q R B N P")
            print("  Unicode样式: ♔ ♕ ♖ ♗ ♘ ♙")
            print("\n设置已保存, 按回车返回设置菜单...")
            input()
        elif choice == "2":
            while True:
                print("\n选择AI难度: ")
                print("  2 - 简单（思考快, 但棋力弱）")
                print("  3 - 中等（平衡）")
                print("  4 - 困难（思考慢, 棋力强）")
                depth_choice = safe_input("请输入 2/3/4: ")
                if depth_choice in ('2', '3', '4'):
                    SETTINGS['ai_depth'] = int(depth_choice)
                    print(f"\n✅ AI深度已设置为 {SETTINGS['ai_depth']} 层")
                    print("   （深度4以上会明显变慢, 不建议更高）")
                    input("\n回车继续...")
                    break
                else:
                    print("❌ 请输入 2/3/4")
                    input("\n回车继续...")
        elif choice == "3":
            SETTINGS['show_history'] = not SETTINGS['show_history']
            status = "开启" if SETTINGS['show_history'] else "关闭"
            print(f"\n✅ 走法历史显示已{status}")
            input("\n回车继续...")
        elif choice == "4":
            SETTINGS['use_colors'] = not SETTINGS.get('use_colors', True)
            status = "开启" if SETTINGS['use_colors'] else "关闭"
            print(f"\n✅ 彩色输出已{status}")
            print("\n预览效果: ")
            if SETTINGS['use_colors']:
                print(f"  {Colors.BRIGHT_WHITE}白方棋子{Colors.RESET} 和 {Colors.RED}黑方棋子{Colors.RESET}")
                print(f"  高亮: {Colors.BG_YELLOW}{Colors.BLACK}K{Colors.RESET}")
            else:
                print("  彩色已关闭, 所有棋子显示为普通字符")
            input("\n回车继续...")
        elif choice == "5":
            SETTINGS['show_suggestions'] = not SETTINGS.get('show_suggestions', True)
            status = "开启" if SETTINGS['show_suggestions'] else "关闭"
            print(f"\n✅ 走法建议已{status}")
            if SETTINGS['show_suggestions']:
                print("   走法建议模式: 先选棋子, 再输入目标位置")
                print("   绿色圆点标记合法走法位置")
            else:
                print("   传统模式: 直接输入完整走法（如 e2e4）")
            input("\n回车继续...")
        else:
            print("❌ 输入无效, 请重新选择")
            input("\n回车继续...")

# ---------------------- 主菜单 ----------------------
def main() -> None:
    """主程序入口, 带全局错误处理"""
    try:
        load_settings()
    except Exception as e:
        print(f"⚠️  加载设置失败: {e}")
    
    # 检测 Windows 终端是否支持 ANSI
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            SETTINGS['use_colors'] = False
    
    while True:
        try:
            clear_terminal()
            print("\n==================== 国际象棋 开始界面 ===================")
            print("| 1 - 人机对战                                           |")
            print("| 2 - 人人对战                                           |")
            print("| 3 - 查看帮助                                           |")
            print("| 4 - 设置                                               |")
            print("| 5 - 退出游戏                                           |")
            print("==========================================================")
            
            sel = safe_input("请输入数字选择: ")
            
            if sel == "1":
                play_ai()
            elif sel == "2":
                play_pvp()
            elif sel == "3":
                show_help()
            elif sel == "4":
                show_settings()
            elif sel == "5" or sel == "quit":
                clear_terminal()
                print("游戏退出, 再见! ")
                break
            else:
                print("❌ 输入无效, 请输入1/2/3/4/5")
                input("回车继续...")
        
        except KeyboardInterrupt:
            clear_terminal()
            print("\n游戏被中断, 再见! ")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            print("程序将返回主菜单")
            input("回车继续...")

if __name__ == "__main__":
    main()