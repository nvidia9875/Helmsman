import { render, screen } from '@testing-library/react';
import { FluentProvider, webDarkTheme } from '@fluentui/react-components';
import { describe, expect, it } from 'vitest';

import { OnboardingSteps } from '../OnboardingSteps';

describe('OnboardingSteps', () => {
  it('renders the 4-step dispatch guide for first-time users', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <OnboardingSteps />
      </FluentProvider>,
    );

    // 4 ステップとして謳っているか
    expect(screen.getByText(/4 ステップで会議を開始/)).toBeInTheDocument();
    // 各ステップのタイトルが描画されている
    expect(screen.getByText(/Teams で会議を作る/)).toBeInTheDocument();
    expect(screen.getByText(/参加リンクをコピー/)).toBeInTheDocument();
    expect(screen.getByText(/下のフォームに貼り付け/)).toBeInTheDocument();
    expect(screen.getByText(/会議で普通に話す/)).toBeInTheDocument();
  });

  it('makes the dispatch positioning explicit (External 表記)', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <OnboardingSteps />
      </FluentProvider>,
    );
    // Helmsman の external 参加性が文中に出ているか
    expect(screen.getByText(/External/)).toBeInTheDocument();
  });
});
