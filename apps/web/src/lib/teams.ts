/**
 * Teams JS SDK 薄ラッパ。
 *
 * Helmsman Web はブラウザ単独でも Teams Tab 内 iframe でも動く。
 * Teams 内で初期化に成功した場合のみ context を返し、それ以外では null を返す。
 */
import { app } from '@microsoft/teams-js';

let initialized: Promise<app.Context | null> | null = null;

/**
 * Teams 内かどうかを判定 + context を取得 (1 回だけ初期化)。
 *
 * - Teams 内: Promise<context>
 * - ブラウザ単独: Promise<null>
 */
export function getTeamsContext(): Promise<app.Context | null> {
  if (initialized) return initialized;
  initialized = (async () => {
    try {
      await app.initialize();
      const ctx = await app.getContext();
      return ctx;
    } catch {
      return null;
    }
  })();
  return initialized;
}

/**
 * Teams 内で動いているかどうかの簡易判定 (副作用なし、UA + window.parent ベース)。
 *
 * SDK 初期化前に layout を変えたい時に使う。確実な判定は getTeamsContext() を待つこと。
 */
export function looksLikeTeamsHost(): boolean {
  if (typeof window === 'undefined') return false;
  const ua = navigator.userAgent || '';
  if (/Teams/i.test(ua)) return true;
  try {
    return window.parent !== window;
  } catch {
    return true;
  }
}
