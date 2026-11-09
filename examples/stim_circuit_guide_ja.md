# Stim 物理回路と論理操作の対応表

生成日: 2026-11-08。Stim 1.15.0、stimflow 1.17.dev0
（pin: `ffe0d043598ed5df0851a3e6b4920359a23fafbd`）を使用。
下記ファイルは既存 example の `main()` が実際にコンパイルした回路から書き出したものです。
元の論理プログラム、ゲート、ノイズ、detector/observable 注釈は変更していません。

## ファイルと行番号

| example / 出力段階 | ideal | noisy (uniform p=0.001) | qubits | raw records | detectors | observables |
|---|---|---|---:|---:|---:|---:|
| two_patch_memory | [two_patch_memory.ideal.stim](two_patch_memory.ideal.stim) (197 行) | [two_patch_memory.noisy.stim](two_patch_memory.noisy.stim) (273 行) | 34 | 82 | 64 | 2 |
| knill_ec_single_round.open | [knill_ec_single_round.open.ideal.stim](knill_ec_single_round.open.ideal.stim) (198 行) | [knill_ec_single_round.open.noisy.stim](knill_ec_single_round.open.noisy.stim) (274 行) | 51 | 74 | 52 | 0 |
| knill_ec_single_round.closed | [knill_ec_single_round.closed.ideal.stim](knill_ec_single_round.closed.ideal.stim) (254 行) | [knill_ec_single_round.closed.noisy.stim](knill_ec_single_round.closed.noisy.stim) (356 行) | 51 | 99 | 72 | 1 |

ideal は noise-free 回路、noisy は実際の物理 noise channel を含む回路です。
Knill の open は `KnillEC` 直後で停止し、B 上の D を測定せずに残します。
closed は同じ prefix に SE×2、論理 H、Z 測定を加えた example の最終回路です。
open に終端測定や `MPP` を補っていません。

**本文の行番号はファイルの1始まり、Stim qubit index・raw measurement index・
detector/observable ID は0始まりです。** ideal/noisy は挿入ノイズのため行番号が異なります。
行を追加すると番号が変わるため、照合時は同時生成のファイルを使用してください。

[stim_line_map.csv](stim_line_map.csv) は全6ファイルの**全行**について、行番号、
物理層、gate/tag、module、論理操作、操作時点の logical ID と block、stage、
測定 record index、detector ID と全支持 block を記載しています。
CSV を file/module/gate で絞ると、並列で入り組んだ操作の行だけを抽出できます。

## 読み方

- 論理 qubit は1個の Stim qubit ではありません。各 d=3 patch は data 9個と
  check ancilla 8個、計17個の物理 qubit からなります。data ID の `D1` と
  論理 ID の `D` は別物です。同じ `D1` は別 block にも存在します。
- `QUBIT_COORDS(x,y) i` が固定された物理 site と global index `i` を定義します。
  `H` やテレポーテーションで index が付け替わることはありません。
- `CX[module0003] ...` の `[module0003]` はコンパイラの primitive fragment ID です。
  composite の `KnillEC` 全体が1個の Stim 命令になるわけではありません。
  module 番号は回路ごとの ID なので、異なる example 間では同じ番号の意味が異なります。
- `CX c0 t0 c1 t1 ...` は左から **control, target** の組です。SE 内の CX は
  data–ancilla interaction、transversal logical CX は data–data interaction です。
- 操作表の行範囲は、その module の tag が付いた命令の最初〜最後の
  **外接範囲**です。並列 module や注釈が範囲内に混在します。正確な各行は
  `[moduleNNNN]` または CSV の `module_id` で確認してください。
- `TICK` は共有物理層の区切りです。CSV の layer 0 は最初の TICK までで、
  TICK 行自体は終了する層に属します。logical operation 1個＝TICK 1個ではありません。
- orientation=0 の X check は ancilla を `RX` で初期化し、ancilla→data の CX と
  `MX` で読み出します。Z check は `R`、data→ancilla の CX、`M` を使います。
  いずれも4層の interaction schedule を通じた stabilizer 測定です。
- `DEPOLARIZE2` は指定 pair、`DEPOLARIZE1` は指定 site の noise、
  `X_ERROR`/`Z_ERROR` は reset 後の誤り、`M(0.001)`/`MX(0.001)` は結果反転です。
  一部の noise と全体 idle noise は tag を持ちません。CSV の module を空欄に
  しており、近傍の1 module に無条件には帰属させていません。対象 site と
  TICK 層を合わせて確認してください。
