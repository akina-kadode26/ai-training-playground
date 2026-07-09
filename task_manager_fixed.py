#!/usr/bin/env python3
"""
タスク管理CLIツール

使い方:
    python task_manager.py add <タイトル> --due <YYYY-MM-DD> [--priority <high|medium|low>]
    python task_manager.py list [--all] [--priority <high|medium|low>]
                                 [--due-before <YYYY-MM-DD>] [--due-after <YYYY-MM-DD>]
                                 [--sort <id|title|due|priority|completed>] [--order <asc|desc>]
    python task_manager.py complete <ID>
    python task_manager.py delete <ID>
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime

TASKS_FILE = "tasks.json"
LOG_FILE = "task_manager.log"

VALID_PRIORITIES = ["high", "medium", "low"]
# 優先度の意味的な並び順（高→中→低）。ソート時に使用する。
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# タイトルの最大文字数（No.1対応）
TITLE_MAX_LENGTH = 30

# 一覧表示時のカラム幅（No.13対応：マジックナンバーを排除）
ID_COLUMN_WIDTH = 4
TITLE_COLUMN_WIDTH = 30
DUE_COLUMN_WIDTH = 12
PRIORITY_COLUMN_WIDTH = 8

# エラー詳細はログファイルに記録し、利用者にはトレースバックを見せない（No.4, No.5対応）
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def load_tasks() -> list[dict]:
    """
    tasks.json からタスク一覧を読み込む。
    ファイルが存在しない場合は空リストを返す。
    ファイルが破損している場合や読み取りに失敗した場合は、
    利用者向けにエラーメッセージを表示して終了し、詳細はログに記録する（No.4対応）。
    """
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error("tasks.json の解析に失敗しました: %s", e)
        print("エラー: タスクデータの読み込みに失敗しました（データ形式が不正です）")
        sys.exit(1)
    except OSError as e:
        logging.error("tasks.json の読み込みに失敗しました: %s", e)
        print("エラー: タスクデータの読み込みに失敗しました（ファイルにアクセスできません）")
        sys.exit(1)


def save_tasks(tasks: list[dict]) -> None:
    """
    タスク一覧を tasks.json に書き込む。
    書き込みに失敗した場合は、利用者向けにエラーメッセージを表示して終了し、
    詳細はログに記録する（No.5対応）。
    """
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logging.error("tasks.json の書き込みに失敗しました: %s", e)
        print("エラー: タスクデータの保存に失敗しました（ディスク容量や権限を確認してください）")
        sys.exit(1)


def generate_id(tasks: list[dict]) -> int:
    """
    タスクリストから新しいタスク ID を採番して返す。
    既存タスクの最大 ID + 1 を採番することで、削除後の再採番による
    ID重複を防ぐ（No.3対応）。
    """
    return max((t["id"] for t in tasks), default=0) + 1


def validate_due_date_not_past(date_str: str) -> date | None:
    """
    期限日文字列（YYYY-MM-DD）を検証する。
    当日以降の有効な日付であれば date オブジェクトを返し、それ以外は None を返す。
    （add コマンドの期限チェック専用。命名を役割に合わせて明確化：No.10対応）
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        if d < date.today():
            return None
        return d
    except ValueError:
        return None


