/**
 * api.ts のエンドポイント組み立て (URL + query) を検証する単純な smoke test。
 * 本物の fetch は飛ばさず、global.fetch を mock。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../api';

describe('api client URL composition', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('builds /meetings/{id}/bot/invite with organizer_id query', async () => {
    await api.inviteBot('m-1', 'u-1', 'https://teams.microsoft.com/l/meetup-join/xxx');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/meetings/m-1/bot/invite?organizer_id=u-1');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({
      teams_meeting_url: 'https://teams.microsoft.com/l/meetup-join/xxx',
    });
  });

  it('builds /meetings/{id}/bot/speak', async () => {
    await api.speakIntoMeeting('m-1', 'u-1', 'こんにちは');
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/meetings/m-1/bot/speak?organizer_id=u-1');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({ text: 'こんにちは' });
  });

  it('builds /meetings/usage/summary with days param', async () => {
    await api.getUsageSummary('u-1', 14);
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/meetings/usage/summary?organizer_id=u-1&days=14');
  });

  it('startMeeting with teams_meeting_url goes to POST /meetings', async () => {
    await api.startMeeting({
      organizer_id: 'u-1',
      goal: '',
      teams_meeting_url: 'https://teams.microsoft.com/l/meetup-join/xxx',
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/meetings');
    expect(init?.method).toBe('POST');
    const body = JSON.parse(String(init?.body));
    expect(body.teams_meeting_url).toBe(
      'https://teams.microsoft.com/l/meetup-join/xxx',
    );
    expect(body.goal).toBe('');
  });
});
