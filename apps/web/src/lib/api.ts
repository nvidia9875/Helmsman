/**
 * Helmsman API client.
 * dev: Vite proxy /api -> http://127.0.0.1:8000
 * prod: VITE_API_BASE で上書き
 */

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api';

export type MeetingMode = 'Decision' | 'Brainstorm' | 'Status' | 'Interview' | '1on1' | 'Kickoff';
export type UserIntensity = 'quiet' | 'normal' | 'aggressive';
export type TopicState = 'not_started' | 'discussing' | 'deep_dive' | 'decided';
export type TopicPriority = 'Critical' | 'Important' | 'Optional';
export type InterventionLevel = 'L1' | 'L2' | 'L3';
export type MeetingState = 'scheduled' | 'in_progress' | 'concluded';

export interface Topic {
  id: string;
  name: string;
  decision_criteria: string;
  time_budget_pct: number;
  priority: TopicPriority;
  dependencies: string[];
  state: TopicState;
  last_mention_at: string | null;
  key_speakers: string[];
  evidence_quote: string | null;
  confidence: number;
}

export interface Meeting {
  id: string;
  organizer_id: string;
  goal: string;
  mode: MeetingMode;
  total_minutes: number;
  state: MeetingState;
  user_intensity: UserIntensity;
  started_at: string | null;
  ended_at: string | null;
  topics: Topic[];
  participant_ids: string[];
  last_intervention_at: string | null;
  recent_utterance_density: number;
}

export interface Participant {
  id: string;
  meeting_id: string;
  display_name: string;
  entra_id: string | null;
  voiceprint_profile_id: string | null;
  is_chair: boolean;
  is_senior: boolean;
  joined_at: string;
  total_speak_seconds: number;
  utterance_count: number;
}

export interface Utterance {
  id: string;
  meeting_id: string;
  speaker_id: string;
  text: string;
  started_at: string;
  ended_at: string;
  duration_sec: number;
  confidence: number;
  is_final: boolean;
}

export interface InterventionCandidate {
  id: string;
  meeting_id: string;
  agent: string;
  content: string;
  reason: string;
  evidence_quote: string | null;
  confidence: number;
  created_at: string;
  allowed_modes: string[];
}

export interface InterventionDelivery {
  id: string;
  meeting_id: string;
  candidate_id: string;
  agent: string;
  content: string;
  reason: string;
  evidence_quote: string | null;
  level: InterventionLevel;
  audience: string[];
  delivered_at: string;
}

export interface StartMeetingRequest {
  organizer_id: string;
  goal: string;
  mode?: MeetingMode;
  total_minutes?: number;
  user_intensity?: UserIntensity;
}

export interface TickRequest {
  recent_utterances?: Utterance[];
  participants?: Participant[];
  current_speaker_id?: string | null;
  chair_id?: string | null;
}

export interface TickResponse {
  meeting: Meeting;
  candidates: InterventionCandidate[];
  delivery: InterventionDelivery | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  config: () => request<Record<string, string>>('/health/config'),
  startMeeting: (req: StartMeetingRequest) =>
    request<Meeting>('/meetings', { method: 'POST', body: JSON.stringify(req) }),
  getMeeting: (id: string, organizerId: string) =>
    request<Meeting>(`/meetings/${id}?organizer_id=${encodeURIComponent(organizerId)}`),
  tick: (id: string, organizerId: string, req: TickRequest) =>
    request<TickResponse>(
      `/meetings/${id}/tick?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: JSON.stringify(req) },
    ),
};
