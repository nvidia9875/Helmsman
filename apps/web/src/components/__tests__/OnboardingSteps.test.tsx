import { render, screen } from '@testing-library/react';
import { FluentProvider, webDarkTheme } from '@fluentui/react-components';
import { describe, expect, it } from 'vitest';

import { OnboardingSteps } from '../OnboardingSteps';

describe('OnboardingSteps', () => {
  it('renders all 3 numbered steps inline', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <OnboardingSteps />
      </FluentProvider>,
    );
    expect(screen.getByText(/Teams カレンダーで会議を作る/)).toBeInTheDocument();
    expect(screen.getByText(/参加 URL をコピーして下に貼る/)).toBeInTheDocument();
    expect(
      screen.getByText(/派遣ボタンで Helmsman を会議に送り出す/),
    ).toBeInTheDocument();
  });

  it('numbers the steps 1-3', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <OnboardingSteps />
      </FluentProvider>,
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});