- tag 内の `\C` は `]` の Stim escape 表記です。量子ゲートや control 指定ではありません。
- `DETECTOR` の tag は check / physical block / anchor module を表します。
  anchor は検出器の全スコープではありません。cross-stage / cross-block の
  record を含むことがあり、CSV の `detector_supporting_blocks` はその全支持です。
- `rec[-k]` はその行までに発生した**全物理測定**から k 個前の結果です。
  他 block の測定も数えます。`m[j]` を0始まり raw index とすると、
  その行までの測定数が N のとき `rec[-k] = m[N-k]` です。
- `SHIFT_COORDS(0,0,dt)` は detector 座標の時間原点を移動する注釈です。
  qubit index や raw record index を移動する量子ゲートではありません。

## 1. two_patch_memory.py

論理プログラムは `data0` の Z 初期化と `data1` の X 初期化を並列実行し、
同時 SE×3、その後同じ基底で destructive measurement します。
初期化内にも SE が1 round あるため、**合計 SE は各 patch 4 rounds**です。
patch0 と patch1 を結ぶゲートはなく、この example に transversal logical CNOT はありません。

| logical ID | 常時使用する physical block | data indices | ancilla indices | init / readout |
|---|---|---|---|---|
| `data0` | `patch0` | 1, 2, 3, 7, 8, 9, 13, 14, 15 | 0, 4, 5, 6, 10, 11, 12, 16 | Z / Z |
| `data1` | `patch1` | 18, 19, 20, 24, 25, 26, 30, 31, 32 | 17, 21, 22, 23, 27, 28, 29, 33 | X / X |

### 論理操作と行

| module | 論理操作 | logical ID → physical block | ideal の行（外接範囲） | noisy の行（外接範囲） |
|---|---|---|---|---|
| `module0000` | `LogicalInit` | data0 → patch0 | 35–56 | 35–76 |
| `module0001` | `LogicalInit` | data1 → patch1 | 36–58 | 37–78 |
| `module0002` | `SyndromeExtraction` | data0 → patch0 | 69–165 | 90–239 |
| `module0003` | `SyndromeExtraction` | data1 → patch1 | 71–167 | 94–241 |
| `module0004` | `LogicalMeasure` | data0 → patch0 | 186 | 261 |
| `module0005` | `LogicalMeasure` | data1 → patch1 | 187 | 262 |

### 全 physical qubit の対応

| Stim index | physical block | local ID | 役割（初期 orientation=0） | QUBIT_COORDS (x,y) |
|---:|---|---|---|---|
| 0 | `patch0` | `X1` | X check ancilla; support=1 2 | (0, 2) |
| 1 | `patch0` | `D1` | data（符号データ） | (1, 1) |
| 2 | `patch0` | `D2` | data（符号データ） | (1, 3) |
| 3 | `patch0` | `D3` | data（符号データ） | (1, 5) |
| 4 | `patch0` | `Z1` | Z check ancilla; support=1 2 7 8 | (2, 2) |
| 5 | `patch0` | `X2` | X check ancilla; support=2 3 8 9 | (2, 4) |
| 6 | `patch0` | `Z2` | Z check ancilla; support=3 9 | (2, 6) |
| 7 | `patch0` | `D4` | data（符号データ） | (3, 1) |
| 8 | `patch0` | `D5` | data（符号データ） | (3, 3) |
| 9 | `patch0` | `D6` | data（符号データ） | (3, 5) |
| 10 | `patch0` | `Z3` | Z check ancilla; support=7 13 | (4, 0) |
| 11 | `patch0` | `X3` | X check ancilla; support=7 8 13 14 | (4, 2) |
| 12 | `patch0` | `Z4` | Z check ancilla; support=8 9 14 15 | (4, 4) |
| 13 | `patch0` | `D7` | data（符号データ） | (5, 1) |
| 14 | `patch0` | `D8` | data（符号データ） | (5, 3) |
| 15 | `patch0` | `D9` | data（符号データ） | (5, 5) |
| 16 | `patch0` | `X4` | X check ancilla; support=14 15 | (6, 4) |
| 17 | `patch1` | `X1` | X check ancilla; support=18 19 | (8, 2) |
| 18 | `patch1` | `D1` | data（符号データ） | (9, 1) |
| 19 | `patch1` | `D2` | data（符号データ） | (9, 3) |
| 20 | `patch1` | `D3` | data（符号データ） | (9, 5) |
| 21 | `patch1` | `Z1` | Z check ancilla; support=18 19 24 25 | (10, 2) |
| 22 | `patch1` | `X2` | X check ancilla; support=19 20 25 26 | (10, 4) |
| 23 | `patch1` | `Z2` | Z check ancilla; support=20 26 | (10, 6) |
| 24 | `patch1` | `D4` | data（符号データ） | (11, 1) |
| 25 | `patch1` | `D5` | data（符号データ） | (11, 3) |
| 26 | `patch1` | `D6` | data（符号データ） | (11, 5) |
| 27 | `patch1` | `Z3` | Z check ancilla; support=24 30 | (12, 0) |
| 28 | `patch1` | `X3` | X check ancilla; support=24 25 30 31 | (12, 2) |
| 29 | `patch1` | `Z4` | Z check ancilla; support=25 26 31 32 | (12, 4) |
| 30 | `patch1` | `D7` | data（符号データ） | (13, 1) |
| 31 | `patch1` | `D8` | data（符号データ） | (13, 3) |
| 32 | `patch1` | `D9` | data（符号データ） | (13, 5) |
| 33 | `patch1` | `X4` | X check ancilla; support=31 32 | (14, 4) |

