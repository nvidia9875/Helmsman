# Helmsman Offline Evaluation Results

> 公開済 25 分の日本語ビジネス会議音声 (YouTube マーケティング戦略会議) を
> オフライン評価ハーネス (`scripts/eval_offline.py`) に通した結果。
>
> 目的:
> 1. パイプラインが実音声で end-to-end 動作することを確認
> 2. ゴール宣言の有無による介入動作の違いを計測
> 3. LLM tier (gpt-5.4 vs gpt-5.4-mini) のコスト/品質トレードオフを評価
> 4. Arbiter rate_limit が eval (時間圧縮) 環境で正しく動くことを確認

## 評価対象

| 項目 | 値 |
|---|---|
| 入力 | MP3 (60 kbps mono) → ffmpeg で 16kHz/16bit/mono WAV に自動変換 |
| 会議時間 | 1,544.7 秒 (25.7 分) |
| ジャンル | 自社マーケティング定例 (実会議をそのまま YouTube 公開した素材) |
| 言語 | 日本語 |
| 参加者 | 2 名 |
| 評価日 | 2026-05-17 |

## 5 通りの設定

| Run | Goal | LLM tier (Decision/Dissent) | 文書 | 入力 |
|---|---|---|---|---|
| **v1** monitor | (なし) | gpt-5.4 | — | Speech SDK 音声 |
| **v2** goal-buggy | "YouTube チャンネル運営方針を決定する" | gpt-5.4 | — | Speech SDK 音声 (rate_limit バグの影響あり) |
| **v2-fixed** goal | (同上) | gpt-5.4 | — | transcript replay (rate_limit 修正後) |
| **v3-fixed** cheap | (同上) | **gpt-5.4-mini** (`--cheap`) | — | transcript replay (rate_limit 修正後) |
| **v4** cheap+doc | (同上) | gpt-5.4-mini | **YouTube 戦略 Memo (合成 1KB)** | transcript replay (`--doc-text`) |

> v2 と v2-fixed は **同じ utterances を入力**。違いは Arbiter rate_limit が
> wall-time (バグ) か audio-time (修正後) かのみ。
> v4 は v3-fixed と同条件 + `--doc-text` で合成文書を `document_excerpts` に注入。

## メインメトリクス比較

| Metric | v1 monitor | v2 buggy | **v2-fixed** | **v3-fixed cheap** | **v4 cheap+doc** |
|---|---:|---:|---:|---:|---:|
| Utterances | 173 | 173 | 173 | 173 | 173 |
| Topics extracted | 0 | 5 | 4 | 5 | **6** |
| **Topics decided** | — | 1 | **4** | **5** | **4** |
| **document_reference 付き topics** | 0/0 | 0/5 | 0/4 | 0/5 | **6/6** ✅ |
| Candidates → Delivered | 13→7 | 33→11 | 26→10 | 33→15 | **42→17** |
| Arbiter acceptance | 53.8 % | 33.3 % | 38.5 % | 45.5 % | 40.5 % |
| **Interventions delivered** | 7 | 11 | 10 | 15 | **17** |
| **Decisions captured** | 0 | 5 | 5 | 10 | **12** |
| **DOC-6 矛盾警告 fired** | 0 | 0 | 0 | 0 | **1** ✅ |
| **LLM cost (USD)** | $0.0793 | $0.1801 | $0.1720 | **$0.0294** | $0.0447 |
| Cost / decision captured | — | $0.036 | $0.034 | $0.003 | **$0.0037** |
| LLM total tokens | 21,787 | 107,861 | 103,708 | 105,902 | 159,116 |
| LLM calls | 25 | 104 | 98 | 100 | 105 |
| Avg tick latency | 2.82 s | 3.34 s | 2.56 s | 2.08 s | 2.91 s |
| Wall duration | 12.0 min | 12.8 min | 73 sec | 61 sec | 81 sec |

## 介入の by-agent 分布

| Agent | v1 | v2 buggy | v2-fixed | v3-fixed cheap |
|---|---:|---:|---:|---:|
| SteeringAgent (gpt-5.4-mini 共通) | 0 | 5 | 0 | 2 |
| DecisionCapture | 0 | 5 | **5** | **10** |
| DissentSurface | 7 | 1 | 5 | 3 |
| QuietActivator | 0 | 0 | 0 | 0 |
| TimeKeeper (rule) | 0 | 0 | 0 | 0 |

## 重要な発見

### 1. Arbiter rate_limit は wall_time ベースで eval は audio-time 圧縮が起きていた

- **Bug**: `Arbiter._can_intervene` が `datetime.now(UTC) - last_intervention_at` を見ていた
- **Symptom**: transcript replay (25 min 音声を 70 秒 wall で再生) では、1 件 deliver した後ほぼ全候補が rate_limit (60s wall) で弾かれていた
- **Fix**: `Arbiter.decide(..., now=...)` 引数を追加。eval runner が `audio_now = run_started_at + audio_offset_accum` を渡す
- **Impact**: v3 (cheap) の deliveries が 3 → **15 件 (5×)** に増加。以前の「mini は品質劣化大」結論が誤りだった

### 2. **cheap モード (gpt-5.4-mini) が default (gpt-5.4) を上回る** — 本ハッカソンの想定外好結果

| 観点 | v2-fixed (high) | v3-fixed (cheap) |
|---|---|---|
| 決定捕捉数 | 5 件 | **10 件** (2 倍) |
| 平日効果 / 3H 戦略 / 青地黄字テンプレ | 一部 | **全部** + ヒーロー本数決定など追加 |
| Steering 介入 | 0 件 (mini 候補は出てたが弾かれてた) | 2 件 |
| Dissent | 5 件 (細かい懸念点) | 3 件 (主要懸念のみ) |
| トータルコスト | $0.17 | **$0.03** (1/6) |
| **決定 1 件あたり** | $0.034 | **$0.003** (1/11) |

