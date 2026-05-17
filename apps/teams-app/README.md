# Helmsman — Teams App Package

Microsoft Teams に Helmsman を「インストール可能なアプリ」として配布するためのパッケージ雛形。
ハッカソン提出後 (6/2 以降) に Teams App Marketplace 申請する想定。

## このパッケージで提供する体験

- **Personal Static Tab** — 個人スコープで Mission Control (SWA) を Teams 内に埋め込み
- **Channel Configurable Tab** — チャンネル単位で会議用のダッシュボードを設置
- (将来) **Bot/Calling Bot** — Bot Framework 登録後に追記

## ハッカソン期間中の状態

現状の Bot 派遣は **ACS Call Automation の anonymous external user 機能** を使っており、
Teams App 配布なしで `POST /meetings/{id}/bot/invite { teams_meeting_url }` だけで動作する。
このパッケージは「正規ルートで Teams Marketplace に申請する」ためのパスを示すためのものです。

## ローカルでテストする手順 (Teams Toolkit が必要)

1. アイコンを 192x192 (color) と 32x32 (outline) で `icons/` に追加
2. `manifest.json` の `id` を新しい UUID で置き換え (`uuidgen` 等)
3. `npm install -g @microsoft/teams-app-publisher` (or use Teams Toolkit VS Code 拡張)
4. zip でパッケージ化: `cd apps/teams-app && zip -r helmsman.zip manifest.json icons/`
5. Teams admin → Apps → Upload custom app

## ハッカソン後の TODO

- [ ] アイコン作成 (192x192 color + 32x32 outline、PNG)
- [ ] Microsoft App ID を Teams Developer Portal で発行
- [ ] Bot Framework 登録 → manifest.json に `bots` セクション追加
- [ ] `permissions` を最小化
- [ ] Marketplace 申請

## 設計判断: なぜ Bot Framework を使わなかったか

Bot Framework + Microsoft Graph Calls API ルートは、テナント管理者の承認 + アプリ検証申請が
必要で、ハッカソン期間 (2 週間弱) では完走不能と判断。代わりに ACS Call Automation の
[Teams Interop の External user 機能](https://learn.microsoft.com/azure/communication-services/concepts/join-teams-meeting)
を使い、Teams App 登録なしで Bot が anonymous で参加する設計にした。
本番化時は Bot Framework に切替えるとよりリッチな Teams 内体験 (専用 UI / 通知 / アダプティブカード) が得られる。
