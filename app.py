import logging
import sys


logging.basicConfig(level=logging.INFO, format="%(message)s")

MIN_ARGUMENT_COUNT = 1


def create_greeting(name: str) -> str:
    """名前からあいさつ文を生成する。

    Args:
        name: あいさつ対象の名前。

    Returns:
        生成されたあいさつ文。

    Raises:
        ValueError: 名前が空文字または空白のみの場合。
    """
    if not name.strip():
        raise ValueError("名前を入力してください")

    return f"こんにちは、{name}さん"


def main(args: list[str]) -> int:
    """コマンドライン引数を受け取り、あいさつ文を出力する。

    Args:
        args: コマンドライン引数のリスト。

    Returns:
        終了コード。正常終了の場合は0、不正な入力の場合は1。

    Raises:
        なし。
    """
    if len(args) < MIN_ARGUMENT_COUNT:
        logging.error("使い方: python app_initial.py <名前>")
        return 1

    try:
        message = create_greeting(args[0])
    except ValueError as error:
        logging.error(str(error))
        return 1

    logging.info(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))