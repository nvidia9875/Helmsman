import { describe, expect, it } from 'vitest';

import type { FaceFrame } from '@/lib/face/landmarker';
import {
  aggregateFrames,
  confusionScore,
  countNods,
  engagementScore,
} from '@/lib/face/detectors';

function makeFrame(
  blendshapes: Record<string, number> = {},
  headPitchDeg = 0,
  detected = true,
): FaceFrame {
  return { blendshapes, headPitchDeg, timestamp: 0, detected };
}

// ===== countNods =====

describe('countNods', () => {
  it('returns 0 for too-short sequences', () => {
    expect(countNods([])).toBe(0);
    expect(countNods([1, 2, 3])).toBe(0);
  });

  it('returns 0 for flat (no oscillation) sequences', () => {
    expect(countNods([5, 5, 5, 5, 5, 5])).toBe(0);
  });

  it('counts a simple up-down-up motion as one or two nods', () => {
    // -10°, +5°, -10°, +5° — クリアな振動
    const pitches = [-10, 0, 5, 2, -10, 0, 5];
    const n = countNods(pitches);
    expect(n).toBeGreaterThanOrEqual(1);
  });

  it('ignores micro-jitter under amplitude threshold', () => {
    // 振幅 1° しか動かない → 0 件
    const pitches = [0, 0.5, 0, -0.5, 0, 0.5, 0];
    expect(countNods(pitches)).toBe(0);
  });

  it('ignores violently large head turns (>25°)', () => {
    // 振幅 30° の極端な振動 (うなずきではなく首振り扱い) → 0 件
    const pitches = [0, 30, 0, -30, 0, 30, 0];
    expect(countNods(pitches)).toBe(0);
  });
});

// ===== confusionScore =====

describe('confusionScore', () => {
  it('returns 0 for undetected frames', () => {
    expect(confusionScore(makeFrame({}, 0, false))).toBe(0);
  });

  it('returns near 0 for a neutral face', () => {
    expect(confusionScore(makeFrame({}, 0))).toBe(0);
  });

  it('returns higher score when brows are strongly down', () => {
    const s = confusionScore(
      makeFrame({ browDownLeft: 0.9, browDownRight: 0.9 }, 0),
    );
    expect(s).toBeGreaterThan(0.4);
  });

  it('clamps within [0, 1]', () => {
    const s = confusionScore(
      makeFrame(
        {
          browDownLeft: 1,
          browDownRight: 1,
          mouthPressLeft: 1,
          mouthPressRight: 1,
          noseSneerLeft: 1,
          noseSneerRight: 1,
        },
        0,
      ),
    );
    expect(s).toBeGreaterThanOrEqual(0);
    expect(s).toBeLessThanOrEqual(1);
  });
});

// ===== engagementScore =====

describe('engagementScore', () => {
  it('returns 0 for undetected frames', () => {
    expect(engagementScore(makeFrame({}, 0, false))).toBe(0);
  });

  it('is near 1 when eyes are open and facing forward', () => {
    const s = engagementScore(
      makeFrame({ eyeBlinkLeft: 0, eyeBlinkRight: 0 }, 0),
    );
    expect(s).toBeGreaterThan(0.9);
  });

  it('drops near zero when eyes are closed', () => {
    const s = engagementScore(
      makeFrame({ eyeBlinkLeft: 1, eyeBlinkRight: 1 }, 0),
    );
    expect(s).toBeLessThan(0.1);
  });

  it('drops when head pitches heavily', () => {
    const forward = engagementScore(makeFrame({}, 0));
    const tilted = engagementScore(makeFrame({}, 20));
    expect(tilted).toBeLessThan(forward);
  });
});

// ===== aggregateFrames =====

describe('aggregateFrames', () => {
  it('returns null for empty input', () => {
    expect(aggregateFrames([])).toBeNull();
  });

  it('reports visible ratio correctly', () => {
    const frames = [
      makeFrame({}, 0, true),
      makeFrame({}, 0, false),
      makeFrame({}, 0, true),
      makeFrame({}, 0, true),
    ];
    const w = aggregateFrames(frames)!;
    expect(w.faceVisibleRatio).toBeCloseTo(0.75, 2);
  });

  it('averages confusion across frames', () => {
    const frames = [
      makeFrame({ browDownLeft: 0, browDownRight: 0 }),
      makeFrame({ browDownLeft: 1, browDownRight: 1 }),
    ];
    const w = aggregateFrames(frames)!;
    // 1 つは 0、もう 1 つは ~0.5 (brow only) → 平均 ~0.25
    expect(w.confusion).toBeGreaterThan(0.15);
    expect(w.confusion).toBeLessThan(0.4);
  });

  it('passes pitch series to nod detector', () => {
    // 明確に振動するパターン
    const pitches = [-10, 0, 5, 2, -10, 0, 5, 2, -10];
    const frames: FaceFrame[] = pitches.map((p) => makeFrame({}, p));
    const w = aggregateFrames(frames)!;
    expect(w.nodCount).toBeGreaterThanOrEqual(1);
  });
});
