import { render, screen } from '@testing-library/react';
import { App } from './App';
import { Providers } from './providers';

vi.mock('../config', () => ({ USE_FIXTURES: true, API_BASE: '/api/v1' }));

describe('App shell', () => {
  it('shows the sample-data banner in fixture mode', () => {
    render(<Providers><App /></Providers>);
    expect(screen.getByTestId('sample-banner')).toHaveTextContent('SAMPLE DATA — not NASA results');
  });
  it('has nav, investigation panel and guide slots', () => {
    render(<Providers><App /></Providers>);
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeInTheDocument();
    expect(screen.getByLabelText('Investigation')).toBeInTheDocument();
    expect(screen.getByLabelText('Guide')).toBeInTheDocument();
  });
});
