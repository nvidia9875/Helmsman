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
  document_reference: string | null;
}

export interface AgentUsageRollup {
  agent_name: string;
  model_deployment: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  call_count: number;
}

export interface MeetingUsage {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  call_count: number;
  by_agent: Record<string, AgentUsageRollup>;
}

export type BotStatus = 'idle' | 'connecting' | 'in_call' | 'disconnected' | 'failed';

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
  parent_meeting_id: string | null;
  series_id: string | null;
  series_index: number | null;
  inherited_topic_ids: string[];
  document_ids: string[];
  document_index_name: string | null;
  usage: MeetingUsage;
  teams_meeting_url: string | null;
  bot_call_connection_id: string | null;
  bot_status: BotStatus;
  bot_last_event_at: string | null;
  delivered_interventions: InterventionDelivery[];
}

export interface BotTranscript {
  bot_active: boolean;
  utterance_count: number;
  utterances: Utterance[];
}

export interface UsageSummaryByDay {
  date: string;
  cost_usd: number;
  total_tokens: number;
  meeting_count: number;
}

export interface UsageSummary {
  total_meetings: number;
  total_cost_usd: number;
  total_tokens: number;
  avg_cost_per_meeting_usd: number;
  by_day: UsageSummaryByDay[];
  by_agent: Record<string, number>;
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
  goal: string; // 任意。空文字なら "監視のみ" モードで派遣
  mode?: MeetingMode;
  total_minutes?: number;
  user_intensity?: UserIntensity;
  parent_meeting_id?: string | null;
  // 任意。指定すると同じリクエスト内で Bot が Teams 会議に派遣される
  teams_meeting_url?: string | null;
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

export type DocumentStatus = 'uploaded' | 'extracting' | 'indexed' | 'failed';

export interface MeetingDocument {
  id: string;
  meeting_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  blob_container: string;
  blob_path: string;
  extracted_text: string | null;
  extracted_at: string | null;
  chunk_count: number;
  index_provider: string | null;
  search_index_name: string | null;
  status: DocumentStatus;
  error_message: string | null;
  uploaded_by: string;
  uploaded_at: string;
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
  listMeetings: (organizerId: string, limit = 20) =>
    request<Meeting[]>(
      `/meetings?organizer_id=${encodeURIComponent(organizerId)}&limit=${limit}`,
    ),
  getUsageSummary: (organizerId: string, days = 30) =>
    request<UsageSummary>(
      `/meetings/usage/summary?organizer_id=${encodeURIComponent(organizerId)}&days=${days}`,
    ),
  listSeries: (seriesId: string, organizerId: string) =>
    request<Meeting[]>(
      `/meetings/series/${seriesId}?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  getMeetingUsage: (id: string, organizerId: string) =>
    request<MeetingUsage>(
      `/meetings/${id}/usage?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  tick: (id: string, organizerId: string, req: TickRequest) =>
    request<TickResponse>(
      `/meetings/${id}/tick?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: JSON.stringify(req) },
    ),
  redecompose: (id: string, organizerId: string) =>
    request<Meeting>(
      `/meetings/${id}/redecompose?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST' },
    ),
  setGoal: (id: string, organizerId: string, goal: string, mode?: MeetingMode) =>
    request<Meeting>(
      `/meetings/${id}/set-goal?organizer_id=${encodeURIComponent(organizerId)}`,
      {
        method: 'POST',
        body: JSON.stringify({ goal, ...(mode ? { mode } : {}) }),
      },
    ),
  listDocuments: (id: string, organizerId: string) =>
    request<MeetingDocument[]>(
      `/meetings/${id}/documents?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  uploadDocument: async (
    id: string,
    organizerId: string,
    file: File,
    uploadedBy: string,
  ) => {
    const form = new FormData();
    form.append('file', file);
    form.append('uploaded_by', uploadedBy);
    const res = await fetch(
      `${API_BASE}/meetings/${id}/documents?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: form },
    );
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
    return (await res.json()) as MeetingDocument;
  },
  inviteBot: (id: string, organizerId: string, teamsMeetingUrl: string) =>
    request<{ meeting: Meeting; call_connection_id: string }>(
      `/meetings/${id}/bot/invite?organizer_id=${encodeURIComponent(organizerId)}`,
      {
        method: 'POST',
        body: JSON.stringify({ teams_meeting_url: teamsMeetingUrl }),
      },
    ),
  leaveBot: (id: string, organizerId: string) =>
    request<Meeting>(
      `/meetings/${id}/bot/leave?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST' },
    ),
  speakIntoMeeting: (id: string, organizerId: string, text: string) =>
    request<{ accepted: boolean; detail: string }>(
      `/meetings/${id}/bot/speak?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: JSON.stringify({ text }) },
    ),
  getBotTranscript: (id: string, organizerId: string, limit = 50) =>
    request<BotTranscript>(
      `/meetings/${id}/bot/transcript?organizer_id=${encodeURIComponent(organizerId)}&limit=${limit}`,
    ),
};
