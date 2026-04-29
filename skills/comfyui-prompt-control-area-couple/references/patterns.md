# AREA / COUPLE パターン

## 1. 最小パターン

```text
DEF(TIMING=0.5)

[AND AREA(0 0.4):COUPLE(0 0.4):TIMING]
  prompt for left area
```

- `TIMING` までは AREA
- それ以降は COUPLE

## 2. 左右分割

```text
DEF(TIMING=0.5)

[AND AREA(0 0.5):COUPLE(0 0.5):TIMING]
  left prompt

[AND AREA(0.5 0.5):COUPLE(0.5 0.5):TIMING]
  right prompt
```

- 横 0〜0.5 が左
- 横 0.5〜1.0 が右
- 隙間なく並べる

## 3. 上下分割

```text
[AND AREA(0 1, 0 0.5):COUPLE(0 1, 0 0.5):TIMING]
  upper prompt

[AND AREA(0 1, 0.5 0.5):COUPLE(0 1, 0.5 0.5):TIMING]
  lower prompt
```

## 4. キャラ本体 + 局所フォーカス

```text
DEF(TIMING=0.5)
DEF(GIRL_A=1girl, serafuku, smile)

[AND AREA(0 0.4):COUPLE(0 0.4):TIMING]
  [1girl::TIMING], GIRL_A, standing, looking at viewer

[AND AREA(0.4 0.2):COUPLE(0.4 0.2):TIMING]
  [1girl::TIMING], GIRL_A, close-up, pussy focus
```

- 本体を大きい領域で固める
- 局所フォーカスを狭い領域で追加する

## 5. タグの遅延適用

```text
[:(multiple views:0.8):TIMING]
```

- 初期ステップでは無効
- 後半だけ `multiple views` を入れる

## 6. 人数タグの制御

```text
[1girl::TIMING]
```

- 序盤だけ `1girl` を強く効かせる
- 形を固めた後は弱める / 外す
