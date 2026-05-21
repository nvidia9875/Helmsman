import { useEffect, useRef, useState } from 'react';

interface Options {
  threshold?: number;
  rootMargin?: string;
  /** 一度可視になったら以後 true 固定 (アニメ用) */
  once?: boolean;
}

/**
 * IntersectionObserver を使った可視判定。
 * - SSR 安全 (window 不在時は false)
 * - prefers-reduced-motion = reduce のときは「最初から true」で発火、アニメをスキップ
 */
export function useInView<T extends Element>({
  threshold = 0.18,
  rootMargin = '0px 0px -10% 0px',
  once = true,
}: Options = {}): [(el: T | null) => void, boolean] {
  const [inView, setInView] = useState(() => {
    if (typeof window === 'undefined') return false;
    const reduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    return reduced;
  });
  const elRef = useRef<T | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const setNode = (el: T | null) => {
    if (observerRef.current && elRef.current) {
      observerRef.current.unobserve(elRef.current);
    }
    elRef.current = el;
    if (el && observerRef.current) {
      observerRef.current.observe(el);
      // 初回マウント時、既に viewport と重なっていれば即時表示にする。
      // (IO の最初の callback まで 1 フレーム以上待つと SSG/print 時に
      //  「reveal が永遠に false のまま」のスナップショットになる)
      const rect = el.getBoundingClientRect();
      const viewportH =
        window.innerHeight || document.documentElement.clientHeight;
      if (rect.top < viewportH && rect.bottom > 0) {
        setInView(true);
      }
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const reduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    if (reduced) {
      setInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setInView(true);
            if (once && elRef.current) {
              observer.unobserve(elRef.current);
            }
          } else if (!once) {
            setInView(false);
          }
        }
      },
      { threshold, rootMargin },
    );
    observerRef.current = observer;
    if (elRef.current) observer.observe(elRef.current);

    // viewport が変わったら IO を待たずに即時再判定
    const recheck = () => {
      const el = elRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const viewportH =
        window.innerHeight || document.documentElement.clientHeight;
      if (rect.top < viewportH && rect.bottom > 0) {
        setInView(true);
      }
    };
    window.addEventListener('resize', recheck);

    // セーフティネット: 2 秒経っても IO が発火しなければ強制 reveal。
    // 主に headless capture (Playwright fullPage / SEO bot / 印刷プレビュー)
    // が IO callback を待たずスナップを撮るケースをカバー。
    const safetyTimer = window.setTimeout(() => setInView(true), 2000);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', recheck);
      window.clearTimeout(safetyTimer);
    };
  }, [threshold, rootMargin, once]);

  return [setNode, inView];
}
