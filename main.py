"""Точка входа DocForge — тонкий лаунчер (запускается из DocForge.bat)."""
import os
import sys
import warnings

# pydub предупреждает об отсутствии ffmpeg в PATH при импорте — до того,
# как мы укажем ему путь. Предупреждение ложное. Глушим до импорта пакета.
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

# Форсируем UTF-8 до любых тяжёлых импортов
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from docforge.app import main

if __name__ == "__main__":
    main()
