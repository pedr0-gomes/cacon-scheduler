"""
Backup do banco SQLite do CACON.

Uso manual:
    uv run python backup.py

Cron diário às 02h:
    0 2 * * * cd /caminho/cacon-scheduler && uv run python backup.py >> /var/log/cacon-backup.log 2>&1
"""
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "cacon.db"
BACKUP_DIR = Path(__file__).parent / "backups"
KEEP = 30


def fazer_backup() -> Path:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Banco não encontrado: {DB_PATH}")

    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = BACKUP_DIR / f"cacon_{ts}.db"
    shutil.copy2(DB_PATH, dest)

    backups = sorted(BACKUP_DIR.glob("cacon_*.db"))
    for antigo in backups[:-KEEP]:
        antigo.unlink()

    return dest


if __name__ == "__main__":
    dest = fazer_backup()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Backup: {dest.name} ({dest.stat().st_size // 1024} KB)")
