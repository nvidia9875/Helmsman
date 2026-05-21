# Helmsman ブラッシュアップ提案 (2026-05-21)

> 世界の Meeting AI / Agent 系プロダクト + デザイン語彙 + アカデミック文献を横断調査し、
> 「Helmsman を一段引き上げるための具体提案」を **インパクト × 実装コスト** で並べたもの。
> 大半は審査前 (5/22-6/1) に実装可能で、Zenn 記事の説得力も増す方向に揃えた。

---

## 0. 調査対象サマリ

| カテゴリ | 参考プロダクト / ソース | 一行特徴 |
|---|---|---|
| 議事録 AI | Granola, Otter, Fathom, Fireflies, tl;dv, MeetGeek | "augmented notes" / 自由メモ強化 / 既存ハイライト機能 |
| リアルタイム介入系 | Cluely, Otter AI Chat, Read.ai | 画面オーバーレイ / live chat / Meeting Score (sentiment+engagement) |
| エンタープライズ | Sembly (Glance View), Spinach.io (AI Scrum), Microsoft Teams Premium Facilitator | 構造化 digest / agile 特化 / 公式 facilitator |
| 基盤 | Recall.ai (meeting bot API), Hume EVI (empathic voice) | bot infra / 感情応答 voice |
| 観測性 | LangSmith, Sentry AI Agents, Datadog DASH 2025 | trace + tool call + cost panel |
| UI 語彙 | Linear (2025 redesign), Vercel/Geist, Bloomberg Terminal, Granola | 単色 + 高密度 + monospace 数値 |
| アカデミック | "Observe, Ask, Intervene" CHI 2025 (Houtti et al.) | OAI フレーム = 介入前に質問する設計 |
| 戦略 | Microsoft Work Trend Index 2025 "Frontier Firm" 4 patterns | Author / Editor / Director / Orchestrator |

---

## A. インパクト大 × 実装小 (≤ 半日)

### A-1. Zenn 記事に「OAI フレームとの位置付け」を入れる ★最優先
**現状**: Arbiter の "Density-aware silence + Authority Gradient" を「論文化レベル」と書いたが、CHI 2025 の **OAI (Observe, Ask, Intervene)** フレームに直接ぶつけて差別化していない。

**提案**: §4.6「論文化レベル」のサブセクションを書き換え、CHI 2025 OAI を引用。

```markdown
### 4.6 既存研究との位置付け ― CHI 2025 OAI フレームを超えて

最も近い先行研究は CHI 2025 の **"Observe, Ask, Intervene" (OAI)**
(Houtti et al., U. of Minnesota, 68 名 12 グループ実験)。
参加者は「介入前に AI が質問する」ことを好み、完全自律よりも OAI を選好した。

Helmsman の Arbiter はこの OAI を**実運用可能な形に拡張**:
- OAI = Observe / Ask / Intervene の 3 段階
- Helmsman = それを **L1 (chair-only ささやき) / L2 (全員サイドバー) / L3 (音声発話)**
  にマッピングしつつ、**Density-aware silence + Authority Gradient + Mode-conditional**
  の 3 軸で「いつ」を判定 → OAI の "Ask" を構造的に置き換える

学術的に「Ask」フェーズは「介入候補をユーザーに見せる」処理であり、
Helmsman の L1/L2 はまさに Ask に相当する。L3 だけが真の Intervene。
```

**効果**: 「個人開発でもアカデミックに位置付けられている」と審査員に伝わる。記事の説得力 +2 段階。
**工数**: 30 分 (1 段落書き換え)。

---

### A-2. ヘッドラインに「Frontier Firm の Orchestrator パターン」を接続
**現状**: 記事冒頭で "Agentic AI" の定義を Anthropic + Microsoft Build 2024 で説明しているが、
Microsoft 2025 の最重要メッセージ **"Frontier Firm" の 4 work patterns** (Author/Editor/Director/Orchestrator) と接続できていない。

**提案**: §3.1 (Agentic AI とは) を以下に拡張。

