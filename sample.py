"""研修演習用のサンプルスクリプト。

TODOコメント検索のデモ用ファイルです。
"""


def greet(name):
    # TODO: 入力値のバリデーションを追加する
    return f"Hello, {name}!"


def calculate_total(items):
    total = 0
    for item in items:
        total += item["price"]
    # TODO: 消費税の計算を実装する
    return total


if __name__ == "__main__":
    print(greet("World"))
    # TODO: サンプルデータでテストを書く
