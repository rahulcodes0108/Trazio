import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Trazio heading', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: 'Trazio' })).toBeInTheDocument();
});
