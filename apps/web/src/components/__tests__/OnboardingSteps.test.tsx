import { render, screen } from '@testing-library/react';
import { FluentProvider, webDarkTheme } from '@fluentui/react-components';
import { describe, expect, it } from 'vitest';

import { OnboardingSteps } from '../OnboardingSteps';

describe('OnboardingSteps', () => {
  it('renders all 4 numbered steps inline', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <OnboardingSteps />
      </FluentProvider>,
    );
    expect(screen.getByText(/Teams で会議を作る/)).toBeInTheDocument();
    expect(screen.getByText(/参加 URL をコピー/)).toBeInTheDocument();
    expect(screen.getByText(/下に貼り付け/)).toBeInTheDocument();
    expect(screen.getByText(/会議で話す/)).toBeInTheDocument();
  });

  it('numbers the steps 1-4', () => {
    render(
      <FluentProvider theme={webDarkTheme}>
        <OnboardingSteps />
      </FluentProvider>,
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });
});
