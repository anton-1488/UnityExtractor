#!/usr/bin/env python3
"""
🎮 APK EXTRACTOR PRO - Извлечение 3D моделей и ресурсов из APK
Современный GUI с поддержкой Unity AssetBundle и Data файлов
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from threading import Thread

# Основные зависимости
try:
    import UnityPy
    UNITYPY_AVAILABLE = True
except ImportError:
    UNITYPY_AVAILABLE = False
    print("⚠️ UnityPy не установлен. Установите: pip install UnityPy pillow")

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("⚠️ PyQt5 не установлен. Установите: pip install PyQt5")

# Для цветного вывода в консоль
try:
    from colorama import init, Fore, Style
    init()
except:
    Fore = Style = type('obj', (object,), {'__getattr__': lambda *args: ''})()

# ============================================================================
# СТИЛИ И ТЕМЫ
# ============================================================================

DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: Arial, sans-serif;
}
QPushButton {
    background-color: #2d2d30;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
    color: #ffffff;
}
QPushButton:hover {
    background-color: #3e3e42;
    border-color: #007acc;
}
QPushButton:pressed {
    background-color: #007acc;
}
QPushButton.primary {
    background-color: #007acc;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton.primary:hover {
    background-color: #0098ff;
}
QPushButton.success {
    background-color: #107c10;
    border: none;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #252526;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}
QProgressBar {
    border: 1px solid #3e3e42;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #007acc;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 1px solid #3e3e42;
    background-color: #252526;
}
QTabBar::tab {
    background-color: #2d2d30;
    color: #cccccc;
    padding: 8px 16px;
    border: 1px solid #3e3e42;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-color: #007acc;
}
QGroupBox {
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #cccccc;
}
QListWidget {
    background-color: #252526;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    color: #ffffff;
}
QListWidget::item:selected {
    background-color: #007acc;
    color: #ffffff;
}
"""

def get_file_size(path):
    """Получить размер файла в читаемом формате"""
    size = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def sanitize_filename(name):
    """Очистка имени файла от недопустимых символов"""
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, '_')
    return name[:100] if len(name) > 100 else name

# ============================================================================
# КЛАСС APK EXTRACTOR
# ============================================================================

