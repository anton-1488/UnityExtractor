#!/usr/bin/env python3
"""
Графический интерфейс для APK Extractor
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QTextEdit, QProgressBar, QListWidget, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from apk_extractor import APKExtractor

class ExtractionThread(QThread):
    """Поток для извлечения"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, apk_path, output_dir):
        super().__init__()
        self.apk_path = apk_path
        self.output_dir = output_dir

    def run(self):
        try:
            extractor = APKExtractor(self.apk_path, self.output_dir)
            extractor.extract_apk()
            self.finished.emit(self.output_dir)
        except Exception as e:
            self.error.emit(str(e))

class APKExtractorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('APK Extractor Pro')
        self.setGeometry(100, 100, 800, 600)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel('APK Extractor Pro')
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Описание
        desc = QLabel('Извлеките все ресурсы из APK файлов')
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # Выбор файла
        file_layout = QHBoxLayout()
        self.file_label = QLabel('Файл не выбран')
        self.file_label.setStyleSheet('padding: 5px; border: 1px solid #ccc;')
        file_btn = QPushButton('Выбрать APK...')
        file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(file_btn)
        layout.addLayout(file_layout)

        # Выбор папки вывода
        output_layout = QHBoxLayout()
        self.output_label = QLabel('Папка вывода: extracted_...')
        self.output_label.setStyleSheet('padding: 5px; border: 1px solid #ccc;')
        output_btn = QPushButton('Изменить...')
        output_btn.clicked.connect(self.select_output)
        output_layout.addWidget(self.output_label, 1)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Кнопки
        button_layout = QHBoxLayout()
        self.extract_btn = QPushButton('Начать извлечение')
        self.extract_btn.clicked.connect(self.start_extraction)
        self.extract_btn.setEnabled(False)

        self.open_btn = QPushButton('Открыть папку')
        self.open_btn.clicked.connect(self.open_output)
        self.open_btn.setEnabled(False)

        exit_btn = QPushButton('Выход')
        exit_btn.clicked.connect(self.close)

        button_layout.addWidget(self.extract_btn)
        button_layout.addWidget(self.open_btn)
        button_layout.addWidget(exit_btn)
        layout.addLayout(button_layout)

        central_widget.setLayout(layout)

        # Переменные
        self.apk_path = None
        self.output_dir = None
        self.thread = None

    def select_file(self):
        """Выбор APK файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Выберите APK файл',
            os.path.expanduser('~/Downloads'),
            'APK Files (*.apk)'
        )

        if file_path:
            self.apk_path = file_path
            self.file_label.setText(os.path.basename(file_path))

            # Автоматически создаем папку вывода
            self.output_dir = f"extracted_{os.path.splitext(os.path.basename(file_path))[0]}"
            self.output_label.setText(f"Папка вывода: {self.output_dir}")

            self.extract_btn.setEnabled(True)
            self.log_text.append(f"📦 Выбран файл: {file_path}")

    def select_output(self):
        """Выбор папки вывода"""
        if not self.apk_path:
            return

        dir_path = QFileDialog.getExistingDirectory(
            self, 'Выберите папку для извлечения',
            os.path.dirname(self.apk_path)
        )

        if dir_path:
            self.output_dir = dir_path
            self.output_label.setText(f"Папка вывода: {dir_path}")

    def start_extraction(self):
        """Начать извлечение"""
        if not self.apk_path:
            return

        # Блокируем кнопки
        self.extract_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс

        # Запускаем поток
        self.thread = ExtractionThread(self.apk_path, self.output_dir)
        self.thread.progress.connect(self.update_log)
        self.thread.finished.connect(self.extraction_finished)
        self.thread.error.connect(self.extraction_error)
        self.thread.start()

    def update_log(self, message):
        """Обновление лога"""
        self.log_text.append(message)

    def extraction_finished(self, output_dir):
        """Извлечение завершено"""
        self.progress_bar.setVisible(False)
        self.open_btn.setEnabled(True)
        self.extract_btn.setText('Извлечь снова')
        self.extract_btn.setEnabled(True)

        self.log_text.append(f"\n✅ Извлечение завершено!")
        self.log_text.append(f"📂 Папка: {output_dir}")

        QMessageBox.information(self, 'Готово',
                                f'Извлечение завершено!\nПапка: {output_dir}')

    def extraction_error(self, error_message):
        """Ошибка извлечения"""
        self.progress_bar.setVisible(False)
        self.extract_btn.setEnabled(True)

        self.log_text.append(f"\n❌ Ошибка: {error_message}")
        QMessageBox.critical(self, 'Ошибка', f'Ошибка извлечения:\n{error_message}')

    def open_output(self):
        """Открыть папку с результатами"""
        if self.output_dir and os.path.exists(self.output_dir):
            if sys.platform == 'darwin':  # macOS
                os.system(f'open "{self.output_dir}"')
            elif sys.platform == 'win32':  # Windows
                os.system(f'explorer "{self.output_dir}"')
            else:  # Linux
                os.system(f'xdg-open "{self.output_dir}"')

def main():
    app = QApplication(sys.argv)
    window = APKExtractorGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()