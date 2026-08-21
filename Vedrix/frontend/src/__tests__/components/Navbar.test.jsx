import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Navbar from '../../components/Navbar';
import useAuthStore from '../../store/useAuthStore';

vi.mock('../../store/useAuthStore', () => ({
  default: vi.fn(() => ({
    isAuthenticated: false,
    user: null,
    logout: vi.fn(),
  })),
}));

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Navbar', () => {
  it('renders logo', () => {
    renderWithRouter(<Navbar />);
    expect(screen.getByText(/autergo/i)).toBeInTheDocument();
  });

  it('shows home link', () => {
    renderWithRouter(<Navbar />);
    expect(screen.getByText(/home/i)).toBeInTheDocument();
  });

  it('shows sign in button when not authenticated', () => {
    renderWithRouter(<Navbar />);
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
  });

  it('shows register button when not authenticated', () => {
    renderWithRouter(<Navbar />);
    expect(screen.getByText(/register/i)).toBeInTheDocument();
  });

  it('shows authenticated links when logged in', () => {
    useAuthStore.mockImplementation(() => ({
      isAuthenticated: true,
      user: { first_name: 'Test', user_type: 'student' },
      logout: vi.fn(),
    }));

    renderWithRouter(<Navbar />);
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
  });
});