### 論理測定と OBSERVABLE_INCLUDE

下記の m index は ideal/noisy で共通です。理想状態では初期化した +1 固有状態を
同じ基底で読むため、各 observable の reference-relative flip は0です。

| observable | logical / basis | raw logical parity | ideal OBS 行 | noisy OBS 行 |
|---|---|---|---|---|
| 0 | data0 / Z | m[70] ⊕ m[71] ⊕ m[72] | 192 | 267 |
| 1 | data1 / X | m[75] ⊕ m[78] ⊕ m[81] | 197 | 272 |

## 2. knill_ec_single_round.py

初期状態は physical_D 上の論理 D の +X。A/B は `KnillEC` 内でそれぞれ +X/+Z
として **3 full SE rounds** で準備されます。A→B に transversal CX を実行して
Bell resource を作り、D→A の transversal CX 後、D を X、A を Z で破壊測定します。

| 時点 | logical D の所在 | logical A/B | 状態 |
|---|---|---|---|
| 初期化後 | physical_D | physical_A / physical_B は未初期化 | D の SE は1 round |
| resource preparation / entangling | physical_D | A→physical_A, B→physical_B | resource SE は各3 rounds |
| Bell readout 後（open） | **physical_B** | A/B の logical ID は retired | physical_D / physical_A は measured |
| closed の SE×2・H・最終Z測定 | **physical_B** | retired のまま | D の identity は継続、最後に B を測定 |

物理 index は前後で不変です。移るのは logical identity D の binding です。
B は準備時には resource の logical ID `B`、移転後には persistent ID `D` を担います。

### block ごとの物理 index

| physical block | 全 index（data＋ancilla） | data indices | 担う logical identity |
|---|---|---|---|
| physical_D | 0–16 | 1,2,3,7,8,9,13,14,15 | 初期 D、Bell X 測定で破壊 |
| physical_A | 17–33 | 18,19,20,24,25,26,30,31,32 | resource A、Bell Z 測定で破壊 |
| physical_B | 34–50 | 35,36,37,41,42,43,47,48,49 | resource B → teleport 後の D |

### 全 physical qubit の対応

