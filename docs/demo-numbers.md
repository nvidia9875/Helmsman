# Demo Video — Before / After 数値 (B-3)

> デモ動画 (Day 14 撮影予定) で使える「効果を数字で示す」素材集。
> 出典は `docs/eval-results.md` の v1 (monitor) vs v3-fixed cheap (goal-driven mini) と
> v4 (cheap + 文書) 計測。同じ 25.7 分の実会議音声 (YouTube マーケ定例) に対する
> 同条件比較。

---

## ヘッドライン 3 連 (動画冒頭スライド用)

### 1. 決定が構造化される

> **0 → 10 件**
>
> ヒト 1 人 (議事メモ無し) では構造化された決定 0 件、
> Helmsman 派遣で **10 件** の「誰が・何を・いつまで」付き決定をキャプチャ。

### 2. 議題が片付く

> **0/5 → 5/5 topics decided**
>
> 同じ 25.7 分。ゴール宣言なしでは topic 抽出すら 0 件。
> ゴール宣言 + Helmsman で **5 個全ての topic を decided 状態に**。

### 3. 安い

> **$0.03 / 会議**
>
> 1 会議あたり LLM コスト約 **3 円**。月 50 会議でも 1,500 円。
> default tier ($0.17) を「決定 1 件あたり 11× 安く」上回る cheap mode が
> 本ハッカソンの想定外好結果。

---

## ビフォア / アフター 比較表 (動画後半に挿入)

同じ 25.7 分の実会議音声に対する計測:

| 観点 | **BEFORE** (Helmsman OFF) | **AFTER** (Helmsman cheap) | 差分 |
|---|---:|---:|---:|
| Topic 抽出 | 0 | 5 | +5 |
| **Topic decided** | 0 | **5/5** | +5 |
| **構造化された決定** | 0 件 | **10 件** | +10 |
| 介入 (L1/L2/L3) | 0 | 15 | +15 |
| Steering 介入 | 0 | 2 | +2 |
| Dissent 介入 | 0 | 3 | +3 |
| LLM コスト | $0 | **$0.03** | +3 円 |
| 平均 tick latency | — | 2.08 sec | — |

> 「Helmsman OFF」は同じ音声を録音しただけ = 議事録なし、構造化なし。
> 「Helmsman cheap」は `--cheap` flag (Decision/Dissent を gpt-5.4-mini に切替)。

---

## モード別 (3-way / cost / quality 比較)

| Mode | 介入 | 決定捕捉 | Topic decided | コスト | Decision あたり |
|---|---:|---:|---:|---:|---:|
| Monitor only (`--goal ""`) | 7 (Dissent only) | 0 | — | $0.08 | — |
| **Cheap (推奨)** | 15 | **10** | **5/5** | **$0.03** | **$0.003** |
| Default (high) | 10 | 5 | 4/5 | $0.17 | $0.034 |

> 「決定 1 件あたり 11× 安く 2 倍捕捉」が cheap mode の特徴。
> default tier は Dissent reasoning が必要な厳格モードでのみ推奨。

---

## RAG 検証 (v4 = cheap + 文書) — 「文書アップで AI が会議中に引用」

戦略 Memo (1KB) を `document_excerpts` に注入した結果:

- **6/6 topics に `document_reference` 自動付与** ✅
  - 「企画配分」→ 「## 3H コンテンツ戦略 (Hero / Hub / Help)」
  - 「KPI 運用」→ 「## KPI と継続観察」
- **DOC-6 矛盾警告 初発火**: 文書と会議の食い違いをリアルタイム指摘
- 文書注入の追加コスト: **+$0.015** (0.044 - 0.029) のみ

> デモシナリオ「文書をアップ → AI が会議中にそれを引用 + 矛盾指摘」を
> リアルタイムで再現可能。

---

## ROI 速算 (README B-1 と整合)

| ペルソナ | 月次工数削減 | Helmsman コスト | ROI |
|---|---:|---:|---:|
| PdM 田中 (週 5 会議) | 8 h × ¥6,000 = ¥48,000 | ¥600 / 月 | **80×** |
| マネジャー 佐藤 (週 10) | 16 h × ¥8,000 = ¥128,000 | ¥1,200 / 月 | **107×** |
| CTO 山田 (週 20) | 32 h × ¥12,000 = ¥384,000 | ¥2,400 / 月 | **160×** |

> 月 1,500 円で議事メモ + 介入 + 決定の構造化が回る = **3,000 円のランチ 1 回 < 1 ヶ月分**。

---

## 撮影台本テンプレ (D-1 用)

### Cold open (15 秒)
> 「会議が終わった瞬間に、Slack に決定 10 件、ToDo 5 件、論点 3 件のメモが届く」
> (画面: Helmsman の Summary パネルを GIF で見せる)

### Hook clip ― 「いま動いている感」5 秒 (P-C1, 2026-05-21 追加)

