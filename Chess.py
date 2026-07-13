#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chess.py - 命令行国际象棋

版本: v1.0.0
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
"""

import random
import subprocess
import os
import copy
import json
from datetime import datetime
from collections import defaultdict

# ---------------------- 全局设置 ----------------------
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    'piece_style': 'letter',  # 'letter' 或 'unicode'
    'ai_depth': 3,            # AI搜索深度: 2=简单, 3=中等, 4=困难
}

SETTINGS = DEFAULT_SETTINGS.copy()

# ---------------------- 设置持久化 ----------------------
def load_settings():
    """从文件加载设置"""
    global SETTINGS
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            SETTINGS.update(loaded)
    except FileNotFoundError:
        save_settings()  # 创建默认设置文件
    except Exception:
        pass  # 文件损坏则使用默认值

def save_settings():
    """保存设置到文件"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ---------------------- Unicode 国际象棋符号 ----------------------
UNICODE_PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
    '.': '·'
}

# 棋子颜色映射（用于显示）
PIECE_COLORS = {
    'K': 'white', 'Q': 'white', 'R': 'white', 'B': 'white', 'N': 'white', 'P': 'white',
    'k': 'black', 'q': 'black', 'r': 'black', 'b': 'black', 'n': 'black', 'p': 'black'
}

# ---------------------- 清屏函数 ----------------------
def clear_screen():
    subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)

# ---------------------- 棋子常量定义 ----------------------
EMPTY = "."
WK, WQ, WR, WB, WN, WP = "K", "Q", "R", "B", "N", "P"
BK, BQ, BR, BB, BN, BP = "k", "q", "r", "b", "n", "p"

# 棋子名称映射（用于PGN）
PIECE_NAMES = {
    'K': 'K', 'Q': 'Q', 'R': 'R', 'B': 'B', 'N': 'N', 'P': '',
    'k': 'K', 'q': 'Q', 'r': 'R', 'b': 'B', 'n': 'N', 'p': ''
}

# ---------------------- 棋子价值（用于AI评估） ----------------------
PIECE_VALUES = {
    'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000,
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000
}

# 位置价值表（简化版, 让兵更愿意前进, 马象占据中心）
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

def get_piece_value(piece, r, c, turn):
    """获取棋子价值（包含位置加成）"""
    if piece == EMPTY:
        return 0
    
    base_value = PIECE_VALUES.get(piece, 0)
    
    # 只有兵有位置加成
    if piece.upper() == 'P':
        if turn == 'white':
            # 白方视角, 行从底部(7)到顶部(0)
            row = 7 - r
        else:
            row = r
        col = c
        return base_value + PAWN_TABLE[row][col]
    
    # 马和象给中心位置加成
    if piece.upper() in ('N', 'B'):
        center_dist = abs(r - 3.5) + abs(c - 3.5)
        center_bonus = (7 - center_dist) * 5
        return base_value + center_bonus
    
    return base_value

# ---------------------- 初始化棋盘 + 易位状态 + 过路兵 ----------------------
def init_board():
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

# ---------------------- 棋盘打印（支持Unicode） ----------------------
def print_board(board):
    print("\n=========== 国际象棋 ===========\n")
    print("    a  b  c  d  e  f  g  h\n")
    for row_idx in range(8):
        line_num = 8 - row_idx
        row_str = f"{line_num}  "
        for col_idx in range(8):
            piece = board[row_idx][col_idx]
            
            if SETTINGS['piece_style'] == 'unicode':
                # 使用Unicode符号
                symbol = UNICODE_PIECES.get(piece, ' ')
                # 为Unicode符号添加间距, 保持对齐
                row_str += f" {symbol} "
            else:
                # 使用字母
                cell = f" {piece} "
                row_str += cell
                
        row_str += f"  {line_num}"
        print(row_str)
    print("\n    a  b  c  d  e  f  g  h")
    print("=================================\n")

# ---------------------- 坐标转换 a1 -> (行,列) ----------------------
def pos_to_rc(pos):
    col = ord(pos[0].lower()) - ord("a")
    row = 8 - int(pos[1])
    return row, col

def rc_to_pos(r, c):
    """(行,列) -> 坐标字符串"""
    return f"{chr(c + ord('a'))}{8 - r}"

# ---------------------- 阵营判断 ----------------------
def is_same_side(piece, turn):
    if piece == EMPTY:
        return False
    if turn == "white":
        return piece.isupper()
    return piece.islower()

def is_enemy(piece, turn):
    if piece == EMPTY:
        return False
    return not is_same_side(piece, turn)

# ---------------------- 王车易位辅助: 判断中间全空 ----------------------
def row_all_empty(board, r, c_start, c_end):
    step = 1 if c_end > c_start else -1
    c = c_start + step
    while c != c_end:
        if board[r][c] != EMPTY:
            return False
        c += step
    return True

# ---------------------- 检查某个位置是否被攻击 ----------------------
def is_square_attacked(board, r, c, by_turn):
    """检查(r,c)是否被by_turn阵营攻击"""
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == EMPTY:
                continue
            if is_same_side(piece, by_turn):
                # 获取该棋子的走法（不检查合法性, 只检查是否能到达目标）
                moves = get_raw_moves(board, row, col, by_turn, None, None)
                if (r, c) in moves:
                    return True
    return False