| Stim index | physical block | local ID | 役割（初期 orientation=0） | QUBIT_COORDS (x,y) |
|---:|---|---|---|---|
| 0 | `physical_D` | `X1` | X check ancilla; support=1 2 | (0, 2) |
| 1 | `physical_D` | `D1` | data（符号データ） | (1, 1) |
| 2 | `physical_D` | `D2` | data（符号データ） | (1, 3) |
| 3 | `physical_D` | `D3` | data（符号データ） | (1, 5) |
| 4 | `physical_D` | `Z1` | Z check ancilla; support=1 2 7 8 | (2, 2) |
| 5 | `physical_D` | `X2` | X check ancilla; support=2 3 8 9 | (2, 4) |
| 6 | `physical_D` | `Z2` | Z check ancilla; support=3 9 | (2, 6) |
| 7 | `physical_D` | `D4` | data（符号データ） | (3, 1) |
| 8 | `physical_D` | `D5` | data（符号データ） | (3, 3) |
| 9 | `physical_D` | `D6` | data（符号データ） | (3, 5) |
| 10 | `physical_D` | `Z3` | Z check ancilla; support=7 13 | (4, 0) |
| 11 | `physical_D` | `X3` | X check ancilla; support=7 8 13 14 | (4, 2) |
| 12 | `physical_D` | `Z4` | Z check ancilla; support=8 9 14 15 | (4, 4) |
| 13 | `physical_D` | `D7` | data（符号データ） | (5, 1) |
| 14 | `physical_D` | `D8` | data（符号データ） | (5, 3) |
| 15 | `physical_D` | `D9` | data（符号データ） | (5, 5) |
| 16 | `physical_D` | `X4` | X check ancilla; support=14 15 | (6, 4) |
| 17 | `physical_A` | `X1` | X check ancilla; support=18 19 | (8, 2) |
| 18 | `physical_A` | `D1` | data（符号データ） | (9, 1) |
| 19 | `physical_A` | `D2` | data（符号データ） | (9, 3) |
| 20 | `physical_A` | `D3` | data（符号データ） | (9, 5) |
| 21 | `physical_A` | `Z1` | Z check ancilla; support=18 19 24 25 | (10, 2) |
| 22 | `physical_A` | `X2` | X check ancilla; support=19 20 25 26 | (10, 4) |
| 23 | `physical_A` | `Z2` | Z check ancilla; support=20 26 | (10, 6) |
| 24 | `physical_A` | `D4` | data（符号データ） | (11, 1) |
| 25 | `physical_A` | `D5` | data（符号データ） | (11, 3) |
| 26 | `physical_A` | `D6` | data（符号データ） | (11, 5) |
| 27 | `physical_A` | `Z3` | Z check ancilla; support=24 30 | (12, 0) |
| 28 | `physical_A` | `X3` | X check ancilla; support=24 25 30 31 | (12, 2) |
| 29 | `physical_A` | `Z4` | Z check ancilla; support=25 26 31 32 | (12, 4) |
| 30 | `physical_A` | `D7` | data（符号データ） | (13, 1) |
| 31 | `physical_A` | `D8` | data（符号データ） | (13, 3) |
| 32 | `physical_A` | `D9` | data（符号データ） | (13, 5) |
| 33 | `physical_A` | `X4` | X check ancilla; support=31 32 | (14, 4) |
| 34 | `physical_B` | `X1` | X check ancilla; support=35 36 | (16, 2) |
| 35 | `physical_B` | `D1` | data（符号データ） | (17, 1) |
| 36 | `physical_B` | `D2` | data（符号データ） | (17, 3) |
| 37 | `physical_B` | `D3` | data（符号データ） | (17, 5) |
| 38 | `physical_B` | `Z1` | Z check ancilla; support=35 36 41 42 | (18, 2) |
| 39 | `physical_B` | `X2` | X check ancilla; support=36 37 42 43 | (18, 4) |
| 40 | `physical_B` | `Z2` | Z check ancilla; support=37 43 | (18, 6) |
| 41 | `physical_B` | `D4` | data（符号データ） | (19, 1) |
| 42 | `physical_B` | `D5` | data（符号データ） | (19, 3) |
| 43 | `physical_B` | `D6` | data（符号データ） | (19, 5) |
| 44 | `physical_B` | `Z3` | Z check ancilla; support=41 47 | (20, 0) |
| 45 | `physical_B` | `X3` | X check ancilla; support=41 42 47 48 | (20, 2) |
| 46 | `physical_B` | `Z4` | Z check ancilla; support=42 43 48 49 | (20, 4) |
| 47 | `physical_B` | `D7` | data（符号データ） | (21, 1) |
| 48 | `physical_B` | `D8` | data（符号データ） | (21, 3) |
| 49 | `physical_B` | `D9` | data（符号データ） | (21, 5) |
| 50 | `physical_B` | `X4` | X check ancilla; support=48 49 | (22, 4) |

### closed の論理操作と行

