import sys
import random
import time
import json
import os
import copy
import math
from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QProgressBar, QSpinBox, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, 
                             QCheckBox, QTextEdit, QDialog, QDialogButtonBox, QComboBox, QLCDNumber)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPolygonF
from PyQt6.QtCore import Qt, QRect, QThread, pyqtSignal, QTimer, QPointF

# ==========================================
# 0. BÖLÜM: GİRİŞ EKRANI
# ==========================================
class StartDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Oyun Kurulumu")
        self.resize(350, 250)
        self.selected_time = None
        self.selected_inc = 0
        self.game_mode = "PvE"
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🎮 Oyun Modu:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Bot'a Karşı (PvE)", "Arkadaşla Oyna (1v1)"])
        layout.addWidget(self.mode_combo)
        
        layout.addWidget(QLabel("⏳ Zaman Kontrolü:"))
        self.time_combo = QComboBox()
        self.time_combo.addItems([
            "Süresiz (Analiz Modu)",
            "Bullet (1 dk + 0 sn)",
            "Blitz (3 dk + 2 sn)",
            "Rapid (10 dk + 0 sn)",
            "Klasik (30 dk + 5 sn)"
        ])
        layout.addWidget(self.time_combo)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept_selection)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def accept_selection(self):
        if "Arkadaşla" in self.mode_combo.currentText(): self.game_mode = "PvP"
        else: self.game_mode = "PvE"
        
        txt = self.time_combo.currentText()
        if "Süresiz" in txt: self.selected_time = None; self.selected_inc = 0
        elif "Bullet" in txt: self.selected_time = 60; self.selected_inc = 0
        elif "Blitz" in txt: self.selected_time = 180; self.selected_inc = 2
        elif "Rapid" in txt: self.selected_time = 600; self.selected_inc = 0
        elif "Klasik" in txt: self.selected_time = 1800; self.selected_inc = 5
        self.accept()

# ==========================================
# 1. BÖLÜM: ARKA PLAN İŞÇİSİ
# ==========================================
class BotWorker(QThread):
    finished = pyqtSignal(object, float, int, int) 

    def __init__(self, ai, gs_clone, valid_moves, time_limit):
        super().__init__()
        self.ai = ai
        self.gs = gs_clone
        self.valid_moves = valid_moves
        self.time_limit = time_limit

    def run(self):
        if self.gs.white_to_move: return

        try:
            print(f"\n🧠 Bot Düşünüyor... (Limit: {self.time_limit:.2f}s)")
            self.ai.nodes_visited = 0
            best_move, score, nodes, max_depth = self.ai.find_best_move_smart(self.gs, self.valid_moves, self.time_limit)
            
            if best_move is None and self.valid_moves:
                best_move = random.choice(self.valid_moves) # Emergency
            
            self.finished.emit(best_move, score, nodes, max_depth)
        except Exception as e:
            print(f"Bot Kritik Hata: {e}")

