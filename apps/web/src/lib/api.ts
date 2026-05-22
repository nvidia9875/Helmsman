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
  group_id: string | null;
  usage: MeetingUsage;
  teams_meeting_url: string | null;
  bot_call_connection_id: string | null;
  bot_status: BotStatus;
  bot_last_event_at: string | null;
  delivered_interventions: InterventionDelivery[];
  // 追加設定 (2026-05-21)
  facilitator_name: string | null;
  steering_enabled: boolean;
  timekeeper_alerts: TimekeeperAlert[];
  // Phase 7 (会議横断記憶): 当会議で MemoryRetriever が surface 済の過去 decision id
  surfaced_decision_ids: string[];
}

// ---------- Phase 7: Decisions (会議横断記憶) ----------

export interface Decision {
  id: string;
  meeting_id: string;
  topic_id: string;
  topic_name: string;
  decision_text: string;
  owner: string;
  deadline: string;
  evidence_quote: string | null;
  series_id: string | null;
  group_id: string | null;
  confidence: number;
  captured_at: string;
}

export interface DecisionSearchHit extends Decision {
  score: number;
}

export interface DecisionSearchRequest {
  query: string;
  organizer_id: string;
  series_id?: string | null;
  group_id?: string | null;
  top_k?: number;
  within_days?: number;
}

// ---------- Phase 6: Face Signals (マルチモーダル) ----------

export interface FaceWindowDto {
  window_start_ms: number;
  sample_count: number;
  nod_count: number;
  confusion: number;
  engagement: number;
  face_visible_ratio: number;
}

export interface FaceSignalBatchDto {
  meeting_id: string;
  organizer_id: string;
  participant_id: string;
  client_sent_at_ms?: number | null;
  windows: FaceWindowDto[];
}

export interface FaceSignalAcceptResponse {
  accepted: boolean;
  windows_received: number;
  buffered_count: number;
}

export interface FaceSignalSummary {
  sample_count: number;
  participants: number;
  total_nods: number;
  mean_confusion: number;
  mean_engagement: number;
  high_confusion_count: number;
  low_engagement_count: number;
}

export interface FaceSignalRecentResponse {
  summary: FaceSignalSummary;
  within_ms: number;
}

export interface TimekeeperAlert {
  id: string;
  minutes_from_start: number;
  message: string;
  enabled: boolean;
  fired: boolean;
  fired_at: string | null;
}

export interface UpdateSettingsRequest {
  facilitator_name?: string | null;
  steering_enabled?: boolean;
  timekeeper_alerts?: Array<{
    id?: string | null;
    minutes_from_start: number;
    message: string;
    enabled: boolean;
  }>;
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
  // 任意。指定するとグループ文書も AI に流れる
  group_id?: string | null;
  // 任意。AI ファシリテーター名
  facilitator_name?: string | null;
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
export type DocumentScope = 'meeting' | 'group';

export interface MeetingDocument {
  id: string;
  scope: DocumentScope;
  meeting_id: string | null;
  group_id: string | null;
  organizer_id: string | null;
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

export interface MeetingGroup {
  id: string;
  organizer_id: string;
  name: string;
  description: string;
  accent_hex: string | null;
  document_ids: string[];
  meeting_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateGroupRequest {
  organizer_id: string;
  name: string;
  description?: string;
  accent_hex?: string | null;
}

export interface DownloadResponse {
  url: string;
  expires_in_seconds: number;
}

export interface UsageRecord {
  agent_name: string;
  model_deployment: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface MeetingReport {
  id: string;
  meeting_id: string;
  organizer_id: string;
  report_markdown: string;
  template_used: boolean;
  memo_used: boolean;
  utterances_included: number;
  template_snapshot: string | null;
  memo_snapshot: string | null;
  generated_at: string;
  generator_agent: string;
  generator_model: string | null;
  usage: UsageRecord | null;
}

export interface GenerateReportRequest {
  template?: string | null;
  memo?: string | null;
  utterances?: Utterance[];
}

export interface GenerateReportResponse {
  id: string;
  meeting_id: string;
  report_markdown: string;
  generated_at: string;
  template_used: boolean;
  memo_used: boolean;
  utterances_included: number;
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
  updateSettings: (id: string, organizerId: string, req: UpdateSettingsRequest) =>
    request<Meeting>(
      `/meetings/${id}/settings?organizer_id=${encodeURIComponent(organizerId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(req),
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
  deleteDocument: async (meetingId: string, documentId: string, organizerId: string) => {
    const res = await fetch(
      `${API_BASE}/meetings/${meetingId}/documents/${documentId}?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'DELETE' },
    );
    if (!res.ok && res.status !== 204) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
  },
  getDocumentDownloadUrl: (
    meetingId: string,
    documentId: string,
    organizerId: string,
  ) =>
    request<DownloadResponse>(
      `/meetings/${meetingId}/documents/${documentId}/download?organizer_id=${encodeURIComponent(organizerId)}`,
    ),

