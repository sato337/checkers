import sys
import sqlite3
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QLineEdit, QPushButton, QVBoxLayout, QMessageBox,
                             QSlider, QMenu)
from PyQt6.QtGui import QPainter, QColor, QPalette, QBrush, QPixmap, QFont
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QSoundEffect


class StartWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.volume = 30
        self.set_background()
        self.create_start_window()

    def set_background(self):
        palette = self.palette()
        pixmap = QPixmap("background.jpg")
        scaled_pixmap = pixmap.scaled(500, 500, Qt.AspectRatioMode.IgnoreAspectRatio)
        palette.setBrush(QPalette.ColorRole.Window, QBrush(scaled_pixmap))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def create_start_window(self):
        self.setWindowTitle('Шашки')
        self.setFixedSize(500, 500)

        layout = QVBoxLayout()

        # Кнопка меню
        self.menu_button = QPushButton('☰', self)
        self.menu_button.setFixedSize(30, 30)
        self.menu = QMenu(self)
        self.rules_action = self.menu.addAction('Правила')
        self.rules_action.triggered.connect(self.show_rules)
        self.menu_button.clicked.connect(self.show_menu)
        layout.addWidget(self.menu_button)

        label1 = QLabel('Игрок 1 (белые):')
        label1.setStyleSheet("color: white;font-weight: 900;")
        layout.addWidget(label1)
        self.player_name1 = QLineEdit()
        self.player_name1.setText('Игрок 1')
        layout.addWidget(self.player_name1)

        label2 = QLabel('Игрок 2 (черные):')
        label2.setStyleSheet("color: white;font-weight: 900;")
        layout.addWidget(label2)
        self.player_name2 = QLineEdit()
        self.player_name2.setText('Игрок 2')
        layout.addWidget(self.player_name2)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        layout.addWidget(self.volume_slider)

        self.volume_value_label = QLabel(f'Громкость: {self.volume}%')
        self.volume_value_label.setStyleSheet("color: white;font-weight: 900;")
        layout.addWidget(self.volume_value_label)

        start_btn = QPushButton('Начать игру')
        start_btn.clicked.connect(self.start_click)
        layout.addWidget(start_btn)

        # В меню добавляем новый пункт
        self.stats_action = self.menu.addAction('Статистика')
        self.stats_action.triggered.connect(self.show_statistics)

        self.setLayout(layout)
        self.center_window()

    def on_volume_changed(self, value):
        self.volume = value
        self.volume_value_label.setText(f'Громкость: {value}%')

    def start_click(self):
        player1 = self.player_name1.text().strip()
        player2 = self.player_name2.text().strip()

        if not player1 or not player2:
            QMessageBox.warning(self, 'Ошибка',
                                'Пожалуйста, введите имена обоих игроков!')
            return

        con = sqlite3.connect('stats.sqlite')
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO name(nickname) VALUES (?)", (player1,))
        cur.execute("INSERT OR IGNORE INTO name(nickname) VALUES (?)", (player2,))
        con.commit()
        con.close()

        self.game_window = GameWindow(player1, player2)
        self.game_window.set_sound_volume(self.volume)
        self.game_window.show()
        self.close()

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def show_menu(self):
        self.menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def show_rules(self):
        """Показывает правила игры из файла"""
        with open('rules.txt', 'r', encoding='utf-8') as file:
            rules = file.read()

        msg = QMessageBox(self)
        msg.setWindowTitle("Правила игры")
        msg.setText(rules)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_statistics(self):
        """Показывает статистику игроков"""
        try:
            con = sqlite3.connect('stats.sqlite')
            cur = con.cursor()

            # Получаем статистику всех игроков, отсортированную по проценту побед
            stats = cur.execute("""
                SELECT nickname, wons, losses, percent 
                FROM name 
                ORDER BY percent DESC, wons DESC
            """).fetchall()
            con.close()

            if not stats:
                QMessageBox.information(self, "Статистика", "Нет доступной статистики")
                return

            # Формируем текст статистики
            stats_text = "Статистика игроков:\n\n"
            stats_text += "{:<15} {:>8} {:>10} {:>10}\n".format("Игрок", "Победы", "Поражения", "Процент")
            stats_text += "-" * 45 + "\n"

            for nickname, wons, losses, percent in stats:
                stats_text += "{:<15} {:>8} {:>10} {:>9.1f}%\n".format(
                    nickname, wons, losses, percent
                )

            # Создаем окно для отображения статистики
            msg = QMessageBox(self)
            msg.setWindowTitle("Статистика игроков")
            msg.setText(stats_text)
            msg.setFont(QFont("Courier New", 10))  # Используем моноширинный шрифт
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при получении статистики: {str(e)}")