# ==========================================
# 2. BÖLÜM: YAPAY ZEKA
# ==========================================
class OpeningBook:
    def __init__(self, brain_file="beyin.json"):
        self.book = {}
        self.load_brain(brain_file)
    def load_brain(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f: self.book = json.load(f)
            except: self.book = {}
    def get_book_move(self, board_fen):
        base_fen = " ".join(board_fen.split(" ")[:4])
        if base_fen in self.book:
            try: return max(self.book[base_fen], key=self.book[base_fen].get)
            except: return None
        return None

class ChessAI:
    def __init__(self):
        self.CHECKMATE = 10000; self.STALEMATE = 0
        self.opening_book = OpeningBook()
        self.piece_score = {"K": 0, "Q": 950, "R": 500, "B": 330, "N": 320, "P": 100}
        self.nodes_visited = 0
        self.pawn_table = [[0]*8]*8; self.knight_table = [[0]*8]*8

    def find_best_move_smart(self, gs, valid_moves, time_limit):
        self.nodes_visited = 0
        start_time = time.time()
        
        book_move = self.opening_book.get_book_move(gs.get_fen())
        if book_move:
            for m in valid_moves:
                if m.get_uci() == book_move: return m, 100.0, 1, 1

        best_global_move = None; best_global_score = -float('inf')
        random.shuffle(valid_moves)
        valid_moves.sort(key=lambda m: (100 if m.piece_captured != "--" else 0), reverse=True)

        current_depth = 1; history = []

        while True:
            if time.time() - start_time > time_limit: break
            try:
                best_move_this_depth = None; best_score_this_depth = -float('inf')
                alpha, beta = -self.CHECKMATE, self.CHECKMATE
                
                for move in valid_moves:
                    gs.make_move(move)
                    score = -self.minimax(gs, current_depth - 1, -beta, -alpha, 1, start_time, time_limit)
                    gs.undo_move()
                    
                    if time.time() - start_time > time_limit: raise TimeoutError
                    if score > best_score_this_depth:
                        best_score_this_depth = score; best_move_this_depth = move
                    if score > alpha: alpha = score

                best_global_move = best_move_this_depth; best_global_score = best_score_this_depth
                print(f"🔎 Derinlik {current_depth}: {best_global_move.get_chess_notation()} ({best_global_score:.2f})")
                
                history.append(best_global_move)
                if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
                    if time.time() - start_time > (time_limit * 0.4): break

                if best_global_score > 9000: break
                current_depth += 1
                if current_depth > 12: break 

            except TimeoutError: break

        if not best_global_move and valid_moves: best_global_move = valid_moves[0]
        return best_global_move, best_global_score, self.nodes_visited, (current_depth - 1)

    def minimax(self, gs, depth, alpha, beta, turn_multiplier, start_time, time_limit):
        self.nodes_visited += 1
        if self.nodes_visited % 500 == 0:
            if time.time() - start_time > time_limit: raise TimeoutError

        if depth == 0: return turn_multiplier * self.score_board(gs)
        
        valid_moves = gs.get_valid_moves()
        if not valid_moves: return -self.CHECKMATE + depth if gs.in_check() else self.STALEMATE

        max_score = -self.CHECKMATE
        for move in valid_moves:
            gs.make_move(move)
            score = -self.minimax(gs, depth - 1, -beta, -alpha, -turn_multiplier, start_time, time_limit)
            gs.undo_move()
            if score > max_score: max_score = score
            if max_score > alpha: alpha = max_score
            if alpha >= beta: break
        return max_score

    def score_board(self, gs):
        if gs.checkmate: return -self.CHECKMATE if gs.white_to_move else self.CHECKMATE
        if gs.stalemate: return self.STALEMATE
        score = 0
        for r in range(8):
            for c in range(8):
                piece = gs.board[r][c]
                if piece != "--":
                    val = self.piece_score[piece[1]]
                    if piece[0] == 'w': score += val
                    else: score -= val
        return score

# ==========================================
# 3. BÖLÜM: OYUN MOTORU (DÜZELTİLDİ: get_fen eklendi)
# ==========================================
class CastleRights:
    def __init__(self, wks, wqs, bks, bqs):
        self.wks = wks; self.wqs = wqs; self.bks = bks; self.bqs = bqs

class GameState:
    def __init__(self):
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bP", "bP", "bP", "bP", "bP", "bP", "bP", "bP"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wP", "wP", "wP", "wP", "wP", "wP", "wP", "wP"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
        ]
        self.white_to_move = True
        self.move_log = []
        self.white_king_location = (7, 4)
        self.black_king_location = (0, 4)
        self.checkmate = False; self.stalemate = False
        self.current_castling_right = CastleRights(True, True, True, True)
        self.castle_rights_log = [CastleRights(True, True, True, True)]

    def clone(self):
        return copy.deepcopy(self)

    def generate_pgn(self):
        pgn = ""; turn = 1
        for i, move in enumerate(self.move_log):
            if i % 2 == 0: pgn += f"{turn}. {move.get_chess_notation()} "
            else: pgn += f"{move.get_chess_notation()} "; turn += 1
        return pgn.strip()

    # --- GERİ GETİRİLEN FONKSİYON: get_fen ---
    def get_fen(self):
        fen = ""; 
        for r in range(8):
            empty = 0
            for c in range(8):
                if self.board[r][c] == "--": empty += 1
                else:
                    if empty > 0: fen += str(empty); empty = 0
                    color = self.board[r][c][0]; piece = self.board[r][c][1]
                    fen += piece.upper() if color == 'w' else piece.lower()
            if empty > 0: fen += str(empty)
            if r < 7: fen += "/"
        fen += " w " if self.white_to_move else " b "
        fen += "KQkq - 0 1"
        return fen
    # -----------------------------------------

    def count_pieces(self):
        counts = {"wQ":0, "wR":0, "wB":0, "wN":0, "wP":0, "bQ":0, "bR":0, "bB":0, "bN":0, "bP":0}
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "--" and p[1] != 'K': counts[p] += 1
        return counts

    def get_center_control(self):
        center_sqs = [(4,3), (4,4), (3,3), (3,4)]
        w_ctrl, b_ctrl = 0, 0
        for r, c in center_sqs:
            p = self.board[r][c]
            if p[0] == 'w': w_ctrl += 1
            elif p[0] == 'b': b_ctrl += 1
        return w_ctrl, b_ctrl

    def make_move(self, move):
        self.board[move.start_row][move.start_col] = "--"
        self.board[move.end_row][move.end_col] = move.piece_moved
        if move.piece_moved == 'wP' and move.end_row == 0: self.board[move.end_row][move.end_col] = 'wQ'; move.is_pawn_promotion = True
        elif move.piece_moved == 'bP' and move.end_row == 7: self.board[move.end_row][move.end_col] = 'bQ'; move.is_pawn_promotion = True
        
        if move.is_castle_move:
            if move.end_col - move.start_col == 2: 
                self.board[move.end_row][move.end_col-1] = self.board[move.end_row][move.end_col+1]
                self.board[move.end_row][move.end_col+1] = "--"
            else: 
                self.board[move.end_row][move.end_col+1] = self.board[move.end_row][move.end_col-2]
                self.board[move.end_row][move.end_col-2] = "--"

        self.move_log.append(move)
        self.update_castle_rights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_right.wks, self.current_castling_right.wqs, self.current_castling_right.bks, self.current_castling_right.bqs))

        if move.piece_moved == 'wK': self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == 'bK': self.black_king_location = (move.end_row, move.end_col)
        self.white_to_move = not self.white_to_move

    def undo_move(self):
        if len(self.move_log) != 0:
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move
            
            if move.piece_moved == 'wK': self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == 'bK': self.black_king_location = (move.start_row, move.start_col)
            
            if move.is_castle_move:
                if move.end_col - move.start_col == 2:
                    self.board[move.end_row][move.end_col+1] = self.board[move.end_row][move.end_col-1]; self.board[move.end_row][move.end_col-1] = "--"
                else:
                    self.board[move.end_row][move.end_col-2] = self.board[move.end_row][move.end_col+1]; self.board[move.end_row][move.end_col+1] = "--"
            
            self.castle_rights_log.pop()
            self.current_castling_right = copy.deepcopy(self.castle_rights_log[-1])
            if move.is_pawn_promotion:
                self.board[move.start_row][move.start_col] = move.piece_moved
                self.board[move.end_row][move.end_col] = move.piece_captured
            self.checkmate = False; self.stalemate = False

    def update_castle_rights(self, move):
        if move.piece_moved == 'wK': self.current_castling_right.wks = False; self.current_castling_right.wqs = False
        elif move.piece_moved == 'bK': self.current_castling_right.bks = False; self.current_castling_right.bqs = False
        elif move.piece_moved == 'wR':
            if move.start_row == 7:
                if move.start_col == 0: self.current_castling_right.wqs = False
                elif move.start_col == 7: self.current_castling_right.wks = False
        elif move.piece_moved == 'bR':
            if move.start_row == 0:
                if move.start_col == 0: self.current_castling_right.bqs = False
                elif move.start_col == 7: self.current_castling_right.bks = False

    def get_valid_moves(self):
        temp_castle_rights = copy.deepcopy(self.current_castling_right)
        moves = self.get_all_possible_moves()
        if self.white_to_move: self.get_castle_moves(self.white_king_location[0], self.white_king_location[1], moves)
        else: self.get_castle_moves(self.black_king_location[0], self.black_king_location[1], moves)

        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.white_to_move = not self.white_to_move 
            if self.in_check(): moves.remove(moves[i])
            self.white_to_move = not self.white_to_move 
            self.undo_move()
        
        if len(moves) == 0:
            if self.in_check(): self.checkmate = True
            else: self.stalemate = True
        else: self.checkmate = False; self.stalemate = False
        
        self.current_castling_right = temp_castle_rights
        return moves

    def in_check(self):
        if self.white_to_move: return self.square_under_attack(self.white_king_location[0], self.white_king_location[1])
        else: return self.square_under_attack(self.black_king_location[0], self.black_king_location[1])

    def square_under_attack(self, r, c):
        self.white_to_move = not self.white_to_move
        opp_moves = self.get_all_possible_moves()
        self.white_to_move = not self.white_to_move
        for move in opp_moves:
            if move.end_row == r and move.end_col == c: return True
        return False

    def get_all_possible_moves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                turn = self.board[r][c][0]
                if (turn == 'w' and self.white_to_move) or (turn == 'b' and not self.white_to_move):
                    piece = self.board[r][c][1]
                    if piece == 'P': self.get_pawn_moves(r, c, moves)
                    elif piece == 'R': self.get_rook_moves(r, c, moves)
                    elif piece == 'N': self.get_knight_moves(r, c, moves)
                    elif piece == 'B': self.get_bishop_moves(r, c, moves)
                    elif piece == 'Q': self.get_bishop_moves(r, c, moves); self.get_rook_moves(r, c, moves)
                    elif piece == 'K': self.get_king_moves(r, c, moves)
        return moves
    
    def get_pawn_moves(self, r, c, moves):
        if self.white_to_move:
            if self.board[r-1][c] == "--":
                moves.append(Move((r, c), (r-1, c), self.board)); 
                if r == 6 and self.board[r-2][c] == "--": moves.append(Move((r, c), (r-2, c), self.board))
            if c-1 >= 0 and self.board[r-1][c-1][0] == 'b': moves.append(Move((r, c), (r-1, c-1), self.board))
            if c+1 <= 7 and self.board[r-1][c+1][0] == 'b': moves.append(Move((r, c), (r-1, c+1), self.board))
        else:
            if r+1 < 8:
                if self.board[r+1][c] == "--":
                    moves.append(Move((r, c), (r+1, c), self.board)); 
                    if r == 1 and self.board[r+2][c] == "--": moves.append(Move((r, c), (r+2, c), self.board))
                if c-1 >= 0 and self.board[r+1][c-1][0] == 'w': moves.append(Move((r, c), (r+1, c-1), self.board))
                if c+1 <= 7 and self.board[r+1][c+1][0] == 'w': moves.append(Move((r, c), (r+1, c+1), self.board))
    def get_rook_moves(self, r, c, moves):
        directions = [(-1, 0), (0, -1), (1, 0), (0, 1)]
        enemy = "b" if self.white_to_move else "w"
        for d in directions:
            for i in range(1, 8):
                er, ec = r + d[0] * i, c + d[1] * i
                if 0 <= er < 8 and 0 <= ec < 8:
                    p = self.board[er][ec]
                    if p == "--": moves.append(Move((r, c), (er, ec), self.board))
                    elif p[0] == enemy: moves.append(Move((r, c), (er, ec), self.board)); break
                    else: break
                else: break
    def get_knight_moves(self, r, c, moves):
        km = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        enemy = "b" if self.white_to_move else "w"
        for m in km:
            er, ec = r + m[0], c + m[1]
            if 0 <= er < 8 and 0 <= ec < 8:
                p = self.board[er][ec]
                if p == "--" or p[0] == enemy: moves.append(Move((r, c), (er, ec), self.board))
    def get_bishop_moves(self, r, c, moves):
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        enemy = "b" if self.white_to_move else "w"
        for d in directions:
            for i in range(1, 8):
                er, ec = r + d[0] * i, c + d[1] * i
                if 0 <= er < 8 and 0 <= ec < 8:
                    p = self.board[er][ec]
                    if p == "--": moves.append(Move((r, c), (er, ec), self.board))
                    elif p[0] == enemy: moves.append(Move((r, c), (er, ec), self.board)); break
                    else: break
                else: break
    def get_king_moves(self, r, c, moves):
        km = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        enemy = "b" if self.white_to_move else "w"
        for m in km:
            er, ec = r + m[0], c + m[1]
            if 0 <= er < 8 and 0 <= ec < 8:
                p = self.board[er][ec]
                if p == "--" or p[0] == enemy: moves.append(Move((r, c), (er, ec), self.board))

    def get_castle_moves(self, r, c, moves):
        if self.square_under_attack(r, c): return
        if (self.white_to_move and self.current_castling_right.wks) or (not self.white_to_move and self.current_castling_right.bks):
            if self.board[r][c+1] == '--' and self.board[r][c+2] == '--':
                if not self.square_under_attack(r, c+1) and not self.square_under_attack(r, c+2):
                    moves.append(Move((r, c), (r, c+2), self.board, is_castle=True))
        if (self.white_to_move and self.current_castling_right.wqs) or (not self.white_to_move and self.current_castling_right.bqs):
            if self.board[r][c-1] == '--' and self.board[r][c-2] == '--' and self.board[r][c-3] == '--':
                if not self.square_under_attack(r, c-1) and not self.square_under_attack(r, c-2):
                    moves.append(Move((r, c), (r, c-2), self.board, is_castle=True))

