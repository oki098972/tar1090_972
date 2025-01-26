<?php
    $arg_halfday = $_GET['Halfday'];
    $arg_noizelevel = $_GET['Noizelevel'];

    //パラメータチェック、AM/PM選択対応版、ただしPHP部分でAM/PM時間帯の抽出処理は行わない（やるならこの先のjavascriptの処理中で）ので必要ない
    //if (preg_match('/^([0-9]{4})\/([0-9]{2})\/([0-9]{2}) (AM|PM)/', $halfday, $ck1) == 1) {
    //パラメータチェック、年月日のみ
    if (preg_match('/^([0-9]{4})\/([0-9]{2})\/([0-9]{2})/', $arg_halfday, $ck1) == 1) {
        $noizefile = "noize_" . $ck1[1] . $ck1[2] . $ck1[3] . ".txt";
    } else {
        echo "日付が不正です";
        return false;
    }
    
    if (preg_match('/\A[1-9][0-9]*\z/', $arg_noizelevel, $ck2) == 1) {
        $level = (int)$arg_noizelevel;
    } else {
        echo "騒音閾値が不正です";
        return false;
    }
    //雑音ファイルを開く
    $fp = fopen("/home/toshi-shimoji/share/noize/" . $noizefile, "r");
    
    $outArray = [];
    $outArray[] = [];  //左記２文で二次元配列の宣言になる
    $samArray = [];
    $samArray[] = [];  //上は単純にarg_noizelevel以上の時間と音量を抽出、下は音が持続した時間を出す
    $his = 0;
    $ct = 0;
    //１．csvデータからNoizelevel以上の音量の時刻と音量を抜き出して配列に入れる
    //２．csvデータから連続する音の開始時間と音量、終了時間と音量を配列に入れる
    while ($data = fgetcsv($fp)) {
        $ct = $ct + 1;
        if (implode($data) != null) {
            if ( (int)$data[1] >= $level ) {
                array_push($outArray, [$data[0], $data[1]]);
                if ( $his == 0 ) {
                    array_push($samArray, [$data[0], $data[1]]);
                    $his = 1;
                }
            }
            if ( ((int)$data[1] <= 400) and ($his == 1) ) {
                array_push($samArray, [$data[0], $data[1]]);
                $his = 0;
            }
        }
    }
    fclose($fp);
    
    //二次元配列の宣言で空要素を作ったことになったらしいので出力前に削る
    //わざわざ消すのはphpの配列で昔変なことになった気がするので上手く行ってるものに変に手を入れない
    array_shift($outArray);
    array_shift($samArray);
    //上記１．のデータをファイルに書き出す
    $fp = fopen("./share/" . str_replace(".txt", "over.csv", $noizefile), "w");
    foreach($outArray as $line) {
        fputcsv($fp, $line);
    }
    fclose($fp);
    
    //上記２．のデータをファイルに書き出す
    $fp = fopen("./share/" . str_replace(".txt", "time.csv", $noizefile), "w");
    foreach($samArray as $line) {
        fputcsv($fp, $line);
    }
    fclose($fp);
    
    echo "./share/" . str_replace(".txt", "time.csv", $noizefile);
    
    return true;
?>

