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

import { createStorage } from '@/services/app/storages';

import { generateMockProjects } from '@/__mocks__/utils/project-mock';
import { generateMockSecrets } from '@/__mocks__/utils/secrets-mock';
import { generateMockStorages } from '@/__mocks__/utils/storages-mock';

import { StorageScope, StorageType } from '@/types/enums/storages';

import { AddS3Storage } from '@/components/features/storages/AddS3Storage';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';
import { fetchSecrets } from '@/services/app/secrets';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
  __esModule: true,
}));

vi.mock('@/services/app/storages', () => ({
  createStorage: vi.fn(),
}));

vi.mock('@/services/app/secrets', () => ({
  fetchSecrets: vi.fn(),
}));

// Test data
const projects = generateMockProjects(2);

type FillFormParams = {
  name?: string;
  bucketUrl?: string;
  accessKeyName?: string;
  secretKeyName?: string;
  projectName?: string;
  secretName?: string;
};

const fillFormAndSubmit = async ({
  name,
  bucketUrl,
  accessKeyName,
  secretKeyName,
  secretName,
  projectName,
}: FillFormParams) => {
  // fill name input
  if (typeof name !== 'undefined') {
    await fireEvent.change(
      screen.getByRole('textbox', { name: /form.add.field.name.label/i }),
      {
        target: { value: name },
      },
    );
  }

  if (typeof bucketUrl !== 'undefined') {
    await fireEvent.change(
      screen.getByRole('textbox', { name: /form.add.field.bucketUrl.label/i }),
      {
        target: { value: bucketUrl },
      },
    );
  }

  if (typeof accessKeyName !== 'undefined') {
    await fireEvent.change(
      screen.getByRole('textbox', {
        name: /form.add.field.accessKeyName.label/i,
      }),
      {
        target: { value: accessKeyName },
      },
    );
  }

  if (typeof secretKeyName !== 'undefined') {
    await fireEvent.change(
      screen.getByRole('textbox', {
        name: /form.add.field.secretKeyName.label/i,
      }),
      {
        target: { value: secretKeyName },
      },
    );
  }

  if (typeof secretName !== 'undefined') {
    await fireEvent.click(
      screen.getAllByLabelText('form.add.field.secretId.label')[1],
    );
    await fireEvent.click(screen.getByRole('option', { name: secretName }));
  }

  if (typeof projectName !== 'undefined') {
    await fireEvent.click(
      screen.getAllByLabelText('form.add.field.projectIds.label')[1],
    );
    await fireEvent.click(screen.getByRole('option', { name: projectName }));
  }

  await fireEvent.click(screen.getByText('form.add.actions.add.label'));
};

