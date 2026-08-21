import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Register from '../../pages/Register';

vi.mock('../../store/useAuthStore', () => ({
  default: vi.fn(() => ({
    register: vi.fn(),
    isLoading: false,
    error: null,
    clearError: vi.fn(),
  })),
}));

vi.mock('../../store/useToastStore', () => ({
  default: vi.fn(() => vi.fn()),
}));

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders registration form with step 1 heading', () => {
    renderWithRouter(<Register />);
    expect(screen.getByText(/how will you use autergo\?/i)).toBeInTheDocument();
  });

  it('has first name input in step 2', () => {
    renderWithRouter(<Register />);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(continueBtn);
    expect(screen.getByPlaceholderText('John')).toBeInTheDocument();
  });

  it('has last name input in step 2', () => {
    renderWithRouter(<Register />);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(continueBtn);
    expect(screen.getByPlaceholderText('Doe')).toBeInTheDocument();
  });

  it('has email input in step 2', () => {
    renderWithRouter(<Register />);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(continueBtn);
    expect(screen.getByPlaceholderText('john@example.com')).toBeInTheDocument();
  });

  it('has username input in step 2', () => {
    renderWithRouter(<Register />);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(continueBtn);
    expect(screen.getByPlaceholderText('johndoe')).toBeInTheDocument();
  });

  it('has password input in step 3', () => {
    renderWithRouter(<Register />);
    
    // Step 1: Click "Continue" to go to Step 2
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));

    // Step 2: Fill in personal details
    fireEvent.change(screen.getByPlaceholderText('John'), { target: { value: 'John' } });
    fireEvent.change(screen.getByPlaceholderText('Doe'), { target: { value: 'Doe' } });
    fireEvent.change(screen.getByPlaceholderText('john@example.com'), { target: { value: 'john@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('johndoe'), { target: { value: 'johndoe' } });
    
    // Step 2: Click "Continue" to go to Step 3
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));

    // Step 3 placeholder in component is "At least 8 characters"
    expect(screen.getByPlaceholderText('At least 8 characters')).toBeInTheDocument();
  });

  it('shows user type selector', () => {
    renderWithRouter(<Register />);
    expect(screen.getByText(/student \/ candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/recruiter \/ hr/i)).toBeInTheDocument();
  });

  it('has sign in link', () => {
    renderWithRouter(<Register />);
    expect(screen.getByText(/already have an account/i)).toBeInTheDocument();
  });
});