class Move:
    def __init__(self, start_sq, end_sq, board, is_castle=False):
        self.start_row = start_sq[0]; self.start_col = start_sq[1]
        self.end_row = end_sq[0]; self.end_col = end_sq[1]
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]
        self.is_pawn_promotion = False
        self.is_castle_move = is_castle
        self.move_id = self.start_row * 1000 + self.start_col * 100 + self.end_row * 10 + self.end_col
    def __eq__(self, other): return isinstance(other, Move) and self.move_id == other.move_id
    def get_chess_notation(self): return self.get_rank_file(self.start_row, self.start_col) + self.get_rank_file(self.end_row, self.end_col)
    def get_rank_file(self, r, c):
        cols = {0:'a', 1:'b', 2:'c', 3:'d', 4:'e', 5:'f', 6:'g', 7:'h'}
        rows = {0:'8', 1:'7', 2:'6', 3:'5', 4:'4', 5:'3', 6:'2', 7:'1'}
        return cols[c] + rows[r]
    def get_uci(self): return self.get_rank_file(self.start_row, self.start_col) + self.get_rank_file(self.end_row, self.end_col)

# ==========================================
# 4. BÖLÜM: ARAYÜZ (GÖRSEL DÜZELTMELER)
# ==========================================
class PGNDialog(QDialog):
    def __init__(self, pgn_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analiz İçin PGN Kodu")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("1. Kodu kopyala:")); t = QTextEdit(); t.setPlainText(pgn_text); t.setReadOnly(True); layout.addWidget(t)
        layout.addWidget(QLabel("2. Siteye yapıştır: wintrchess.com/analysis"))
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok); b.accepted.connect(self.accept); layout.addWidget(b)

