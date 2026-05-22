import { FluentProvider, webDarkTheme } from '@fluentui/react-components';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Meeting } from '@/lib/api';

import { MemoryEchoCard } from '../MemoryEchoCard';

function makeMeeting(overrides: Partial<Meeting> = {}): Meeting {
  return {
    id: 'm1',
    organizer_id: 'u1',
    goal: 'test',
    mode: 'Decision',
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
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_tokens: 0,
      total_cost_usd: 0,
      call_count: 0,
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
    surfaced_decision_ids: [],
    ...overrides,
  };
}

function renderWithProviders(meeting: Meeting) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <FluentProvider theme={webDarkTheme}>
        <MemoryEchoCard meeting={meeting} organizerId="u1" />
      </FluentProvider>
    </QueryClientProvider>,
  );
}

describe('MemoryEchoCard', () => {
  it('shows the empty state when no memory has been surfaced', () => {
    renderWithProviders(makeMeeting());
    expect(screen.getByLabelText('過去会議からの引き継ぎ')).toBeInTheDocument();
    expect(screen.getByText(/0 echo/)).toBeInTheDocument();
    expect(screen.getByText(/前回こう決めましたよね/)).toBeInTheDocument();
  });

  it('shows the count of MemoryRetriever interventions delivered', () => {
    const meeting = makeMeeting({
      delivered_interventions: [
        {
          id: 'i1',
          meeting_id: 'm1',
          candidate_id: 'c1',
          agent: 'MemoryRetriever',
          content: '📜 2026-05-15 に「価格」について…',
          reason: 'cross_meeting_recall',
          evidence_quote: 'past:t1',
          level: 'L2',
          audience: ['all'],
          delivered_at: new Date().toISOString(),
        },
        {
          // 別 agent の介入は含まれない
          id: 'i2',
          meeting_id: 'm1',
          candidate_id: 'c2',
          agent: 'DecisionCapture',
          content: '決定: X',
          reason: 'decision_captured',
          evidence_quote: null,
          level: 'L2',
          audience: ['all'],
          delivered_at: new Date().toISOString(),
        },
      ],
    });
    renderWithProviders(meeting);
    expect(screen.getByText(/1 echo/)).toBeInTheDocument();
  });
});