```markdown
### 3.1 Agentic AI とは — Microsoft "Frontier Firm" 4 パターンとの対応

Microsoft Work Trend Index 2025 は AI と人間の協業を 4 パターンで定義した:

| Pattern | 主導 | Helmsman 該当 |
|---|---|---|
| Author | 人間 | 議事録手入力 (旧来) |
| Editor | AI 初稿 → 人間が編集 | 議事録 AI (Otter / Granola) |
| Director | 人間が仕様 → AI 実行 | レポート生成 (§11) |
| **Orchestrator** | **複数 agent 並列 + 人間が例外対応** | **Helmsman 本体** |

Helmsman は **Orchestrator パターンの実装サンプル**。
8 agent が並列で観測・分析し、人間 (chair) は L1/L2/L3 の介入を承認/却下するだけ。
Microsoft 自身の 2025 ビジョンを個人開発で具体化したのが本作の位置付け。
```

**効果**: ハッカソン審査は Microsoft の語彙で語った方が刺さる。"Frontier Firm" は 2025 の最重要キーワード。
**工数**: 30 分。

---

### A-3. Read.ai 由来「Meeting Score」を OFF/ON 比較に追加
**現状**: BEFORE/AFTER 表 (§7.2) で「決定数 / 介入数 / コスト」を出しているが、Read.ai の **Read Score** (sentiment × engagement) の概念は使っていない。

**提案**: 既存 `MeetingPulse.tsx` の `computeTemperature()` が既に temperature を出しているので、
これを **"Helmsman Score" (0-100)** として正式に名付け、KPI ストリップに追加。

```typescript
// apps/web/src/lib/score.ts (新規)
export function computeHelmsmanScore(m: Meeting): number {
  const coverageScore = (m.topics.filter(t => t.state === 'decided').length / Math.max(1, m.topics.length)) * 40;
  const interventionScore = Math.min(30, m.delivered_interventions.length * 3);
  const decisionScore = Math.min(20, m.decisions_count * 2);
  const timeScore = m.bot_status === 'in_call' ? 10 : 0;
  return Math.round(coverageScore + interventionScore + decisionScore + timeScore);
}
```

Landing/MeetingRoom の KPI 行に 1 つ追加するだけ。Read.ai の "Read Score" を上回る具体性 (Read は感情ベースで因果不明、Helmsman は構造化決定ベース) を主張できる。

**効果**: 「会議が良かったか」を 1 数字で語れる → デモのキャッチが強くなる。
**工数**: 2-3 時間 (関数 + KPI 表示 + 表記の調整)。

---

### A-4. ダッシュボード冒頭に「Right Now ストリップ」を追加 (Granola/Linear 由来)
**現状**: MeetingRoom が `BotStatusStrip` を上に置いているが、「今何が起きているか」を 1 行で語る要素がない。Granola の「右上の今録音中インジケータ」、Linear の "Recent activity" ストリップが参考。

**提案**: KpiRow の真上に 1 行の "Right Now" ストリップ。

```
[●LIVE] Listening · 田中 speaking · last decision 3 min ago · next nudge in 12s
```

`apps/web/src/components/RightNowStrip.tsx` を新規作成。
- 1 行 / 高さ 32px / monospace
- pulsing ドット (`.glow-active` 既存) + 最新発話者 + 直近決定 + 次のテック
- `meeting.delivered_interventions[last].delivered_at` から `since` 計算

**効果**: デモ動画の冒頭 5 秒で「いま動いている感」を伝えられる。
**工数**: 2-3 時間。

---

### A-5. Granola の "augmented notes" を Report Panel に移植
**現状**: `ReportPanel` は memo + template を入れたら markdown が返るだけ。Granola の **「自分のメモは黒、AI 補強は灰色」** の augmented design に学ぶ。

**提案**: 生成済みレポート表示で、ユーザー memo に由来した行と Helmsman 構造化に由来した行を視覚的に区別。

```tsx
// ReportPanel の preview レンダリング
// memo に含まれる substring の行 → text-1 (黒/白)
// それ以外 → text-2 (灰色)
// 引用 (> ...) → accent border-left (既存)
```

実装は markdown を行単位で splitし、memo の substring match で 2 段着色するだけ。

**効果**: 「あなたが書いたことを Helmsman は塗り直さない」という Granola 由来の "invisible AI" 哲学が現れる。
**工数**: 2-3 時間。

