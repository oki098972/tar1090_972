#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
import re
import sys
from urllib.parse import parse_qs

# Noizelevel以上の音量を検知した時間帯を表示機能の為のコード
# /home/toshi-shimoji/share/noize/に蓄積したデータから下記コメントの１．２．のファイルを作る
# phpコードにした理由は上記ディレクトリがブラウザからアクセス不能の場所にあり、javascriptで操作できない為
# 本機能をEnableにするには、/usr/local/share/tar1090_972/html/shareディレクトリをパーミッション777で手動作成すること
# (Python版でも上記の事情は同じ。CGIとして実行する場合は、カレントディレクトリを html にしておくこと)


def php_int(s):
    # PHPの(int)キャストに合わせる（先頭の数字部分だけ読み、数字でなければ0）
    m = re.match(r'\s*[+-]?[0-9]+', s)
    return int(m.group()) if m else 0


def main():
    # CGIとして呼ばれた場合はQUERY_STRINGから、コマンドラインから呼ばれた場合は引数から取得
    # 使い方(CLI): python3 noizetime.py "2026/10/25 AM" 500
    if os.environ.get("QUERY_STRING") is not None:
        query = parse_qs(os.environ["QUERY_STRING"])
        arg_halfday = query.get("Halfday", [None])[0]
        arg_noizelevel = query.get("Noizelevel", [None])[0]
        print("Content-Type: text/html; charset=utf-8\n")
    else:
        arg_halfday = sys.argv[1] if len(sys.argv) > 1 else None
        arg_noizelevel = sys.argv[2] if len(sys.argv) > 2 else None

    # パラメータチェック、AM/PM選択対応版、ただしPython部分でAM/PM時間帯の抽出処理は行わない（やるならこの先のjavascriptの処理中で）ので必要ない
    # if re.match(r'^([0-9]{4})/([0-9]{2})/([0-9]{2}) (AM|PM)', halfday):
    # パラメータチェック、年月日のみ
    ck1 = re.match(r'^([0-9]{4})/([0-9]{2})/([0-9]{2})', arg_halfday or "")
    if ck1:
        noizefile = "noize_" + ck1.group(1) + ck1.group(2) + ck1.group(3) + ".txt"
    else:
        print("日付が不正です")
        return False

    if re.fullmatch(r'[1-9][0-9]*', arg_noizelevel or ""):
        level = int(arg_noizelevel)
    else:
        print("騒音閾値が不正です")
        return False

    # 雑音ファイルを開く
    fp = open("/home/toshi-shimoji/share/noize/" + noizefile, "r", newline="")

    outArray = []  # 上は単純にarg_noizelevel以上の時間と音量を抽出、下は音が持続した時間を出す
    samArray = []
    his = 0
    ct = 0
    # １．csvデータからNoizelevel以上の音量の時刻と音量を抜き出して配列に入れる
    # ２．csvデータから連続する音の開始時間と音量、終了時間と音量を配列に入れる
    for data in csv.reader(fp):
        ct = ct + 1
        # 空行、または列が足りない行は読み飛ばす（PHPでは implode($data) != null の判定部分）
        if "".join(data) != "" and len(data) >= 2:
            if php_int(data[1]) >= level:
                outArray.append([data[0], data[1]])
                if his == 0:
                    samArray.append([data[0], data[1]])
                    his = 1
            if php_int(data[1]) <= 400 and his == 1:
                samArray.append([data[0], data[1]])
                his = 0
    fp.close()

    # （PHP版では二次元配列の宣言で作られた空要素をarray_shiftで削っていたが、
    #   Pythonでは空要素が出来ないので不要）

    # 上記１．のデータをファイルに書き出す
    # fputcsvに合わせて改行は\nにする
    fp = open("./share/" + noizefile.replace(".txt", "over.csv"), "w", newline="")
    writer = csv.writer(fp, lineterminator="\n")
    for line in outArray:
        writer.writerow(line)
    fp.close()

    # 上記２．のデータをファイルに書き出す
    fp = open("./share/" + noizefile.replace(".txt", "time.csv"), "w", newline="")
    writer = csv.writer(fp, lineterminator="\n")
    for line in samArray:
        writer.writerow(line)
    fp.close()

    print("./share/" + noizefile.replace(".txt", "time.csv"))

    return True


if __name__ == "__main__":
    main()
