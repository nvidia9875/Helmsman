/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * 無料の Web Speech API を使ったブラウザ内 STT。
 * Azure Speech が無くてもデモ可能にするための軽量フォールバック。
 * Safari は webkitSpeechRecognition、Chrome は SpeechRecognition。
 */
export function useBrowserSTT(lang: string = 'ja-JP', onFinal?: (text: string) => void) {
  const [available, setAvailable] = useState(false);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const recRef = useRef<any>(null);

  useEffect(() => {
    const SR: any =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setAvailable(false);
      return;
    }
    setAvailable(true);
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang;
    rec.onresult = (event: any) => {
      let interimTxt = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          const text = result[0].transcript.trim();
          if (text && onFinal) onFinal(text);
        } else {
          interimTxt += result[0].transcript;
        }
      }
      setInterim(interimTxt);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    return () => {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    };
  }, [lang, onFinal]);

  const start = useCallback(() => {
    try {
      recRef.current?.start();
      setListening(true);
    } catch {
      /* already started */
    }
  }, []);

  const stop = useCallback(() => {
    try {
      recRef.current?.stop();
    } catch {
      /* ignore */
    }
    setListening(false);
  }, []);

  return { available, listening, interim, start, stop };
}
