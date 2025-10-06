# プロンプトテンプレート仕様書

このドキュメントでは **プロンプトテンプレート** の書き方と使用方法を説明します。Preset、Placeholder、Wildcardの3つの機能を組み合わせて、効率的なプロンプト生成を実現できます。

---
## 1. 概要

### 1.1 サポートする記法
| 記法 | 例 | 用途 |
|------|------|------|
| **Constant** | `%base_quality%` | 固定文字列定数を挿入 |
| **Iterator** | `$[location]` | 順次選択値を挿入 |
| **Preset** | `<preset:quality#base>` | 事前定義したタグ集合を挿入 |
| **Placeholder** | `{emotion}` | 設定値からランダム/全展開選択 |
| **Wildcard** | `__hair_color__` | ファイルからランダム選択 |
| **Text** | `1girl, standing` | 通常のテキスト |

### 1.2 処理順序
```
Template → ⓪ Constant → ⓪ Iterator → ① Parse → ② PresetEval → ③ Placeholder → ④ Wildcard → ⑤ Filter → ⑥ Format
```

---
## 2. Preset記法 `<preset:...>`

### 2.1 基本書き方
```yaml
# presets/quality.yaml
contents:
  default: "masterpiece, best quality, finely detailed"
  hdr: ["HDR", "vibrant colors"]
  low: "simple background"
```

### 2.2 呼び出し方法
| 記法 | 説明 | 結果例 |
|------|------|--------|
| `<preset:quality>` | 全グループの和集合 | `masterpiece, best quality, finely detailed, HDR, vibrant colors, simple background` |
| `<preset:quality#default>` | defaultグループのみ | `masterpiece, best quality, finely detailed` |
| `<preset:quality#default+hdr>` | 複数グループ結合 | `masterpiece, best quality, finely detailed, HDR, vibrant colors` |
| `<preset:quality#default-hdr>` | グループ差集合 | `masterpiece, best quality, finely detailed` |

### 2.3 ファイル階層サポート
```
presets/
├── character/
│   └── akira/
│       ├── akira.yaml
│       └── school_uniform.yaml
└── quality.yaml
```

**呼び出し例**:
```
<preset:character/akira#base>  # ✅ サポート済み
<preset:character/akira/school_uniform#default>  # ✅ サポート済み
```

### 2.4 制限事項
- **グループ内ドット記法未サポート**: `<preset:name#style.anime>` → `<preset:name#style_anime>` を使用
- **異なるPreset間演算未定義**: `<preset:quality+style#anime>` は未サポート

---
## 3. Placeholder記法 `{...}`

### 3.1 設定ファイル
```yaml
# config.yaml
placeholders:
  emotion: ["happy", "sad", "excited"]
  pose: ["standing", "sitting", "lying"]
  lighting: ["soft lighting", "dramatic lighting"]
```

### 3.2 動作モード

#### sampleモード（デフォルト）
```
テンプレート: "1girl, {emotion} face, {pose}"
結果: "1girl, happy face, standing"  # ランダム選択
```

#### expandモード（全組み合わせ）
```
テンプレート: "{emotion} girl, {pose}"
結果: [
  "happy girl, standing",
  "happy girl, sitting", 
  "sad girl, standing",
  "sad girl, sitting",
  "excited girl, standing",
  "excited girl, sitting"
]
```

### 3.3 制限事項
- **展開数制限**: 129件（`MAX_EXPANSION`）
- **深度制限**: 20（`MAX_DEPTH`、ネスト対応）

---
## 4. Wildcard記法 `__...__`

### 4.1 ファイル定義
```txt
# prompts/wildcards/hair_color.txt
blonde hair
black hair
brown hair
red hair
```

### 4.2 基本使用
```
テンプレート: "1girl, __hair_color__"
結果: "1girl, blonde hair"  # ランダム選択
```

### 4.3 ネスト再パース
```txt
# prompts/wildcards/style.txt
<preset:quality#base>
<preset:anime#kawaii>
photorealistic
```

```
テンプレート: "__style__, 1girl"
結果: "masterpiece, best quality, 1girl"  # Preset展開後
```

---
## 5. V1/V2フォーマット対応

### 5.1 V2フォーマット（推奨）
```yaml
# presets/quality.yaml
version: 2  # 省略可
contents:
  default: "masterpiece, best quality"  # 横書き可
  hdr: ["HDR", "vibrant colors"]        # リスト形式
```

### 5.2 V1フォーマット（互換）
```yaml
# presets/character.yaml
- hero girl
- warrior
- solo
```
→ 自動的に `contents: {"__all__": [...]}` に変換

### 5.3 階層構造サポート状況
| 階層タイプ | 例 | サポート状況 |
|-----------|---|-------------|
| **プリセットファイル階層** | `<preset:character/akira#base>` | ✅ **サポート済み** |
| **グループ内ドット記法** | `<preset:name#style.anime>` | ❌ 未サポート（将来課題） |
| **グループアンダースコア記法** | `<preset:name#style_anime>` | ✅ **サポート済み** |