---

## B. インパクト大 × 実装中 (1-2 日)

### B-1. "Cluely 風" Real-Time Coach パネル (sales / interview 系の介入カード)
**現状**: InterventionFeed は「過去の介入が流れる」設計。Cluely は **「いま何を言うべきか」を画面に出す** 設計。

**提案**: 会議中の Sidebar に "Coach" タブを 1 つ追加。
- 直近 30s の発言を読んで、chair に対してだけ表示される L1 ささやき:
  - 「次は『launch_date』の決定が必要です」
  - 「鈴木さんの懸念 (10 分前) がまだ未解決」
  - 「決定基準を 1 文で言うと?」

これは既存の `SteeringAgent` の出力を「過去 5 件」ではなく「今出ている 1-3 件」として表示し直すだけ。Cluely の "live battlecard" を「会議司会者の battlecard」に転用。

**効果**: 介入の "受け身フィード" から "能動的コーチング" に進化。デモでの説得力 +1 段。
**工数**: 1 日 (UI + 既存 agent 出力の再配線)。

---

### B-2. Fathom 風「ハイライト 1-click」+ クリップ共有
**現状**: 介入や決定が流れるが、「ここが重要だった」を残す UI がない。Fathom は **magic highlight button** が代表機能。

**提案**: 各 Utterance / Decision / Intervention に hover で出る 🔖 ボタン。
- click → `meeting.highlights[]` に `{utterance_id, timestamp, note?}` 追加
- 会議後レポートに「ハイライト集 (chair が手で選んだもの)」セクション自動挿入
- 共有可能 URL `/meetings/{id}/h/{highlight_id}` で 30 秒切り出し再生 (audio_url が将来あれば)

**効果**: 「議事録の AI 自動 + 人間の手選び」のハイブリッド。ReportPanel の memo + template と思想的に一致。
**工数**: 1.5 日。

---

### B-3. LangSmith 風 "Agent Trace" Inspector を追加
**現状**: `eval_runs/*/` に JSONL が落ちているが、Web UI で見るには別ツールが必要。LangSmith / Sentry AI Agents の trace ビューが世界標準。

**提案**: `/meetings/{id}/trace/{tick_id}` という新ルートを追加。
- 横軸 = 時間軸 (60 分の会議)
- 縦軸 = 8 agent
- 各 tick で agent が出した候補 / Arbiter が drop した理由 / final delivery
- click で prompt/response/cost も見える

これは「審査員が触った時の納得感」を爆増させる。Datadog DASH 2025 の execution flow chart が直近の SOTA。

**効果**: 「Agentic AI のデバッグを log 漁りではなく決定論的 replay にできる」(§6.7) を実画面で証明。
**工数**: 1.5-2 日。記事内に static スクショ載せるだけでも価値あり。

---

### B-4. Command Palette (Cmd+K) — Cluely/Linear 由来
**現状**: ナビは Sidebar のリンクと CreateMeeting ボタンのみ。

**提案**: `Cmd+K` で開く palette。
- 「会議を始める」「直近の会議に戻る」「Bot を派遣」「テンプレ A でレポート生成」
- Headless UI / cmdk ライブラリで 200 行 + 既存 store と接続するだけ

**効果**: 「Power user 向け」感が出る。Linear 由来の世界観に合う。
**工数**: 半日。

---

## C. インパクト中 × 実装小 (≤ 半日)

### C-1. Sembly "Glance View" 風の会議 Digest URL
**現状**: 会議終了後はダッシュボードでしか結果が見られない。

**提案**: `/meetings/{id}/glance` で **A4 1 枚** に収まる "Glance View" ページ。
- 上 30%: ゴール / 5 topics / 状態 stamp (decided/parked)
- 中 40%: 決定 10 件 + evidence_quote
- 下 30%: 未解決 concerns + document_conflicts

PDF 出力ボタン (`window.print()`) を 1 つ置けば PDF 化も無料。社内共有 / Slack 投稿が捗る。

**工数**: 半日。

---

### C-2. Spinach.io 風 "Sprint Mode" テンプレ
**現状**: ゴールは自由文。Sprint planning / Daily / Retro のような **会議タイプ別テンプレ** がない。

