import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

vi.mock('react-router-dom', () => ({
  useParams: () => ({ assignmentId: '7' }),
  useNavigate: () => vi.fn(),
}));

vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import apiClient from '../../services/api';
import AssessmentRoom from '../../pages/AssessmentRoom';

describe('AssessmentRoom', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({
      data: {
        assignment: {
          id: 7,
          title: 'Backend assessment',
          instructions: 'Complete the questions.',
          duration_minutes: 30,
          proctoring_enabled: true,
        },
        questions: [{ id: 1, prompt: 'Explain async I/O.', question_type: 'text', points: 2 }],
        proctoring_notice: 'Reviewable evidence only.',
      },
    });
    apiClient.post.mockResolvedValue({ data: { id: 99, attempt_number: 1 } });
  });

  it('requires consent before starting and renders candidate-safe questions', async () => {
    render(<AssessmentRoom />);
    expect(await screen.findByRole('heading', { name: 'Backend assessment' })).toBeInTheDocument();
    expect(screen.getByText(/reviewable evidence only/i)).toBeInTheDocument();
    expect(screen.queryByText(/explain async i\/o/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /start assessment/i }));
    expect(apiClient.post).not.toHaveBeenCalled();
    expect(screen.getByText(/please confirm/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /start assessment/i }));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/hiring/assignments/7/attempt'));
    expect(await screen.findByText(/explain async i\/o/i)).toBeInTheDocument();
    expect(screen.getByText(/autosave on/i)).toBeInTheDocument();
  });
});
