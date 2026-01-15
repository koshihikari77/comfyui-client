# Conventional Commits ガイド

このドキュメントでは、プロジェクトで採用する **Conventional Commits** 規約の書き方と運用フローをまとめます。コミット履歴をわかりやすく保ち、自動リリース・自動 CHANGELOG 生成を円滑にするために必須のルールです。

---

## 1. 基本フォーマット

```
<type>(<scope>)?: <subject>

[optional body]

[optional footer(s)]
```

- `type` (必須) : 変更の種類を示すキーワード。
- `scope` (任意) : 影響範囲（ファイル名、モジュール名、パッケージ名など）。
- `subject` (必須) : 50 文字以内で、文末にピリオドを付けない。
- `body` (任意) : 何を・なぜ行ったかを 72 文字毎に改行しながら詳細説明。
- `footer` (任意) : `BREAKING CHANGE:` や `Closes #123` などのメタ情報。

### 1.1 BREAKING CHANGE の書式

破壊的変更がある場合は、`!` を付けるか `footer` に `BREAKING CHANGE:` を記載します。

```
feat(core)!: remove legacy authentication

BREAKING CHANGE: 旧 API v1 を削除したため、クライアントは v2 へ移行が必要
```

---

## 2. `type` 一覧

| type | 説明 |
|------|------|
| **feat** | 新しい機能 |
| **fix** | バグ修正 |
| **docs** | ドキュメントのみの変更 |
| **style** | コードの動作に影響しないフォーマット修正 (空白, インデント, セミコロン等) |
| **refactor** | バグ修正でも機能追加でもないコード変更 |
| **perf** | パフォーマンス向上を意図した変更 |
| **test** | テスト追加・修正 |
| **build** | ビルドシステム・依存管理に関する変更 (npm, pip, gulp など) |
| **ci** | CI 設定やスクリプトの変更 (GitHub Actions, CircleCI など) |
| **chore** | ソース・テスト・ドキュメント以外の補助ツール変更 (リント設定等) |
| **revert** | 以前のコミットを Revert する |

> 必要に応じて `wip` や `merge` などを追加する場合はチーム合意の上で行ってください。

---

## 3. 具体例

```
feat(prompt_resolver): support list-style presets and recursion

プリセットをリスト形式で定義できるようにし、再帰的解決ロジックを追加。
これにより階層プリセットの記述が簡潔になり、拡張性が向上する。
```

```
chore(gitignore): ignore coverage and lock files

`.coverage`, `htmlcov/`, `uv.lock` など開発時に生成されるファイルを無視。
```

```
fix(connection): update fallback server address

Connection timeout の主因だった旧 IP を新しいロードバランサに置換。
```

```
feat(core)!: migrate to v2 api

BREAKING CHANGE: `core.api_client` のシグネチャが変更され、旧バージョンとの互換性がありません。
```

---

## 4. ワークフロー

1. **ステージング**: 目的ごとにファイルを `git add` で選別。
2. **コミット作成**: `git commit` で Conventional Commits に則ったメッセージを書く。VSCode の「ソース管理」パネルやターミナルで入力。
3. **プッシュ**: `git push origin <branch>`
4. **プルリク**: GitHub 上で Pull Request を作成し、タイトルをそのまま Conventional Commits 形式に。
5. **自動チェック**: `commitlint` や GitHub Actions でメッセージフォーマットを検証 (任意)。

### 4.1 Commitlint 導入 (オプション)
- `npm install --save-dev @commitlint/{config-conventional,cli}`
- `echo "module.exports = { extends: ['@commitlint/config-conventional'] };" > commitlint.config.js`
- Husky で `commit-msg` フックに組み込み。

---

## 5. よくある Q&A

**Q. スコープは必ず書くべき?**  
A. 厳密ではありませんが、大きなプロジェクトで影響範囲を明示するとレビューが楽になります。

**Q. 複数の変更が混ざった場合は?**  
A. 変更を意味・目的ごとに分割し、コミットを複数回に分けてください。

**Q. ドキュメントだけ修正した場合は `docs`?**  
A. はい。コードに影響がない場合は `docs` を使用します。

---

## 6. 参考リンク

- [Conventional Commits 公式](https://www.conventionalcommits.org/)
- [Commitizen](https://commitizen-tools.github.io/commitizen/) – 対話的にコミットメッセージを生成
- [commitlint](https://commitlint.js.org/) – コミットメッセージ Lint ツール

---

以上を守ることで、コミットログの検索性と自動化が向上し、保守が容易になります。 