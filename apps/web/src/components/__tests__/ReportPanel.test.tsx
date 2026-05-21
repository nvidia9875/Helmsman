import { FluentProvider, webDarkTheme } from '@fluentui/react-components';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/lib/api';

import { ReportPanel } from '../ReportPanel';

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <FluentProvider theme={webDarkTheme}>{children}</FluentProvider>
    </QueryClientProvider>
  );
};

describe('ReportPanel', () => {
  beforeEach(() => {
    vi.spyOn(api, 'listReports').mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders empty state when no reports exist', async () => {
    render(<ReportPanel meetingId="m-1" organizerId="u-1" />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getByText(/まだレポートはありません/),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole('button', { name: /レポートを生成/ }),
    ).toBeInTheDocument();
  });

  it('passes trimmed template and memo when generating', async () => {
    const generateSpy = vi.spyOn(api, 'generateReport').mockResolvedValue({
      id: 'r-1',
      meeting_id: 'm-1',
      report_markdown: '# レポート本体',
      generated_at: '2026-05-21T10:00:00Z',
      template_used: true,
      memo_used: true,
      utterances_included: 0,
    });

    render(<ReportPanel meetingId="m-1" organizerId="u-1" />, { wrapper });

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /レポートを生成/ }),
      ).toBeEnabled(),
    );

    const textareas = screen.getAllByRole('textbox');
    fireEvent.change(textareas[0], { target: { value: '  # テンプレ\n  ' } });
    fireEvent.change(textareas[1], {
      target: { value: '  山田 CTO の発言通り...  ' },
    });

    fireEvent.click(screen.getByRole('button', { name: /レポートを生成/ }));

    await waitFor(() => expect(generateSpy).toHaveBeenCalledTimes(1));
    const [, , req] = generateSpy.mock.calls[0];
    expect(req.template).toBe('# テンプレ');
    expect(req.memo).toBe('山田 CTO の発言通り...');
  });

  it('sends null when template and memo are blank', async () => {
    const generateSpy = vi.spyOn(api, 'generateReport').mockResolvedValue({
      id: 'r-2',
      meeting_id: 'm-1',
      report_markdown: '# default',
      generated_at: '2026-05-21T10:00:00Z',
      template_used: false,
      memo_used: false,
      utterances_included: 0,
    });

    render(<ReportPanel meetingId="m-1" organizerId="u-1" />, { wrapper });

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /レポートを生成/ }),
      ).toBeEnabled(),
    );

    fireEvent.click(screen.getByRole('button', { name: /レポートを生成/ }));

    await waitFor(() => expect(generateSpy).toHaveBeenCalledTimes(1));
    const [, , req] = generateSpy.mock.calls[0];
    expect(req.template).toBeNull();
    expect(req.memo).toBeNull();
  });
});