---
## 6. 複合使用例

### 6.1 基本的な組み合わせ
```
テンプレート:
<preset:quality#base+hdr>, {emotion} girl, __hair_color__, {pose}

設定:
placeholders:
  emotion: ["happy", "sad"]
  pose: ["standing", "sitting"]

結果例:
masterpiece, best quality, HDR, vibrant colors, happy girl, blonde hair, standing
```

### 6.2 実用的なテンプレート
```
# キャラクター生成
<preset:character/akira#base>, {emotion} expression, __outfit__, {pose}, <preset:quality#hdr>

# 背景付きシーン
<preset:scene/indoor#bedroom>, {lighting}, {emotion} girl, __hair_style__, {pose}

# 品質重視
<preset:quality#base-low>, detailed {emotion} face, __art_style__, perfect anatomy
```

### 6.3 新形式: jobファイルでのリスト記述（v2.6新機能）
```yaml
# jobファイルでのprompts新記法
prompts:
  # ブロックスタイル：要素ごとに改行
  - - "<preset:quality#base>"
    - "1girl"
    - "<preset:character/akira#base>"
    - "{emotion} expression"
    - "__outfit__"
    - "{pose}"
  
  # フロースタイル：1行でコンパクト
  - ["<preset:quality>", "1boy", "__hair_color__", "serious"]
  
  # 従来形式との混在も可能
  - template: "<preset:scene/outdoor>, beautiful landscape"
    runs: 3
```

**新機能の特徴**:
- **複数行記述**: プロンプトを要素ごとに分けて記述可能
- **default_runs対応**: runsが未指定の場合はdefault_runsを使用
- **混在サポート**: 新形式と従来形式を同一ファイルで使用可能
- **正規化**: 内部で自動的にカンマ区切りのtemplate文字列に変換

---
## 7. Constant機能（v2.8新機能）

### 7.1 概要
変化しない固定のプロンプト部分を定数として定義する機能です。複数のプロンプトで共通する部分を一箇所で管理でき、保守性が向上します。

**主要特徴**:
- `sequence`ジョブ専用機能
- `%constant_name%`記法でプロンプト内参照
- シンプルな文字列置換
- Iterator処理よりも前に実行

### 7.2 Constant定義

```yaml
# Job設定ファイル内
constants:
  # 基本品質タグ
  base_quality: "masterpiece, best quality, amazing quality"
  
  # キャラクター基本設定
  base_character: "1girl, shiina yuika \\(nijisanji\\), nijiyuika"
  
  # 共通描画設定
  base_tags: "detailed skin, detailed beautiful face and eye"
```

### 7.3 プロンプト内での使用

```yaml
prompts:
  - template: "%base_character%, %base_quality%, %base_tags%, happy, in a library"
    runs: 3
    
  - template: "%base_character%, %base_quality%, sad, crying"
    runs: 2
```

### 7.4 処理順序と組み合わせ

```yaml
# Constant + Iterator + Preset の組み合わせ例
constants:
  base_setup: "1girl, <preset:quality>"

iterators:
  emotion: ["happy", "sad", "angry"]

prompts:
  - template: "%base_setup%, $[emotion], sitting"
```

**処理順序**:
1. Constant置換: `%base_setup%` → `"1girl, <preset:quality>"`
2. Iterator置換: `$[emotion]` → `"happy"` (1回目)
3. Preset解決: `<preset:quality>` → `"masterpiece, best quality"`

**最終結果**: `"1girl, masterpiece, best quality, happy, sitting"`

---
## 8. Iterator機能（v2.7新機能）

### 8.1 概要
プロンプト内で特定の要素を順次（シーケンシャル）に変化させる機能です。ランダム選択ではなく、決定論的な順番でプロンプトの一部を置き換えることができます。

**主要特徴**:
- `sequence`ジョブ専用機能
- `$[iterator_name]`記法でプロンプト内参照
- 巡回ロジック（リストの要素不足時は先頭に戻る）
- プリセットからの自動展開に対応

### 8.2 Iterator定義

```yaml
# Job設定ファイル内
iterators:
  # 方法1: 手動リスト定義
  location:
    - "in a library"
    - "in a cafe" 
    - "at a futuristic spaceport"
  
  # 方法2: プリセットからグループを自動展開
  expression_type:
    expand_preset: "expression"
```

### 7.3 使用方法

**プロンプト内での参照**:
```yaml
prompts:
  - template: "<preset:quality>, 1girl, $[expression_type], $[location]"
    runs: 8
```

**処理の流れ**:
1. **事前処理**: `expand_preset`を解決し、全Iteratorを文字列リストに統一
2. **実行時置換**: `$[iterator_name]` → 該当リストの要素に置換
3. **巡回処理**: `index % len(iterator_list)`で要素選択

### 7.4 巡回ロジック

