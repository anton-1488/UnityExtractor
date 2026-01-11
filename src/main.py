#!/usr/bin/env python3
"""
APK Extractor Pro - Извлекает все ресурсы из APK файлов
Поддержка: Unity, Android, текстуры, модели, звуки и т.д.
"""

import os
import sys
import zipfile
import shutil
import json
import subprocess
from pathlib import Path
from datetime import datetime
import UnityPy
from PIL import Image
import argparse
from tqdm import tqdm
import colorama
from colorama import Fore, Style

colorama.init()

class APKExtractor:
    def __init__(self, apk_path, output_dir=None):
        self.apk_path = Path(apk_path)
        self.output_dir = Path(output_dir or f"extracted_{self.apk_path.stem}")
        self.temp_dir = self.output_dir / "temp"

        # Создаем структуру папок
        self.create_folders()

    def create_folders(self):
        """Создает структуру папок для экспорта"""
        folders = [
            self.output_dir,
            self.temp_dir,
            self.output_dir / "models",
            self.output_dir / "textures",
            self.output_dir / "audio",
            self.output_dir / "animations",
            self.output_dir / "scripts",
            self.output_dir / "icons",
            self.output_dir / "xml",
            self.output_dir / "unity_assets",
            self.output_dir / "other",
            ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def extract_apk(self):
        """Основной метод извлечения"""
        print(f"{Fore.CYAN}🔧 APK Extractor Pro запущен{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📦 APK: {self.apk_path}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📂 Выходная папка: {self.output_dir}{Style.RESET_ALL}")

        # Шаг 1: Распаковка APK
        self.extract_apk_contents()

        # Шаг 2: Поиск Unity AssetBundle
        self.extract_unity_assets()

        # Шаг 3: Поиск текстур
        self.extract_textures()

        # Шаг 4: Поиск 3D моделей
        self.extract_models()

        # Шаг 5: Поиск звуков
        self.extract_audio()

        # Шаг 6: Поиск иконок
        self.extract_icons()

        # Шаг 7: Декомпиляция (опционально)
        self.decompile_apk()

        # Шаг 8: Создание отчета
        self.create_report()

        print(f"{Fore.GREEN}✅ Извлечение завершено!{Style.RESET_ALL}")

    def extract_apk_contents(self):
        """Распаковка APK как ZIP архива"""
        print(f"{Fore.BLUE}📁 Распаковываю APK...{Style.RESET_ALL}")

        try:
            with zipfile.ZipFile(self.apk_path, 'r') as zip_ref:
                # Получаем список файлов с прогресс-баром
                file_list = zip_ref.namelist()
                for file in tqdm(file_list, desc="Распаковка", unit="файл"):
                    try:
                        zip_ref.extract(file, self.temp_dir)
                    except:
                        pass

            print(f"{Fore.GREEN}✅ APK распакован в {self.temp_dir}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка распаковки APK: {e}{Style.RESET_ALL}")

    def extract_unity_assets(self):
        """Поиск и извлечение Unity AssetBundle"""
        print(f"{Fore.BLUE}🎮 Поиск Unity AssetBundle...{Style.RESET_ALL}")

        assetbundle_extensions = ['.assetbundle', '.bundle', '.unity3d']
        found_bundles = []

        # Ищем все AssetBundle
        for ext in assetbundle_extensions:
            for bundle_file in self.temp_dir.rglob(f"*{ext}"):
                found_bundles.append(bundle_file)

        if not found_bundles:
            print(f"{Fore.YELLOW}⚠️ AssetBundle не найдены{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}✅ Найдено AssetBundle: {len(found_bundles)}{Style.RESET_ALL}")

        for bundle_path in tqdm(found_bundles, desc="Обработка AssetBundle"):
            try:
                self.process_asset_bundle(bundle_path)
            except Exception as e:
                print(f"{Fore.RED}❌ Ошибка обработки {bundle_path.name}: {e}{Style.RESET_ALL}")

    def process_asset_bundle(self, bundle_path):
        """Обработка одного AssetBundle"""
        rel_path = bundle_path.relative_to(self.temp_dir)
        output_subdir = self.output_dir / "unity_assets" / rel_path.parent

        # Создаем папку для этого бандла
        output_subdir.mkdir(parents=True, exist_ok=True)

        try:
            # Загружаем AssetBundle
            env = UnityPy.load(str(bundle_path))

            # Сохраняем информацию о бандле
            bundle_info = {
                "name": bundle_path.name,
                "path": str(rel_path),
                "objects_count": len(env.objects),
                "objects": []
            }

            # Обрабатываем каждый объект
            for obj in env.objects:
                obj_data = {
                    "type": obj.type.name,
                    "name": "",
                    "exported": False
                }

                try:
                    data = obj.read()

                    if hasattr(data, 'name'):
                        obj_data["name"] = data.name

                    # Экспортируем в зависимости от типа
                    if obj.type.name == "Texture2D":
                        self.export_texture2d(data, output_subdir)
                        obj_data["exported"] = True

                    elif obj.type.name == "Mesh":
                        self.export_mesh(data, output_subdir)
                        obj_data["exported"] = True

                    elif obj.type.name == "Sprite":
                        self.export_sprite(data, output_subdir)
                        obj_data["exported"] = True

                    elif obj.type.name == "AudioClip":
                        self.export_audio_clip(data, output_subdir)
                        obj_data["exported"] = True

                    elif obj.type.name == "TextAsset":
                        self.export_text_asset(data, output_subdir)
                        obj_data["exported"] = True

                    elif obj.type.name == "GameObject":
                        self.export_gameobject_info(data, output_subdir)

                except Exception as e:
                    obj_data["error"] = str(e)

                bundle_info["objects"].append(obj_data)

            # Сохраняем информацию о бандле
            info_file = output_subdir / f"{bundle_path.stem}_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(bundle_info, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"{Fore.RED}❌ Не удалось загрузить {bundle_path.name}: {e}{Style.RESET_ALL}")

    def export_texture2d(self, texture_data, output_dir):
        """Экспорт текстуры"""
        try:
            # Сохраняем как PNG
            if hasattr(texture_data, 'image'):
                img = texture_data.image
                name = texture_data.name or f"texture_{hash(texture_data)}"
                img.save(output_dir / f"{name}.png")
        except:
            pass

    def export_mesh(self, mesh_data, output_dir):
        """Экспорт 3D модели"""
        try:
            name = mesh_data.name or f"mesh_{hash(mesh_data)}"
            obj_content = mesh_data.export()
            with open(output_dir / f"{name}.obj", 'w', encoding='utf-8') as f:
                f.write(obj_content)
        except:
            pass

    def export_sprite(self, sprite_data, output_dir):
        """Экспорт спрайта"""
        try:
            name = sprite_data.name or f"sprite_{hash(sprite_data)}"
            if hasattr(sprite_data, 'image'):
                sprite_data.image.save(output_dir / f"{name}.png")
        except:
            pass

    def export_audio_clip(self, audio_data, output_dir):
        """Экспорт аудио"""
        try:
            name = audio_data.name or f"audio_{hash(audio_data)}"
            # Сохраняем как WAV если возможно
            if hasattr(audio_data, 'audio_data'):
                with open(output_dir / f"{name}.wav", 'wb') as f:
                    f.write(audio_data.audio_data)
        except:
            pass

    def export_text_asset(self, text_data, output_dir):
        """Экспорт текстового файла"""
        try:
            name = text_data.name or f"text_{hash(text_data)}"
            if hasattr(text_data, 'm_Script'):
                content = text_data.m_Script
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                with open(output_dir / f"{name}.txt", 'w', encoding='utf-8') as f:
                    f.write(str(content))
        except:
            pass

    def export_gameobject_info(self, gameobject_data, output_dir):
        """Сохранение информации о GameObject"""
        try:
            name = gameobject_data.name or f"go_{hash(gameobject_data)}"
            info = {
                "name": gameobject_data.name,
                "components": []
            }

            # Сохраняем информацию о компонентах
            info_file = output_dir / f"{name}_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2)
        except:
            pass

    def extract_textures(self):
        """Поиск и извлечение текстур из всех мест"""
        print(f"{Fore.BLUE}🎨 Поиск текстур...{Style.RESET_ALL}")

        texture_extensions = ['.png', '.jpg', '.jpeg', '.tga', '.dds', '.bmp', '.tiff']
        textures_found = 0

        for ext in texture_extensions:
            for texture_file in self.temp_dir.rglob(f"*{ext}"):
                try:
                    rel_path = texture_file.relative_to(self.temp_dir)
                    dest_path = self.output_dir / "textures" / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    shutil.copy2(texture_file, dest_path)
                    textures_found += 1
                except:
                    pass

        print(f"{Fore.GREEN}✅ Найдено текстур: {textures_found}{Style.RESET_ALL}")

    def extract_models(self):
        """Поиск 3D моделей"""
        print(f"{Fore.BLUE}📐 Поиск 3D моделей...{Style.RESET_ALL}")

        model_extensions = ['.obj', '.fbx', '.dae', '.3ds', '.blend', '.max', '.mb', '.ma']
        models_found = 0

        for ext in model_extensions:
            for model_file in self.temp_dir.rglob(f"*{ext}"):
                try:
                    rel_path = model_file.relative_to(self.temp_dir)
                    dest_path = self.output_dir / "models" / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    shutil.copy2(model_file, dest_path)
                    models_found += 1
                except:
                    pass

        print(f"{Fore.GREEN}✅ Найдено моделей: {models_found}{Style.RESET_ALL}")

    def extract_audio(self):
        """Поиск аудио файлов"""
        print(f"{Fore.BLUE}🎵 Поиск аудио...{Style.RESET_ALL}")

        audio_extensions = ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a']
        audio_found = 0

        for ext in audio_extensions:
            for audio_file in self.temp_dir.rglob(f"*{ext}"):
                try:
                    rel_path = audio_file.relative_to(self.temp_dir)
                    dest_path = self.output_dir / "audio" / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    shutil.copy2(audio_file, dest_path)
                    audio_found += 1
                except:
                    pass

        print(f"{Fore.GREEN}✅ Найдено аудио файлов: {audio_found}{Style.RESET_ALL}")

    def extract_icons(self):
        """Извлечение иконок приложения"""
        print(f"{Fore.BLUE}🖼️  Поиск иконок...{Style.RESET_ALL}")

        # Ищем иконки в стандартных местах
        icon_patterns = ['*icon*', '*ic_launcher*', '*app_icon*', '*logo*']
        icons_found = 0

        for pattern in icon_patterns:
            for icon_file in self.temp_dir.rglob(f"{pattern}.png"):
                try:
                    rel_path = icon_file.relative_to(self.temp_dir)
                    dest_path = self.output_dir / "icons" / rel_path.name

                    # Пробуем открыть как изображение
                    try:
                        img = Image.open(icon_file)
                        img.save(dest_path)
                        icons_found += 1
                    except:
                        shutil.copy2(icon_file, dest_path)
                        icons_found += 1
                except:
                    pass

        print(f"{Fore.GREEN}✅ Найдено иконок: {icons_found}{Style.RESET_ALL}")

    def decompile_apk(self):
        """Декомпиляция APK с помощью apktool (опционально)"""
        print(f"{Fore.BLUE}🔍 Декомпиляция APK...{Style.RESET_ALL}")

        try:
            # Проверяем, установлен ли apktool
            result = subprocess.run(['which', 'apktool'], capture_output=True, text=True)
            if not result.stdout.strip():
                print(f"{Fore.YELLOW}⚠️ Apktool не установлен. Пропускаем декомпиляцию.{Style.RESET_ALL}")
                return

            decompile_dir = self.output_dir / "decompiled"
            decompile_dir.mkdir(exist_ok=True)

            # Запускаем apktool
            cmd = ['apktool', 'd', str(self.apk_path), '-o', str(decompile_dir), '-f']
            subprocess.run(cmd, capture_output=True)

            print(f"{Fore.GREEN}✅ APK декомпилирован в {decompile_dir}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка декомпиляции: {e}{Style.RESET_ALL}")

    def create_report(self):
        """Создание отчета о извлечении"""
        print(f"{Fore.BLUE}📊 Создание отчета...{Style.RESET_ALL}")

        report = {
            "apk_name": self.apk_path.name,
            "extraction_date": datetime.now().isoformat(),
            "output_directory": str(self.output_dir),
            "summary": {}
        }

        # Подсчет файлов по категориям
        for category in ["models", "textures", "audio", "icons", "unity_assets"]:
            category_dir = self.output_dir / category
            if category_dir.exists():
                file_count = sum(1 for _ in category_dir.rglob('*') if _.is_file())
                report["summary"][category] = file_count

        # Сохраняем отчет
        report_file = self.output_dir / "extraction_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Создаем HTML отчет для удобства
        self.create_html_report(report)

        print(f"{Fore.GREEN}✅ Отчет создан: {report_file}{Style.RESET_ALL}")

    def create_html_report(self, report):
        """Создание HTML отчета"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>APK Extractor Report - {report['apk_name']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #4CAF50; }}
                .stats {{ display: flex; flex-wrap: wrap; gap: 20px; }}
                .stat-box {{ background: #f5f5f5; padding: 15px; border-radius: 5px; min-width: 150px; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
                .file-list {{ max-height: 300px; overflow-y: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📱 APK Extractor Report</h1>
                <p>APK: {report['apk_name']}</p>
                <p>Дата: {report['extraction_date']}</p>
            </div>
            
            <div class="section">
                <h2>📊 Статистика извлечения</h2>
                <div class="stats">
        """

        for category, count in report["summary"].items():
            icon = {
                "models": "📐",
                "textures": "🎨",
                "audio": "🎵",
                "icons": "🖼️",
                "unity_assets": "🎮"
            }.get(category, "📁")

            html_content += f"""
                    <div class="stat-box">
                        <div>{icon} {category.replace('_', ' ').title()}</div>
                        <div class="stat-value">{count}</div>
                    </div>
            """

        html_content += """
                </div>
            </div>
            
            <div class="section">
                <h2>📁 Структура папок</h2>
                <pre>
        """

        # Добавляем структуру папок
        for root, dirs, files in os.walk(self.output_dir):
            level = root.replace(str(self.output_dir), '').count(os.sep)
            indent = ' ' * 4 * level
            html_content += f'{indent}{os.path.basename(root)}/\n'
            subindent = ' ' * 4 * (level + 1)
            for file in files[:10]:  # Показываем первые 10 файлов
                html_content += f'{subindent}{file}\n'

        html_content += """
                </pre>
            </div>
            
            <div class="section">
                <h2>🚀 Следующие шаги</h2>
                <ul>
                    <li>Модели находятся в папке <code>models/</code></li>
                    <li>Текстуры в <code>textures/</code></li>
                    <li>Unity AssetBundle в <code>unity_assets/</code></li>
                    <li>Используйте Blender для редактирования моделей</li>
                </ul>
            </div>
        </body>
        </html>
        """

        html_file = self.output_dir / "report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    parser = argparse.ArgumentParser(description='APK Extractor Pro - Извлекает все ресурсы из APK')
    parser.add_argument('apk_file', help='Путь к APK файлу')
    parser.add_argument('-o', '--output', help='Выходная папка (по умолчанию: extracted_имя_файла)')
    parser.add_argument('--no-decompile', action='store_true', help='Не декомпилировать APK')

    args = parser.parse_args()

    # Проверяем существование файла
    if not Path(args.apk_file).exists():
        print(f"{Fore.RED}❌ Файл не найден: {args.apk_file}{Style.RESET_ALL}")
        sys.exit(1)

    # Создаем экстрактор
    extractor = APKExtractor(args.apk_file, args.output)

    # Запускаем извлечение
    extractor.extract_apk()

    print(f"\n{Fore.CYAN}✨ Извлечение завершено!{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📂 Откройте папку: {extractor.output_dir}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📊 Отчет: {extractor.output_dir}/report.html{Style.RESET_ALL}")

if __name__ == "__main__":
    main()