#!/bin/bash
# install.sh - Установка APK Extractor Pro

echo "🚀 Установка APK Extractor Pro..."

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен!"
    echo "Установите Python3: brew install python@3.9"
    exit 1
fi

# Создаем виртуальное окружение (опционально)
echo "📦 Создаю виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
echo "📥 Устанавливаю зависимости..."
pip install --upgrade pip
pip install UnityPy pillow
pip install PyQt5
pip install tqdm colorama

echo "✅ Зависимости установлены!"

# Делаем скрипты исполняемыми
chmod +x apk_extractor.py
chmod +x gui.py
chmod +x install.sh

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "Использование:"
echo "  Консольная версия: python3 apk_extractor.py ваш_файл.apk"
echo "  Графическая версия: python3 gui.py"
echo ""
echo "Для извлечения всех ресурсов из APK:"
echo "  python3 apk_extractor.py путь/к/файлу.apk -o папка_для_результатов"