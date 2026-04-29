# ハマりどころ

## 1. 接続先が違う

- 症状: run 時に server 接続で失敗する
- 原因: `configs/connection_config.yaml` または環境変数側の接続先が想定と違う
- 対処: `core/cli.py` の解決順と `configs/connection_config.yaml` を確認する

## 2. prompt resolver を見間違える

- 症状: 新規実装で古い resolver を追ってしまう
- 原因: `core/prompt_resolver.py` と `core/prompt_resolver_v2.py` が両方ある
- 対処: 現行は V2 を優先して読む

## 3. configs の扱いを誤る

- 症状: 期待した job や prompt が repo に見当たらない
- 原因: `configs/` は一部 Git 管理外前提の運用
- 対処: 実ファイルの存在と環境依存の差分を確認する