仮説:
- gpt-5.4 の reasoning depth は本タスク (構造化された会議の決定捕捉) では過剰
- mini は granular な決定をより多く拾う傾向 (会議の細部までカバー)
- ただし Dissent の reasoning は浅め → v2-fixed の方が長期影響の懸念を多く出している

### 3. monitor mode (v1) は実質 Dissent agent のみ稼働

Goal なしだと CoverageTracker / Steering / DecisionCapture / Quiet が trivial skip (topics 空のため)。Dissent agent だけが動作。**Helmsman の本質は「ゴール宣言で論点分解 → 5 agents 並列稼働」**。

### 4. v2-fixed の Steering 0 件は仕様通り

mini Steering 候補は 7 件出ていたが、Arbiter で Decision (priority 100) と競合し、Decision がほぼ全 tick で優先採用されたため Steering の出番がなかった。**rate_limit ではなく priority ソートの結果**。

## コスト分析

| Agent | v2-fixed (high) | v3-fixed (cheap) | 削減率 |
|---|---:|---:|---:|
| GoalDecomposer (high) | $0.0052 | $0.0060 | — |
| CoverageTracker (mini) | $0.0114 | $0.0117 | — |
| SteeringAgent (mini) | $0.0027 | $0.0027 | — |
| DecisionCapture | $0.0728 | $0.0046 | **−94 %** |
| DissentSurface | $0.0799 | $0.0044 | **−94 %** |
| **合計** | **$0.1720** | **$0.0294** | **−83 %** |

`--cheap` は **DecisionCapture と DissentSurface を mini に落とす**。両 agent はそれぞれ ~50% のコスト占有 (high tier 時)。

## 推奨運用 (本結果を踏まえて)

| シナリオ | 設定 |
|---|---|
| **本番 (Teams 派遣) - cost-optimal** | `--cheap` 相当 (Decision + Dissent も mini) — 1 会議 ~$0.03 |
| **本番 (Teams 派遣) - quality-optimal** | デフォルト (Decision + Dissent gpt-5.4) — 1 会議 ~$0.18 |
| **プロンプト調整サイクル** | `--cheap` + `--transcript` (utterances replay) — 60 秒 / $0.03 |
| **STT 単体検証** | `--audio` + monitor mode (`--goal` 空) — Dissent のみ動作で $0.08 |

> **更新**: 当初は「cheap モードは dev 用」と書いたが、再評価で **本番 cost-optimal 設定として推奨可** に格上げ。Dissent の reasoning depth が必要な厳格モードでのみ default 推奨。

## 文書 RAG (DOC-*) 検証 — v4 で完全動作確認

v4 (`--doc-text scripts/fixtures/youtube_strategy_memo.txt`) で合成戦略 Memo (1 KB) を
注入した結果:

- **6/6 topics に `document_reference` が自動付与** された
  - 企画配分 → 「## 3H コンテンツ戦略 (Hero / Hub / Help)」
  - 制作体制 → 「## 制作リソース」
  - 見た目方針 → 「## 視覚デザイン」
  - 商談導線 → 「## 商談導線」
  - KPI 運用 → 「## KPI と継続観察」
- **DOC-6 矛盾警告が初発火**: DecisionCapture が「⚠️ 文書と矛盾の可能性: 参考文書『YouTube Channel Strategy Memo』のKPI と継続観察では『再生回数を主目標に』としているが …」を出力。文書と会議の食い違いをリアルタイム指摘
- GoalDecomposer の topic 名が文書のセクション名と意味的に揃う (e.g.「KPI運用」)
- 介入数 +2 (15 → 17)、決定捕捉 +2 (10 → 12)
- 文書注入コスト: +$0.015 (0.044 - 0.029)、入力 token +50%

**結論**: RAG 経路 (document → Coverage / Decision → topics / interventions)
は完全動作。Demo シナリオで「文書をアップ → AI が会議中にそれを引用 + 矛盾指摘」
を再現可能。

## Speech SDK 安定性

- Speech SDK が 25 分 mp3 を 2 連続で途中 cancel する事象を確認
- 修正: 長 WAV を 8 分単位でチャンク分割 (Microsoft 推奨パターン) + SDK 停止を timeout 付き ack
- v2-fixed と v3-fixed はどちらも transcript replay (= STT スキップ) のため、Speech SDK 修正は別途 audio 入力で smoke 検証要

## 再現方法

```bash
# v1 monitor (Speech SDK + 音声)
uv run python scripts/eval_offline.py --audio recording.mp3 --label monitor

# v2-fixed production (transcript モードで高速イテレーション)
uv run python scripts/eval_offline.py \
    --transcript eval_runs/<earlier-run>/utterances.jsonl \
    --goal "<会議のゴール>" --label production

# v3-fixed cheap
uv run python scripts/eval_offline.py \
    --transcript eval_runs/<earlier-run>/utterances.jsonl \
    --goal "<会議のゴール>" --cheap --label cheap
```

出力: `eval_runs/<timestamp>-<label>/` に `metrics.json` / `report.md` / `utterances.jsonl` / `interventions.jsonl` / `candidates.jsonl` / `ticks.jsonl` / `final_meeting.json` が生成される。

## 関連修正

- `commit 3a1f592`: Arbiter clock injection for eval correctness
- `commit 1899ad1`: Speech SDK chunking + bounded stop wait
- `commit f58b2fe`: `--cheap` flag (Decision + Dissent → mini)
- `commit pending`: `--doc-text` flag for RAG validation
