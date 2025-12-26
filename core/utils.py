from pathlib import Path
from typing import List

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".aiff", ".aif"}

def is_audio_file(path: str) -> bool:
    """Проверяет, является ли файл аудиофайлом с допустимым расширением."""
    p = Path(path)
    return p.is_file() and p.suffix.lower() in AUDIO_EXTS

def find_audio_files(folder: str) -> List[str]:
    """
    Находит все аудиофайлы в указанной папке (без рекурсии).
    """
    root = Path(folder)
    if not root.is_dir():
        return []

    files: List[str] = []
    try:
        for entry in root.iterdir():
            if entry.is_file() and entry.suffix.lower() in AUDIO_EXTS:
                files.append(str(entry))
    except PermissionError:
        print(f"Ошибка доступа к папке {folder}.")
    except Exception as e:
        print(f"Неизвестная ошибка при чтении папки: {e}")

    return sorted(files)