**提案**: CreateMeeting 画面の「ゴール」欄の隣に "Templates" ボタン。
- Sprint Planning / Daily Standup / 1on1 / 顧客 Discovery / 役員 Decision の 5 種
- 選ぶと goal + topics + 時間配分が prefill される

Spinach.io は Atlassian Marketplace で評価されている方向。Helmsman のゴール駆動と相性が良い。

**工数**: 半日 (テンプレ 5 個 + UI)。

---

### C-3. Read.ai 由来 "Participation Equity" バー (既存 MeetingPulse 拡張)
**現状**: `MeetingPulse.tsx` で発言量 bar は既に出している。

**提案**: そのバーの上に **Gini 係数** (`G = Σ|x_i - x_j| / 2n²μ`) を 1 数字で表示。
- 0.0 = 完全平等 / 0.5+ = 偏重
- 既存の Quiet Activator の z-score と整合性ある

**工数**: 1-2 時間。

---

### C-4. Hume EVI 由来 "Tone-aware" TTS の言及 (将来形として記事に)
**現状**: TTS は Azure Speech Nanami の固定 prosody。Hume EVI は感情に合わせて speech 生成。

**提案**: 記事の Phase 6 に「Hume EVI 統合で、緊張時は柔らかいトーン / 切迫時はキビキビと」を追加。実装はしないが、ロードマップとして書くと記事の格が上がる。

**工数**: 0 (記事 1 段落のみ)。

---

## D. 記事 (Zenn) の構造改善 — Anthropic 流に寄せる

### D-1. 冒頭にスクショ 1 枚 + 5 行で全部分かる "What it looks like"
Anthropic / Granola の記事はどちらも **冒頭にプロダクト画面が 1 枚 + caption** が来る。
TL;DR の前に Mission Control の 1 枚を貼る。**Right Now strip + KPI + 介入フィード** が見える 1 枚を 1280x720 で。

### D-2. 「失敗から学んだこと」を 1 セクションにまとめる
現状 §6 の中に散らばっているが、Anthropic の "Building Effective Agents" は **What didn't work** を独立章として持つ。
- ACS TeamsMeetingLinkLocator が存在しなかった事件 (§6.4)
- Arbiter rate_limit が wall-clock 依存だった事件 (§6.1)
- Cheap mode が quality を超えた事件 (§6.2)
- Decision Capture の memo 過信問題 (§3.8)

を「§X. 4 つの "盛大に間違えた瞬間"」として独立化 → 個人開発者が読みたくなる構造。

### D-3. Microsoft 公式コンセプトを脚注で全部リンク
- "Frontier Firm" → Microsoft Work Trend Index 2025
- "Orchestrator pattern" → 同上
- "Intelligent Recap / Facilitator" → Learn ドキュメント
- "Multi-agent orchestration (Build 2025)" → Copilot Studio blog

審査員は Microsoft の公式語彙でレビューするので、それを記事内で使い切ると有利。

### D-4. 比較表は「Granola / Cluely / Read.ai / Facilitator / Helmsman」の 5 列で
現状 §8 は Facilitator との比較のみ。世界の代表 4 製品との比較表に拡張すると、ポジショニングが明確になる。

| 軸 | Granola | Cluely | Read.ai | MS Facilitator | **Helmsman** |
|---|---|---|---|---|---|
| 介入の能動性 | なし (事後) | live coach (個人のみ) | dashboard | テキストメイン | **音声 + テキスト** |
| メタロジック | — | — | engagement | — | **6 段階 Arbiter** |
| 多agent | 1 | 1 | 1 | 1 | **8 並列** |
| 価格 | $14/月 | $19/月 | $19.75/月 | $30/月 + M365 | **¥1,200/月相当** |
| OSS | ❌ | ❌ | ❌ | ❌ | **✅ MIT** |

### D-5. 「2026 年の AI Meeting カテゴリマップ」を 1 枚図解
4 象限 (横 = 事前/最中/事後, 縦 = 受動/能動) で各製品をプロット。Helmsman は唯一の「最中 × 能動」象限。
Excalidraw or mermaid で 30 分。

---

## E. UI 細部のポリッシュ (Linear / Vercel / Bloomberg 由来)