class BoardWidget(QWidget):
    grid_clicked = pyqtSignal(int, int, str)

    def __init__(self, game_state, parent=None):
        super().__init__(parent)
        self.gs = game_state
        self.sq_size = 65; self.margin = 30
        self.setFixedSize(self.sq_size * 8 + self.margin * 2, self.sq_size * 8 + self.margin * 2)
        self.selected_sq = (); self.valid_moves = []; self.arrows = []; self.drawing_arrow = False; self.start_arrow_sq = None
        self.player_clicks = [] 
        self.semboller = {'wK': '♔', 'wQ': '♕', 'wR': '♖', 'wB': '♗', 'wN': '♘', 'wP': '♙', 'bK': '♚', 'bQ': '♛', 'bR': '♜', 'bB': '♝', 'bN': '♞', 'bP': '♟'}

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_coordinates(painter)
        painter.translate(self.margin, self.margin)
        colors = [QColor(240, 217, 181), QColor(181, 136, 99)]
        for r in range(8):
            for c in range(8):
                color = colors[(r + c) % 2]
                painter.fillRect(c * self.sq_size, r * self.sq_size, self.sq_size, self.sq_size, color)
                if self.selected_sq == (c, r): painter.fillRect(c * self.sq_size, r * self.sq_size, self.sq_size, self.sq_size, QColor(0, 255, 255, 100))
        
        if len(self.gs.move_log) > 0:
            last = self.gs.move_log[-1]
            painter.fillRect(last.start_col * self.sq_size, last.start_row * self.sq_size, self.sq_size, self.sq_size, QColor(255, 255, 0, 100))
            painter.fillRect(last.end_col * self.sq_size, last.end_row * self.sq_size, self.sq_size, self.sq_size, QColor(255, 255, 0, 100))

        self.draw_hints(painter)
        self.draw_arrows(painter)
        
        painter.setFont(QFont("Segoe UI Symbol", 45))
        for r in range(8):
            for c in range(8):
                tas = self.gs.board[r][c]
                if tas != "--":
                    rect = QRect(c * self.sq_size, r * self.sq_size, self.sq_size, self.sq_size)
                    painter.setPen(QColor(0, 0, 0))
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.semboller[tas])

    def draw_coordinates(self, painter):
        painter.setPen(QColor(200, 200, 200)); painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']; numbers = ['8', '7', '6', '5', '4', '3', '2', '1']
        for i in range(8):
            x = self.margin + i * self.sq_size + self.sq_size // 2 - 5
            painter.drawText(x, self.margin - 10, letters[i]); painter.drawText(x, self.margin + 8 * self.sq_size + 20, letters[i])
        for i in range(8):
            y = self.margin + i * self.sq_size + self.sq_size // 2 + 5
            painter.drawText(5, y, numbers[i]); painter.drawText(self.margin + 8 * self.sq_size + 10, y, numbers[i])

    def draw_hints(self, painter):
        if self.selected_sq == (): return
        # --- KOORDİNAT SİSTEMİNE GÖRE İPUCU ÇİZİMİ (DÜZELTİLDİ) ---
        # Move nesnesi (satır, sütun) olarak tutuyor. 
        # Bizim seçimimiz (sütun, satır) yani (c, r).
        # Eşleşme: m.start_row == r (yani selected_sq[1]) VE m.start_col == c (yani selected_sq[0])
        moves = [m for m in self.valid_moves if m.start_row == self.selected_sq[1] and m.start_col == self.selected_sq[0]]
        
        for m in moves:
            # Hedef kareyi boya (m.end_row, m.end_col) -> (y, x)
            r, c = m.end_row, m.end_col
            
            if self.gs.board[r][c] != "--": # Taş yiyorsa kırmızımsı halka
                painter.setBrush(Qt.BrushStyle.NoBrush); pen = QPen(QColor(200, 50, 50, 150)); pen.setWidth(5); painter.setPen(pen)
                painter.drawEllipse(c * self.sq_size + 5, r * self.sq_size + 5, self.sq_size - 10, self.sq_size - 10)
            else: # Boşa gidiyorsa gri nokta
                painter.setBrush(QColor(100, 100, 100, 150)); painter.setPen(Qt.PenStyle.NoPen)
                radius = self.sq_size // 6
                painter.drawEllipse(c * self.sq_size + self.sq_size // 2 - radius, r * self.sq_size + self.sq_size // 2 - radius, radius * 2, radius * 2)

    def draw_arrows(self, painter):
        for start, end in self.arrows:
            c1, r1 = start; c2, r2 = end
            start_pt = QPointF(c1 * self.sq_size + self.sq_size/2, r1 * self.sq_size + self.sq_size/2)
            end_pt = QPointF(c2 * self.sq_size + self.sq_size/2, r2 * self.sq_size + self.sq_size/2)
            pen = QPen(QColor(0, 255, 0, 150)); pen.setWidth(8); painter.setPen(pen); painter.setBrush(QColor(0, 255, 0, 150))
            painter.drawLine(start_pt, end_pt)
            angle = math.atan2(end_pt.y() - start_pt.y(), end_pt.x() - start_pt.x())
            arrow_size = 20
            p1 = end_pt - QPointF(math.cos(angle - math.pi / 6) * arrow_size, math.sin(angle - math.pi / 6) * arrow_size)
            p2 = end_pt - QPointF(math.cos(angle + math.pi / 6) * arrow_size, math.sin(angle + math.pi / 6) * arrow_size)
            painter.drawPolygon(QPolygonF([end_pt, p1, p2]))

    def mousePressEvent(self, event):
        x = event.position().x() - self.margin; y = event.position().y() - self.margin
        c, r = int(x // self.sq_size), int(y // self.sq_size)
        if 0 <= c < 8 and 0 <= r < 8:
            if event.button() == Qt.MouseButton.RightButton:
                self.drawing_arrow = True; self.start_arrow_sq = (c, r)
            elif event.button() == Qt.MouseButton.LeftButton:
                self.grid_clicked.emit(c, r, "LEFT")

    def mouseReleaseEvent(self, event):
        if self.drawing_arrow and event.button() == Qt.MouseButton.RightButton:
            x = event.position().x() - self.margin; y = event.position().y() - self.margin
            c, r = int(x // self.sq_size), int(y // self.sq_size)
            if 0 <= c < 8 and 0 <= r < 8 and (c, r) != self.start_arrow_sq:
                self.arrows.append((self.start_arrow_sq, (c, r))); self.update()
            self.drawing_arrow = False

class SatrancAnaliz(QWidget):
    def __init__(self, time_limit, increment, game_mode):
        super().__init__()
        self.setWindowTitle("MTU Projesi: V28.0 (Final Stable)"); self.setGeometry(50, 50, 1350, 850)
        self.setStyleSheet("background-color: #2c2c2c; color: white;")
        
        self.gs = GameState(); self.ai = ChessAI()
        self.valid_moves = self.gs.get_valid_moves()
        self.worker = None; self.last_nodes = 0; self.bot_thinking = False
        
        self.total_time = time_limit; self.increment = increment; self.game_mode = game_mode
        self.white_time = time_limit if time_limit else 0; self.black_time = time_limit if time_limit else 0
        self.is_timed = True if time_limit else False
        self.player_clicks = [] 
        
        self.timer = QTimer(); self.timer.timeout.connect(self.update_clock)
        if self.is_timed: self.timer.start(1000)

        main_layout = QHBoxLayout()
        left = QFrame(); left.setStyleSheet("background: #383838; border-radius: 10px;"); l_lay = QVBoxLayout(left)
        
        clock_layout = QHBoxLayout()
        self.lcd_white = QLCDNumber(); self.lcd_white.setDigitCount(5); self.lcd_white.setStyleSheet("border: 2px solid white; color: white;")
        self.lcd_black = QLCDNumber(); self.lcd_black.setDigitCount(5); self.lcd_black.setStyleSheet("border: 2px solid black; color: black; background: #888;")
        clock_layout.addWidget(QLabel("Beyaz:")); clock_layout.addWidget(self.lcd_white)
        clock_layout.addWidget(QLabel("Siyah:")); clock_layout.addWidget(self.lcd_black)
        l_lay.addLayout(clock_layout); self.display_time()

        l_lay.addWidget(QLabel("📝 Hamleler"))
        self.move_table = QTableWidget(0, 2); self.move_table.setHorizontalHeaderLabels(["Beyaz", "Siyah"])
        self.move_table.setStyleSheet("background: #444; border: none; font-size: 13px; color: white;")
        self.move_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l_lay.addWidget(self.move_table)
        
        self.lbl_status = QLabel("Oyun Başladı! Sıra Beyazda."); self.lbl_status.setStyleSheet("color: #aaa; font-style: italic; margin-top: 10px;")
        l_lay.addWidget(self.lbl_status)
        main_layout.addWidget(left, 3)
        
        self.board = BoardWidget(self.gs)
        self.board.grid_clicked.connect(self.handle_grid_click) 
        c_lay = QVBoxLayout(); c_lay.addWidget(self.board); c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(c_lay, 5)
        
        right = QFrame(); right.setStyleSheet("background: #383838; border-radius: 10px;"); r_lay = QVBoxLayout(right)
        
        self.lbl_check_alert = QLabel(""); self.lbl_check_alert.setStyleSheet("color: red; font-size: 20px; font-weight: bold;")
        self.lbl_check_alert.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_lay.addWidget(self.lbl_check_alert)

        r_lay.addWidget(QLabel("📊 İstatistikler"))
        self.stats_tbl = QTableWidget(13, 2); self.stats_tbl.horizontalHeader().hide(); self.stats_tbl.verticalHeader().hide(); self.stats_tbl.setStyleSheet("background: #444;")
        self.stats_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        labels = ["Oyun Durumu", "Sıra", "Vezirler (Q)", "Kaleler (R)", "Filler (B)", "Atlar (N)", "Piyonlar (P)", "Merkez Kontrolü", "Hesaplanan (Nodes)", "Ulaşılan Derinlik", "Tehdit Durumu", "Materyal Dengesi", "Sonuç"]
        for i, t in enumerate(labels): self.stats_tbl.setItem(i, 0, QTableWidgetItem(t))
        r_lay.addWidget(self.stats_tbl)
        
        r_lay.addWidget(QLabel("Kazanma Olasılığı"))
        self.bar = QProgressBar(); self.bar.setValue(50); self.bar.setStyleSheet("QProgressBar { background: #222; } QProgressBar::chunk { background: #4CAF50; }")
        r_lay.addWidget(self.bar)
        
        btn_layout = QHBoxLayout()
        self.undo = QPushButton("Geri Al (Z)"); self.undo.setStyleSheet("background: #d9534f; padding: 10px; font-weight: bold;"); self.undo.clicked.connect(self.undo_move)
        btn_layout.addWidget(self.undo)
        self.btn_clear = QPushButton("Okları Sil"); self.btn_clear.clicked.connect(lambda: setattr(self.board, 'arrows', []) or self.board.update())
        btn_layout.addWidget(self.btn_clear)
        self.btn_quit = QPushButton("Çıkış"); self.btn_quit.setStyleSheet("background: #555; padding: 10px; font-weight: bold;"); self.btn_quit.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_quit)
        r_lay.addLayout(btn_layout)
        r_lay.addStretch()
        
        f_fr = QFrame(); f_fr.setStyleSheet("background: #222; padding: 5px;"); f_l = QVBoxLayout(f_fr)
        f_l.addWidget(QLabel("<b>Yapay Zeka Destekli Satranç Botu</b>"))
        f_l.addWidget(QLabel("MTU Projesi"))
        f_l.addWidget(QLabel("Hazırlayan: Ahmet Buğra KURTBOĞAN"))
        f_l.addWidget(QLabel("Presented to: Burak Ulu"))
        r_lay.addWidget(f_fr)
        main_layout.addWidget(right, 4)
        self.setLayout(main_layout); self.update_stats()

    def update_clock(self):
        if not self.is_timed or self.gs.checkmate or self.gs.stalemate: return
        if self.gs.white_to_move:
            self.white_time -= 1
            if self.white_time <= 0: self.game_over("Süre Bitti! Siyah Kazandı.")
        else:
            self.black_time -= 1
            if self.black_time <= 0: self.game_over("Süre Bitti! Beyaz Kazandı.")
        self.display_time()

    def display_time(self):
        if not self.is_timed: self.lcd_white.display("--:--"); self.lcd_black.display("--:--"); return
        wm, ws = divmod(self.white_time, 60); self.lcd_white.display(f"{wm:02}:{ws:02}")
        bm, bs = divmod(self.black_time, 60); self.lcd_black.display(f"{bm:02}:{bs:02}")

    def game_over(self, msg):
        self.timer.stop()
        QMessageBox.information(self, "Oyun Bitti", msg)

    def handle_grid_click(self, c, r, btn_type):
        if btn_type == "LEFT":
            if self.game_mode == "PvE" and (self.bot_thinking or not self.gs.white_to_move): return

            if self.board.arrows:
                self.board.arrows = []
                self.board.update()
                return

            if self.board.selected_sq == (c, r):
                self.board.selected_sq = ()
                self.player_clicks = []
            else:
                self.board.selected_sq = (c, r)
                self.player_clicks.append((c, r))
            
            self.board.update()

            if len(self.player_clicks) == 2:
                s, e = self.player_clicks
                m = Move((s[1], s[0]), (e[1], e[0]), self.gs.board) # Coordinate Swap
                
                for valid_move in self.valid_moves:
                    if m == valid_move: m = valid_move; break
                
                if m in self.valid_moves:
                    player = "Beyaz" if self.gs.white_to_move else "Siyah"
                    self.gs.make_move(m); self.add_to_table(m, player)
                    if self.is_timed:
                        if player == "Beyaz": self.white_time += self.increment
                        else: self.black_time += self.increment
                    
                    self.board.selected_sq = (); self.player_clicks = []
                    self.refresh(); self.display_time()
                    
                    if not self.gs.checkmate and not self.gs.stalemate:
                        if self.game_mode == "PvE" and not self.gs.white_to_move:
                            self.start_bot_turn()
                else:
                    self.player_clicks = [(c, r)]
                    self.board.selected_sq = (c, r)
                    self.board.update()

    def start_bot_turn(self):
        self.bot_thinking = True
        self.lbl_status.setText("Bot Düşünüyor...")
        self.lbl_status.setStyleSheet("color: yellow")
        think_time = (self.black_time / 20) + self.increment if self.is_timed else 3
        gs_clone = self.gs.clone() 
        self.worker = BotWorker(self.ai, gs_clone, self.valid_moves, think_time)
        self.worker.finished.connect(self.handle_bot_result)
        self.worker.start()

    def handle_bot_result(self, best_move, score, nodes, max_depth):
        self.bot_thinking = False
        if best_move:
            self.gs.make_move(best_move); self.add_to_table(best_move, "Siyah")
            if self.is_timed: self.black_time += self.increment
            self.last_nodes = nodes
            self.stats_tbl.setItem(9, 1, QTableWidgetItem(str(max_depth)))
            self.board.arrows = []
            self.refresh(); self.display_time()
            self.lbl_status.setText("Sıra Beyazda.")
            self.lbl_status.setStyleSheet("color: #0f0")

    def refresh(self):
        self.valid_moves = self.gs.get_valid_moves(); self.board.valid_moves = self.valid_moves
        self.update_stats(); self.board.update()
        
        if self.gs.checkmate or self.gs.stalemate:
            self.timer.stop()
            msg = "Kazandınız!" if (self.gs.checkmate and not self.gs.white_to_move) else "Kaybettiniz!" if self.gs.checkmate else "Berabere!"
            QMessageBox.information(self, "Oyun Bitti", msg)
            reply = QMessageBox.question(self, "Analiz", "Bu oyunu analiz etmek için PGN kodunu almak ister misin?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                dlg = PGNDialog(self.gs.generate_pgn(), self); dlg.exec()

    def add_to_table(self, m, p):
        t = m.get_chess_notation(); t += "+" if self.gs.in_check() else ""
        row = self.move_table.rowCount()
        if self.gs.white_to_move: self.move_table.setItem(row - 1, 1, QTableWidgetItem(t))
        else: self.move_table.insertRow(row); self.move_table.setItem(row, 0, QTableWidgetItem(t))
        self.move_table.scrollToBottom()

    def undo_move(self):
        if self.bot_thinking: return
        if self.game_mode == "PvE":
            if len(self.gs.move_log) >= 2:
                self.gs.undo_move(); self.gs.undo_move()
                if self.move_table.rowCount() > 0: self.move_table.removeRow(self.move_table.rowCount()-1)
        else:
            if len(self.gs.move_log) >= 1:
                self.gs.undo_move()
                r = self.move_table.rowCount()
                if self.move_table.item(r-1, 1): self.move_table.setItem(r-1, 1, QTableWidgetItem(""))
                else: self.move_table.removeRow(r-1)
        self.board.arrows = []
        self.refresh()
        self.lbl_status.setText("Hamle Geri Alındı.")

    def update_stats(self):
        self.stats_tbl.setItem(0, 1, QTableWidgetItem("Devam Ediyor" if not self.gs.checkmate else "MAT!"))
        self.stats_tbl.setItem(1, 1, QTableWidgetItem("Beyaz" if self.gs.white_to_move else "Siyah"))
        cnt = self.gs.count_pieces()
        self.stats_tbl.setItem(2, 1, QTableWidgetItem(f"{cnt['wQ']} vs {cnt['bQ']}"))
        self.stats_tbl.setItem(3, 1, QTableWidgetItem(f"{cnt['wR']} vs {cnt['bR']}"))
        self.stats_tbl.setItem(4, 1, QTableWidgetItem(f"{cnt['wB']} vs {cnt['bB']}"))
        self.stats_tbl.setItem(5, 1, QTableWidgetItem(f"{cnt['wN']} vs {cnt['bN']}"))
        self.stats_tbl.setItem(6, 1, QTableWidgetItem(f"{cnt['wP']} vs {cnt['bP']}"))
        wc, bc = self.gs.get_center_control()
        self.stats_tbl.setItem(7, 1, QTableWidgetItem(f"Beyaz: {wc} / Siyah: {bc}"))
        self.stats_tbl.setItem(8, 1, QTableWidgetItem(f"{self.last_nodes:,}".replace(",", ".")))
        
        if self.gs.in_check():
            self.lbl_check_alert.setText("⚠️ ŞAH ÇEKİLDİ! ⚠️")
            self.stats_tbl.setItem(10, 1, QTableWidgetItem("EVET"))
        else:
            self.lbl_check_alert.setText("")
            self.stats_tbl.setItem(10, 1, QTableWidgetItem("Hayır"))

        sc = self.ai.score_board(self.gs)
        txt = f"Beyaz +{sc}" if sc > 0 else f"Siyah +{abs(sc)}" if sc < 0 else "Eşit"
        self.stats_tbl.setItem(11, 1, QTableWidgetItem(txt))
        status = "Oynanıyor"
        if self.gs.checkmate: status = "MAT Bitti"
        elif self.gs.stalemate: status = "PAT"
        self.stats_tbl.setItem(12, 1, QTableWidgetItem(status))
        try: wp = 1 / (1 + 10 ** (-sc / 1000)) * 100
        except: wp = 100 if sc > 0 else 0
        self.bar.setValue(int(wp))
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Z: self.undo_move()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = StartDialog()
    if dialog.exec():
        w = SatrancAnaliz(dialog.selected_time, dialog.selected_inc, dialog.game_mode)
        w.show()
        sys.exit(app.exec())
    else:
        sys.exit()