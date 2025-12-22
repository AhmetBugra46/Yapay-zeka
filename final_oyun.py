import sys
import random
import time
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QProgressBar, QSpinBox, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRect, QThread, pyqtSignal

# ==========================================
# 1. BÖLÜM: ARKA PLAN İŞÇİSİ (HESAPLAMA)
# ==========================================
class BotWorker(QThread):
    finished = pyqtSignal(object, float) 

    def __init__(self, ai, gs, valid_moves, depth):
        super().__init__()
        self.ai = ai
        self.gs = gs 
        self.valid_moves = valid_moves
        self.depth = depth

    def run(self):
        try:
            # Alpha-Beta algoritmasıyla en iyi hamleyi bul
            best_move, score = self.ai.find_best_move(self.gs, self.valid_moves, self.depth)
            self.finished.emit(best_move, score)
        except Exception as e:
            print(f"Analiz Hatası: {e}")

# ==========================================
# 2. BÖLÜM: YAPAY ZEKA (TURBO MOTOR)
# ==========================================
class OpeningBook:
    def __init__(self, brain_file="beyin.json"):
        self.book = {}
        self.load_brain(brain_file)

    def load_brain(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    self.book = json.load(f)
            except: self.book = {}
        else: self.book = {}

    def get_book_move(self, board_fen):
        base_fen = " ".join(board_fen.split(" ")[:4])
        if base_fen in self.book:
            moves = list(self.book[base_fen].keys())
            weights = list(self.book[base_fen].values())
            try: return random.choices(moves, weights=weights, k=1)[0]
            except: return None
        return None

class ChessAI:
    def __init__(self):
        self.CHECKMATE = 10000; self.STALEMATE = 0
        self.opening_book = OpeningBook()
        self.piece_score = {"K": 0, "Q": 90, "R": 50, "B": 33, "N": 32, "P": 10}
        # Merkez karelere (d4,e4,d5,e5) yakınlık bonusu
        self.knight_scores = [[1,1,1,1,1,1,1,1],[1,2,2,2,2,2,2,1],[1,2,3,3,3,3,2,1],[1,2,3,4,4,3,2,1],[1,2,3,4,4,3,2,1],[1,2,3,3,3,3,2,1],[1,2,2,2,2,2,2,1],[1,1,1,1,1,1,1,1]]
        
    def find_best_move(self, gs, valid_moves, depth):
        # 1. Hafıza (Varsa direkt döndür, hesaplama yapma)
        book_move = self.opening_book.get_book_move(gs.get_fen())
        if book_move:
            for m in valid_moves:
                if m.get_uci() == book_move: return m, 100.0
        
        # 2. Alpha-Beta Budama ile Hesaplama
        self.next_move = None
        
        # Hamle Sıralaması (Move Ordering): Taş yiyen hamlelere öncelik ver
        # Bu, Alpha-Beta'nın daha hızlı kesim yapmasını sağlar
        random.shuffle(valid_moves)
        valid_moves.sort(key=lambda m: 10 if m.piece_captured != "--" else 0, reverse=True)
        
        self.minimax_alpha_beta(gs, valid_moves, depth, -self.CHECKMATE, self.CHECKMATE, 1 if gs.white_to_move else -1)
        return self.next_move, 0.0

    def minimax_alpha_beta(self, gs, valid_moves, depth, alpha, beta, turn_multiplier):
        if depth == 0: return turn_multiplier * self.score_board(gs)
        
        max_score = -self.CHECKMATE
        for move in valid_moves:
            gs.make_move(move)
            next_moves = gs.get_valid_moves()
            
            # Move Ordering (Basit seviye)
            # next_moves.sort(key=lambda m: 10 if m.piece_captured != "--" else 0, reverse=True)

            score = -self.minimax_alpha_beta(gs, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
            gs.undo_move()
            
            if score > max_score:
                max_score = score
                if depth == depth: self.next_move = move
            
            # Alpha-Beta Budama Mantığı
            if max_score > alpha: alpha = max_score
            if alpha >= beta: 
                break # Bu dalı daha fazla arama (Budama)
                
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
                    if piece[1] == "N": val += self.knight_scores[r][c] * 0.1
                    if piece[0] == 'w': score += val
                    else: score -= val
        return score

# ==========================================
# 3. BÖLÜM: OYUN MANTIĞI
# ==========================================
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

    def make_move(self, move):
        self.board[move.start_row][move.start_col] = "--"
        self.board[move.end_row][move.end_col] = move.piece_moved
        if move.piece_moved == 'wP' and move.end_row == 0: self.board[move.end_row][move.end_col] = 'wQ'; move.is_pawn_promotion = True
        elif move.piece_moved == 'bP' and move.end_row == 7: self.board[move.end_row][move.end_col] = 'bQ'; move.is_pawn_promotion = True
        self.move_log.append(move)
        self.white_to_move = not self.white_to_move
        if move.piece_moved == 'wK': self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == 'bK': self.black_king_location = (move.end_row, move.end_col)

    def undo_move(self):
        if len(self.move_log) != 0:
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move
            if move.piece_moved == 'wK': self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == 'bK': self.black_king_location = (move.start_row, move.start_col)
            if move.is_pawn_promotion:
                self.board[move.start_row][move.start_col] = move.piece_moved
                self.board[move.end_row][move.end_col] = move.piece_captured
            self.checkmate = False; self.stalemate = False

    def get_valid_moves(self):
        moves = self.get_all_possible_moves()
        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.white_to_move = not self.white_to_move
            if self.in_check(): moves.remove(moves[i])
            self.white_to_move = not self.white_to_move
            self.undo_move()
        if len(moves) == 0:
            if self.in_check(): self.checkmate = True
            else: self.stalemate = True
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

    def get_fen(self):
        fen = ""
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

    # --- DETAYLI İSTATİSTİK İÇİN YENİ FONKSİYONLAR ---
    def count_pieces(self):
        counts = {"wQ":0, "wR":0, "wB":0, "wN":0, "wP":0, "bQ":0, "bR":0, "bB":0, "bN":0, "bP":0}
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "--" and p[1] != 'K':
                    counts[p] += 1
        return counts

    def get_center_control(self):
        # Merkez Kareler: d4(4,3), e4(4,4), d5(3,3), e5(3,4)
        center_sqs = [(4,3), (4,4), (3,3), (3,4)]
        w_ctrl = 0
        b_ctrl = 0
        
        # Basit kontrol: Taşların bu karelerde olması veya piyonların tehdit etmesi
        # Tam hesaplamak çok uzun sürer, basitleştirilmiş "Taş Varlığı"na bakıyoruz
        for r, c in center_sqs:
            p = self.board[r][c]
            if p[0] == 'w': w_ctrl += 1
            elif p[0] == 'b': b_ctrl += 1
            
        return w_ctrl, b_ctrl

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
    
    # Taş Hareketleri
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

class Move:
    def __init__(self, start_sq, end_sq, board):
        self.start_row = start_sq[0]; self.start_col = start_sq[1]
        self.end_row = end_sq[0]; self.end_col = end_sq[1]
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]
        self.is_pawn_promotion = False
        self.move_id = self.start_row * 1000 + self.start_col * 100 + self.end_row * 10 + self.end_col
    def __eq__(self, other): return isinstance(other, Move) and self.move_id == other.move_id
    def get_chess_notation(self): return self.get_rank_file(self.start_row, self.start_col) + self.get_rank_file(self.end_row, self.end_col)
    def get_rank_file(self, r, c):
        cols = {0:'a', 1:'b', 2:'c', 3:'d', 4:'e', 5:'f', 6:'g', 7:'h'}
        rows = {0:'8', 1:'7', 2:'6', 3:'5', 4:'4', 5:'3', 6:'2', 7:'1'}
        return cols[c] + rows[r]
    def get_uci(self): return self.get_rank_file(self.start_row, self.start_col) + self.get_rank_file(self.end_row, self.end_col)

# ==========================================
# 4. BÖLÜM: ARAYÜZ
# ==========================================
class BoardWidget(QWidget):
    def __init__(self, game_state, parent=None):
        super().__init__(parent)
        self.gs = game_state
        self.sq_size = 65; self.margin = 30
        self.setFixedSize(self.sq_size * 8 + self.margin * 2, self.sq_size * 8 + self.margin * 2)
        self.selected_sq = (); self.valid_moves = []; self.suggested_move = None 
        self.semboller = {'wK': '♔', 'wQ': '♕', 'wR': '♖', 'wB': '♗', 'wN': '♘', 'wP': '♙', 'bK': '♚', 'bQ': '♛', 'bR': '♜', 'bB': '♝', 'bN': '♞', 'bP': '♟'}

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_coordinates(painter)
        painter.translate(self.margin, self.margin)
        colors = [QColor(240, 217, 181), QColor(181, 136, 99)]
        for r in range(8):
            for c in range(8):
                color = colors[(r + c) % 2]
                painter.fillRect(r * self.sq_size, c * self.sq_size, self.sq_size, self.sq_size, color)
                if self.selected_sq == (c, r): painter.fillRect(r * self.sq_size, c * self.sq_size, self.sq_size, self.sq_size, QColor(0, 255, 255, 100))
                
                # ÖNERİ SİSTEMİ
                if self.suggested_move:
                    if (c, r) == (self.suggested_move.start_col, self.suggested_move.start_row):
                        painter.setBrush(QColor(0, 0, 255, 50)); painter.setPen(QPen(QColor(0, 0, 255), 3))
                        painter.drawEllipse(c * self.sq_size + 5, r * self.sq_size + 5, self.sq_size - 10, self.sq_size - 10)
                    if (c, r) == (self.suggested_move.end_col, self.suggested_move.end_row):
                        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor(0, 200, 0), 5))
                        painter.drawRect(c * self.sq_size, r * self.sq_size, self.sq_size, self.sq_size)

        self.draw_hints(painter)
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
        moves = [m for m in self.valid_moves if m.start_row == self.selected_sq[0] and m.start_col == self.selected_sq[1]]
        for m in moves:
            r, c = m.end_row, m.end_col
            if self.gs.board[r][c] != "--":
                painter.setBrush(Qt.BrushStyle.NoBrush); pen = QPen(QColor(200, 50, 50, 150)); pen.setWidth(5); painter.setPen(pen)
                painter.drawEllipse(c * self.sq_size + 5, r * self.sq_size + 5, self.sq_size - 10, self.sq_size - 10)
            else:
                painter.setBrush(QColor(100, 200, 255, 180)); painter.setPen(Qt.PenStyle.NoPen)
                radius = self.sq_size // 6
                painter.drawEllipse(c * self.sq_size + self.sq_size // 2 - radius, r * self.sq_size + self.sq_size // 2 - radius, radius * 2, radius * 2)

class SatrancAnaliz(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MTU Projesi: Optimize Edilmiş Satranç Botu (V10)"); self.setGeometry(50, 50, 1350, 850)
        self.setStyleSheet("background-color: #2c2c2c; color: white;")
        
        self.gs = GameState(); self.ai = ChessAI()
        self.valid_moves = self.gs.get_valid_moves()
        self.player_clicks = []
        self.worker = None

        main_layout = QHBoxLayout()
        
        # SOL PANEL
        left = QFrame(); left.setStyleSheet("background: #383838; border-radius: 10px;"); l_lay = QVBoxLayout(left)
        l_lay.addWidget(QLabel("📝 Hamleler"))
        self.move_table = QTableWidget(0, 2); self.move_table.setHorizontalHeaderLabels(["Beyaz", "Siyah"])
        self.move_table.setStyleSheet("background: #444; border: none; font-size: 13px;")
        header_style = "QHeaderView::section { background-color: #d0d0d0; color: black; font-weight: bold; font-size: 14px; border: 1px solid #666; }"
        self.move_table.horizontalHeader().setStyleSheet(header_style)
        self.move_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l_lay.addWidget(self.move_table)
        
        l_lay.addWidget(QLabel("💡 Profesyonel Analiz"))
        self.sugg_box = QLabel("Analiz bekleniyor..."); self.sugg_box.setStyleSheet("background: #222; color: #0f0; padding: 10px; font-weight: bold;")
        l_lay.addWidget(self.sugg_box)
        self.depth_s = QSpinBox(); self.depth_s.setRange(1, 6); self.depth_s.setValue(4); self.depth_s.setPrefix("Analiz Gücü: "); self.depth_s.setStyleSheet("background: #555; padding: 5px;")
        l_lay.addWidget(self.depth_s)
        main_layout.addWidget(left, 3)
        
        # ORTA PANEL
        self.board = BoardWidget(self.gs); self.board.valid_moves = self.valid_moves; self.board.mousePressEvent = self.handle_click
        c_lay = QVBoxLayout(); c_lay.addWidget(self.board); c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(c_lay, 5)
        
        # SAĞ PANEL
        right = QFrame(); right.setStyleSheet("background: #383838; border-radius: 10px;"); r_lay = QVBoxLayout(right)
        r_lay.addWidget(QLabel("📊 Detaylı İstatistikler"))
        # İstatistik Tablosu Büyütüldü
        self.stats_tbl = QTableWidget(12, 2); self.stats_tbl.horizontalHeader().hide(); self.stats_tbl.verticalHeader().hide(); self.stats_tbl.setStyleSheet("background: #444;")
        self.stats_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        labels = ["Oyun Durumu", "Sıra", "Vezirler (Q)", "Kaleler (R)", "Filler (B)", "Atlar (N)", "Piyonlar (P)", "Merkez Kontrolü", "Olası Hamleler", "Şah Tehdidi", "Materyal Dengesi", "Sonuç"]
        for i, t in enumerate(labels): self.stats_tbl.setItem(i, 0, QTableWidgetItem(t))
        r_lay.addWidget(self.stats_tbl)
        
        r_lay.addWidget(QLabel("Kazanma Olasılığı"))
        self.bar = QProgressBar(); self.bar.setValue(50); self.bar.setStyleSheet("QProgressBar { background: #222; } QProgressBar::chunk { background: #4CAF50; }")
        r_lay.addWidget(self.bar)
        self.undo = QPushButton("↩ Geri Al (Z)"); self.undo.setStyleSheet("background: #d9534f; padding: 10px; font-weight: bold;"); self.undo.clicked.connect(self.undo_move)
        r_lay.addWidget(self.undo); r_lay.addStretch()
        
        # İMZA
        f_fr = QFrame(); f_fr.setStyleSheet("background: #222; padding: 5px;"); f_l = QVBoxLayout(f_fr)
        f_l.addWidget(QLabel("<b>Yapay Zeka Destekli Satranç Botu</b>"))
        f_l.addWidget(QLabel("MTU Projesi"))
        f_l.addWidget(QLabel("Hazırlayan: Ahmet Buğra KURTBOĞAN"))
        f_l.addWidget(QLabel("Presented to: Burak Ulu"))
        r_lay.addWidget(f_fr)
        main_layout.addWidget(right, 4) # Sağ paneli biraz genişlet
        self.setLayout(main_layout); self.update_stats(); self.trigger_analysis()

    def handle_click(self, event):
        if self.worker and self.worker.isRunning(): return
        
        x = event.position().x() - self.board.margin; y = event.position().y() - self.board.margin
        if x < 0 or y < 0 or x > 8*self.board.sq_size or y > 8*self.board.sq_size: return
        c = int(x // self.board.sq_size); r = int(y // self.board.sq_size)
        
        if self.board.selected_sq == (r, c): self.board.selected_sq = (); self.player_clicks = []
        else: self.board.selected_sq = (r, c); self.player_clicks.append((r, c))
        
        if len(self.player_clicks) == 2:
            s, e = self.player_clicks
            m = Move(s, e, self.gs.board)
            match = next((x for x in self.valid_moves if x == m), None)
            if match:
                player = "Beyaz" if self.gs.white_to_move else "Siyah"
                self.gs.make_move(match); self.add_to_table(match, player); self.refresh()
                if not self.gs.checkmate: self.start_analysis()
            else: self.player_clicks = [self.board.selected_sq]
        self.board.update()

    def start_analysis(self):
        # SADECE BEYAZ İÇİN ÖNERİ YAP (İSTEK 2)
        if self.gs.white_to_move:
            self.sugg_box.setText("⏳ Analiz (Turbo)..."); self.sugg_box.setStyleSheet("color: yellow")
            self.worker = BotWorker(self.ai, self.gs, self.valid_moves, self.depth_s.value())
            self.worker.finished.connect(self.handle_result)
            self.worker.start()
        else:
            self.sugg_box.setText("⚫ Sıra Siyahta\n(Analiz Kapalı)"); self.sugg_box.setStyleSheet("color: gray")
            self.board.suggested_move = None; self.board.update()

    def handle_result(self, best_move, score):
        if best_move:
            self.sugg_box.setText(f"✅ Öneri: {best_move.get_chess_notation()}\nPuan: {score:.1f}")
            self.sugg_box.setStyleSheet("color: #0f0")
            self.board.suggested_move = best_move; self.board.update()

    def trigger_analysis(self):
        if not self.gs.checkmate: self.start_analysis()

    def refresh(self):
        self.valid_moves = self.gs.get_valid_moves(); self.board.valid_moves = self.valid_moves
        self.board.selected_sq = (); self.board.suggested_move = None; self.player_clicks = []
        self.update_stats(); self.board.update()

    def add_to_table(self, m, p):
        t = m.get_chess_notation(); t += "+" if self.gs.in_check() else ""
        row = self.move_table.rowCount()
        if p == "Beyaz": self.move_table.insertRow(row); self.move_table.setItem(row, 0, QTableWidgetItem(t))
        else: self.move_table.setItem(row - 1, 1, QTableWidgetItem(t))
        self.move_table.scrollToBottom()

    def update_stats(self):
        self.stats_tbl.setItem(0, 1, QTableWidgetItem("Devam Ediyor" if not self.gs.checkmate else "MAT!"))
        self.stats_tbl.setItem(1, 1, QTableWidgetItem("Beyaz" if self.gs.white_to_move else "Siyah"))
        
        # DETAYLI İSTATİSTİKLER (İSTEK 1)
        cnt = self.gs.count_pieces()
        self.stats_tbl.setItem(2, 1, QTableWidgetItem(f"{cnt['wQ']} vs {cnt['bQ']}")) # Vezir
        self.stats_tbl.setItem(3, 1, QTableWidgetItem(f"{cnt['wR']} vs {cnt['bR']}")) # Kale
        self.stats_tbl.setItem(4, 1, QTableWidgetItem(f"{cnt['wB']} vs {cnt['bB']}")) # Fil
        self.stats_tbl.setItem(5, 1, QTableWidgetItem(f"{cnt['wN']} vs {cnt['bN']}")) # At
        self.stats_tbl.setItem(6, 1, QTableWidgetItem(f"{cnt['wP']} vs {cnt['bP']}")) # Piyon
        
        wc, bc = self.gs.get_center_control()
        self.stats_tbl.setItem(7, 1, QTableWidgetItem(f"Beyaz: {wc} / Siyah: {bc}")) # Merkez
        
        self.stats_tbl.setItem(8, 1, QTableWidgetItem(str(len(self.valid_moves))))
        self.stats_tbl.setItem(9, 1, QTableWidgetItem("ŞAH!" if self.gs.in_check() else "Yok"))
        
        # Puan durumu
        sc = self.ai.score_board(self.gs)
        if sc > 0: txt = f"Beyaz +{sc}"
        elif sc < 0: txt = f"Siyah +{abs(sc)}"
        else: txt = "Eşit"
        self.stats_tbl.setItem(10, 1, QTableWidgetItem(txt))
        
        status = "Oynanıyor"
        if self.gs.checkmate: status = "MAT Bitti"
        elif self.gs.stalemate: status = "PAT"
        self.stats_tbl.setItem(11, 1, QTableWidgetItem(status))

        try: wp = 1 / (1 + 10 ** (-sc / 50)) * 100
        except: wp = 100 if sc > 0 else 0
        self.bar.setValue(int(wp))

    def undo_move(self):
        if len(self.gs.move_log) > 0:
            self.gs.undo_move()
            rows = self.move_table.rowCount()
            if rows > 0:
                if self.move_table.item(rows-1, 1): self.move_table.setItem(rows-1, 1, QTableWidgetItem(""))
                else: self.move_table.removeRow(rows-1)
            self.refresh(); self.trigger_analysis()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Z: self.undo_move()

if __name__ == "__main__":
    app = QApplication(sys.argv); w = SatrancAnaliz(); w.show(); sys.exit(app.exec())