# ---------------------- 获取原始走法（不检查将军） ----------------------
def get_raw_moves(board, r, c, turn, castling_state, en_passant_target):
    """获取不考虑将军的走法"""
    piece = board[r][c]
    moves = []
    piece_type = piece.upper()
    dirs = []

    if piece_type == "R":
        dirs = [(-1,0), (1,0), (0,-1), (0,1)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == EMPTY:
                    moves.append((nr, nc))
                elif is_enemy(target, turn):
                    moves.append((nr, nc))
                    break
                else:
                    break
                nr += dr
                nc += dc
    
    elif piece_type == "B":
        dirs = [(-1,-1), (-1,1), (1,-1), (1,1)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == EMPTY:
                    moves.append((nr, nc))
                elif is_enemy(target, turn):
                    moves.append((nr, nc))
                    break
                else:
                    break
                nr += dr
                nc += dc
    
    elif piece_type == "Q":
        dirs = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == EMPTY:
                    moves.append((nr, nc))
                elif is_enemy(target, turn):
                    moves.append((nr, nc))
                    break
                else:
                    break
                nr += dr
                nc += dc
    
    elif piece_type == "N":
        dirs = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == EMPTY or is_enemy(target, turn):
                    moves.append((nr, nc))
    
    elif piece_type == "K":
        dirs = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == EMPTY or is_enemy(target, turn):
                    moves.append((nr, nc))
        
        # 王车易位（只在有castling_state时检查）
        if castling_state is not None:
            if turn == "white" and r == 7 and c == 4 and not castling_state["w_king"]:
                # 检查王是否在将军状态
                if not is_square_attacked(board, 7, 4, "black"):
                    # 短易位
                    if not castling_state["w_r_right"] and row_all_empty(board,7,4,7):
                        # 检查经过和到达的格子是否被攻击
                        if (not is_square_attacked(board, 7, 5, "black") and 
                            not is_square_attacked(board, 7, 6, "black")):
                            moves.append((7,6))
                    # 长易位
                    if not castling_state["w_r_left"] and row_all_empty(board,7,4,0):
                        if (not is_square_attacked(board, 7, 3, "black") and 
                            not is_square_attacked(board, 7, 2, "black")):
                            moves.append((7,2))
            
            if turn == "black" and r == 0 and c == 4 and not castling_state["b_king"]:
                if not is_square_attacked(board, 0, 4, "white"):
                    if not castling_state["b_r_right"] and row_all_empty(board,0,4,7):
                        if (not is_square_attacked(board, 0, 5, "white") and 
                            not is_square_attacked(board, 0, 6, "white")):
                            moves.append((0,6))
                    if not castling_state["b_r_left"] and row_all_empty(board,0,4,0):
                        if (not is_square_attacked(board, 0, 3, "white") and 
                            not is_square_attacked(board, 0, 2, "white")):
                            moves.append((0,2))
    
    elif piece_type == "P":
        dr = -1 if turn == "white" else 1
        start_r = 6 if turn == "white" else 1
        nr = r + dr
        # 直走一格
        if 0 <= nr < 8 and board[nr][c] == EMPTY:
            moves.append((nr, c))
            # 开局双走两格
            if r == start_r:
                nr2 = r + dr * 2
                if board[nr2][c] == EMPTY:
                    moves.append((nr2, c))
        # 斜吃普通棋子
        for dc in (-1, 1):
            nc = c + dc
            nr = r + dr
            if 0 <= nr < 8 and 0 <= nc < 8 and is_enemy(board[nr][nc], turn):
                moves.append((nr, nc))
        # 吃过路兵
        if en_passant_target is not None:
            ep_r, ep_c = en_passant_target
            for dc in (-1, 1):
                if (r + dr, c + dc) == (ep_r, ep_c):
                    moves.append((ep_r, ep_c))
    
    return moves

# ---------------------- 获取合法走法（考虑将军） ----------------------
def get_legal_moves(board, r, c, turn, castling_state, en_passant_target):
    """获取合法的走法（不能导致己方王被将军）"""
    raw_moves = get_raw_moves(board, r, c, turn, castling_state, en_passant_target)
    legal_moves = []
    
    for tr, tc in raw_moves:
        # 模拟走一步
        temp_board = copy.deepcopy(board)
        temp_castling = copy.deepcopy(castling_state) if castling_state else None
        
        # 模拟移动（简化版, 只用于检查将军）
        piece = temp_board[r][c]
        temp_board[tr][tc] = piece
        temp_board[r][c] = EMPTY
        
        # 如果是王, 更新位置
        if piece.upper() == "K":
            # 检查易位
            if piece == "K" and r == 7 and c == 4 and tr == 7 and tc == 6:
                temp_board[7][5] = temp_board[7][7]
                temp_board[7][7] = EMPTY
            elif piece == "K" and r == 7 and c == 4 and tr == 7 and tc == 2:
                temp_board[7][3] = temp_board[7][0]
                temp_board[7][0] = EMPTY
            elif piece == "k" and r == 0 and c == 4 and tr == 0 and tc == 6:
                temp_board[0][5] = temp_board[0][7]
                temp_board[0][7] = EMPTY
            elif piece == "k" and r == 0 and c == 4 and tr == 0 and tc == 2:
                temp_board[0][3] = temp_board[0][0]
                temp_board[0][0] = EMPTY
        
        # 过路兵
        if piece.upper() == "P" and abs(tc - c) == 1 and temp_board[tr][tc] == EMPTY:
            temp_board[r][tc] = EMPTY
        
        # 检查模拟后的局面是否导致己方王被将军
        if not is_king_in_check(temp_board, turn):
            legal_moves.append((tr, tc))
    
    return legal_moves

# ---------------------- 检查王是否被将军 ----------------------
def is_king_in_check(board, turn):
    """检查turn方的王是否被将军"""
    king = 'K' if turn == 'white' else 'k'
    king_pos = None
    
    # 找到王的位置
    for r in range(8):
        for c in range(8):
            if board[r][c] == king:
                king_pos = (r, c)
                break
        if king_pos:
            break
    
    if not king_pos:
        return True  # 王被吃了
    
    r, c = king_pos
    enemy = 'black' if turn == 'white' else 'white'
    
    # 检查所有敌方棋子是否能攻击到王
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == EMPTY:
                continue
            if is_enemy(piece, turn):
                # 获取该棋子的走法（不需要检查将军）
                moves = get_raw_moves(board, row, col, enemy, None, None)
                if (r, c) in moves:
                    return True
    return False

# ---------------------- 获取全部合法走法 ----------------------
def get_all_legal_moves(board, turn, castling_state, en_passant_target):
    all_steps = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if is_same_side(p, turn):
                legal = get_legal_moves(board, r, c, turn, castling_state, en_passant_target)
                for tr, tc in legal:
                    all_steps.append(((r, c), (tr, tc)))
    return all_steps

# ---------------------- 兵升变选择函数 ----------------------
def promotion_select(is_white):
    while True:
        print("\n兵到达底线, 请选择升变棋子: ")
        print("1 - 后(Q/q) | 2 - 车(R/r) | 3 - 象(B/b) | 4 - 马(N/n)")
        sel = input("输入数字: ").strip()
        if sel == "1":
            return WQ if is_white else BQ
        elif sel == "2":
            return WR if is_white else BR
        elif sel == "3":
            return WB if is_white else BB
        elif sel == "4":
            return WN if is_white else BN
        else:
            print("输入无效, 请输入1/2/3/4! ")

# ---------------------- 落子逻辑（返回完整状态用于悔棋） ----------------------
def make_move(board, fr, fc, tr, tc, castling_state, turn, en_passant_target):
    """执行走法, 返回所有需要记录的信息"""
    piece = board[fr][fc]
    captured_piece = board[tr][tc]
    new_ep = None
    dr_abs = abs(tr - fr)
    dc_abs = abs(tc - fc)
    is_capture = captured_piece != EMPTY
    moved_piece = piece
    promotion_piece = None
    is_en_passant = False
    is_castling = False
    en_passant_captured = None
    
    # 保存当前过路兵目标（用于悔棋恢复）
    old_en_passant = en_passant_target
    
    # 保存易位状态快照
    old_castling = copy.deepcopy(castling_state)

    # 1. 吃过路兵
    if piece.upper() == "P" and dc_abs == 1 and board[tr][tc] == EMPTY:
        en_passant_captured = (fr, tc)  # 被吃兵的位置
        board[fr][tc] = EMPTY
        is_capture = True
        is_en_passant = True

    # 2. 兵一次走两格, 记录过路兵坐标
    if piece.upper() == "P" and dr_abs == 2:
        ep_row = (fr + tr) // 2
        new_ep = (ep_row, tc)

    # 3. 王车易位, 自动移动车
    if piece == "K":
        castling_state["w_king"] = True
        if fr == 7 and fc == 4 and tr == 7 and tc == 6:
            board[7][5] = board[7][7]
            board[7][7] = EMPTY
            moved_piece = "K"
            is_castling = True
        if fr == 7 and fc == 4 and tr == 7 and tc == 2:
            board[7][3] = board[7][0]
            board[7][0] = EMPTY
            moved_piece = "K"
            is_castling = True
    if piece == "k":
        castling_state["b_king"] = True
        if fr == 0 and fc == 4 and tr == 0 and tc == 6:
            board[0][5] = board[0][7]
            board[0][7] = EMPTY
            moved_piece = "k"
            is_castling = True
        if fr == 0 and fc == 4 and tr == 0 and tc == 2:
            board[0][3] = board[0][0]
            board[0][0] = EMPTY
            moved_piece = "k"
            is_castling = True

    # 4. 车移动标记, 禁止易位
    if piece == "R":
        if fc == 0: castling_state["w_r_left"] = True
        if fc == 7: castling_state["w_r_right"] = True
    if piece == "r":
        if fc == 0: castling_state["b_r_left"] = True
        if fc == 7: castling_state["b_r_right"] = True
    
    # 如果车被吃, 也要标记
    if tr == 7 and tc == 0:
        castling_state["w_r_left"] = True
    if tr == 7 and tc == 7:
        castling_state["w_r_right"] = True
    if tr == 0 and tc == 0:
        castling_state["b_r_left"] = True
    if tr == 0 and tc == 7:
        castling_state["b_r_right"] = True

    # 5. 基础移动
    board[tr][tc] = board[fr][fc]
    board[fr][fc] = EMPTY

    # 6. 兵升变
    if board[tr][tc] in ("P", "p"):
        if turn == "white" and tr == 0:
            new_piece = promotion_select(True)
            promotion_piece = new_piece
            board[tr][tc] = new_piece
        elif turn == "black" and tr == 7:
            new_piece = promotion_select(False)
            promotion_piece = new_piece
            board[tr][tc] = new_piece
    
    # 创建移动记录（保存所有信息用于悔棋）
    move_record = {
        'fr': fr, 'fc': fc, 'tr': tr, 'tc': tc,
        'piece': piece,
        'captured': captured_piece,
        'castling_state': old_castling,          # 移动前的易位状态
        'old_en_passant': old_en_passant,       # 移动前的过路兵目标
        'new_ep': new_ep,                       # 移动后的过路兵目标
        'is_capture': is_capture,
        'is_en_passant': is_en_passant,
        'is_castling': is_castling,
        'promotion_piece': promotion_piece,
        'en_passant_captured': en_passant_captured,
        'turn': turn
    }
    
    return new_ep, move_record

# ---------------------- 悔棋函数 ----------------------
def undo_move(board, castling_state, move_record):
    """撤销一步走法"""
    fr, fc = move_record['fr'], move_record['fc']
    tr, tc = move_record['tr'], move_record['tc']
    piece = move_record['piece']
    captured = move_record['captured']
    is_castling = move_record['is_castling']
    is_en_passant = move_record['is_en_passant']
    en_passant_captured = move_record.get('en_passant_captured')
    promotion_piece = move_record.get('promotion_piece')
    
    # 1. 恢复棋子
    board[fr][fc] = piece
    
    # 2. 恢复被吃棋子
    if is_en_passant and en_passant_captured:
        # 恢复过路兵
        ep_r, ep_c = en_passant_captured
        board[ep_r][ep_c] = 'p' if piece.islower() else 'P'
        board[tr][tc] = EMPTY
    elif is_castling:
        # 王车易位: 恢复王和车的位置
        if piece == "K":
            board[tr][tc] = EMPTY
            if tc == 6:  # 短易位
                board[7][7] = 'R'
                board[7][5] = EMPTY
            else:  # 长易位
                board[7][0] = 'R'
                board[7][3] = EMPTY
        else:  # 黑王
            board[tr][tc] = EMPTY
            if tc == 6:  # 短易位
                board[0][7] = 'r'
                board[0][5] = EMPTY
            else:  # 长易位
                board[0][0] = 'r'
                board[0][3] = EMPTY
    else:
        # 普通移动
        board[tr][tc] = captured
        
        # 如果吃子, 恢复被吃的棋子
        if captured != EMPTY:
            board[tr][tc] = captured
        
        # 如果是升变, 恢复兵
        if promotion_piece:
            board[fr][fc] = piece  # 恢复为兵
    
    # 3. 恢复易位状态
    castling_state.update(move_record['castling_state'])
    
    # 4. 返回之前的过路兵目标（从记录中恢复）
    return move_record['old_en_passant']

# ---------------------- 走法描述生成 ----------------------
def generate_move_description(board, fr, fc, tr, tc, turn, move_record):
    """生成标准的走法描述"""
    if move_record['is_castling']:
        if tc > fc:
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
            move_str += rc_to_pos(fr, fc)[0] + "x"
        move_str += rc_to_pos(tr, tc)
        if promotion:
            move_str += f"={promotion.upper()}"
        return move_str
    
    move_str = piece_type
    if is_capture:
        move_str += "x"
    move_str += rc_to_pos(tr, tc)
    return move_str

# ---------------------- 胜负判定增强 ----------------------

def get_board_hash(board):
    """生成棋盘哈希值用于检测重复局面"""
    return ''.join(''.join(row) for row in board)

def check_threefold_repetition(position_history):
    """检查是否出现三次重复局面"""
    if len(position_history) < 6:  # 至少需要6步才可能出现三次重复
        return False
    
    # 统计每个局面的出现次数
    position_count = defaultdict(int)
    for pos_hash in position_history:
        position_count[pos_hash] += 1
        if position_count[pos_hash] >= 3:
            return True
    return False

def check_fifty_move_rule(halfmove_clock):
    """检查50步规则（50步内没有兵移动或吃子）"""
    return halfmove_clock >= 100  # 50步 = 100个半步

def check_insufficient_material(board):
    """检查是否子力不足（无法将杀）"""
    pieces = {'white': [], 'black': []}
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != EMPTY:
                if piece.isupper():
                    pieces['white'].append(piece)
                else:
                    pieces['black'].append(piece)
    
    # 获取双方的棋子（排除王）
    white_pieces = [p for p in pieces['white'] if p != 'K']
    black_pieces = [p for p in pieces['black'] if p != 'k']
    
    # 如果双方都没有棋子, 只有王 vs 王
    if not white_pieces and not black_pieces:
        return True
    
    # 王 + 马 vs 王
    if len(white_pieces) == 1 and white_pieces[0] == 'N' and not black_pieces:
        return True
    if len(black_pieces) == 1 and black_pieces[0] == 'n' and not white_pieces:
        return True
    
    # 王 + 象 vs 王
    if len(white_pieces) == 1 and white_pieces[0] == 'B' and not black_pieces:
        return True
    if len(black_pieces) == 1 and black_pieces[0] == 'b' and not white_pieces:
        return True
    
    # 王 + 象 vs 王 + 象（同色格象）
    if len(white_pieces) == 1 and white_pieces[0] == 'B' and len(black_pieces) == 1 and black_pieces[0] == 'b':
        # 检查象是否在同色格
        white_bishop_pos = None
        black_bishop_pos = None
        for r in range(8):
            for c in range(8):
                if board[r][c] == 'B':
                    white_bishop_pos = (r, c)
                elif board[r][c] == 'b':
                    black_bishop_pos = (r, c)
        if white_bishop_pos and black_bishop_pos:
            # 检查是否在同色格
            if (white_bishop_pos[0] + white_bishop_pos[1]) % 2 == (black_bishop_pos[0] + black_bishop_pos[1]) % 2:
                return True
    
    return False

def check_game_end(board, turn, castling_state, en_passant_target, position_history, halfmove_clock):
    """
    检查游戏是否结束
    返回: (is_end, result, reason)
    result: '1-0' 白胜, '0-1' 黑胜, '1/2-1/2' 和棋
    """
    moves = get_all_legal_moves(board, turn, castling_state, en_passant_target)
    
    # 1. 检查将杀
    if not moves:
        if is_king_in_check(board, turn):
            winner = "1-0" if turn == "black" else "0-1"
            return True, winner, "将杀"
        else:
            return True, "1/2-1/2", "逼和"
    
    # 2. 检查三次重复局面
    if check_threefold_repetition(position_history):
        return True, "1/2-1/2", "三次重复局面"
    
    # 3. 检查50步规则
    if check_fifty_move_rule(halfmove_clock):
        return True, "1/2-1/2", "50步规则"
    
    # 4. 检查子力不足
    if check_insufficient_material(board):
        return True, "1/2-1/2", "子力不足"
    
    return False, None, None

# ---------------------- 走法记录类 ----------------------
class GameRecorder:
    def __init__(self):
        self.moves = []  # 每个元素: {'move_num': int, 'white': str, 'black': str, 'fen': str}
        self.move_records = []  # 存储完整的move_record用于悔棋
        self.position_history = []  # 存储历史局面哈希
        self.halfmove_clock = 0  # 半步计数器（用于50步规则）
        self.result = None
        self.start_time = datetime.now()
        self.white_player = "Player"
        self.black_player = "AI"
        self.game_type = "AI"
    
    def add_move(self, move_num, white_move, black_move=None, move_record=None):
        """添加一步棋"""
        if black_move is None:
            self.moves.append({
                'move_num': move_num,
                'white': white_move,
                'black': '',
                'fen': ''
            })
            if move_record:
                self.move_records.append(move_record)
                # 更新半步计数器
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
    
    def add_position(self, board):
        """记录当前局面"""
        self.position_history.append(get_board_hash(board))
    
    def undo_last_move(self):
        """撤销最后一步走法"""
        if self.move_records:
            # 恢复半步计数器（需要重新计算）
            self.halfmove_clock = 0
            # 移除最后一个位置记录
            if self.position_history:
                self.position_history.pop()
            return self.move_records.pop()
        return None
    
    def remove_last_move_from_history(self):
        """从历史记录中移除最后一步"""
        if self.moves:
            last_move = self.moves[-1]
            if last_move['black']:
                self.moves.pop()
                if self.moves and not self.moves[-1]['black']:
                    self.moves.pop()
            else:
                self.moves.pop()
    
    def set_result(self, result):
        self.result = result
    
    def get_pgn(self):
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
    
    def save_pgn(self, filename=None):
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
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.get_pgn())
        
        return filename
    
    def display_history(self):
        if not self.moves:
            print("\n📜 暂无走法记录")
            return
        
        print("\n" + "="*50)
        print("📜 走法历史")
        print("="*50)
        
        max_moves = len(self.moves)
        num_width = len(str(max_moves))
        
        for move in self.moves:
            num = move['move_num']
            white = move['white']
            black = move['black']
            
            if black:
                print(f"{num:>{num_width}}. {white:<10} {black:<10}")
            else:
                print(f"{num:>{num_width}}. {white:<10} {'...':<10}")
        
        if self.result:
            print("\n" + "="*50)
            print(f"结果: {self.result}")
        print("="*50)

# ---------------------- AI评估函数 ----------------------
def evaluate_board(board):
    score = 0
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece == EMPTY:
                continue
            if piece.isupper():
                score += get_piece_value(piece, r, c, 'white')
            else:
                score -= get_piece_value(piece, r, c, 'black')
    return score

# ---------------------- AI极小极大搜索 ----------------------
def minimax(board, depth, alpha, beta, is_maximizing, castling_state, en_passant_target):
    if depth == 0:
        return evaluate_board(board), None
    
    turn = "white" if is_maximizing else "black"
    moves = get_all_legal_moves(board, turn, castling_state, en_passant_target)
    
    if not moves:
        if is_king_in_check(board, turn):
            return -100000 + depth if is_maximizing else 100000 - depth, None
        else:
            return 0, None
    
    best_move = random.choice(moves) if moves else None
    
    if is_maximizing:
        max_eval = float('-inf')
        for move in moves:
            temp_board = copy.deepcopy(board)
            temp_castling = copy.deepcopy(castling_state)
            fr, fc = move[0]
            tr, tc = move[1]
            new_ep, _ = make_move(temp_board, fr, fc, tr, tc, temp_castling, turn, en_passant_target)
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
            fr, fc = move[0]
            tr, tc = move[1]
            new_ep, _ = make_move(temp_board, fr, fc, tr, tc, temp_castling, turn, en_passant_target)
            eval, _ = minimax(temp_board, depth - 1, alpha, beta, True, temp_castling, new_ep)
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

# ---------------------- AI走棋（只计算走法, 不执行移动）--------------------
def get_ai_move(board, castling_state, en_passant_target, depth):
    """AI计算走法, 返回 (fr, fc, tr, tc) 或 None"""
    all_moves = get_all_legal_moves(board, "black", castling_state, en_passant_target)
    if not all_moves:
        return None
    
    _, best_move = minimax(board, depth, float('-inf'), float('inf'), False, 
                           castling_state, en_passant_target)
    
    if best_move is None:
        best_move = random.choice(all_moves)
    
    return best_move

# ---------------------- 人机对战 ----------------------
def play_ai():
    board, castling_state, en_passant_target = init_board()
    recorder = GameRecorder()
    recorder.white_player = "You"
    recorder.black_player = "AI"
    recorder.game_type = "AI"
    
    # 记录初始局面
    recorder.add_position(board)
    
    print("=========== 简易国际象棋人机对战 ===========")
    print("操作说明: ")
    print("  1. 你操控白方大写, AI黑方小写")
    print("  2. 王车易位: e1g1(短) / e1c1(长)")
    print("  3. 吃过路兵: 敌方兵双走后斜一格吃掉, 仅限下一回合")
    print("  4. 兵走到底线可升变后/车/象/马")
    print("  5. 格式示例 e2e4 | quit 返回菜单")
    print(f"  6. AI难度: 深度{SETTINGS['ai_depth']}层 (设置中可调整)")
    print("  7. 输入 'history' 查看历史走法")
    print("  8. 输入 'save' 保存PGN文件")
    print("  9. 输入 'undo' 悔棋（撤销上一步）")
    print("  10. 胜负判定: 将杀、逼和、三次重复、50步规则、子力不足\n")
    
    move_count = 0
    
    while True:
        clear_screen()
        print_board(board)
        
        # 显示游戏状态信息
        # print("================================")
        print(f"\n当前回合: {'白方' if move_count % 2 == 0 else '黑方'}")
        print(f"半步计数: {recorder.halfmove_clock}/100 (50步规则)")
        print(f"记录局面数: {len(recorder.position_history)}")
        
        # 检查游戏是否结束（在玩家走棋前）
        is_end, result, reason = check_game_end(
            board, "white", castling_state, en_passant_target,
            recorder.position_history, recorder.halfmove_clock
        )
        if is_end:
            print_board(board)
            print(f"\n🏁 游戏结束! 原因: {reason}")
            if result == "1-0":
                print("🎉 你赢了! ")
            elif result == "0-1":
                print("💀 AI赢了! ")
            else:
                print("🤝 和棋! ")
            recorder.set_result(result)
            recorder.display_history()
            save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
            if save_choice == 'y':
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            input("\n回车返回菜单...")
            break
        
        # 检查玩家是否被将杀
        if is_king_in_check(board, "white"):
            print("⚠️  注意: 你的王被将军了! ")
        
        user_input = input("【你的回合 - 白方】请输入走棋: ").strip().lower()
        
        if user_input == "quit":
            clear_screen()
            print("返回主菜单...")
            break
        
        if user_input == "history":
            recorder.display_history()
            input("\n回车继续...")
            continue
        
        if user_input == "save":
            if recorder.moves:
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            else:
                print("❌ 还没有走法可以保存")
            input("\n回车继续...")
            continue
        
        if user_input == "undo":
            # 悔棋逻辑: 需要撤销两步（AI走+玩家走）
            if len(recorder.move_records) < 2:
                print("❌ 没有足够的走法可以悔棋! ")
                input("\n回车继续...")
                continue
            
            # 撤销AI的走法
            ai_record = recorder.undo_last_move()
            if ai_record:
                en_passant_target = undo_move(board, castling_state, ai_record)
                recorder.remove_last_move_from_history()
            
            # 撤销玩家的走法
            player_record = recorder.undo_last_move()
            if player_record:
                en_passant_target = undo_move(board, castling_state, player_record)
                recorder.remove_last_move_from_history()
            
            move_count -= 2
            print("✅ 已悔棋")
            input("\n回车继续...")
            continue
        
        # 去除空格和连字符, 增强容错性
        user_input = user_input.replace(' ', '').replace('-', '')
        
        if len(user_input) != 4:
            print("❌ 格式错误! 示例: e2e4 或 e2-e4")
            input("\n回车继续...")
            continue
        
        try:
            fpos, tpos = user_input[:2], user_input[2:]
            fr, fc = pos_to_rc(fpos)
            tr, tc = pos_to_rc(tpos)
        except:
            print("❌ 坐标无效 a~h 1~8")
            input("\n回车继续...")
            continue
        
        piece = board[fr][fc]
        if not is_same_side(piece, "white"):
            print("❌ 不是你的棋子! ")
            input("\n回车继续...")
            continue
        
        legal = get_legal_moves(board, fr, fc, "white", castling_state, en_passant_target)
        if (tr, tc) not in legal:
            print("❌ 非法走棋! ")
            input("\n回车继续...")
            continue
        
        # 执行走法
        en_passant_target, move_record = make_move(board, fr, fc, tr, tc, castling_state, "white", en_passant_target)
        move_count += 1
        
        # 记录局面
        recorder.add_position(board)
        
        # 生成走法描述
        move_desc = generate_move_description(board, fr, fc, tr, tc, "white", move_record)
        
        # 记录走法
        move_num = (move_count + 1) // 2
        recorder.add_move(move_num, move_desc, move_record=move_record)
        
        # 检查AI是否被将杀
        if is_king_in_check(board, "black"):
            ai_moves = get_all_legal_moves(board, "black", castling_state, en_passant_target)
            if not ai_moves:
                clear_screen()
                print_board(board)
                print("\n🎉 将杀! 你赢了! ")
                recorder.set_result("1-0")
                recorder.display_history()
                save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
                if save_choice == 'y':
                    filename = recorder.save_pgn()
                    print(f"✅ 已保存到: {filename}")
                input("\n回车返回菜单...")
                break
        
        # 检查游戏是否结束（玩家走棋后）
        is_end, result, reason = check_game_end(
            board, "black", castling_state, en_passant_target,
            recorder.position_history, recorder.halfmove_clock
        )
        if is_end:
            clear_screen()
            print_board(board)
            print(f"\n🏁 游戏结束! 原因: {reason}")
            if result == "1-0":
                print("🎉 你赢了! ")
            elif result == "0-1":
                print("💀 AI赢了! ")
            else:
                print("🤝 和棋! ")
            recorder.set_result(result)
            recorder.display_history()
            save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
            if save_choice == 'y':
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            input("\n回车返回菜单...")
            break
        
        print("\n✅ 落子成功, AI思考中...")
        
        # AI计算走法（不执行）
        best_move = get_ai_move(board, castling_state, en_passant_target, SETTINGS['ai_depth'])
        
        if best_move is None:
            # AI无走法, 检查是否被将杀或逼和
            if is_king_in_check(board, "black"):
                clear_screen()
                print_board(board)
                print("\n🎉 将杀! 你赢了! ")
                recorder.set_result("1-0")
            else:
                clear_screen()
                print_board(board)
                print("\n🤝 逼和! ")
                recorder.set_result("1/2-1/2")
            recorder.display_history()
            save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
            if save_choice == 'y':
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            input("\n回车返回菜单...")
            break
        
        # 执行AI走法
        (fr, fc), (tr, tc) = best_move
        en_passant_target, ai_record = make_move(board, fr, fc, tr, tc, castling_state, "black", en_passant_target)
        move_count += 1
        
        # 生成走法描述
        ai_move_desc = generate_move_description(board, fr, fc, tr, tc, "black", ai_record)
        
        # 记录AI走后的局面
        recorder.add_position(board)
        
        # 更新记录（添加黑方走法）
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
        
        # 检查AI是否被将杀（AI走棋后）
        if is_king_in_check(board, "black"):
            ai_moves = get_all_legal_moves(board, "black", castling_state, en_passant_target)
            if not ai_moves:
                clear_screen()
                print_board(board)
                print("\n🎉 将杀! 你赢了! ")
                recorder.set_result("1-0")
                recorder.display_history()
                save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
                if save_choice == 'y':
                    filename = recorder.save_pgn()
                    print(f"✅ 已保存到: {filename}")
                input("\n回车返回菜单...")
                break
        
        # 检查游戏是否结束（AI走棋后）
        is_end, result, reason = check_game_end(
            board, "white", castling_state, en_passant_target,
            recorder.position_history, recorder.halfmove_clock
        )
        if is_end:
            clear_screen()
            print_board(board)
            print(f"\n🏁 游戏结束! 原因: {reason}")
            if result == "1-0":
                print("🎉 你赢了! ")
            elif result == "0-1":
                print("💀 AI赢了! ")
            else:
                print("🤝 和棋! ")
            recorder.set_result(result)
            recorder.display_history()
            save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
            if save_choice == 'y':
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            input("\n回车返回菜单...")
            break
        
        input("\n回车下一回合...")

# ---------------------- 人人对战 ----------------------
def play_pvp():
    board, castling_state, en_passant_target = init_board()
    turn = "white"
    recorder = GameRecorder()
    recorder.white_player = "Player1"
    recorder.black_player = "Player2"
    recorder.game_type = "PVP"
    
    # 记录初始局面
    recorder.add_position(board)
    
    print("=========== 人人对战 ===========")
    print("白先行, 支持易位、过路兵、兵升变")
    print("输入 'history' 查看历史走法")
    print("输入 'save' 保存PGN文件")
    print("输入 'undo' 悔棋")
    print("输入 'quit' 返回菜单")
    print("胜负判定: 将杀、逼和、三次重复、50步规则、子力不足\n")
    
    move_count = 0
    
    while True:
        clear_screen()
        print_board(board)
        
        # 显示游戏状态信息
        print(f"半步计数: {recorder.halfmove_clock}/100 (50步规则)")
        
        # 检查游戏是否结束
        is_end, result, reason = check_game_end(
            board, turn, castling_state, en_passant_target,
            recorder.position_history, recorder.halfmove_clock
        )
        if is_end:
            print_board(board)
            print(f"\n🏁 游戏结束! 原因: {reason}")
            if result == "1-0":
                print("🎉 白方胜利! ")
            elif result == "0-1":
                print("🎉 黑方胜利! ")
            else:
                print("🤝 和棋! ")
            recorder.set_result(result)
            recorder.display_history()
            save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
            if save_choice == 'y':
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            input("\n回车返回菜单...")
            break
        
        # 检查当前玩家是否被将杀
        if is_king_in_check(board, turn):
            print(f"⚠️  注意: {turn}方的王被将军了! ")
        
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
            save_choice = input("\n是否保存PGN文件？(y/n): ").strip().lower()
            if save_choice == 'y':
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            input("\n回车返回菜单...")
            break
        
        tip = "【白方回合 大写棋子】" if turn == "white" else "【黑方回合 小写棋子】"
        user_in = input(f"{tip} 输入走棋: ").strip().lower()
        
        if user_in == "quit":
            clear_screen()
            print("返回主菜单...")
            break
        
        if user_in == "history":
            recorder.display_history()
            input("\n回车继续...")
            continue
        
        if user_in == "save":
            if recorder.moves:
                filename = recorder.save_pgn()
                print(f"✅ 已保存到: {filename}")
            else:
                print("❌ 还没有走法可以保存")
            input("\n回车继续...")
            continue
        
        if user_in == "undo":
            if len(recorder.move_records) < 1:
                print("❌ 没有走法可以悔棋! ")
                input("\n回车继续...")
                continue
            
            # 撤销走法
            last_record = recorder.undo_last_move()
            if last_record:
                en_passant_target = undo_move(board, castling_state, last_record)
                recorder.remove_last_move_from_history()
                # 移除位置历史
                if recorder.position_history:
                    recorder.position_history.pop()
                move_count -= 1
                turn = last_record['turn']
                print("✅ 已悔棋")
            input("\n回车继续...")
            continue
        
        # 去除空格和连字符, 增强容错性
        user_in = user_in.replace(' ', '').replace('-', '')
        
        if len(user_in) != 4:
            print("❌ 格式错误 e2e4 或 e2-e4")
            input("\n回车继续...")
            continue
        
        try:
            fpos, tpos = user_in[:2], user_in[2:]
            fr, fc = pos_to_rc(fpos)
            tr, tc = pos_to_rc(tpos)
        except:
            print("❌ 坐标范围 a~h 1~8")
            input("\n回车继续...")
            continue
        
        piece = board[fr][fc]
        if not is_same_side(piece, turn):
            print("❌ 当前回合不能移动该棋子! ")
            input("\n回车继续...")
            continue
        
        legal = get_legal_moves(board, fr, fc, turn, castling_state, en_passant_target)
        if (tr, tc) not in legal:
            print("❌ 非法移动! ")
            input("\n回车继续...")
            continue
        
        # 执行走法
        en_passant_target, move_record = make_move(board, fr, fc, tr, tc, castling_state, turn, en_passant_target)
        move_count += 1
        
        # 记录局面
        recorder.add_position(board)
        
        # 生成走法描述
        move_desc = generate_move_description(board, fr, fc, tr, tc, turn, move_record)
        
        # 记录走法
        move_num = (move_count + 1) // 2
        if turn == "white":
            recorder.add_move(move_num, move_desc, move_record=move_record)
        else:
            if len(recorder.moves) >= move_num:
                recorder.moves[move_num - 1]['black'] = move_desc
                recorder.move_records.append(move_record)
                if move_record['is_capture'] or move_record['piece'].upper() == 'P':
                    recorder.halfmove_clock = 0
                else:
                    recorder.halfmove_clock += 1
        
        print("✅ 落子完成, 切换对手")
        turn = "black" if turn == "white" else "white"
        input("\n回车切换棋盘...")

# ---------------------- 帮助界面 ----------------------
def show_help():
    clear_screen()
    print("==================== 游戏帮助 ====================")
    print("1.菜单选项: 1人机 2人人 3帮助 4设置 5退出")
    print("2.走棋格式: 4字符, 起点+终点 例e2e4 (支持 e2-e4)")
    print("3.棋子: 白大写 KQRNBP | 黑小写 kqrnbp")
    print("4.特殊规则: ")
    print("   ① 王车易位: 王、车未移动, 中间无棋子")
    print("     白短e1g1 / 白长e1c1 | 黑短e8g8 / 黑长e8c8")
    print("     注: 王不能处于被将军状态, 经过和到达的格子不能被攻击")
    print("   ② 吃过路兵: 敌方兵一步两格, 斜一格吃掉, 仅限下一回合")
    print("   ③ 兵升变: 兵走到底线, 可选后/车/象/马；AI自动升后")
    print("5.对局输入quit随时返回主菜单")
    print("6.胜负判定（增强）: ")
    print("   - 将杀: 王被将军且无法应将")
    print("   - 逼和: 轮到走棋时无合法走法但王未被将军")
    print("   - 三次重复局面: 同一局面出现3次")
    print("   - 50步规则: 50步内无兵移动或吃子")
    print("   - 子力不足: 无法将杀（如王vs王、王+马vs王等）")
    print("7.交互命令: ")
    print("   - 'history' 查看历史走法")
    print("   - 'save' 保存PGN文件")
    print("   - 'undo' 悔棋（人机模式撤销两步, 人人模式撤销一步）")
    print("8.设置功能: ")
    print("   - 切换棋子显示样式（字母 ↔ Unicode符号）")
    print("   - 调整AI难度（搜索深度 2=简单 / 3=中等 / 4=困难）")
    print("==================================================")
    input("\n回车返回菜单...")

# ---------------------- 设置界面 ----------------------
def show_settings():
    """显示和修改设置"""
    while True:
        clear_screen()
        print("\n==================== 设置 ====================")
        print("当前设置: ")
        print(f"  1. 棋子样式: {'Unicode符号 ♔♚' if SETTINGS['piece_style'] == 'unicode' else '字母 KQ'}")
        print(f"  2. AI难度: 深度 {SETTINGS['ai_depth']} 层 "
              f"({'简单' if SETTINGS['ai_depth'] <= 2 else '中等' if SETTINGS['ai_depth'] == 3 else '困难'})")
        print("\n请选择要修改的设置: ")
        print("  1 - 切换棋子样式（字母 ↔ Unicode符号）")
        print("  2 - 调整AI难度（2=简单 / 3=中等 / 4=困难）")
        print("  0 - 返回主菜单")
        print("==============================================")
        
        choice = input("请输入数字选择: ").strip()
        
        if choice == "0":
            save_settings()
            break
        elif choice == "1":
            # 切换棋子样式
            if SETTINGS['piece_style'] == 'letter':
                SETTINGS['piece_style'] = 'unicode'
                print("\n✅ 已切换到 Unicode 符号样式")
            else:
                SETTINGS['piece_style'] = 'letter'
                print("\n✅ 已切换到 字母 样式")
            
            # 显示预览
            print("\n预览效果: ")
            print("  字母样式: K Q R B N P")
            print("  Unicode样式: ♔ ♕ ♖ ♗ ♘ ♙")
            print("\n设置已保存, 按回车返回设置菜单...")
            input()
        elif choice == "2":
            # 调整AI深度
            while True:
                print("\n选择AI难度: ")
                print("  2 - 简单（思考快, 但棋力弱）")
                print("  3 - 中等（平衡）")
                print("  4 - 困难（思考慢, 棋力强）")
                depth_choice = input("请输入 2/3/4: ").strip()
                if depth_choice in ('2', '3', '4'):
                    SETTINGS['ai_depth'] = int(depth_choice)
                    print(f"\n✅ AI深度已设置为 {SETTINGS['ai_depth']} 层")
                    print("   （深度4以上会明显变慢, 不建议更高）")
                    input("\n回车继续...")
                    break
                else:
                    print("❌ 请输入 2/3/4")
                    input("\n回车继续...")
        else:
            print("❌ 输入无效, 请重新选择")
            input("\n回车继续...")

# ---------------------- 主菜单 ----------------------
def main():
    # 加载设置
    load_settings()
    
    while True:
        clear_screen()
        print("\n==================== 国际象棋 开始界面 ===================")
        print("| 1 - 人机对战                                           |")
        print("| 2 - 人人对战                                           |")
        print("| 3 - 查看帮助                                           |")
        print("| 4 - 设置                                               |")
        print("| 5 - 退出游戏                                           |")
        print("==========================================================")
        sel = input("请输入数字选择: ").strip()
        if sel == "1":
            play_ai()
        elif sel == "2":
            play_pvp()
        elif sel == "3":
            show_help()
        elif sel == "4":
            show_settings()
        elif sel == "5":
            clear_screen()
            print("游戏退出, 再见! ")
            break
        else:
            print("输入无效, 请输入1/2/3/4/5")
            input("回车继续...")

if __name__ == "__main__":
    main()