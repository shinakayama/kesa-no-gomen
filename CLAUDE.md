# kesa-no-gomen

## 発行時のpush
けさの五面を発行したら、作業ブランチへのpushに加えて、毎回 main にも push する（ユーザーの恒久的な指示）。

    git push origin HEAD:main

main は発行ごとに fast-forward で進める。履歴の書き換え（force push）はしない。