| module | 論理操作 | logical ID → physical block | ideal の行（外接範囲） | noisy の行（外接範囲） |
|---|---|---|---|---|
| `module0000` | `LogicalInit` | D → physical_D | 52–66 | 52–79 |
| `module0001` | `LogicalInit` | A → physical_A | 73–164 | 87–234 |
| `module0002` | `LogicalInit` | B → physical_B | 74–166 | 89–236 |
| `module0003` | `TransversalCNOT` | A → physical_A, B → physical_B | 185 | 256 |
| `module0004` | `TransversalCNOT` | D → physical_D, A → physical_A | 187 | 260 |
| `module0005` | `LogicalMeasure` | D → physical_D | 189 | 264 |
| `module0006` | `LogicalMeasure` | A → physical_A | 190 | 265 |
| `module0007` | `SyndromeExtraction` | D → physical_B | 201–236 | 277–335 |
| `module0008` | `TransversalH` | D → physical_B | 247 | 347 |
| `module0009` | `LogicalMeasure` | D → physical_B | 249 | 350 |

### open の論理操作と行

| module | 論理操作 | logical ID → physical block | ideal の行（外接範囲） | noisy の行（外接範囲） |
|---|---|---|---|---|
| `module0000` | `LogicalInit` | D → physical_D | 52–66 | 52–79 |
| `module0001` | `LogicalInit` | A → physical_A | 73–164 | 87–234 |
| `module0002` | `LogicalInit` | B → physical_B | 74–166 | 89–236 |
| `module0003` | `TransversalCNOT` | A → physical_A, B → physical_B | 185 | 256 |
| `module0004` | `TransversalCNOT` | D → physical_D, A → physical_A | 187 | 260 |
| `module0005` | `LogicalMeasure` | D → physical_D | 189 | 264 |
| `module0006` | `LogicalMeasure` | A → physical_A | 190 | 265 |

### 2個の transversal CNOT を直接照合する

どちらも9組の data–data CX です。check ancilla は transversal pair に含まれません。
これ以外に SE 用の data–ancilla CX 行が多数あります。

| module | 意味 | open ideal / noisy 行 | closed ideal / noisy 行 |
|---|---|---|---|
| `module0003` | Bell resource A→B | 185 / 256 | 185 / 256 |

```stim
CX[module0003] 18 35 19 36 20 37 24 41 25 42 26 43 30 47 31 48 32 49
```

| local data ID | control index | target index |
|---|---:|---:|
| D1 | 18 (physical_A) | 35 (physical_B) |
| D2 | 19 (physical_A) | 36 (physical_B) |
| D3 | 20 (physical_A) | 37 (physical_B) |
| D4 | 24 (physical_A) | 41 (physical_B) |
| D5 | 25 (physical_A) | 42 (physical_B) |
| D6 | 26 (physical_A) | 43 (physical_B) |
| D7 | 30 (physical_A) | 47 (physical_B) |
| D8 | 31 (physical_A) | 48 (physical_B) |
| D9 | 32 (physical_A) | 49 (physical_B) |

| module | 意味 | open ideal / noisy 行 | closed ideal / noisy 行 |
|---|---|---|---|
| `module0004` | Bell measurement D→A | 187 / 260 | 187 / 260 |

```stim
CX[module0004] 1 18 2 19 3 20 7 24 8 25 9 26 13 30 14 31 15 32
```

| local data ID | control index | target index |
|---|---:|---:|
| D1 | 1 (physical_D) | 18 (physical_A) |
| D2 | 2 (physical_D) | 19 (physical_A) |
| D3 | 3 (physical_D) | 20 (physical_A) |
| D4 | 7 (physical_D) | 24 (physical_A) |
| D5 | 8 (physical_D) | 25 (physical_A) |
| D6 | 9 (physical_D) | 26 (physical_A) |
| D7 | 13 (physical_D) | 30 (physical_A) |
| D8 | 14 (physical_D) | 31 (physical_A) |
| D9 | 15 (physical_D) | 32 (physical_A) |

### Bell readout・H・最終測定

| module | 測定 / 操作 | closed ideal 行 | closed noisy 行 | raw indices（0始まり） |
|---|---|---|---|---|
| module0005 | physical_D の MX (Bell X) | 189 | 264 | 56, 57, 58, 59, 60, 61, 62, 63, 64 |
| module0006 | physical_A の M (Bell Z) | 190 | 265 | 65, 66, 67, 68, 69, 70, 71, 72, 73 |
| module0008 | physical_B data 全9個への H | 247 | 347 | 測定なし |
| module0009 | physical_B の M (最終Z) | 249 | 350 | 90, 91, 92, 93, 94, 95, 96, 97, 98 |