def validate_date_format(date_str: str) -> date | None:
    """
    日付文字列（YYYY-MM-DD）の形式のみを検証する。
    形式が正しければ date オブジェクトを返し、不正なら None を返す。
    （絞り込み用。add コマンドの期限チェックとは異なり、過去日も許可する）
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def cmd_add(args: argparse.Namespace) -> None:
    """タスクを追加する。"""
    tasks = load_tasks()

    due_date = validate_due_date_not_past(args.due)
    if due_date is None:
        print(f"エラー: 有効な期限を指定してください（今日以降の日付、例: {date.today()}）")
        sys.exit(1)

    # タイトルの空文字列・前後空白・文字数超過をチェックする（No.1対応）
    title = args.title.strip()
    if not title:
        print("エラー: タイトルを空にすることはできません")
        sys.exit(1)
    if len(title) > TITLE_MAX_LENGTH:
        print(f"エラー: タイトルは{TITLE_MAX_LENGTH}文字以内で指定してください")
        sys.exit(1)

    # 優先度は argparse の choices で既に検証済みのため、重複チェックは行わない（No.2対応）

    task = {
        "id": generate_id(tasks),
        "title": title,
        "due": args.due,
        "priority": args.priority,
        "completed": False,
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f"タスクを追加しました: [{task['id']}] {task['title']} (期限: {task['due']}, 優先度: {task['priority']})")


def _parse_task_due_date(task: dict) -> date | None:
    """
    タスクの due フィールドをパースする。
    tasks.json が手動編集等で不正な日付形式になっている場合に備え、
    例外を発生させず None を返す（No.6対応）。
    """
    try:
        return datetime.strptime(task["due"], "%Y-%m-%d").date()
    except (ValueError, KeyError):
        return None


def filter_tasks(
    tasks: list[dict],
    show_all: bool,
    priority: str | None,
    due_before: date | None,
    due_after: date | None,
) -> list[dict]:
    """
    絞り込み条件に従ってタスクをフィルタする（No.11対応：cmd_list から責務を分離）。
    due の形式が不正なタスクは警告を表示したうえでスキップする（No.6対応）。
    """
    if not show_all:
        tasks = [t for t in tasks if not t["completed"]]

    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    if due_before is not None or due_after is not None:
        filtered = []
        for t in tasks:
            task_due = _parse_task_due_date(t)
            if task_due is None:
                print(f"警告: タスク {t.get('id', '?')} の期限データが不正なため、絞り込み対象から除外しました")
                continue
            if due_before is not None and task_due > due_before:
                continue
            if due_after is not None and task_due < due_after:
                continue
            filtered.append(t)
        tasks = filtered

    return tasks


def sort_tasks(tasks: list[dict], sort_key: str | None, order: str) -> list[dict]:
    """並び替え条件に従ってタスクをソートする（No.11対応：cmd_list から責務を分離）。"""
    if not sort_key:
        return tasks

    reverse = order == "desc"
    if sort_key == "priority":
        # 優先度は文字列の五十音/アルファベット順ではなく、
        # 「高→中→低」の意味的な順序で並べ替える
        return sorted(tasks, key=lambda t: PRIORITY_ORDER[t["priority"]], reverse=reverse)
    return sorted(tasks, key=lambda t: t[sort_key], reverse=reverse)


def display_tasks(tasks: list[dict]) -> None:
    """タスク一覧をテーブル形式で表示する（No.11対応：cmd_list から責務を分離）。"""
    if not tasks:
        print("タスクはありません")
        return

    print(
        f"{'ID':>{ID_COLUMN_WIDTH}}  {'タイトル':<{TITLE_COLUMN_WIDTH}}  "
        f"{'期限':<{DUE_COLUMN_WIDTH}}  {'優先度':<{PRIORITY_COLUMN_WIDTH}}  {'状態'}"
    )
    print("-" * 70)
    for t in tasks:
        status = "完了" if t["completed"] else "未完了"
        print(
            f"{t['id']:>{ID_COLUMN_WIDTH}}  {t['title']:<{TITLE_COLUMN_WIDTH}}  "
            f"{t['due']:<{DUE_COLUMN_WIDTH}}  {t['priority']:<{PRIORITY_COLUMN_WIDTH}}  {status}"
        )


def cmd_list(args: argparse.Namespace) -> None:
    """
    タスクを一覧表示する。絞り込み条件・並び替え条件を指定できる。
    フィルタリング・並び替え・表示の責務を関数に分割し、
    本関数は各処理を呼び出すだけの構成にした（No.11対応）。
    """
    tasks = load_tasks()

    due_before = None
    if args.due_before:
        due_before = validate_date_format(args.due_before)
        if due_before is None:
            print("エラー: --due-before の日付形式が不正です（例: YYYY-MM-DD）")
            sys.exit(1)

    due_after = None
    if args.due_after:
        due_after = validate_date_format(args.due_after)
        if due_after is None:
            print("エラー: --due-after の日付形式が不正です（例: YYYY-MM-DD）")
            sys.exit(1)

    tasks = filter_tasks(tasks, args.all, args.priority, due_before, due_after)
    tasks = sort_tasks(tasks, args.sort, args.order)
    display_tasks(tasks)


def cmd_complete(args: argparse.Namespace) -> None:
    """指定した ID のタスクを完了状態にする。"""
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == args.id:
            task["completed"] = True
            save_tasks(tasks)
            print(f"タスク {args.id} を完了にしました: {task['title']}")
            return
    print(f"エラー: ID {args.id} のタスクが見つかりません")
    sys.exit(1)


def cmd_delete(args: argparse.Namespace) -> None:
    """指定した ID のタスクを削除する。"""
    tasks = load_tasks()
    new_tasks = [t for t in tasks if t["id"] != args.id]
    if len(new_tasks) == len(tasks):
        print(f"エラー: ID {args.id} のタスクが見つかりません")
        sys.exit(1)
    save_tasks(new_tasks)
    print(f"タスク {args.id} を削除しました")


def main() -> None:
    """エントリーポイント。引数を解析して対応するコマンドを実行する。"""
    parser = argparse.ArgumentParser(
        description="タスク管理CLIツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="コマンド")

    # add サブコマンド
    p_add = subparsers.add_parser("add", help="タスクを追加する")
    p_add.add_argument("title", help="タスクのタイトル")
    p_add.add_argument("--due", required=True, help="期限 (YYYY-MM-DD)")
    p_add.add_argument(
        "--priority",
        default="medium",
        choices=VALID_PRIORITIES,
        help="優先度 (デフォルト: medium)",
    )
    p_add.set_defaults(func=cmd_add)

    # list サブコマンド
    p_list = subparsers.add_parser("list", help="タスク一覧を表示する")
    p_list.add_argument("--all", action="store_true", help="完了済みも含めて表示する")
    p_list.add_argument(
        "--priority",
        choices=VALID_PRIORITIES,
        help="指定した優先度のタスクのみ表示する",
    )
    p_list.add_argument(
        "--due-before",
        help="期限が指定日以前のタスクのみ表示する (YYYY-MM-DD)",
    )
    p_list.add_argument(
        "--due-after",
        help="期限が指定日以降のタスクのみ表示する (YYYY-MM-DD)",
    )
    p_list.add_argument(
        "--sort",
        choices=["id", "title", "due", "priority", "completed"],
        help="指定した項目で並び替える",
    )
    p_list.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="asc",
        help="並び順 (デフォルト: asc)",
    )
    p_list.set_defaults(func=cmd_list)

    # complete サブコマンド
    p_complete = subparsers.add_parser("complete", help="タスクを完了にする")
    p_complete.add_argument("id", type=int, help="完了にするタスクの ID")
    p_complete.set_defaults(func=cmd_complete)

    # delete サブコマンド
    p_delete = subparsers.add_parser("delete", help="タスクを削除する")
    p_delete.add_argument("id", type=int, help="削除するタスクの ID")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