class APKExtractorCore:
    """Ядро для извлечения ресурсов из APK"""

    def __init__(self, apk_path, output_dir=None):
        self.apk_path = Path(apk_path)

        # Определяем папку вывода
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            apk_name = self.apk_path.stem
            self.output_dir = Path(f"extracted_{apk_name}")

        self.temp_dir = self.output_dir / "_temp"

        # Статистика
        self.stats = {
            'models': 0,
            'textures': 0,
            'assetbundles': 0,
            'data_files': 0
        }

        # Создаем папки
        self.create_folders()

    def create_folders(self):
        """Создание структуры папок"""
        folders = [
            self.output_dir,
            self.temp_dir,
            self.output_dir / "3d_models",
            self.output_dir / "textures",
            self.output_dir / "audio",
            self.output_dir / "icons",
            self.output_dir / "unity_assets",
            self.output_dir / "unity_data",
            self.output_dir / "reports"
        ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def extract_apk(self, progress_callback=None, log_callback=None):
        """Основной метод извлечения"""
        try:
            # 1. Распаковка APK
            self._log(log_callback, "📦 Начинаю распаковку APK...", "info")
            self._extract_apk_contents(progress_callback, log_callback)

            # 2. Поиск Data файлов В ПЕРВУЮ ОЧЕРЕДЬ
            self._log(log_callback, "💾 Ищу Unity Data файлы...", "info")
            self._process_unity_data_files(progress_callback, log_callback)

            # 3. Поиск AssetBundle
            self._log(log_callback, "🔍 Ищу Unity AssetBundle...", "info")
            self._extract_unity_assets(progress_callback, log_callback)

            # 4. Извлечение других ресурсов
            self._log(log_callback, "🎨 Ищу текстуры и иконки...", "info")
            self._extract_resources(log_callback)

            # 5. Создание отчетов
            self._log(log_callback, "📊 Создаю отчеты...", "info")
            self._create_reports(log_callback)

            self._log(log_callback, "✅ Извлечение завершено!", "success")
            return True

        except Exception as e:
            self._log(log_callback, f"❌ Ошибка: {str(e)}", "error")
            return False

    @staticmethod
    def _log(callback, message, level="info"):
        """Логирование с уровнями"""
        if callback:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted = f"[{timestamp}] {message}"
            callback(formatted, level)

    def _extract_apk_contents(self, progress_callback, log_callback):
        """Распаковка APK с рекурсивной распаковкой вложенных APK"""
        try:
            with zipfile.ZipFile(self.apk_path, 'r') as zip_ref:
                files = zip_ref.namelist()

                if progress_callback:
                    progress_callback(0, len(files), "Распаковка основного APK...")

                # Список для хранения вложенных APK
                nested_apks = []

                for i, file in enumerate(files):
                    try:
                        zip_ref.extract(file, self.temp_dir)

                        # Проверяем, является ли файл вложенным APK
                        file_path = self.temp_dir / file
                        if file.lower().endswith('.apk') and file_path.is_file():
                            nested_apks.append(file_path)
                            self._log(log_callback, f"📦 Найден вложенный APK: {file}", "info")

                        if progress_callback and i % 100 == 0:
                            progress_callback(i, len(files), f"Распаковка: {i}/{len(files)}")
                    except:
                        pass

                self._log(log_callback, f"✅ Распаковано {len(files)} файлов", "success")

                # Рекурсивно распаковываем вложенные APK
                if nested_apks:
                    self._log(log_callback, f"🔄 Начинаю распаковку {len(nested_apks)} вложенных APK...", "info")

                    for i, nested_apk in enumerate(nested_apks):
                        try:
                            # Создаем папку для распаковки вложенного APK
                            nested_name = nested_apk.stem
                            nested_temp_dir = self.temp_dir / f"_nested_{nested_name}"
                            nested_temp_dir.mkdir(exist_ok=True)

                            self._log(log_callback, f"  📦 Распаковка {nested_apk.name}...", "info")

                            # Распаковываем вложенный APK
                            with zipfile.ZipFile(nested_apk, 'r') as nested_zip:
                                nested_files = nested_zip.namelist()

                                for nested_file in nested_files:
                                    try:
                                        nested_zip.extract(nested_file, nested_temp_dir)
                                    except:
                                        pass

                                self._log(log_callback, f"  ✅ Распаковано {len(nested_files)} файлов из {nested_apk.name}", "success")

                            # Объединяем содержимое с основным temp_dir
                            self._merge_directories(nested_temp_dir, self.temp_dir)

                            # Удаляем временную папку
                            shutil.rmtree(nested_temp_dir, ignore_errors=True)

                        except Exception as e:
                            self._log(log_callback, f"  ⚠️ Ошибка распаковки {nested_apk.name}: {e}", "warning")
                            continue

                    self._log(log_callback, f"✅ Все вложенные APK распакованы", "success")

        except Exception as e:
            self._log(log_callback, f"❌ Ошибка распаковки: {e}", "error")
            raise

    def _merge_directories(self, src_dir, dst_dir):
        """Объединение содержимого двух директорий"""
        src_dir = Path(src_dir)
        dst_dir = Path(dst_dir)

        for item in src_dir.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(src_dir)
                dst_path = dst_dir / rel_path

                # Создаем целевую директорию если нужно
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                # Копируем файл, если его еще нет
                if not dst_path.exists():
                    shutil.copy2(item, dst_path)

    def _process_unity_data_files(self, progress_callback, log_callback):
        """Обработка Unity Data файлов - ГЛАВНЫЙ МЕТОД ДЛЯ ИЗВЛЕЧЕНИЯ МОДЕЛЕЙ"""
        try:
            # РЕКУРСИВНЫЙ ПОИСК ПАПКИ Data
            data_dirs = []
            for root, dirs, files in os.walk(self.temp_dir):
                if "Data" in dirs:
                    data_path = Path(root) / "Data"
                    if data_path.exists():
                        data_dirs.append(data_path)

            # Также ищем другие возможные пути
            possible_paths = [
                self.temp_dir / "assets" / "bin" / "Data",
                self.temp_dir / "assets" / "data",
                self.temp_dir / "data",
                self.temp_dir / "Assets" / "Data",
                self.temp_dir / "Assets" / "data",
            ]

            for path in possible_paths:
                if path.exists() and path.is_dir():
                    data_dirs.append(path)

            if not data_dirs:
                self._log(log_callback, "ℹ️ Папка Data не найдена", "info")
                return

            # Убираем дубликаты
            data_dirs = list(set(data_dirs))

            for data_dir in data_dirs:
                self._log(log_callback, f"📁 Найдена папка Data: {data_dir.relative_to(self.temp_dir)}", "info")

                # Ищем ВСЕ файлы в папке Data
                all_files = []
                for ext in ['', '.assets', '.resource', '.unity3d', '.bundle', '.dat', '.bin']:
                    all_files.extend(data_dir.rglob(f"*{ext}"))

                # Также добавляем все файлы без проверки расширения
                for file_path in data_dir.rglob('*'):
                    if file_path.is_file() and file_path not in all_files:
                        all_files.append(file_path)

                # Фильтруем: оставляем только файлы > 1KB
                files = [f for f in all_files if f.is_file() and f.stat().st_size > 1024]

                if not files:
                    self._log(log_callback, f"  ℹ️ В этой папке Data нет файлов для обработки", "info")
                    continue

                self._log(log_callback, f"  💾 Найдено {len(files)} файлов для обработки", "success")

                if progress_callback:
                    progress_callback(0, len(files), f"Обработка Data файлов...")

                total_meshes = 0
                total_textures = 0

                # Обрабатываем КАЖДЫЙ файл
                for i, file_path in enumerate(files):
                    try:
                        self._log(log_callback, f"    📄 Проверяю файл: {file_path.name} ({get_file_size(file_path)})", "info")

                        if UNITYPY_AVAILABLE:
                            meshes, textures = self._process_single_data_file(file_path, log_callback)
                            total_meshes += meshes
                            total_textures += textures
                            self.stats['data_files'] += 1
                        else:
                            # Копируем файлы если UnityPy нет
                            rel_path = file_path.relative_to(self.temp_dir)
                            dest = self.output_dir / "unity_data" / rel_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file_path, dest)

                        if progress_callback and i % 5 == 0:
                            progress_callback(i, len(files), f"Data файл: {file_path.name}")

                        # Небольшая задержка чтобы не грузить систему
                        import time
                        time.sleep(0.01)

                    except Exception as e:
                        error_msg = str(e)
                        if "cannot unpack" in error_msg or "invalid" in error_msg:
                            # Это не Unity файл, пропускаем
                            pass
                        else:
                            self._log(log_callback, f"    ⚠️ Ошибка {file_path.name}: {e}", "warning")
                        continue

                self.stats['models'] += total_meshes
                self.stats['textures'] += total_textures

                if total_meshes > 0 or total_textures > 0:
                    self._log(log_callback, f"  ✅ Из этой папки Data: {total_meshes} мешей, {total_textures} текстур", "success")

            if self.stats['data_files'] == 0:
                self._log(log_callback, "ℹ️ Не удалось обработать ни одного Data файла", "info")

        except Exception as e:
            self._log(log_callback, f"❌ Ошибка обработки Data файлов: {e}", "error")

    def _process_single_data_file(self, file_path, log_callback):
        """Обработка одного Data файла"""
        meshes = 0
        textures = 0

        try:
            # Пробуем загрузить файл через UnityPy
            env = UnityPy.load(str(file_path))

            if not env.objects:
                return 0, 0

            # Создаем папку для этого файла
            rel_path = file_path.relative_to(self.temp_dir)
            output_dir = self.output_dir / "unity_data" / file_path.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            # Собираем статистику по типам
            object_types = {}
            for obj in env.objects:
                obj_type = obj.type.name
                object_types[obj_type] = object_types.get(obj_type, 0) + 1

            # Записываем информацию о типах
            self._log(log_callback, f"    📊 Типы объектов в {file_path.name}:", "info")
            for obj_type, count in object_types.items():
                self._log(log_callback, f"      • {obj_type}: {count}", "info")

            # Обрабатываем только Mesh и Texture2D
            for obj in env.objects:
                try:
                    data = obj.read()

                    # МЕШИ
                    if obj.type.name == "Mesh":
                        try:
                            obj_content = data.export()
                            if obj_content:
                                mesh_name = getattr(data, 'name', f'mesh_{obj.path_id}')
                                mesh_name = sanitize_filename(mesh_name)
                                mesh_path = output_dir / "meshes" / f"{mesh_name}.obj"
                                mesh_path.parent.mkdir(exist_ok=True)

                                with open(mesh_path, 'w', encoding='utf-8') as f:
                                    f.write(obj_content)
                                meshes += 1

                                if meshes == 1:
                                    self._log(log_callback, f"    📐 Найден первый меш!", "success")
                        except Exception as e:
                            # Пробуем альтернативный способ
                            pass

                    # ТЕКСТУРЫ
                    elif obj.type.name == "Texture2D" and PILLOW_AVAILABLE:
                        try:
                            if hasattr(data, 'image'):
                                texture_name = getattr(data, 'name', f'texture_{obj.path_id}')
                                texture_name = sanitize_filename(texture_name)
                                tex_path = output_dir / "textures" / f"{texture_name}.png"
                                tex_path.parent.mkdir(exist_ok=True)

                                data.image.save(tex_path)
                                textures += 1
                        except:
                            pass

                except Exception as e:
                    continue

            # Сохраняем статистику
            if meshes > 0 or textures > 0:
                stats = {
                    'file': file_path.name,
                    'size': get_file_size(file_path),
                    'total_objects': len(env.objects),
                    'object_types': object_types,
                    'meshes': meshes,
                    'textures': textures
                }

                stats_path = output_dir / "info.json"
                with open(stats_path, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2)

                self._log(log_callback, f"    ✅ Сохранено: {meshes} мешей, {textures} текстур", "success")

            return meshes, textures

        except Exception as e:
            # Если ошибка при загрузке UnityPy, это не Unity файл
            raise Exception(f"Не Unity файл: {e}")

    def _extract_unity_assets(self, progress_callback, log_callback):
        """Поиск и обработка AssetBundle"""
        try:
            # Ищем AssetBundle
            bundle_exts = ['.assetbundle', '.bundle', '.unity3d']
            bundles = []

            for ext in bundle_exts:
                bundles.extend(self.temp_dir.rglob(f"*{ext}"))

            self.stats['assetbundles'] = len(bundles)

            if not bundles:
                self._log(log_callback, "ℹ️ AssetBundle не найдены", "info")
                return

            self._log(log_callback, f"🎮 Найдено {len(bundles)} AssetBundle", "success")

            if progress_callback:
                progress_callback(0, len(bundles), "Обработка AssetBundle...")

            # Обрабатываем каждый AssetBundle
            for i, bundle in enumerate(bundles):
                try:
                    if UNITYPY_AVAILABLE:
                        self._process_asset_bundle(bundle, log_callback)
                    else:
                        # Просто копируем если UnityPy нет
                        rel_path = bundle.relative_to(self.temp_dir)
                        dest = self.output_dir / "unity_assets" / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(bundle, dest)

                    if progress_callback:
                        progress_callback(i, len(bundles), f"AssetBundle: {bundle.name}")

                except Exception as e:
                    self._log(log_callback, f"⚠️ Ошибка обработки {bundle.name}: {e}", "warning")

        except Exception as e:
            self._log(log_callback, f"❌ Ошибка поиска AssetBundle: {e}", "error")

    def _process_asset_bundle(self, bundle_path, log_callback):
        """Обработка одного AssetBundle"""
        try:
            env = UnityPy.load(str(bundle_path))

            # Создаем папку для этого бандла
            rel_path = bundle_path.relative_to(self.temp_dir)
            output_dir = self.output_dir / "unity_assets" / rel_path.parent / bundle_path.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            meshes = 0
            textures = 0

            # Обрабатываем объекты
            for obj in env.objects:
                try:
                    data = obj.read()

                    # Меши
                    if obj.type.name == "Mesh":
                        try:
                            obj_content = data.export()
                            if obj_content:
                                name = sanitize_filename(getattr(data, 'name', f'mesh_{obj.path_id}'))
                                mesh_path = output_dir / "meshes" / f"{name}.obj"
                                mesh_path.parent.mkdir(exist_ok=True)

                                with open(mesh_path, 'w', encoding='utf-8') as f:
                                    f.write(obj_content)
                                meshes += 1
                        except:
                            pass

                    # Текстуры
                    elif obj.type.name == "Texture2D":
                        try:
                            if hasattr(data, 'image') and PILLOW_AVAILABLE:
                                name = sanitize_filename(getattr(data, 'name', f'texture_{obj.path_id}'))
                                tex_path = output_dir / "textures" / f"{name}.png"
                                tex_path.parent.mkdir(exist_ok=True)

                                data.image.save(tex_path)
                                textures += 1
                        except:
                            pass

                except:
                    continue

            self.stats['models'] += meshes
            self.stats['textures'] += textures

            if meshes > 0 or textures > 0:
                self._log(log_callback, f"  📁 {bundle_path.name}: {meshes} мешей, {textures} текстур", "info")

        except Exception as e:
            raise Exception(f"Ошибка обработки AssetBundle: {e}")

    def _extract_resources(self, log_callback):
        """Извлечение других ресурсов"""
        try:
            # Текстуры
            texture_exts = ['.png', '.jpg', '.jpeg', '.tga']
            for ext in texture_exts:
                for tex in self.temp_dir.rglob(f"*{ext}"):
                    try:
                        rel_path = tex.relative_to(self.temp_dir)
                        dest = self.output_dir / "textures" / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(tex, dest)
                    except:
                        pass

            # Иконки
            icon_patterns = ['*icon*', '*launcher*', '*logo*']
            for pattern in icon_patterns:
                for icon in self.temp_dir.rglob(f"{pattern}.png"):
                    try:
                        name = icon.name
                        dest = self.output_dir / "icons" / name
                        shutil.copy2(icon, dest)
                    except:
                        pass

            # Аудио
            audio_exts = ['.mp3', '.wav', '.ogg']
            for ext in audio_exts:
                for audio in self.temp_dir.rglob(f"*{ext}"):
                    try:
                        rel_path = audio.relative_to(self.temp_dir)
                        dest = self.output_dir / "audio" / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(audio, dest)
                    except:
                        pass

            self._log(log_callback, "✅ Ресурсы извлечены", "success")

        except Exception as e:
            self._log(log_callback, f"❌ Ошибка извлечения ресурсов: {e}", "error")

    def _create_reports(self, log_callback):
        """Создание отчетов"""
        try:
            # JSON отчет
            report = {
                'apk': str(self.apk_path.name),
                'date': datetime.now().isoformat(),
                'output_dir': str(self.output_dir),
                'statistics': self.stats,
                'files': {
                    'models': len(list((self.output_dir / "3d_models").rglob("*.obj"))),
                    'textures': len(list((self.output_dir / "textures").rglob("*.*"))),
                    'icons': len(list((self.output_dir / "icons").rglob("*.*"))),
                    'audio': len(list((self.output_dir / "audio").rglob("*.*"))),
                }
            }

            # Сохраняем JSON
            json_path = self.output_dir / "reports" / "extraction_report.json"
            json_path.parent.mkdir(exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            # HTML отчет
            self._create_html_report(report)

            self._log(log_callback, f"📄 Отчеты сохранены в {self.output_dir}/reports/", "info")

        except Exception as e:
            self._log(log_callback, f"❌ Ошибка создания отчетов: {e}", "error")

    def _create_html_report(self, report):
        """Создание HTML отчета"""
        try:
            html = f"""
            <!DOCTYPE html>
            <html lang="ru">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>APK Extractor Report - {report['apk']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; background: #1e1e1e; color: white; padding: 20px; }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .header {{ text-align: center; padding: 40px; }}
                    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 40px 0; }}
                    .stat-card {{ background: #252526; padding: 20px; border-radius: 10px; text-align: center; }}
                    .stat-value {{ font-size: 2em; font-weight: bold; color: #007acc; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📱 APK Extractor Report</h1>
                        <h3>{report['apk']}</h3>
                    </div>
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-value">{report['statistics']['models']}</div>
                            <div>3D Models</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{report['statistics']['textures']}</div>
                            <div>Textures</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{report['statistics']['assetbundles']}</div>
                            <div>AssetBundles</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{report['statistics']['data_files']}</div>
                            <div>Data Files</div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            html_path = self.output_dir / "reports" / "report.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

        except Exception as e:
            raise Exception(f"Ошибка создания HTML отчета: {e}")

# ============================================================================
# ПОТОК ДЛЯ ИЗВЛЕЧЕНИЯ
# ============================================================================

class ExtractionThread(QThread):
    """Поток для выполнения извлечения"""

    progress_updated = pyqtSignal(int, int, str)
    log_message = pyqtSignal(str, str)
    extraction_finished = pyqtSignal(dict)
    extraction_error = pyqtSignal(str)

    def __init__(self, apk_path, output_dir):
        super().__init__()
        self.apk_path = apk_path
        self.output_dir = output_dir
        self.extractor = None

    def run(self):
        try:
            self.log_message.emit(f"🚀 Начинаю извлечение из: {os.path.basename(self.apk_path)}", "info")

            # Создаем экстрактор
            self.extractor = APKExtractorCore(self.apk_path, self.output_dir)

            # Запускаем извлечение
            success = self.extractor.extract_apk(
                progress_callback=self._progress_callback,
                log_callback=self._log_callback
            )

            if success:
                results = {
                    'success': True,
                    'output_dir': str(self.extractor.output_dir),
                    'stats': self.extractor.stats
                }
                self.extraction_finished.emit(results)
            else:
                self.extraction_error.emit("Извлечение завершилось с ошибками")

        except Exception as e:
            self.extraction_error.emit(f"Критическая ошибка: {str(e)}")

    def _progress_callback(self, current, total, message):
        self.progress_updated.emit(current, total, message)

    def _log_callback(self, message, level="info"):
        self.log_message.emit(message, level)

# ============================================================================
# ГЛАВНОЕ ОКНО (СОХРАНИТЬ БЕЗ ИЗМЕНЕНИЙ)
# ============================================================================

class APKExtractorGUI(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        # Проверяем зависимости
        self._check_dependencies()

        # Настройка окна
        self.setWindowTitle("🎮 APK Extractor Pro")
        self.setGeometry(100, 100, 1200, 800)

        # Устанавливаем стиль
        self.setStyleSheet(DARK_THEME)

        # Инициализация переменных
        self.apk_path = None
        self.output_dir = None
        self.extraction_thread = None

        # Создаем UI
        self._init_ui()

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

    def _check_dependencies(self):
        """Проверка зависимостей"""
        if not UNITYPY_AVAILABLE:
            QMessageBox.warning(
                self, "Внимание",
                "UnityPy не установлен. 3D модели не будут извлекаться.\n"
                "Установите: pip install UnityPy pillow"
            )

        if not PILLOW_AVAILABLE:
            QMessageBox.warning(
                self, "Внимание",
                "Pillow не установлен. Текстуры не будут сохраняться.\n"
                "Установите: pip install pillow"
            )

    def _init_ui(self):
        """Инициализация интерфейса"""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Шапка
        self._create_header(main_layout)

        # Основная область с вкладками
        self.tab_widget = QTabWidget()
        self._create_extract_tab()
        self._create_logs_tab()
        self._create_results_tab()

        main_layout.addWidget(self.tab_widget)

        # Статусная панель
        self._create_status_panel(main_layout)

    @staticmethod
    def _create_header(layout):
        """Создание шапки"""
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🎮 APK Extractor Pro")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #ffffff; padding: 10px 0;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Извлечение 3D моделей, текстур и ресурсов из APK файлов")
        subtitle.setStyleSheet("font-size: 14px; color: #cccccc; padding-bottom: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

    def _create_extract_tab(self):
        """Создание вкладки извлечения"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Карточка выбора APK
        apk_card = self._create_card("📦 Выбор APK файла")
        apk_layout = QVBoxLayout(apk_card)

        apk_path_layout = QHBoxLayout()
        self.apk_path_label = QLabel("Файл не выбран")
        self.apk_path_label.setStyleSheet("""
            QLabel {
                padding: 12px;
                border: 2px dashed #3e3e42;
                border-radius: 8px;
                background: #252526;
                min-height: 40px;
                font-size: 13px;
            }
        """)
        self.apk_path_label.setWordWrap(True)

        apk_buttons = QHBoxLayout()
        self.select_apk_btn = QPushButton("Выбрать APK...")
        self.select_apk_btn.setObjectName("primary")
        self.select_apk_btn.clicked.connect(self._select_apk)

        self.clear_apk_btn = QPushButton("Очистить")
        self.clear_apk_btn.clicked.connect(self._clear_apk)
        self.clear_apk_btn.setEnabled(False)

        apk_buttons.addWidget(self.select_apk_btn)
        apk_buttons.addWidget(self.clear_apk_btn)
        apk_buttons.addStretch()

        apk_path_layout.addWidget(self.apk_path_label, 1)
        apk_layout.addLayout(apk_path_layout)
        apk_layout.addLayout(apk_buttons)

        layout.addWidget(apk_card)

        # Карточка настроек
        settings_card = self._create_card("⚙️ Настройки извлечения")
        settings_layout = QVBoxLayout(settings_card)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Папка вывода:"))

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Будет создана автоматически")

        self.browse_output_btn = QPushButton("Обзор...")
        self.browse_output_btn.clicked.connect(self._select_output_dir)

        output_layout.addWidget(self.output_path_edit, 1)
        output_layout.addWidget(self.browse_output_btn)
        settings_layout.addLayout(output_layout)

        layout.addWidget(settings_card)

        # Прогресс
        progress_card = self._create_card("📊 Прогресс")
        progress_layout = QVBoxLayout(progress_card)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #cccccc;")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        layout.addWidget(progress_card)

        # Кнопки управления
        buttons_card = QWidget()
        buttons_layout = QHBoxLayout(buttons_card)

        self.extract_btn = QPushButton("🚀 Начать извлечение")
        self.extract_btn.setObjectName("primary")
        self.extract_btn.clicked.connect(self._start_extraction)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setMinimumHeight(45)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self._cancel_extraction)
        self.cancel_btn.setEnabled(False)

        self.open_results_btn = QPushButton("📂 Открыть результаты")
        self.open_results_btn.setObjectName("success")
        self.open_results_btn.clicked.connect(self._open_results)
        self.open_results_btn.setEnabled(False)

        buttons_layout.addWidget(self.extract_btn)
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.open_results_btn)
        buttons_layout.addStretch()

        layout.addWidget(buttons_card)
        layout.addStretch()

        self.tab_widget.addTab(tab, "📦 Извлечение")

    def _create_logs_tab(self):
        """Создание вкладки логов"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        logs_header = QWidget()
        logs_header_layout = QHBoxLayout(logs_header)
        logs_header_layout.setContentsMargins(0, 0, 0, 0)

        logs_title = QLabel("📝 Логи выполнения")
        logs_title.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.clear_logs_btn = QPushButton("Очистить логи")
        self.clear_logs_btn.clicked.connect(self._clear_logs)

        self.save_logs_btn = QPushButton("Сохранить логи")
        self.save_logs_btn.clicked.connect(self._save_logs)

        logs_header_layout.addWidget(logs_title)
        logs_header_layout.addStretch()
        logs_header_layout.addWidget(self.clear_logs_btn)
        logs_header_layout.addWidget(self.save_logs_btn)

        layout.addWidget(logs_header)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout.addWidget(self.logs_text)
        self.tab_widget.addTab(tab, "📝 Логи")

    def _create_results_tab(self):
        """Создание вкладки результатов"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        results_title = QLabel("📊 История извлечений")
        results_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(results_title)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._open_result_folder)
        layout.addWidget(self.results_list, 1)

        results_buttons = QHBoxLayout()

        self.refresh_results_btn = QPushButton("🔄 Обновить")
        self.refresh_results_btn.clicked.connect(self._refresh_results)

        self.open_selected_btn = QPushButton("📂 Открыть выбранное")
        self.open_selected_btn.clicked.connect(self._open_selected_result)

        self.delete_selected_btn = QPushButton("🗑️ Удалить выбранное")
        self.delete_selected_btn.clicked.connect(self._delete_selected_result)
        self.delete_selected_btn.setStyleSheet("background-color: #f0ad4e;")

        results_buttons.addWidget(self.refresh_results_btn)
        results_buttons.addWidget(self.open_selected_btn)
        results_buttons.addWidget(self.delete_selected_btn)
        results_buttons.addStretch()

        layout.addLayout(results_buttons)

        self.tab_widget.addTab(tab, "📊 Результаты")
        self._refresh_results()

    def _create_status_panel(self, layout):
        """Создание статусной панели"""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("color: #cccccc; font-style: italic;")

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #4CAF50; font-weight: bold;")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.stats_label)

        layout.addWidget(status_widget)

    @staticmethod
    def _create_card(title):
        """Создание карточки с заголовком"""
        card = QGroupBox(title)
        card.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3e3e42;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 10px;
                background-color: #1e1e1e;
            }
        """)
        return card

    def _select_apk(self):
        """Выбор APK файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите APK файл",
            os.path.expanduser("~/Downloads"),
            "APK Files (*.apk);;All Files (*)"
        )

        if file_path:
            self.apk_path = file_path
            self.apk_path_label.setText(f"📦 {os.path.basename(file_path)}")
            self.clear_apk_btn.setEnabled(True)

            apk_name = os.path.splitext(os.path.basename(file_path))[0]
            self.output_path_edit.setText(f"extracted_{apk_name}")

            self.extract_btn.setEnabled(True)
            self._add_log(f"✅ Выбран файл: {file_path}", "success")

    def _clear_apk(self):
        """Очистка выбранного APK"""
        self.apk_path = None
        self.apk_path_label.setText("Файл не выбран")
        self.clear_apk_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.output_path_edit.clear()
        self._add_log("🗑️ Файл очищен", "info")

    def _select_output_dir(self):
        """Выбор папки вывода"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Выберите папку для извлечения",
            os.path.dirname(self.apk_path) if self.apk_path else os.path.expanduser("~")
        )

        if dir_path:
            self.output_path_edit.setText(dir_path)
            self._add_log(f"📁 Папка вывода: {dir_path}", "info")

    def _start_extraction(self):
        """Начало извлечения"""
        if not self.apk_path:
            self._show_error("Ошибка", "Выберите APK файл!")
            return

        output_dir = self.output_path_edit.text().strip()
        if not output_dir:
            apk_name = os.path.splitext(os.path.basename(self.apk_path))[0]
            output_dir = f"extracted_{apk_name}"
            self.output_path_edit.setText(output_dir)

        if os.path.exists(output_dir):
            reply = QMessageBox.question(
                self, "Подтверждение",
                f'Папка "{output_dir}" уже существует. Перезаписать?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Подготовка...")

        self.logs_text.clear()
        self._add_log("=" * 60, "info")
        self._add_log("🚀 ЗАПУСК ИЗВЛЕЧЕНИЯ", "info")
        self._add_log("=" * 60, "info")

        self.extraction_thread = ExtractionThread(self.apk_path, output_dir)
        self.extraction_thread.progress_updated.connect(self._update_progress)
        self.extraction_thread.log_message.connect(self._add_log)
        self.extraction_thread.extraction_finished.connect(self._extraction_completed)
        self.extraction_thread.extraction_error.connect(self._extraction_error)
        self.extraction_thread.start()

    def _update_progress(self, current, total, message):
        """Обновление прогресса"""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
        self.status_label.setText(message)

    def _add_log(self, message, level="info"):
        """Добавление записи в лог"""
        import re
        clean_message = re.sub(r'\x1b\[[0-9;]*[mK]', '', message)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {clean_message}"

        colors = {
            "info": "#cccccc",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336"
        }

        color = colors.get(level, "#cccccc")

        self.logs_text.moveCursor(QTextCursor.End)
        self.logs_text.insertHtml(f'<span style="color: {color};">{log_entry}</span><br>')
        self.logs_text.moveCursor(QTextCursor.End)

    def _extraction_completed(self, results):
        """Извлечение завершено"""
        self._add_log("=" * 60, "info")
        self._add_log("✅ ИЗВЛЕЧЕНИЕ ЗАВЕРШЕНО!", "success")
        self._add_log("=" * 60, "info")

        stats = results['stats']
        self._add_log(f"📁 Папка с результатами: {results['output_dir']}", "info")
        self._add_log(f"📐 Найдено 3D моделей: {stats['models']}", "success")
        self._add_log(f"🎨 Найдено текстур: {stats['textures']}", "success")
        self._add_log(f"📦 Найдено AssetBundle: {stats['assetbundles']}", "info")
        self._add_log(f"💾 Обработано Data файлов: {stats['data_files']}", "info")

        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.open_results_btn.setEnabled(True)

        self.stats_label.setText(f"📊 {stats['models']} моделей, {stats['textures']} текстур")
        self._refresh_results()
        self.tab_widget.setCurrentIndex(1)

        self._show_success(
            "Извлечение завершено!",
            f"• 3D моделей: {stats['models']}\n"
            f"• Текстур: {stats['textures']}\n"
            f"• AssetBundle: {stats['assetbundles']}\n"
            f"• Data файлов: {stats['data_files']}\n\n"
            f"Результаты сохранены в:\n{results['output_dir']}"
        )

        self.status_label.setText("Готов к работе")

    def _extraction_error(self, error_message):
        """Ошибка при извлечении"""
        self._add_log(f"❌ ОШИБКА: {error_message}", "error")
        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._show_error("Ошибка", f"Ошибка при извлечении:\n{error_message}")
        self.status_label.setText("Ошибка при извлечении")

    def _cancel_extraction(self):
        """Отмена извлечения"""
        if self.extraction_thread and self.extraction_thread.isRunning():
            self.extraction_thread.terminate()
            self.extraction_thread.wait()
            self._add_log("⚠️ Извлечение отменено пользователем", "warning")
            self._set_ui_enabled(True)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.status_label.setText("Извлечение отменено")

    def _open_results(self):
        """Открытие папки с результатами"""
        output_dir = self.output_path_edit.text()
        if output_dir and os.path.exists(output_dir):
            self._open_folder(output_dir)
        else:
            self._show_warning("Предупреждение", "Папка результатов не найдена")

    def _refresh_results(self):
        """Обновление списка результатов"""
        self.results_list.clear()
        current_dir = os.getcwd()

        for item in os.listdir(current_dir):
            if item.startswith('extracted_') and os.path.isdir(item):
                report_file = os.path.join(item, 'reports', 'extraction_report.json')
                if os.path.exists(report_file):
                    try:
                        with open(report_file, 'r', encoding='utf-8') as f:
                            report = json.load(f)
                            stats = report.get('statistics', {})
                            models = stats.get('models', 0)
                            textures = stats.get('textures', 0)
                            date_str = report.get('date', '')[:10] if report.get('date') else 'N/A'

                            item_text = f"📁 {item}\n📐 {models} моделей | 🎨 {textures} текстур | 📅 {date_str}"
                    except:
                        item_text = f"📁 {item}"
                else:
                    item_text = f"📁 {item}"

                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, item)
                self.results_list.addItem(list_item)

    def _open_selected_result(self):
        """Открытие выбранного результата"""
        selected = self.results_list.selectedItems()
        if selected:
            folder = selected[0].data(Qt.UserRole)
            self._open_folder(folder)

    def _open_result_folder(self, item):
        """Открытие результата по двойному клику"""
        folder = item.data(Qt.UserRole)
        self._open_folder(folder)

    def _delete_selected_result(self):
        """Удаление выбранного результата"""
        selected = self.results_list.selectedItems()
        if not selected:
            return

        folder = selected[0].data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f'Удалить папку "{folder}" и все её содержимое?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(folder)
                self._add_log(f"🗑️ Удалена папка: {folder}", "info")
                self._refresh_results()
            except Exception as e:
                self._show_error("Ошибка", f"Не удалось удалить папку:\n{e}")

    def _clear_logs(self):
        """Очистка логов"""
        self.logs_text.clear()

    def _save_logs(self):
        """Сохранение логов в файл"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить логи",
            f"apk_extractor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.logs_text.toPlainText())
                self._add_log(f"💾 Логи сохранены: {file_path}", "success")
            except Exception as e:
                self._show_error("Ошибка", f"Не удалось сохранить логи:\n{e}")

    def _set_ui_enabled(self, enabled):
        """Блокировка/разблокировка UI"""
        self.select_apk_btn.setEnabled(enabled)
        self.clear_apk_btn.setEnabled(enabled and self.apk_path is not None)
        self.browse_output_btn.setEnabled(enabled)
        self.extract_btn.setEnabled(enabled and self.apk_path is not None)
        self.cancel_btn.setEnabled(not enabled)
        self.output_path_edit.setEnabled(enabled)

    def _open_folder(self, path):
        """Открытие папки в файловом менеджере"""
        if os.path.exists(path):
            if sys.platform == 'darwin':
                subprocess.run(['open', path])
            elif sys.platform == 'win32':
                os.startfile(path)
            else:
                subprocess.run(['xdg-open', path])
        else:
            self._show_warning("Предупреждение", f"Папка не найдена:\n{path}")

    def _show_error(self, title, message):
        """Показать ошибку"""
        QMessageBox.critical(self, title, message)

    def _show_warning(self, title, message):
        """Показать предупреждение"""
        QMessageBox.warning(self, title, message)

    @staticmethod
    def _show_success(title, message):
        """Показать успешное сообщение"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

# ============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================================

def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)
    app.setApplicationName("APK Extractor Pro")
    app.setApplicationVersion("1.0.0")

    if not PYQT_AVAILABLE:
        print("❌ PyQt5 не установлен!")
        print("💡 Установите: pip install PyQt5")
        sys.exit(1)

    window = APKExtractorGUI()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()