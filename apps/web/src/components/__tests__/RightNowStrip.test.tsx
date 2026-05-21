import { render, screen } from '@testing-library/react';
import { FluentProvider, webDarkTheme } from '@fluentui/react-components';
import { describe, expect, it } from 'vitest';

import { RightNowStrip } from '../RightNowStrip';
import type { BotTranscript, Meeting } from '@/lib/api';

function makeMeeting(overrides: Partial<Meeting> = {}): Meeting {
  return {
    id: 'm1',
    organizer_id: 'u1',
    goal: 'test',
    mode: 'decision',
    total_minutes: 60,
    state: 'in_progress',
    user_intensity: 'normal',
    started_at: new Date().toISOString(),
    ended_at: null,
    topics: [],
    participant_ids: [],
    last_intervention_at: null,
    recent_utterance_density: 0,
    parent_meeting_id: null,
    series_id: null,
    series_index: null,
    inherited_topic_ids: [],
    document_ids: [],
    document_index_name: null,
    group_id: null,
    usage: {
      total_cost_usd: 0,
      total_tokens: 0,
      prompt_tokens: 0,
      completion_tokens: 0,
      call_count: 0,
      by_model: {},
      by_agent: {},
    },
    teams_meeting_url: null,
    bot_call_connection_id: null,
    bot_status: 'idle',
    bot_last_event_at: null,
    delivered_interventions: [],
    facilitator_name: null,
    steering_enabled: true,
    timekeeper_alerts: [],
    ...overrides,
  } as Meeting;
}

function makeTranscript(overrides: Partial<BotTranscript> = {}): BotTranscript {
  return {
    bot_active: true,
    utterance_count: 0,
    utterances: [],
    ...overrides,
  };
}

describe('RightNowStrip', () => {
  it('shows STAND BY when bot is idle', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <RightNowStrip meeting={makeMeeting()} transcript={undefined} />
      </FluentProvider>,
    );
    expect(screen.getByText('STAND BY')).toBeInTheDocument();
    expect(screen.getByText(/awaiting dispatch/)).toBeInTheDocument();
  });

  it('shows LIVE + speaker when bot in_call and there are utterances', () => {
    const tx = makeTranscript({
      bot_active: true,
      utterance_count: 1,
      utterances: [
        {
          id: 'u1',
          meeting_id: 'm1',
          speaker_id: '田中',
          text: 'こんにちは',
          started_at: new Date().toISOString(),
          ended_at: new Date().toISOString(),
          duration_sec: 1,
          confidence: 0.9,
          is_final: true,
        },
      ],
    });
    render(
      <FluentProvider theme={webDarkTheme}>
        <RightNowStrip
          meeting={makeMeeting({ bot_status: 'in_call' })}
          transcript={tx}
        />
      </FluentProvider>,
    );
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(screen.getByText(/田中 speaking/)).toBeInTheDocument();
  });

  it('exposes intervention count when idle', () => {
    const meeting = makeMeeting({
      delivered_interventions: [
        {
          id: 'd1',
          meeting_id: 'm1',
          candidate_id: 'c1',
          agent: 'DecisionCapture',
          content: '決定',
          reason: 'r',
          evidence_quote: null,
          level: 'L2',
          audience: ['chair'],
          delivered_at: new Date().toISOString(),
        },
      ],
    });
    render(
      <FluentProvider theme={webDarkTheme}>
        <RightNowStrip meeting={meeting} transcript={undefined} />
      </FluentProvider>,
    );
    expect(screen.getByText(/1 delivered/)).toBeInTheDocument();
  });
});
