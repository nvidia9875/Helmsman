# Helmsman Offline Evaluation Results

> 公開済 25 分の日本語ビジネス会議音声 (YouTube マーケティング戦略会議) を
> オフライン評価ハーネス (`scripts/eval_offline.py`) に通した結果。
>
> 目的:
> 1. パイプラインが実音声で end-to-end 動作することを確認
> 2. ゴール宣言の有無による介入動作の違いを計測
> 3. LLM tier (gpt-5.4 vs gpt-5.4-mini) のコスト/品質トレードオフを評価

## 評価対象

| 項目 | 値 |
|---|---|
| 入力 | MP3 (60 kbps mono) → ffmpeg で 16kHz/16bit/mono WAV に自動変換 |
| 会議時間 | 1,544.7 秒 (25.7 分) |
| ジャンル | 自社マーケティング定例 (実会議をそのまま YouTube 公開した素材) |
| 言語 | 日本語 |
| 参加者 | 2 名 |
| 評価日 | 2026-05-17 |

## 3 通りの設定

| Run | Goal | LLM tier (Decision/Dissent) | STT | 用途 |
|---|---|---|---|---|
| **v1** monitor | (なし) | gpt-5.4 | Speech SDK | 「監視のみ」モードのベースライン |
| **v2** goal-default | "YouTube チャンネル運営方針を決定する" | **gpt-5.4** | Speech SDK | プロダクション相当 |
| **v3** goal-cheap | (同上) | **gpt-5.4-mini** (`--cheap`) | transcript replay | コスト/品質トレードオフ確認 |

## メトリクス

| Metric | v1 monitor | v2 goal | v3 goal-cheap | 備考 |
|---|---:|---:|---:|---|
| Utterances captured | 173 | 173 | 173 | STT 結果は同一 (v3 は v2 の replay) |
| Ticks fired | 26 | 26 | 26 | 45 sec ごと (audio time) |
| Candidates generated | 13 | 33 | **34** | mini も同等数の候補を出す |
| Interventions delivered | 7 | 11 | **3** | Arbiter 通過件数 |
| **Arbiter acceptance** | **53.8 %** | **33.3 %** | **8.8 %** | Arbiter が品質基準で削り込み |
| Topics extracted | 0 | 5 | 5 | GoalDecomposer (gpt-5.4) は両 run で同じ |
| Topics decided | — | 1 | 3 | Coverage が「決定」と判定した数 |
| **LLM cost (USD)** | **$0.0793** | **$0.1801** | **$0.0315** | v3 は v2 の **1/6** |
| Tokens | 21,787 | 107,861 | 111,140 | mini もトークン消費は同等 |
| LLM calls | 25 | 104 | 104 | 同条件 |
| Avg tick latency | 2.82 s | 3.34 s | 2.45 s | mini は若干速い |
| Wall duration | 12.0 min | 12.8 min | **70.7 sec** | transcript モードは STT スキップで爆速 |

### 介入の by-agent 分布

| Agent | v1 | v2 | v3 |
|---|---:|---:|---:|
| SteeringAgent (gpt-5.4-mini) | 0 | **5** | 0 *(候補は 0 ではないが Arbiter 全弾き)* |
| DecisionCapture | 0 | **5** | 2 |
| DissentSurface | **7** | 1 | 1 |
| CoverageTracker | (背景処理) | (背景処理) | (背景処理) |
| QuietActivator | 0 | 0 | 0 |
| TimeKeeper (rule) | 0 | 0 | 0 |

## 質的観察

### v2 (gpt-5.4) で正しく構造化された決定 5 件

実際の会議内で決まった内容を AI が下記の形で捕捉:

1. 「再生回数にフォーカスした目標設定」(平日効果のデータ分析後)
2. **「3H 戦略 (Hero / Hub / Help) で進める」** (役割分担と一緒に決定)
3. 「ペンギンメンバーに資料作らせてスキルセット肌感つかむ」
4. **「ノウハウ動画タイトルは青地に黄色文字テンプレ」** (CTR 改善)
5. 「現状の相関関数で今月予測に使う」(KPI 評価方法)

→ デモ動画でビフォアアフター対比の主軸になる。

### v3 (cheap, mini) の劣化パターン

- **SteeringAgent**: 5 件の redirect 候補を出すが Arbiter が全部 filter 弾き
  - mini の出力は **confidence と evidence_quote 品質が低く**、Arbiter の閾値を割る
- **DecisionCapture**: 5 件 → 2 件に減 (60% 漏れ)
  - 3H 戦略・青黄テンプレ・平日効果が漏れた
  - 残った 2 件 (再生回数 KPI / 試作リソース確認) は正確
- **DissentSurface**: 1 件キープ (差は小さい)

### v1 monitor mode の発見

Goal なしだと **Coverage / Steering / Decision / Quiet が trivial skip** (topics が空のため)。実質 Dissent agent のみ稼働。

→ Helmsman の本質的価値は **ゴール宣言 + 論点分解** で発揮される。Bot を「ただ会議に同席させる」だけでは Dissent しか機能しない。

## コスト分析

| 項目 | v2 (gpt-5.4 keep) | v3 (cheap mini) | 削減率 |
|---|---:|---:|---:|
| GoalDecomposer | $0.0057 | $0.0060 | — |
| CoverageTracker (mini) | $0.0114 | $0.0130 | — |
| SteeringAgent (mini) | $0.0030 | $0.0030 | — |
| DecisionCapture (HIGH→MINI) | **$0.0807** | $0.0049 | **−94 %** |
| DissentSurface (HIGH→MINI) | **$0.0793** | $0.0046 | **−94 %** |
| **合計** | **$0.1801** | **$0.0315** | **−83 %** |

コストの 88% は Decision + Dissent が占める。mini 化で 1/6 に下がるが、**品質劣化が大きいため本番では gpt-5.4 維持を推奨**。

## 推奨運用

| シナリオ | 設定 |
|---|---|
| **本番 (Teams 派遣)** | デフォルト (gpt-5.4 / Decision + Dissent HIGH) — 1 会議 ~$0.20 |
| **プロンプト調整サイクル** | `--cheap` + `--transcript`(同じ utterances を replay) — 70 秒 / $0.03 |
| **STT 単体検証** | `--audio` + monitor mode (`--goal` 空) — Dissent のみ動作で $0.08 |

## 再現方法

```bash
# v1 monitor
uv run python scripts/eval_offline.py --audio recording.mp3 --label monitor

# v2 production
uv run python scripts/eval_offline.py \
    --audio recording.mp3 \
    --goal "<会議のゴール>" \
    --label production

# v3 cheap (要 v2 の utterances.jsonl)
uv run python scripts/eval_offline.py \
    --transcript eval_runs/<v2 run>/utterances.jsonl \
    --goal "<会議のゴール>" \
    --cheap --label cheap
```

出力: `eval_runs/<timestamp>-<label>/` に `metrics.json` / `report.md` / `utterances.jsonl` / `interventions.jsonl` / `candidates.jsonl` / `ticks.jsonl` / `final_meeting.json` が生成される。

## 未解決事項

- Speech SDK が 25 分 mp3 を 2 回連続で途中 cancel する事象を確認 (v3 を transcript モードで実施した理由)。バックオフ + リトライまたは UNMIXED 切替 (本番では既に UNMIXED) で改善見込み
- v3 の Steering 全弾きの原因切り分け: `candidates.jsonl` を見ると confidence は低くないので、Arbiter の評価軸を mini 出力にあわせて調整できるか要検討
- 既存の AGENT_NAME ごとの Arbiter rule (rate limit / mode-conditional) が cheap モードで不利に働いていないか要分析
