import { useCallback, useState } from 'react';

import type { Utterance } from '@/lib/api';

/** クライアント側で utterance を蓄積する簡易ストア。Tick 時に backend へ送る。 */
export function useUtteranceLog(meetingId: string, speakerId: string) {
  const [utterances, setUtterances] = useState<Utterance[]>([]);

  const append = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      const now = new Date();
      const start = new Date(now.getTime() - Math.max(1000, text.length * 80));
      const u: Utterance = {
        id: crypto.randomUUID(),
        meeting_id: meetingId,
        speaker_id: speakerId,
        text,
        started_at: start.toISOString(),
        ended_at: now.toISOString(),
        duration_sec: (now.getTime() - start.getTime()) / 1000,
        confidence: 1.0,
        is_final: true,
      };
      setUtterances((prev) => [...prev, u]);
    },
    [meetingId, speakerId],
  );

  const clear = useCallback(() => setUtterances([]), []);

  return { utterances, append, clear };
}
