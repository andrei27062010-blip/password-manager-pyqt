import os
import shutil
import sys
from pathlib import Path


def _copy_legacy_data(source_dir: Path, target_dir: Path) -> None:
    """Копирует старые файлы хранилища, не перезаписывая существующие."""
    for filename in ("master_config.json", "passwords.db"):
        source = source_dir / filename
        target = target_dir / filename
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)

        if filename == "passwords.db" and source.is_file():
            for suffix in ("-wal", "-shm"):
                source_sidecar = Path(str(source) + suffix)
                target_sidecar = Path(str(target) + suffix)
                if source_sidecar.is_file() and not target_sidecar.exists():
                    shutil.copy2(source_sidecar, target_sidecar)


def get_data_directory() -> Path:
    """Возвращает каталог данных приложения."""
    if not getattr(sys, "frozen", False):
        return Path.cwd()

    appdata = os.environ.get("APPDATA")
    roaming_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    data_dir = roaming_dir / "PasswordManager"
    data_dir.mkdir(parents=True, exist_ok=True)

    # При первом запуске переносим прежнее хранилище из каталога запуска
    # или рядом с EXE. Исходные файлы остаются на месте.
    if not (data_dir / "master_config.json").exists() and not (data_dir / "passwords.db").exists():
        candidates = (Path.cwd(), Path(sys.executable).resolve().parent)
        for candidate in candidates:
            try:
                if candidate.resolve() == data_dir.resolve():
                    continue
            except OSError:
                continue

            if any((candidate / name).is_file() for name in ("master_config.json", "passwords.db")):
                _copy_legacy_data(candidate, data_dir)
                break

    return data_dir
