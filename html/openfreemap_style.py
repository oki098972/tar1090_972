#!/usr/bin/env python3

#openfreemapを表示用の地図に選ぶと、地名等で日本語と英語が２つ表示されて雑然とするので
#都市名、島名を英語表記のみにし、県名を表示しないように設定ファイルを書き換える為のコード
#手動で起動する必要あり（ブラウザから起動不能）
#このコードで変更するのはある種のスタイルファイルのようなので、今後実行する事は無いと思われる
#このコードでopenfreemapより取得して改変したファイルはhtml/openfreemap_stylesに格納してある

import json
import sys
from pathlib import Path

import requests


STYLE_NAMES = [
    "bright",
    "dark",
    "fiord",
    "liberty",
    "positron",
]

STYLE_URL = "https://tiles.openfreemap.org/styles/{}"

OUTPUT_DIR = Path("./openfreemap_styles")


# 英語表記に変更するラベルレイヤー
ENGLISH_LABEL_LAYERS = {
    "label_village",
    "label_town",
    "label_city",
    "label_city_capital",
}


def warning(message):
    print(f"WARNING: {message}")


def modify_style(style, style_name):
    """
    Style JSONを変更する。

    変更内容:
      - label_state を削除
      - 都市・町・村のラベルを英語優先に変更
      - label_other から province を除外
      - label_other の island だけ英語名を表示
    """

    layers = style.get("layers")

    if not isinstance(layers, list):
        warning(
            f"{style_name}: 'layers' が見つからないため、"
            "変更せず保存します。"
        )
        return style

    new_layers = []

    state_removed = False
    english_layers_found = set()
    label_other_found = False

    for layer in layers:

        if not isinstance(layer, dict):
            warning(
                f"{style_name}: layers 内に不正なデータがあります。"
                "そのレイヤーはそのまま残します。"
            )
            new_layers.append(layer)
            continue

        layer_id = layer.get("id")

        # --------------------------------------------------
        # 都道府県用レイヤー
        # --------------------------------------------------
        if layer_id == "label_state":
            print(f"  Removing layer: {layer_id}")
            state_removed = True
            continue

        # --------------------------------------------------
        # 都市・町・村 → 英語名優先
        # --------------------------------------------------
        if layer_id in ENGLISH_LABEL_LAYERS:

            layout = layer.setdefault("layout", {})

            layout["text-field"] = [
                "coalesce",
                ["get", "name_en"],
                ["get", "name:latin"],
                ["get", "name"],
            ]

            english_layers_found.add(layer_id)

            print(f"  English labels: {layer_id}")

        # --------------------------------------------------
        # その他の地名
        # --------------------------------------------------
        if layer_id == "label_other":

            label_other_found = True

            # ----------------------------------------------
            # province を除外
            # ----------------------------------------------
            filter_expr = layer.get("filter")

            if isinstance(filter_expr, list):
                try:
                    # 現在のOpenFreeMap Positronの
                    # label_other のfilterを想定。
                    #
                    # [
                    #   "match",
                    #   ["get", "class"],
                    #   [...],
                    #   false,
                    #   true
                    # ]
                    if (
                        len(filter_expr) >= 3
                        and filter_expr[0] == "match"
                        and filter_expr[1] == ["get", "class"]
                        and isinstance(filter_expr[2], list)
                    ):
                        classes = filter_expr[2]

                        if "province" not in classes:
                            classes.append("province")
                            print(
                                "  Excluding class 'province' "
                                "from label_other"
                            )
                        else:
                            print(
                                "  class 'province' is already "
                                "excluded from label_other"
                            )

                    else:
                        warning(
                            f"{style_name}: label_other のfilter形式が"
                            "想定と違います。provinceの除外は行いません。"
                        )

                except Exception as e:
                    warning(
                        f"{style_name}: label_other のfilter変更に失敗: "
                        f"{e}"
                    )

            else:
                warning(
                    f"{style_name}: label_other に有効なfilterがありません。"
                    "provinceの除外は行いません。"
                )

            # ----------------------------------------------
            # island だけ日本語を表示しない
            # ----------------------------------------------
            layout = layer.setdefault("layout", {})

            original_text_field = layout.get("text-field")

            if original_text_field is None:
                warning(
                    f"{style_name}: label_other に text-field がありません。"
                    "島名の変更は行いません。"
                )
            else:
                layout["text-field"] = [
                    "case",

                    # class == island
                    ["==", ["get", "class"], "island"],

                    # 島の場合：
                    # 英語名を優先し、日本語(name:nonlatin)は使わない
                    [
                        "coalesce",
                        ["get", "name_en"],
                        ["get", "name:latin"],
                        ["get", "name"],
                    ],

                    # 島以外：
                    # 元の設定をそのまま使用
                    original_text_field,
                ]

                print(
                    "  Island labels: English only"
                )

        new_layers.append(layer)

    style["layers"] = new_layers

    # ------------------------------------------------------
    # 処理結果のWARNING
    # ------------------------------------------------------

    if not state_removed:
        warning(
            f"{style_name}: label_state が見つかりませんでした。"
        )

    missing = ENGLISH_LABEL_LAYERS - english_layers_found

    if missing:
        warning(
            f"{style_name}: 以下のlabel layerが見つかりません: "
            + ", ".join(sorted(missing))
        )

    if not label_other_found:
        warning(
            f"{style_name}: label_other が見つかりませんでした。"
        )

    return style


def download_style(style_name):
    """
    OpenFreeMapからStyle JSONを取得して変更し、保存する。
    """

    url = STYLE_URL.format(style_name)

    print()
    print("=" * 60)
    print(f"Processing: {style_name}")
    print(f"URL: {url}")

    try:
        response = requests.get(
            url,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as e:
        warning(
            f"{style_name}: ダウンロードに失敗しました: {e}"
        )
        return False

    try:
        style = response.json()

    except ValueError as e:
        warning(
            f"{style_name}: JSONとして解析できませんでした: {e}"
        )
        return False

    try:
        style = modify_style(style, style_name)

    except Exception as e:
        # 念のため、予期しないエラーでも処理全体を止めない
        warning(
            f"{style_name}: JSON変更中に予期しないエラー: {e}"
        )
        return False

    output_file = OUTPUT_DIR / f"{style_name}.json"

    try:
        with output_file.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                style,
                f,
                ensure_ascii=False,
                indent=2,
            )

            # 最後に改行
            f.write("\n")

    except OSError as e:
        warning(
            f"{style_name}: ファイル保存に失敗しました: {e}"
        )
        return False

    print(f"Saved: {output_file}")

    return True


def main():

    print("OpenFreeMap Style updater")
    print()

    try:
        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as e:
        print(
            f"ERROR: 出力ディレクトリを作成できません: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    success = 0
    failed = 0

    for style_name in STYLE_NAMES:

        if download_style(style_name):
            success += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(
        f"Finished: {success} succeeded, {failed} failed."
    )

    # 一部失敗しても最後まで処理する。
    # 全部失敗した場合だけ終了コード1。
    if success == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

