"""Pytest 配置：確保測試不依賴用戶本地的 .env 文件。

機制：
- Session 開始時把 .env 移到 .env.pytest_backup
- 測試運行時只讀 monkeypatch 設置的環境變量
- Session 結束時還原 .env
"""
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"
ENV_BACKUP = PROJECT_ROOT / ".env.pytest_backup"


@pytest.fixture(scope="session", autouse=True)
def isolate_dotenv():
    """Session 範圍：暫時移除 .env，測試結束後還原。"""
    if ENV_FILE.exists():
        ENV_FILE.rename(ENV_BACKUP)
        print(f"\n[conftest] 暫時移走 .env → .env.pytest_backup")
    try:
        yield
    finally:
        if ENV_BACKUP.exists() and not ENV_FILE.exists():
            ENV_BACKUP.rename(ENV_FILE)
            print("[conftest] 還原 .env")
