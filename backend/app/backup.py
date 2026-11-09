import argparse
from pathlib import Path
import sqlite3

from .config import Settings
from .database import Database


def main() -> None:
    parser = argparse.ArgumentParser(description="稼働中の旅の手帳を整合性のあるSQLiteファイルへ保存する")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--database", type=Path, default=Settings().db_path)
    arguments = parser.parse_args()
    if not arguments.database.is_file():
        parser.error("保存元のデータベースが見つかりません。")
    if arguments.destination.exists():
        parser.error("保存先は既に存在します。別のファイル名を指定してください。")
    try:
        Database(arguments.database).backup(arguments.destination)
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"バックアップを保存できませんでした（{type(error).__name__}）。\n")
    print("バックアップを保存し、DBと参照関係の整合性を確認しました。")


if __name__ == "__main__":
    main()