describe('AddS3Storage', () => {
  const mockSecret = generateMockSecrets(1)[0];
  mockSecret.name = 'secret-001';
  mockSecret.id = 'secret-001-uuid';

  const mockProject = generateMockProjects(1)[0];
  mockProject.id = 'project-001-uuid';
  mockProject.name = 'project-001';

  const mockOpenAddSecret = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open and displays form fields', () => {
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[]}
          isOpen
          projects={projects}
          onClose={vi.fn()}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    expect(screen.getByText('form.add.title')).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.secretId.label')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.name.label')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.bucketUrl.label')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.accessKeyName.label')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.secretKeyName.label')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.projectIds.label')[0],
    ).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const { container } = render(
      <AddS3Storage
        storages={[]}
        secrets={[]}
        isOpen={false}
        projects={projects}
        onClose={vi.fn()}
        openAddSecret={mockOpenAddSecret}
      />,
      { wrapper },
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('fetchSecret to have been called on render', () => {
    const { container } = render(
      <AddS3Storage
        storages={[]}
        secrets={[]}
        isOpen={false}
        projects={projects}
        onClose={vi.fn()}
        openAddSecret={mockOpenAddSecret}
      />,
      { wrapper },
    );
    expect(fetchSecrets).toHaveBeenCalled();
  });

  it('calls onClose when cancel is clicked', () => {
    const onClose = vi.fn();

    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[]}
          isOpen
          projects={projects}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });
    fireEvent.click(screen.getByText('form.add.actions.cancel.label'));
    expect(onClose).toHaveBeenCalled();
  });

  it('checks for invalid name', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage 1',
      bucketUrl: 'http://test/test-bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.name.error.invalidName'),
      ).toBeInTheDocument();
    });
  });

  it('checks for duplicate name', async () => {
    const mockStorage = generateMockStorages(1)[0];
    mockStorage.name = 'test-storage-1';

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[mockStorage]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://test/test-bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.name.error.duplicateName'),
      ).toBeInTheDocument();
    });
  });

  it('checks for min length on name', async () => {
    const mockStorage = generateMockStorages(1)[0];
    mockStorage.name = 'test-storage-1';

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[mockStorage]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: '1',
      bucketUrl: 'http://test/test-bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.name.error.minLength'),
      ).toBeInTheDocument();
    });
  });

  it('checks for max length on name', async () => {
    const mockStorage = generateMockStorages(1)[0];
    mockStorage.name = 'test-storage-1';

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[mockStorage]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'a'.repeat(254),
      bucketUrl: 'http://test/test-bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.name.error.maxLength'),
      ).toBeInTheDocument();
    });
  });

  it('checks valid url format on bucketUrl', async () => {
    const mockStorage = generateMockStorages(1)[0];
    mockStorage.name = 'test-storage-1';

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://example.com/bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.queryByText('form.add.field.bucketUrl.error.invalidUrl'),
      ).not.toBeInTheDocument();
    });
  });

  it('checks invalid url format on bucketUrl', async () => {
    const mockStorage = generateMockStorages(1)[0];
    mockStorage.name = 'test-storage-1';

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'invalid',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.bucketUrl.error.invalidUrl'),
      ).toBeInTheDocument();
    });
  });

  it('calls mutate and onClose on form submit', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://example.com/bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(createStorage).toHaveBeenCalledWith({
        project_ids: ['project-001-uuid'],
        name: 'test-storage-1',
        secret_id: 'secret-001-uuid',
        scope: StorageScope.ORGANIZATION,
        type: StorageType.S3,
        spec: {
          bucket_url: 'http://example.com/bucket',
          access_key_name: 'test-access-key',
          secret_key_name: 'test-secret-key',
        },
      });
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows bucket url required error when bucket url does not start with http:// or https://', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'ftp://test',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.bucketUrl.error.invalidUrl'),
      ).toBeInTheDocument();
    });
  });

  it('shows bucket url required error when bucket url exceeds max 2043 characters', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://' + 'a'.repeat(2040),
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.bucketUrl.error.maxLength'),
      ).toBeInTheDocument();
    });
  });

  it('shows bucket url required error when bucket url is required', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    // change to make the form dirty first before filling blank
    await fireEvent.change(
      screen.getByRole('textbox', { name: /form.add.field.bucketUrl.label/i }),
      {
        target: { value: 'http://example.com/s3' },
      },
    );

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: '',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.bucketUrl.error.required'),
      ).toBeInTheDocument();
    });
  });

  it('calls mutate with correct project id when project is in props and onClose on form submit', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://example.com/bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast on mutation error', async () => {
    (createStorage as Mock).mockRejectedValueOnce(new Error('fail'));

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://example.com/bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'form.add.notification.error',
        expect.any(Error),
      );
    });
  });

  it('shows success toast on success create api call', async () => {
    (createStorage as Mock).mockResolvedValueOnce({});

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit({
      name: 'test-storage-1',
      bucketUrl: 'http://example.com/bucket',
      accessKeyName: 'test-access-key',
      secretKeyName: 'test-secret-key',
      secretName: 'secret-001',
      projectName: 'project-001',
    });

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith(
        'form.add.notification.success',
      );
    });
  });

  it('create secret button will open openAddSecret props callback', async () => {
    (createStorage as Mock).mockResolvedValueOnce({});

    const onClose = vi.fn();
    act(() => {
      render(
        <AddS3Storage
          storages={[]}
          secrets={[mockSecret]}
          isOpen
          projects={[mockProject]}
          onClose={onClose}
          openAddSecret={mockOpenAddSecret}
        />,
        {
          wrapper,
        },
      );
    });

    await fireEvent.click(
      screen.getByText('form.add.field.secretId.actions.createSecret'),
    );

    expect(mockOpenAddSecret).toHaveBeenCalled();
  });
});
