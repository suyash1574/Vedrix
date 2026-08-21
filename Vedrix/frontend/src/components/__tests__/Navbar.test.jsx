import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Navbar from '../Navbar';

// Mock useAuthStore
vi.mock('../store/useAuthStore', () => ({
  default: () => ({
    isAuthenticated: false,
    user: null,
    logout: vi.fn(),
  }),
}));

describe('Navbar', () => {
  it('renders logo and sign in button when not authenticated', () => {
    render(
      <BrowserRouter>
        <Navbar />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Autergo/i)).toBeInTheDocument();
    expect(screen.getByText(/Sign In/i)).toBeInTheDocument();
    expect(screen.getByText(/Register/i)).toBeInTheDocument();
  });
});