  // ---------- Groups ----------
  listGroups: (organizerId: string, limit = 50) =>
    request<MeetingGroup[]>(
      `/groups?organizer_id=${encodeURIComponent(organizerId)}&limit=${limit}`,
    ),
  getGroup: (groupId: string, organizerId: string) =>
    request<MeetingGroup>(
      `/groups/${groupId}?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  createGroup: (req: CreateGroupRequest) =>
    request<MeetingGroup>('/groups', { method: 'POST', body: JSON.stringify(req) }),
  updateGroup: (
    groupId: string,
    organizerId: string,
    patch: { name?: string; description?: string; accent_hex?: string | null },
  ) =>
    request<MeetingGroup>(
      `/groups/${groupId}?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'PATCH', body: JSON.stringify(patch) },
    ),
  deleteGroup: async (groupId: string, organizerId: string) => {
    const res = await fetch(
      `${API_BASE}/groups/${groupId}?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'DELETE' },
    );
    if (!res.ok && res.status !== 204) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
  },
  attachMeetingToGroup: (
    groupId: string,
    meetingId: string,
    organizerId: string,
  ) =>
    request<Meeting>(
      `/groups/${groupId}/meetings/${meetingId}?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST' },
    ),
  detachMeetingFromGroup: (
    groupId: string,
    meetingId: string,
    organizerId: string,
  ) =>
    request<Meeting>(
      `/groups/${groupId}/meetings/${meetingId}?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'DELETE' },
    ),
  listGroupMeetings: (groupId: string, organizerId: string) =>
    request<Meeting[]>(
      `/groups/${groupId}/meetings?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  listGroupDocuments: (groupId: string, organizerId: string) =>
    request<MeetingDocument[]>(
      `/groups/${groupId}/documents?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  uploadGroupDocument: async (
    groupId: string,
    organizerId: string,
    file: File,
    uploadedBy: string,
  ) => {
    const form = new FormData();
    form.append('file', file);
    form.append('uploaded_by', uploadedBy);
    const res = await fetch(
      `${API_BASE}/groups/${groupId}/documents?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: form },
    );
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
    return (await res.json()) as MeetingDocument;
  },
  deleteGroupDocument: async (
    groupId: string,
    documentId: string,
    organizerId: string,
  ) => {
    const res = await fetch(
      `${API_BASE}/groups/${groupId}/documents/${documentId}?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'DELETE' },
    );
    if (!res.ok && res.status !== 204) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
  },
  getGroupDocumentDownloadUrl: (
    groupId: string,
    documentId: string,
    organizerId: string,
  ) =>
    request<DownloadResponse>(
      `/groups/${groupId}/documents/${documentId}/download?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
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

  // ---------- Reports ----------
  generateReport: (
    meetingId: string,
    organizerId: string,
    req: GenerateReportRequest,
  ) =>
    request<GenerateReportResponse>(
      `/meetings/${meetingId}/report?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: JSON.stringify(req) },
    ),
  listReports: (meetingId: string, organizerId: string, limit = 20) =>
    request<MeetingReport[]>(
      `/meetings/${meetingId}/reports?organizer_id=${encodeURIComponent(organizerId)}&limit=${limit}`,
    ),
  getLatestReport: (meetingId: string, organizerId: string) =>
    request<MeetingReport>(
      `/meetings/${meetingId}/reports/latest?organizer_id=${encodeURIComponent(organizerId)}`,
    ),

  // ---------- Phase 7: Decisions (会議横断記憶) ----------
  listDecisions: (
    organizerId: string,
    opts?: { seriesId?: string | null; groupId?: string | null; withinDays?: number; limit?: number },
  ) => {
    const params = new URLSearchParams({ organizer_id: organizerId });
    if (opts?.seriesId) params.set('series_id', opts.seriesId);
    if (opts?.groupId) params.set('group_id', opts.groupId);
    if (opts?.withinDays) params.set('within_days', String(opts.withinDays));
    if (opts?.limit) params.set('limit', String(opts.limit));
    return request<Decision[]>(`/decisions?${params.toString()}`);
  },
  listDecisionsByMeeting: (meetingId: string, organizerId: string) =>
    request<Decision[]>(
      `/decisions/by-meeting/${meetingId}?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  getDecision: (decisionId: string, organizerId: string) =>
    request<Decision>(
      `/decisions/${encodeURIComponent(decisionId)}?organizer_id=${encodeURIComponent(organizerId)}`,
    ),
  searchDecisions: (req: DecisionSearchRequest) =>
    request<DecisionSearchHit[]>('/decisions/search', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  // ---------- Phase 6: Face Signals (マルチモーダル) ----------
  ingestFaceSignals: (
    meetingId: string,
    organizerId: string,
    batch: FaceSignalBatchDto,
  ) =>
    request<FaceSignalAcceptResponse>(
      `/meetings/${meetingId}/face-signals?organizer_id=${encodeURIComponent(organizerId)}`,
      { method: 'POST', body: JSON.stringify(batch) },
    ),
  getRecentFaceSignals: (
    meetingId: string,
    organizerId: string,
    withinMs = 300_000,
  ) =>
    request<FaceSignalRecentResponse>(
      `/meetings/${meetingId}/face-signals/recent?organizer_id=${encodeURIComponent(organizerId)}&within_ms=${withinMs}`,
    ),
};