> **撮影**: Cold open の **最初の 1 cut** を Right Now strip のクローズアップに差し替える。
> 1. Mission Control を 1280×720 で表示
> 2. `Right Now` strip (BotStatusStrip の直下、KPI 行の上) を画面中央へクローズアップ
> 3. cyan の pulsing dot + `LIVE  Listening · 田中 speaking · last decision 12s ago · next nudge in 8s` の monospace 文字列が **2 秒間更新される** のを撮る (数字 countdown が下がる瞬間が欲しい)
> 4. 次の cut へ脱フェード
>
> **ナレーション (上の 5 秒に被せる)**:
> > 「8 agent が今この瞬間、観測している」
>
> **狙い**: 「これは本物の SaaS が動いている」を 5 秒で伝える。
> 審査員が動画冒頭で「触れるプロトタイプか / 本気で動いてるサービスか」を判断する瞬間に勝つ。

### Problem (20 秒)
> 「毎週 15 時間。日本の会社員 1 人当たりの会議時間 (経産省 2023)」
> 「そのうち 40% が議事録なし、決定が来週には記憶から消える」

### Demo (60 秒)
> 1. ゴール宣言 → topic 5 件自動抽出 (3 秒)
> 2. 会議中に 3 つ介入: Steering / Dissent / DecisionCapture (15 秒)
> 3. リアルタイムで topic state が discussing → decided に遷移 (10 秒)
> 4. 終了 → 構造化決定 10 件 (15 秒)

### Equity cut ― Gini クローズアップ 4 秒 (P-C1, 2026-05-21 追加)

> Demo (60 秒) の中盤 (Dissent 介入が出た直後の 4 秒) に挿入:
>
> 1. `MeetingPulse` の **参加者カード** にズーム
> 2. ヘッダ直下の `Equity (Gini)` 行 (例: `0.42  偏重` 赤バッジ) をクローズアップ
> 3. ナレーション: 「**Quiet Activator はこの偏りを z-score で見て、誰を当てるか決めている**」
>
> **狙い**: 「§3.7 Authority Gradient と §5 代弁構造を 1 数字で見せられる」感を出す。
> Dissent 介入 → 偏りが減る → 0.42 → 0.31 と変化する瞬間が撮れたらベスト。

### Report scene (20 秒) — 2026-05-21 追加

> 「会議の後はこう変わる」
> (画面遷移: MeetingRoom → Accordion `会議後レポート · テンプレ + メモから生成` を開く)
>
> 1. 自社の議事録テンプレートを左の textarea に貼る (3 秒)
> 2. 会議中の手書きメモを右の textarea に貼る (3 秒、ペースト)
> 3. 「レポートを生成」クリック → spinner → ~6 秒で markdown プレビュー (8 秒)
> 4. ハイライト: テンプレの `{{decisions}}` が決定文に置換、メモの「KPI 議論不十分」が「⚠️ 事実関係要確認」として注記される (6 秒)

**ナレーション台本**:
> 「会議が終わったら、いつも使ってる議事録テンプレートを貼って、会議中に取ったメモを貼って、生成ボタン。
>  Helmsman は、決定事項を `evidence_quote` 付きで埋め込み、メモと食い違うところは『要確認』と明示。
>  3 秒で、いつもの議事録フォーマットで、6 円分のコストで仕上がる」

**Augmented notes クローズアップ (P-C1, 2026-05-21 追加)**

> 生成結果のプレビュー部で、**memo 由来の行 (白) と Helmsman 構造化由来の行 (灰) の 2 色** が見える瞬間をクローズアップする。
> 画面下に小さく `■ あなたの memo 由来 / ■ Helmsman 構造化由来` の legend が出ているのも 1 cut。
>
> ナレーション差し込み:
> > 「あなたが書いたメモは黒で残る。Helmsman が補ったところは灰色。塗り直さない、ということ」
>
> **狙い**: Granola 由来の "Invisible AI" 哲学が Helmsman の §5 代弁構造と一貫することを 4 秒で伝える。

### Numbers (15 秒)
> **0 → 10 件**: 構造化された決定
> **0/5 → 5/5**: Topic decided
> **$0.03 / 会議**: LLM コスト (8 agents 並列分)
> **$0.01 / レポート**: 会議後レポート生成 (gpt-5.4, テンプレ+メモ取込)
> **= 6 円 / 会議**: 介入 + 構造化 + レポートまで全部

### CTA (10 秒)
> 「Helmsman を Teams 会議に派遣 — `https://kind-glacier-0122f6400.7.azurestaticapps.net`」

---

## 出典

- 計測コード: `scripts/eval_offline.py` (会議介入)
- 計測コード: `scripts/smoke_report.py` (会議後レポート、本番 Azure OpenAI 3 ケース)
- 計測コード: `scripts/smoke_rag.py` (本番 AI Search vector pipeline)
- 元データ: `eval_runs/2026-05-17-*` (5 ラン)
- 詳細解説: `docs/eval-results.md`
- ROI 計算根拠: `README.md` のビジネスインパクト section (B-1)
