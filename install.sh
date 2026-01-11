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

chmod +x main.py
chmod +x build.sh

echo ""
echo "🎉 Установка завершена!"