実行回数がIteratorの要素数を超える場合の動作例:

```yaml
iterators:
  mood: ["happy", "sad"]      # 2要素
  place: ["park", "beach", "mountain"]  # 3要素

prompts:
  - template: "1girl, $[mood], $[place]"
    runs: 7  # 7回実行
```

**実行結果**:
- 1回目: mood[0]="happy", place[0]="park"
- 2回目: mood[1]="sad", place[1]="beach" 
- 3回目: mood[0]="happy", place[2]="mountain" (moodが巡回)
- 4回目: mood[1]="sad", place[0]="park" (placeが巡回)
- 5回目: mood[0]="happy", place[1]="beach"
- 6回目: mood[1]="sad", place[2]="mountain"
- 7回目: mood[0]="happy", place[0]="park"

### 7.5 expand_preset機能

**プリセットからの自動展開**:
```yaml
iterators:
  character_style:
    expand_preset: "expression"
```

この設定により、`expression`プリセットの全グループが自動的に展開され、以下のような参照リストが生成されます:
```
["<preset:expression#1>", "<preset:expression#pre_fella_sad>", ...]
```

**対象プリセット**: V2形式プリセット（`contents`セクション含む）のみ対応

### 7.6 制約と注意事項

- **SequenceJobExecutor専用**: GridSearchジョブでは使用不可
- **PromptResolverとの協調**: `$[...]`置換後、通常のpreset/wildcard処理を実行
- **エラーハンドリング**: 未定義Iterator名は警告ログ出力し、元文字列を維持
- **パフォーマンス**: 事前処理でIterator解決済みのため実行時オーバーヘッド最小

---
## 8. エラーハンドリング

### 8.1 strict_level設定
```yaml
# config.yaml
strict_level: "warn"  # error/warn/soft
```

| レベル | 未定義時の動作 |
|--------|---------------|
| `error` | 例外発生・処理停止 |
| `warn` | 警告ログ・空文字に置換・処理続行 |
| `soft` | サイレント・空文字に置換・処理続行 |

### 8.2 よくあるエラー
```
# ❌ 未定義Preset
<preset:undefined_preset>

# ❌ 未定義グループ
<preset:quality#undefined_group>

# ❌ 未定義Placeholder
{undefined_placeholder}

# ❌ 未定義Wildcard
__undefined_wildcard__

# ❌ 未定義Iterator (v2.7)
$[undefined_iterator]
```

---
## 9. locale対応（出力形式）

### 9.1 区切り文字設定
```yaml
# config.yaml
locale: ","  # デフォルト: カンマ+スペース
```

| locale | 出力例 |
|--------|--------|
| `,` | `tag1, tag2, tag3` |
| `、` | `tag1、tag2、tag3` |
| `;` | `tag1;tag2;tag3` |

### 9.2 重要な仕様
- **単一要素時**: locale変換なし、元文字列保持
- **複数要素時**: 指定locale区切り文字で結合

---
## 10. フィルタリング機能

### 10.1 設定方法
```yaml
# config.yaml
ignore_tags:
  - HDR
  - lowres
ignore_groups:
  - quality#low
```

### 10.2 動作
最終出力からマッチするタグ・グループを除外

---
## 11. ベストプラクティス

### 11.1 効率的な記述
```yaml
# ✅ 横書きで差分を短く
quality:
  default: "masterpiece, best quality, finely detailed"
  
# ❌ 縦書きは差分が長い
quality:
  default:
    - masterpiece
    - best quality
    - finely detailed
```

### 10.2 グループ名規則
```yaml
# ✅ kebab-case推奨
contents:
  base-quality: "masterpiece, best quality"
  hdr-effects: "HDR, vibrant colors"
  
# ❌ 衝突リスク
contents:
  quality: "..."
  Quality: "..."  # 大文字小文字で区別されない
```

### 10.3 ファイル分割
```
presets/
├── quality.yaml      # 品質系
├── character/        # キャラクター系
├── scene/           # シーン系
└── style/           # スタイル系
```

---
## 11. 移行ガイド

### 11.1 V1からV2への移行
```bash
# CLI移行ツール
preset migrate presets/*.yaml --to 2
```

### 11.2 段階的移行
1. 既存V1ファイルはそのまま動作（自動変換）
2. 新規作成はV2形式を推奨
3. 必要に応じてグループ化・横書き化

---
## 12. よくある質問

| 質問 | 回答 |
|------|------|
| version書かないとどうなる？ | 自動でversion: 2として扱います |
| V2でcontents忘れた場合？ | strict_levelに応じてエラー/警告 |
| セミコロン区切りにしたい | `locale: ";"`に設定 |
| グループなしPresetの呼び出し | `<preset:name>`で全グループ和集合 |
| ファイル階層の区切り文字 | スラッシュ`/`（`character/akira`） |
| グループ階層の区切り文字 | アンダースコア`_`（`style_anime`）※ドット記法未サポート |

---
(End of Document)