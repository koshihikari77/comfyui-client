# AREA / COUPLE パターン

> **前提**: `[A:B:step]` スケジュール記法は **`PCLazyTextEncode`（PC: Schedule Prompt）専用**。
> `PCTextEncode` では無音で効かない。`DEF` も同様。
>
> **座標系**: `AREA(x 幅)` は位置と大きさ / `MASK・COUPLE(x1 x2)` は始点と終点。**同じ領域でも数字が違う**。

---

## 1. 横長・左右2キャラ（純COUPLE）— まずこれ

横分割は融合しにくく打率が高い。スケジュール不要。**領域間に隙間を空ける**。

```text
sfw, general, indoors, 2girls,

COUPLE(0 0.45)
1girl, long hair, blonde hair, white nurse,

COUPLE(0.55 1)
1girl, twintails, blue hair, black maid,
```

---

## 2. AREA 単体の左右分割 — 隙間なく密着

AREA は隙間を作ると、そこに base だけが強く出る。

```text
sfw, general, outdoors,

AND AREA(0 0.5)
1girl, long hair, blonde hair, white nurse,

AND AREA(0.5 0.5)
1girl, twintails, blue hair, black maid,
```

---

## 3. AREA:COUPLE スケジュール（定石）— 密着・split screen なし

序盤 AREA で構図を固め、以降 COUPLE で馴染ませる。**一枚絵にしたいなら `split screen` を入れない**。

```text
sfw, general, indoors,

[AND AREA(0 0.5):COUPLE(0 0.5):0.3]
1girl, long hair, blonde hair,

[AND AREA(0.5 0.5):COUPLE(0.5 1):0.3]
1girl, twintails, blue hair,
```

**★右側の表記に注意**: AREA は `(0.5 0.5)`、COUPLE は `(0.5 1)`。
`COUPLE(0.5 0.5)` と書くと**幅ゼロのマスク**になる。

---

## 4. 縦（上下）分割 — 難しいので AREA:COUPLE ＋ 区切りタグ

頭〜足が融合しやすい。区切り線タグを遅らせて入れると打率が上がる。

```text
sfw, general, outdoors,
[:split screen:0.3]

[AND AREA(0 1, 0 0.5):COUPLE(0 1, 0 0.5):0.3]
1girl, long hair, blonde hair, white nurse, frown,

[AND AREA(0 1, 0.5 0.5):COUPLE(0 1, 0.5 1):0.3]
1girl, twintails, blue hair, black maid, surprised,
```

- X のペアは省略不可 → 常に先頭に `0 1,`。
- 3 分割なら `split screen` より `silent comic` 等（split screen は 2 分割に寄る）。

---

## 5. 部分配置（ズームレイヤー）— FILL() 必須

COUPLE 領域がキャンバスを覆い切らないので、base を `FILL()` で領域外に限定する。

```text
sfw, general, simple background,

1girl, serafuku, smile, open mouth,
brown hair, short hair, arms up,
close-up, upper body,

FILL()

[AND AREA(0.7 1, 0.5 0.5):COUPLE(0.7 1, 0.5 1):0.3]
1girl, serafuku, brown hair, short hair, standing, v arms,
```

- FILL() が無いと base が COUPLE 領域にブレンドされ、下地が曖昧だと領域内容が消し飛ぶ。
- AREA 期（COUPLE がまだ 1 つも無い段）では FILL() は無視される。

---

## 6. 3 エリア（MASK → AREA 書き換えの罠）

MASK は始点/終点、AREA は位置/幅なので数字が変わる。

```text
MASK: (0 0.35)   (0.35 0.65)  (0.65 1)
AREA: (0 0.35)   (0.35 0.35)  (0.65 0.35)
```

COUPLE で 3 分割するなら隙間を空ける: `COUPLE(0 0.3)` `COUPLE(0.4 0.6)` `COUPLE(0.7 1)`

---

## 7. タグの遅延適用 / 人数タグの制御

```text
[:(multiple views:0.8):0.3]   ← 初期は無効、後半だけ効かせる
[1girl::0.3]                  ← 序盤だけ効かせて形を固める
```

いずれも **`PCLazyTextEncode` 必須**。

---

## 8. base の書き方

- base にキャラ固有タグ（髪色・目・服）を書かない。COUPLE 時に領域へ滲む。
- `2girls` は必須ではない。誤配置を招くこともあるので、削る / `(2girls:1.1)` と強調するの両方を試す。
- CFG を上げる・総ステップを増やすと反応が良くなる。