Bell の論理 raw parity は次のとおりです。これらは intrinsic にランダムで、
単独の zero-expected observable/detector ではありません。

- `m_X = m[58] ⊕ m[61] ⊕ m[64]`（physical_D の D7, D4, D1）
- `m_Z = m[71] ⊕ m[72] ⊕ m[73]`（physical_A の D3, D2, D1）
- symbolic Bell byproduct は `X_L^(m_Z) Z_L^(m_X)`。この `.stim` に
  shot-dependent な補正ゲートは入りません。準備 sector の physical frame も別途必要です。

closed の H は physical_B の data にだけ作用し、code orientation を0→1へ変更します。
そのため最終Zの logical representative は D3,D6,D9 となります。H 前の代表を
そのまま当てはめないでください。B 上の SE は H **前**に2 rounds 実行され、
準備時の3 rounds と合わせて syndrome history の round_index は0〜4になります。

最終 readout は Stim 命令の target 順に `m[90]`（B.D9）から
`m[98]`（B.D1）へ入ります。local ID 昇順と raw record 順は逆です。

closed の observable 0 は、最終 raw parity だけではありません。書き出された式は

```text
OBS0 = m[58] XOR m[61] XOR m[64]
     XOR m[82] XOR m[83] XOR m[84] XOR m[85]
     XOR m[90] XOR m[93] XOR m[96]
```

実際の Stim 行では、最終測定数 N=99 に対する相対参照になっています。

```stim
OBSERVABLE_INCLUDE(0) rec[-41] rec[-38] rec[-35] rec[-17] rec[-16] rec[-15] rec[-14] rec[-9] rec[-6] rec[-3]
```

たとえば `rec[-17] = m[99-17] = m[82]` です。

ここで `m[82..85]` は physical_B の最終 SE round の X1..X4、
`m[90],m[93],m[96]` は H 後の Z logical representative の raw data parity です。
H 前の旧 X logical support は D1,D4,D7 です。旧 X1..X4 の support を
GF(2) で足すと D1,D3,D4,D6,D7,D9 となり、これは旧 support と H 後の
Z representative D3,D6,D9 の対称差です。したがって4個の check sector 符号の
XOR が、H による representative の取り直しを補う項になります。

Bell X parity とこの code-frame representative 変更に伴う affine correction
が観測量に含まれます。理想 observable flip が0でも、最終 data の raw parity
そのものや各 Bell bit が常に0という意味にはなりません。

OBSERVABLE_INCLUDE は closed ideal **254行**、
closed noisy **355行**です。
open は observable が0個で、最終 logical measurement を合成していません。
両回路は canonical な全 global detector を保持し、decoder 境界で省略していません。
この example は preparation corrections を未解決のまま出力する回路生成デモです。
OBS の flow 検証と、デコード後の physical/logical state recovery の主張は区別してください。

## 再生成と機械的な照合

リポジトリ直下から以下を実行すると、同じ example の返す artifact から6個の
`.stim` を再生成します（既存 `.stim` を上書き）。logical program は exporter に
重複定義せず、元の2つの example を呼び出します。

```bash
python examples/export_stim_circuits.py
```

exporter は Stim text を読み戻して元回路との **完全一致** を確認し、
浮動小数点の丸めで意味が変わる場合は書き出しを拒否します。今回の p=0.001 は
全6ファイルで一致しています。コードや依存版を変更して再生成した場合、
この解説と CSV の行番号は自動更新されないため、対応表も合わせて更新してください。

```python
import stim
c = stim.Circuit.from_file("examples/knill_ec_single_round.closed.ideal.stim")
dets, obs = c.compile_detector_sampler(seed=9).sample(100, separate_observables=True)
assert not dets.any() and not obs.any()
dem = c.detector_error_model()
```

確認済み: 全6ファイルの元回路との一致、Stim parse / DEM 構成、全 metadata 対応、
理想回路の100-shot detector/observable parity、および noisy の raw record から
同一バッチの detector/observable parity の再構成。decoder の性能をこの
テキスト出力から評価したものではありません。
