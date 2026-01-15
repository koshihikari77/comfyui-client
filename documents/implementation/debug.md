### これまでの主要なエラーと対処法のまとめ

#### 1. WebSocketの初期化エラー
*   **エラーメッセージ**: `TypeError: WebSocket.__init__() missing 3 required positional arguments...`
*   **原因**: `websocket-client`ライブラリの`WebSocket`クラスのインスタンス化方法が誤っていた。`new websocket.WebSocket()` のような使い方は想定されていなかった。
*   **対処法**: `websocket.create_connection(url)` 関数を使用する方式に修正。これにより、接続の確立とWebSocketオブジェクトの取得が一行で正しく行えるようになった。

#### 2. WebSocketの接続関数が見つからないエラー
*   **エラーメッセージ**: `AttributeError: module 'websocket' has no attribute 'create_connection'`
*   **原因**: Python環境内に、`websocket-client`と、それとは別の`websocket`という名前のライブラリが衝突してインストールされていた。`import websocket`が意図しない方のライブラリを読み込んでいた。
*   **対処法**: `pip uninstall websocket websocket-client`で両方を完全にアンインストールした後、`pip install websocket-client`で必要なライブラリのみを再インストール。これにより、名前空間の衝突を解消した。

#### 3. ファイルパスの階層エラー
*   **エラーメッセージ**: `'results/images/...' is not in the subpath of '/mnt/c/Users/...'`
*   **原因**: データベースに保存する相対パスを `pathlib.Path.relative_to(Path.cwd())` で計算していたが、実行環境（特にデバッガーやWSL）によって`Path.cwd()`（カレントワーキングディレクトリ）が予期せぬ場所を指し、パスの親子関係が崩れていた。
*   **対処法**: 実行環境に依存しないよう、DBに保存するパスは `'results/images/' + filename` のように固定の文字列として生成する方法に変更。これにより、どこで実行しても一貫した相対パスが記録されるようになった。

#### 4. プログラムが終了しない（WebSocketの無限待機）
*   **現象**: ComfyUIサーバー側で画像は生成されているが、クライアント側の処理が終わらない。
*   **原因の特定**:
    1.  **当初の仮説**: `Save Image`ノードがない、またはカスタム保存ノードが原因で、ComfyUIが標準の完了メッセージを送っていない。
    2.  **ログでの判明**: 予期せぬカスタムノード（`Crystools-Monitor`）が、クライアントが処理できない独自のWebSocketメッセージを送信していた。
    3.  **切り分けで判明**: `LCM`サンプラーや特定のLoRAの適用順など、一部のノードの組み合わせや設定が、ComfyUIからの標準的な進捗・完了メッセージの送信を妨げることがあった。
*   **対処法**:
    *   **クライアントの堅牢化**: `api_client`のWebSocket受信ループを修正。自分が関心のあるメッセージタイプ（`executing`, `progress`）以外はすべて無視（`continue`）するようにした。これにより、未知のメッセージが来ても処理が停止しなくなった。
    *   **デバッグ機能の追加**: `--verbose` (`-v`) オプションを追加し、`logging`モジュールを使って詳細なログ（特にWebSocketの生データ）を出力できるようにした。これにより、将来同様の問題が発生した際に、原因の特定が容易になった。

これらのエラーと対処の経験を通じて、ComfyVは外部API（ComfyUI）との連携における様々なエッジケースに対応できる、より堅牢でデバッグしやすいフレームワークへと進化しました。