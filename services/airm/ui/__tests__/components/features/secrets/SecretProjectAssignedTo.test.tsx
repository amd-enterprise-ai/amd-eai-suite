// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { SecretProjectAssignedTo } from '@/components/features/secrets/SecretProjectAssignedTo';
import { Secret } from '@/types/secrets';
import {
  generateMockProjectSecretsWithParentSecret,
  generateMockSecrets,
} from '@/__mocks__/utils/secrets-mock';

vi.mock('@heroui/react', async (importOriginal) => ({
  ...(await importOriginal()),
  Tooltip: ({
    content,
    children,
  }: {
    children: React.ReactNode;
    content: React.ReactNode;
  }) => (
    <div>
      <div>{content}</div>
      <div>{children}</div>
    </div>
  ),
}));

vi.mock(
  '@/components/shared/DataTable/CustomRenderers',
  async (importOriginal) => ({
    ...(await importOriginal()),
    NoDataDisplay: () => <div>no data</div>,
  }),
);

describe('ProjectAssignedTo', () => {
  it('renders IconLineDashed when secret has no projectSecrets', () => {
    const secret: Secret = { projectSecrets: [] } as unknown as Secret;
    act(() => {
      render(<SecretProjectAssignedTo secret={secret} />);
    });
    expect(screen.getByText('no data')).toBeInTheDocument();
  });

  it('renders NoDisplay when projectSecrets is empty array', () => {
    const secret: Secret = generateMockSecrets(1)[0];
    secret.projectSecrets = [];
    act(() => {
      render(<SecretProjectAssignedTo secret={secret} />);
    });
    expect(screen.getByText('no data')).toBeInTheDocument();
  });

  it('renders single project name when projectSecrets has one item', () => {
    const secret: Secret = generateMockSecrets(1)[0];
    secret.projectSecrets = generateMockProjectSecretsWithParentSecret(
      1,
      'Project Name 1',
    );
    act(() => {
      render(<SecretProjectAssignedTo secret={secret} />);
    });
    expect(screen.getByText('Project Name 1')).toBeInTheDocument();
  });

  it('renders tooltip with project count when projectSecrets has multiple items', () => {
    const secret: Secret = {
      projectSecrets: [
        { id: '1', projectName: 'Project Alpha' },
        { id: '2', projectName: 'Project Beta' },
        { id: '3', projectName: 'Project Gamma' },
      ],
    } as Secret;
    act(() => {
      render(<SecretProjectAssignedTo secret={secret} />);
    });
    expect(screen.getByText('3 projects')).toBeInTheDocument();
  });

  it('renders all project names in tooltip content when multiple projects exist', async () => {
    const secret: Secret = {
      projectSecrets: [
        { id: '1', projectName: 'Project Alpha' },
        { id: '2', projectName: 'Project Beta' },
      ],
    } as Secret;

    act(() => {
      render(<SecretProjectAssignedTo secret={secret} />);
    });

    const trigger = await screen.getByText('2 projects');
    await fireEvent.mouseEnter(trigger);

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.getByText('Project Beta')).toBeInTheDocument();
    });
  });

  it('applies correct CSS classes to tooltip trigger', () => {
    const secret: Secret = {
      projectSecrets: [
        { id: '1', projectName: 'Project Alpha' },
        { id: '2', projectName: 'Project Beta' },
      ],
    } as Secret;
    act(() => {
      render(<SecretProjectAssignedTo secret={secret} />);
    });
    const trigger = screen.getByText('2 projects');
    expect(trigger).toHaveClass('cursor-pointer', 'underline');
  });
});
