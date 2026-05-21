# Teams Sideload Guide (N.C)

Helmsman を **Teams Tab** として実会議で動かす手順。
Bot は既に稼働中 (Graph Communications API 経由)。このガイドは
「会議内に Mission Control タブを表示する」配線。

> 前提: `manifest.json` が calling bot + configurableTabs 両方に対応済 (v0.2.0)。
> Tab JS SDK 配線も `/teams-config` ルートに実装済。

## 1. アプリパッケージ作成

```bash
cd apps/teams-app
zip helmsman-app.zip manifest.json icons/color.png icons/outline.png
```

出力: `apps/teams-app/helmsman-app.zip`

> 注: `zip` がない場合は Finder / 7z 等で同階層に zip 化。**ディレクトリ階層を含めず、
> manifest.json と icons/ がトップレベル**になるように。

## 2. Teams Admin Center で許可 (テナント Owner のみ)

1. <https://admin.teams.microsoft.com> → 「Teams アプリ」→「アプリのセットアップ ポリシー」
2. global ポリシーで「カスタム アプリのアップロードを許可」を **ON**
3. 「Manage apps」→「カスタムアプリのアップロード」も **ON** にする
4. 反映まで 最大 24 時間 (大抵 数分)

## 3. Teams クライアントにサイドロード

### 個人スコープ (一番簡単)
1. Teams 左下 `アプリ` → 右上 `アプリの管理` → `アプリをアップロード`
2. `helmsman-app.zip` を選ぶ → `追加`
3. 左サイドバーに Helmsman アイコン (船舵) が出る

### 会議に Tab として追加 (本命)
1. Teams で会議をスケジュール (or 既存会議を編集)
2. `+` (タブを追加) → 検索: `Helmsman` → 選択
3. **TeamsConfig ページが iframe で開く** → 「✓ Teams context ready」表示を確認
4. `保存` を押す → タブが会議に追加される
5. 会議中・会議前にタブを開くと Mission Control が表示

> Tab は `contentUrl: ?teamsTab=1` を読む。標準 Landing が iframe 内で表示される。

## 4. 動作確認チェックリスト

| 項目 | 期待動作 |
|---|---|
| Tab iframe で Landing 表示 | ✅ |
| 派遣 URL 入力 → 派遣ボタン | ✅ Bot が会議に参加する |
| Bot がスピーカーで挨拶 | ✅ "こんにちは、ヘルムスマンです …" |
| Mission Control の LiveTranscript | ✅ 会議の音声が逐次表示 |
| 介入が IntervetionFeed に流れる | ✅ Steering / Dissent / Decision |
| 会議終了で auto-hangup | ✅ 1 人 (Bot のみ) を検知して退出 |

## 5. トラブルシューティング

| 症状 | 対処 |
|---|---|
| Tab が iframe で「リフレッシュしてください」 | dev URL が `Strict-Transport-Security` 付き HTTPS か確認 |
| `app.initialize()` がタイムアウト | manifest の `validDomains` に SWA URL が入っているか |
| 「テナントから許可されていません」 | Admin Center のカスタムアプリポリシーが ON か |
| Bot が join できず 401 | Application Access Policy が admin@helmsmanjp に効いているか (`Get-CsApplicationAccessPolicy`) |

## 6. 撤去 (デモ後の cleanup)

```text
Teams → アプリ → Helmsman → 削除
(管理者が global で削除する場合は admin center → Manage apps → Block)
```

Bot Service / Container App は別途 azure CLI で。手順: actions.md の TB-E5 参照。