| 提案 | Where | Why | 工数 |
|---|---|---|---|
| 数値は全部 monospace + tabular-nums | 既に大半済 — 取りこぼし確認 | Vercel Geist の原則 | 1 時間 |
| Status dot は色 + 形 (●/▲/✓) | StatusDot.tsx | a11y (色覚) | 1 時間 |
| `oklch()` palette 採用 (pure black `oklch(0 0 0)` 等) | global.css | Vercel 2025 ベスト | 1 時間 |
| 区切り線をやめて空白に | 複数 panel | Linear 2025 redesign で実証済 | 1 時間 |
| 数字 KPI に "delta" バッジ (前回比 +12%) | Kpi.tsx | Bloomberg 由来 | 2 時間 |
| InterventionFeed に "filter by agent" chip | InterventionFeed.tsx | データ密度↑ | 半日 |
| L3 音声介入のボタンは🎙️アイコン + scanline animation | InterventionFeed.tsx | demo 映え | 1 時間 |

---

## F. 優先順位の推奨 (5/22-6/1 の 10 日間で最大効果)

| 日 | やること |
|---|---|
| 5/22 (Day 1) | A-1 (OAI フレーム引用) + A-2 (Frontier Firm) + D-4 (5 列比較表) + D-5 (象限マップ) **— 記事 Day** |
| 5/23 (Day 2) | A-3 (Helmsman Score) + A-4 (Right Now strip) + A-5 (augmented report) **— UI 一斉 polish Day** |
| 5/24 (Day 3) | B-1 (Coach panel) **— 唯一の機能追加 Day** |
| 5/25 (Day 4) | B-3 (Agent Trace inspector) **— "観測性が独自" の主張を実装で固める** |
| 5/26-5/27 (Day 5-6) | デモ動画再撮影 (新 UI + 新ストリップ + Coach パネル使用) |
| 5/28 (Day 7) | C-1 (Glance View) + C-2 (Sprint テンプレ) + D-2 (失敗集約) |
| 5/29 (Day 8) | E 系ポリッシュ + 記事最終稿 + スクショ差し替え |
| 5/30 (Day 9) | 動画最終版 + Zenn 公開予告 + 試用 URL のキャッシュウォーム |
| 5/31 (Day 10) | バッファ / 最終 smoke / READMEと記事のリンク同期 |
| 6/01 | 提出 |

---

## G. やらないことを明示 (YAGNI)

- Hume EVI 統合 → 記事のロードマップで触れるだけ
- Recall.ai 移行 → 現行 Graph Calling + ACS 構成で十分
- Copilot Studio Multi-Agent への移植 → §3.3 で「採用しない理由」を既に書いた
- 多言語対応 (英語 UI) → 審査員は日本語OK
- モバイルアプリ → 審査は Web で行われる

---

## H. 一次ソース (記事の引用元として推奨)

- [Observe, Ask, Intervene (CHI 2025)](https://arxiv.org/abs/2501.10553) — Houtti et al.
- [What Does Success Look Like? Catalyzing Meeting Intentionality with AI-Assisted Prospective Reflection (CHIWORK 2025)](https://arxiv.org/pdf/2505.14370)
- [Microsoft Work Trend Index 2025: Frontier Firm](https://www.microsoft.com/en-us/worklab/work-trend-index/2025-the-year-the-frontier-firm-is-born)
- [Microsoft Build 2025: Copilot Studio Multi-Agent Orchestration](https://www.microsoft.com/en-us/microsoft-copilot/blog/copilot-studio/multi-agent-orchestration-maker-controls-and-more-microsoft-copilot-studio-announcements-at-microsoft-build-2025/)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic: Multi-agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Read.ai: About Sentiment, Engagement, and the Read Score](https://support.read.ai/hc/en-us/articles/4406653674003-About-Sentiment-Engagement-and-the-Read-Score)
- [Granola UX teardown — "Invisible AI"](https://uxplanet.org/the-art-of-invisible-ai-what-granolas-70-retention-teaches-us-about-product-design-2de5a2836d17)
- [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines)
- [LangSmith Agent Observability](https://www.langchain.com/langsmith/observability)