class GameWindow(QMainWindow):
    def __init__(self, player1, player2):
        super().__init__()
        # Сохраняем имена игроков
        self.player1 = player1
        self.player2 = player2

        # Настройки окна
        self.setFixedSize(800, 850)  # Возвращаем фиксированный размер
        self.setWindowTitle('Шашки')

        # Размер одной клетки доски
        self.cell_size = 100

        # Цвета для доски
        self.light_square = QColor(255, 206, 158)
        self.dark_square = QColor(209, 139, 71)

        # Игровые параметры
        self.current_player = 1
        self.selected_piece = None
        self.last_captured = None
        self.multiple_capture_in_progress = False

        # Создаем пустую доску 8x8
        self.board = [[0] * 8 for _ in range(8)]

        # Расставляем шашки
        self.setup_board()

        # Инициализация звука
        self.move_sound = QSoundEffect()
        self.move_sound.setSource(QUrl.fromLocalFile("move.wav"))

        # Создаем меню
        self.menu = QMenu(self)
        self.menu_button = QPushButton('☰', self)  # Кнопка меню
        self.menu_button.setGeometry(10, 10, 30, 30)

        # Добавляем пункты меню
        self.return_action = self.menu.addAction('Вернуться в главное меню')
        self.restart_action = self.menu.addAction('Начать заново')
        self.exit_action = self.menu.addAction('Выйти из игры')

        # Привязываем действия к функциям
        self.return_action.triggered.connect(self.return_to_start)
        self.restart_action.triggered.connect(self.restart_game)
        self.exit_action.triggered.connect(self.close)

        # Привязываем меню к кнопке
        self.menu_button.clicked.connect(self.show_menu)

        self.multiple_capture_in_progress = False  # Добавляем флаг множественного взятия
        self.game_over = False  # Добавляем флаг окончания игры

    def on_sound_loaded(self):
        """Обработчик загрузки звука"""
        if not self.move_sound.isLoaded():
            print("Ошибка загрузки звука")

    def setup_board(self):
        # Раставляем черне шашки
        for row in range(3):
            for col in range(8):
                # Ставим шашки только на емных клетках
                if self.is_dark_square(row, col):
                    self.board[row][col] = 2

        # Расставляем белые шашки
        for row in range(5, 8):
            for col in range(8):
                # Ставим шашки только на темных клетках
                if self.is_dark_square(row, col):
                    self.board[row][col] = 1

    def is_dark_square(self, row, col):
        """Проверяет, является и клетка темной"""
        return (row + col) % 2 == 1

    def is_white_piece(self, piece):
        """Проверяет, является ли шашка белой"""
        return piece in [1, 3]  # 1 - белая шашка, 3 - белая дамка

    def is_black_piece(self, piece):
        """Проверяет, является ли шашка черной"""
        return piece in [2, 4]  # 2 - черная шашка, 4 - черная дамка

    def is_king(self, piece):
        """Проверяет, является ли шашка дамкой"""
        return piece in [3, 4]  # 3 - белая дамка, 4 - черная дамка

    def paintEvent(self, event):
        painter = QPainter(self)

        # Рисуем доску
        self.draw_board(painter)

        # Рисуем шашки
        self.draw_pieces(painter)

        # Отображаем информацию о текущем игроке
        self.draw_game_info(painter)

    def draw_board(self, painter):
        """Рисует летки доски"""
        for row in range(8):
            for col in range(8):
                x = col * self.cell_size
                y = row * self.cell_size

                # Выбираем цвет клетки
                if self.is_dark_square(row, col):
                    color = self.dark_square
                else:
                    color = self.light_square

                # Рисуем клетку
                painter.fillRect(x, y, self.cell_size, self.cell_size, color)

    def draw_pieces(self, painter):
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece != 0:  # если на клетке есть шашка
                    self.draw_single_piece(painter, row, col, piece)

    def draw_single_piece(self, painter, row, col, piece):
        """Рисует одну шашку"""
        x = col * self.cell_size
        y = row * self.cell_size
        margin = self.cell_size // 8
        size = self.cell_size - 2 * margin

        # Устанавливаем цвет шашк
        if self.is_white_piece(piece):
            painter.setBrush(Qt.GlobalColor.white)
        else:
            painter.setBrush(Qt.GlobalColor.black)

        # станавливаем цвет контура
        is_selected = self.selected_piece == (row, col)
        if is_selected:
            painter.setPen(Qt.GlobalColor.red)
        else:
            painter.setPen(Qt.GlobalColor.black)

        # Рисуем шашку
        painter.drawEllipse(x + margin, y + margin, size, size)

        # Если это дамка, рсуем корону
        if self.is_king(piece):
            self.draw_crown(painter, x, y)

    def draw_crown(self, painter, x, y):
        """Рисует корну на дамке"""
        painter.setPen(Qt.GlobalColor.red)
        crown_size = self.cell_size // 4
        center_x = x + self.cell_size // 2 - crown_size // 2
        center_y = y + self.cell_size // 2 + crown_size // 4
        painter.drawText(center_x, center_y, "♔")

    def mousePressEvent(self, event):
        col = event.pos().x() // self.cell_size
        row = event.pos().y() // self.cell_size

        # Проверяем, что клик был в пределах доски
        if not self.is_valid_position(row, col):
            return

        if self.selected_piece is None:
            self.try_select_piece(row, col)
        else:
            self.try_make_move(row, col)
            self.selected_piece = None

        self.update()

    def is_valid_position(self, row, col):
        """Проверяет, что позиция находится в пределах доски"""
        return 0 <= row < 8 and 0 <= col < 8

    def try_select_piece(self, row, col):
        """Пытается выбрать шашку"""
        piece = self.board[row][col]

        # Проверяем, что выбрана не пустая клетка
        if piece == 0:
            return

        # Проверяем, что выбрана шашка текущего игрока
        if self.current_player == 1 and not self.is_white_piece(piece):
            return
        if self.current_player == 2 and not self.is_black_piece(piece):
            return

        # Если есть обязательные взятия, разрешаем выбирать только те шашки,
        # которые могут совершить взятие
        if self.has_mandatory_captures(self.current_player):
            if not self.has_capture_moves(row, col):
                return

        self.selected_piece = (row, col)
        self.update()

    def try_make_move(self, end_row, end_col):
        """Пытается сделать ход выбранной шашкой"""
        if not self.selected_piece:
            return

        start_row, start_col = self.selected_piece

        # Пропускаем, если кликнули по той же клетке
        if (end_row, end_col) == (start_row, start_col):
            self.selected_piece = None
            self.update()
            return

        # Проверяем наличие обязательных взятий
        has_mandatory = self.has_mandatory_captures(self.current_player)

        # Проверяем, является ли текущий ход взятием
        is_capture = self.is_capture_move(start_row, start_col, end_row, end_col)

        # Если есть обязательные взятия, но ход не является взятием
        if has_mandatory and not is_capture and not self.multiple_capture_in_progress:
            self.selected_piece = None
            self.update()
            return

        # Делаем ход
        move_result = self.make_move(start_row, start_col, end_row, end_col)

        if not move_result:
            self.selected_piece = None
            self.update()
            return

        # Проверяем возможность множестенного взятия
        if is_capture and self.has_capture_moves(end_row, end_col):
            self.multiple_capture_in_progress = True
            self.selected_piece = (end_row, end_col)
        else:
            self.multiple_capture_in_progress = False
            self.selected_piece = None
            # Передаем ход другому игроку только если нет возможности продолжить взятие
            self.current_player = 3 - self.current_player

        # После завершения хода проверяем окончание игры
        if not self.multiple_capture_in_progress:
            if self.check_game_over() > 0:
                return

        self.update()

    def is_capture_move(self, start_row, start_col, end_row, end_col):
        """Проверяет, является ли ход взятием"""
        piece = self.board[start_row][start_col]

        # Для дамки
        if self.is_king(piece):
            # Проверяем, что ход по диагонали
            if abs(end_row - start_row) != abs(end_col - start_col):
                return False

            row_step = 1 if end_row > start_row else -1
            col_step = 1 if end_col > start_col else -1
            current_row = start_row + row_step
            current_col = start_col + col_step
            enemy_found = False

            while current_row != end_row:
                if self.board[current_row][current_col] != 0:
                    if enemy_found:  # Если уже нашли одну шашку
                        return False
                    # Проверяем, что это шашка противника
                    if ((self.is_white_piece(piece) and self.is_black_piece(self.board[current_row][current_col])) or
                            (self.is_black_piece(piece) and self.is_white_piece(self.board[current_row][current_col]))):
                        enemy_found = True
                        self.last_captured = (current_row, current_col)
                    else:
                        return False
                current_row += row_step
                current_col += col_step

            return enemy_found

        # Для обычной шашки
        if abs(end_row - start_row) == 2 and abs(end_col - start_col) == 2:
            middle_row = (start_row + end_row) // 2
            middle_col = (start_col + end_col) // 2
            captured_piece = self.board[middle_row][middle_col]

            if ((self.is_white_piece(piece) and self.is_black_piece(captured_piece)) or
                    (self.is_black_piece(piece) and self.is_white_piece(captured_piece))):
                self.last_captured = (middle_row, middle_col)
                return True

        return False

    def is_valid_move(self, start_row, start_col, end_row, end_col):
        """Проверяет возможность хода"""
        # Проверяем, что конечная позиция находится в пределах доски
        if not self.is_valid_position(end_row, end_col):
            return False

        # Проверяем, что конечная позиция пуста
        if self.board[end_row][end_col] != 0:
            return False

        piece = self.board[start_row][start_col]

        # Для дамки
        if self.is_king(piece):
            return self._is_valid_king_move(start_row, start_col, end_row, end_col)

        # Проверяем взятие
        if abs(end_row - start_row) == 2 and abs(end_col - start_col) == 2:
            middle_row = (start_row + end_row) // 2
            middle_col = (start_col + end_col) // 2
            captured_piece = self.board[middle_row][middle_col]

            # Проверяем, что взятая шашка принадлежит противнику
            if self.is_white_piece(piece) and self.is_black_piece(captured_piece):
                self.last_captured = (middle_row, middle_col)
                return True
            if self.is_black_piece(piece) and self.is_white_piece(captured_piece):
                self.last_captured = (middle_row, middle_col)
                return True
            return False

        # Проверяем обычный ход (только если не в процессе множественного взятия)
        if not self.multiple_capture_in_progress:
            if abs(end_col - start_col) == 1:
                if self.is_white_piece(piece):
                    return end_row == start_row - 1  # белые ходят вверх
                else:
                    return end_row == start_row + 1  # черные ходят вниз
        return False

    def _is_valid_king_move(self, start_row, start_col, end_row, end_col):
        """Проверят возможность хода дамки"""
        # Проверяем, что ход по диагонали
        if abs(end_row - start_row) != abs(end_col - start_col):
            return False

        # Определяем направление движения
        row_step = 1 if end_row > start_row else -1
        col_step = 1 if end_col > start_col else -1

        # Проверяем путь
        current_row = start_row + row_step
        current_col = start_col + col_step
        enemy_found = False
        enemy_position = None

        while current_row != end_row:
            if self.board[current_row][current_col] != 0:
                # Если уже нашли одну шашку на пути
                if enemy_found:
                    return False
                # Проверяем, что это шашка противника
                piece = self.board[start_row][start_col]
                current_piece = self.board[current_row][current_col]
                if ((self.is_white_piece(piece) and self.is_black_piece(current_piece)) or
                        (self.is_black_piece(piece) and self.is_white_piece(current_piece))):
                    enemy_found = True
                    enemy_position = (current_row, current_col)
                else:
                    return False

            current_row += row_step
            current_col += col_step

        # Если нашли шашку противника, сохраняем её позицию для взятия
        if enemy_found:
            self.last_captured = enemy_position

        # Ход возможен если:
        # 1. Не было шашек на пути (обычный ход)
        # 2. Была только одна шашка противника (взятие)
        return True

    def make_move(self, start_row, start_col, end_row, end_col):
        """Выполняет ход"""
        if not self.is_valid_move(start_row, start_col, end_row, end_col):
            return False

        piece = self.board[start_row][start_col]
        was_king = self.is_king(piece)

        if not self.multiple_capture_in_progress:
            if self.has_mandatory_captures(self.current_player) and not self.is_capture_move(start_row, start_col,
                                                                                             end_row, end_col):
                return False

        if self.last_captured:
            captured_row, captured_col = self.last_captured
            self.board[captured_row][captured_col] = 0
            self.last_captured = None

        self.board[start_row][start_col] = 0
        self.board[end_row][end_col] = piece

        became_king = False
        if piece == 1 and end_row == 0:
            self.board[end_row][end_col] = 3
            became_king = True
        elif piece == 2 and end_row == 7:
            self.board[end_row][end_col] = 4
            became_king = True

        try:
            self.move_sound.play()
        except Exception:
            pass

        if became_king and not was_king:
            if self.has_capture_moves(end_row, end_col):
                self.multiple_capture_in_progress = True
                return True
            else:
                self.multiple_capture_in_progress = False
                return True

        return True

    def has_mandatory_captures(self, player):
        """Проверяет, есть ли обязательные взятия для игрока"""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if ((player == 1 and self.is_white_piece(piece)) or
                        (player == 2 and self.is_black_piece(piece))):
                    if self.has_capture_moves(row, col):
                        return True
        return False

    def has_capture_moves(self, row, col):
        """Проверяет возможность взятия для шашки"""
        piece = self.board[row][col]
        if piece == 0:
            return False

        # Для дамки
        if self.is_king(piece):
            # Проверяем все четыре направления
            directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
            for d_row, d_col in directions:
                current_row = row + d_row
                current_col = col + d_col
                enemy_found = False

                while self.is_valid_position(current_row, current_col):
                    if self.board[current_row][current_col] != 0:
                        if enemy_found:  # Если уже нашли одну шашку
                            break
                        # Проверяем, что это шашка противника
                        if ((self.is_white_piece(piece) and self.is_black_piece(
                                self.board[current_row][current_col])) or
                                (self.is_black_piece(piece) and self.is_white_piece(
                                    self.board[current_row][current_col]))):
                            enemy_found = True
                        else:
                            break
                    elif enemy_found:  # Если нашли пустую клетку после шашки противника
                        return True
                    current_row += d_row
                    current_col += d_col
            return False

        # Для обычной шашки (существующий код)
        directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
        for d_row, d_col in directions:
            new_row = row + d_row
            new_col = col + d_col

            if self.is_valid_position(new_row, new_col) and self.board[new_row][new_col] == 0:
                middle_row = row + d_row // 2
                middle_col = col + d_col // 2

                if self.is_valid_position(middle_row, middle_col):
                    middle_piece = self.board[middle_row][middle_col]
                    if (self.is_white_piece(piece) and self.is_black_piece(middle_piece)) or \
                            (self.is_black_piece(piece) and self.is_white_piece(middle_piece)):
                        return True

        return False

    def check_game_over(self):
        """Проверяет окончание игры"""
        white_pieces = 0
        black_pieces = 0

        # Подсчитываем количество шашек каждого цвета
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if self.is_white_piece(piece):
                    white_pieces += 1
                elif self.is_black_piece(piece):
                    black_pieces += 1

        # Если у одной из сторон не осталось шашек
        if white_pieces == 0:
            self.show_game_over_message("Черные победили!")
            return 2  # победа черных
        elif black_pieces == 0:
            self.show_game_over_message("Белые победили!")
            return 1  # победа белых

        # Проверка на отсутствие ходов
        if not self.has_valid_moves(self.current_player):
            winner = "Белые" if self.current_player == 2 else "Черные"
            self.show_game_over_message(f"{winner} победили!")
            return 3 - self.current_player

        return 0  # игра продолжается

    def show_game_over_message(self, message):
        """Показывает сообщение об окончании игры и обновляет статистику"""
        if self.game_over:  # Проверяем, не было ли уже окончания игры
            return

        self.game_over = True  # Устанавливаем флаг

        # Определяем победителя и проигравшего
        winner = self.player1 if "Белые" in message else self.player2
        loser = self.player2 if "Белые" in message else self.player1

        try:
            con = sqlite3.connect('stats.sqlite')
            cur = con.cursor()

            # Обновляем статистику победителя
            cur.execute("UPDATE name SET wons = wons + 1 WHERE nickname = ?", (winner,))
            # Получаем обновленную статистику победителя
            cur.execute("SELECT wons, losses FROM name WHERE nickname = ?", (winner,))
            winner_wons, winner_losses = cur.fetchone()
            # Рассчитываем процент побед для победителя
            winner_total = winner_wons + winner_losses
            winner_percent = round((winner_wons / winner_total * 100) if winner_total > 0 else 0, 2)
            cur.execute("UPDATE name SET percent = ? WHERE nickname = ?", (winner_percent, winner))

            # Обновляем статистику проигравшего
            cur.execute("UPDATE name SET losses = losses + 1 WHERE nickname = ?", (loser,))
            # Получаем обновленную статистику проигравшего
            cur.execute("SELECT wons, losses FROM name WHERE nickname = ?", (loser,))
            loser_wons, loser_losses = cur.fetchone()
            # Рассчитываем процент побед для проигравшего
            loser_total = loser_wons + loser_losses
            loser_percent = round((loser_wons / loser_total * 100) if loser_total > 0 else 0, 2)
            cur.execute("UPDATE name SET percent = ? WHERE nickname = ?", (loser_percent, loser))

            con.commit()
            con.close()

        except Exception as e:
            print(f"Ошибка при обновлении статистики: {str(e)}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Конец игры")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.buttonClicked.connect(self.return_to_start)
        msg.exec()

    def has_valid_moves(self, player):
        """Проверяет, есть ли доступные ходы у игрока"""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if ((player == 1 and self.is_white_piece(piece)) or
                        (player == 2 and not self.is_white_piece(piece))):
                    if self.has_any_moves(row, col):
                        return True
        return False

    def draw_game_info(self, painter):
        """Отображает информацию о текущем состоянии игры"""
        painter.setPen(Qt.GlobalColor.black)
        text = f"Ход {'белых' if self.current_player == 1 else 'черых'}"

        # Проверяем окончание игры
        winner = self.check_game_over()
        if winner > 0:
            text = f"Победил {'белые' if winner == 1 else 'черные'}!"

        painter.drawText(10, 820, text)

    def has_any_moves(self, row, col):
        """Проверяет наличие любых возмжных ходов для шашки"""
        piece = self.board[row][col]

        # Проверяем возможность взятия
        if self.has_capture_moves(row, col):
            return True

        # Для дамки
        if self.is_king(piece):
            directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
            for d_row, d_col in directions:
                new_row = row + d_row
                new_col = col + d_col
                while self.is_valid_position(new_row, new_col):
                    if self.board[new_row][new_col] == 0:
                        return True
                    new_row += d_row
                    new_col += d_col
        # Для обычной шаши
        else:
            # Определяем направление движения (вверх для белы, вниз для черных)
            direction = -1 if self.is_white_piece(piece) else 1

            # Проверяем ходы по диагонали
            for d_col in [-1, 1]:
                new_row = row + direction
                new_col = col + d_col
                if self.is_valid_position(new_row, new_col) and self.board[new_row][new_col] == 0:
                    return True

        return False

    def _has_king_capture_moves(self, row, col):
        """Проверяет возможность взятия для дамки"""
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        piece = self.board[row][col]

        for d_row, d_col in directions:
            new_row = row + d_row
            new_col = col + d_col
            found_enemy = False

            while self.is_valid_position(new_row, new_col):
                if self.board[new_row][new_col] != 0:
                    if found_enemy:  # Если уже нашли одну шашку
                        break
                    # Проверяем, что это шашка противника
                    if ((self.is_white_piece(piece) and not self.is_white_piece(self.board[new_row][new_col])) or
                            (not self.is_white_piece(piece) and self.is_white_piece(self.board[new_row][new_col]))):
                        found_enemy = True
                    else:
                        break
                elif found_enemy:  # Если нашли пустую клетку после шашки противника
                    return True
                new_row += d_row
                new_col += d_col

        return False

    def set_sound_volume(self, volume):
        """Устанавливает громкость звука"""
        try:
            self.move_sound.setVolume(volume / 100)
        except Exception:
            pass

    def return_to_start(self):
        """Обработчик нажати кнопки возврата"""
        try:
            self.start_window = StartWindow()
            self.start_window.show()
            self.close()
        except Exception as e:
            print(f"Ошибка при возврате к стартовому окну: {str(e)}")

    def restart_game(self):
        """Перезапускает игру"""
        self.board = [[0] * 8 for _ in range(8)]
        self.setup_board()
        self.current_player = 1
        self.selected_piece = None
        self.last_captured = None
        self.multiple_capture_in_progress = False
        self.game_over = False  # Сбрасываем флаг окончания игры
        self.update()

    def show_menu(self):
        """Показывает меню при нажатии на кнопку"""
        self.menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    start_window = StartWindow()
    start_window.show()
    sys.exit(app.exec())
