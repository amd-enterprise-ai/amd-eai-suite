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

import { createSecret } from '@/services/app/secrets';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';

import { SecretScope, SecretStatus, SecretType } from '@/types/enums/secrets';

import { AddSecret } from '@/components/features/secrets/AddSecret';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

const mockValidExternalSecretYAML = `
# example-external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-app-secrets
  namespace: <your project namespace> # or any namespace you want
spec:
  refreshInterval: 1m
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend-dev
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: secret1
      remoteRef:
        key: test # 'test' is the KV key path under local-testing/
        property: secret1
    - secretKey: secret2
      remoteRef:
        key: test
        property: secret2
 `;
const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
  __esModule: true,
}));

vi.mock('@/services/app/secrets', () => ({
  createSecret: vi.fn(),
}));

// Test data
const projects = generateMockProjects(2);

const fillFormAndSubmit = async (
  secretYaml: string = mockValidExternalSecretYAML,
) => {
  // fill project select
  await fireEvent.click(
    screen.getAllByLabelText('form.add.field.type.label')[1],
  );
  await fireEvent.click(
    screen.getByRole('option', { name: 'secretType.External' }),
  );

  // fill secret input
  fireEvent.change(
    screen.getByRole('textbox', { name: /form.add.field.manifest.label/i }),
    {
      target: { value: secretYaml },
    },
  );

  fireEvent.click(screen.getByText('form.add.action.add'));
};

describe('AddSecret', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open and displays form fields', () => {
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={vi.fn()} />,
        {
          wrapper,
        },
      );
    });

    expect(screen.getByText('form.add.title')).toBeInTheDocument();
    expect(
      screen.getByText('form.add.field.manifest.label'),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.type.label')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('form.add.field.projectIds.label')[0],
    ).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const { container } = render(
      <AddSecret
        secrets={[]}
        isOpen={false}
        projects={projects}
        onClose={vi.fn()}
      />,
      { wrapper },
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('calls onClose when cancel is clicked', () => {
    const onClose = vi.fn();

    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });
    fireEvent.click(screen.getByText('form.add.action.cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('checks for invalid ExternalSecrets api version', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit(
      mockValidExternalSecretYAML.replace(
        'apiVersion: external-secrets.io/v1beta1',
        'apiVersion: external-secrets.com/v1alpha1',
      ),
    );

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.manifest.error.yaml.incorrectGroup'),
      ).toBeInTheDocument();
    });
  });

  it('checks for invalid ExternalSecrets no name specified', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit(
      mockValidExternalSecretYAML.replace('name: my-app-secrets', ''),
    );

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.manifest.error.yaml.noName'),
      ).toBeInTheDocument();
    });
  });

  it('checks for invalid ExternalSecrets invalid name specified', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit(
      mockValidExternalSecretYAML.replace(
        'name: my-app-secrets',
        'name: My-app-secrets',
      ),
    );

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.manifest.error.yaml.invalidName'),
      ).toBeInTheDocument();
    });
  });

  it('checks for invalid ExternalSecrets wrong resource kind', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit(
      mockValidExternalSecretYAML.replace(
        'kind: ExternalSecret',
        'kind: OtherResourceKind',
      ),
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          'form.add.field.manifest.error.yaml.notExternalSecret',
        ),
      ).toBeInTheDocument();
    });
  });

  it('checks for invalid ExternalSecrets missing spec section', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit(
      mockValidExternalSecretYAML.replace(/spec:[\s\S]*/, ''),
    );

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.manifest.error.yaml.noSpec'),
      ).toBeInTheDocument();
    });
  });

  it('checks for duplicate secret name', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret
          secrets={[
            {
              name: 'my-app-secrets',
              displayName: '',
              id: '',
              type: SecretType.EXTERNAL,
              status: SecretStatus.UNASSIGNED,
              statusReason: null,
              scope: SecretScope.USER,
              projectSecrets: [],
              createdAt: '',
              updatedAt: '',
            },
          ]}
          isOpen
          projects={projects}
          onClose={onClose}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit(mockValidExternalSecretYAML);

    await waitFor(() => {
      expect(
        screen.getByText('form.add.field.manifest.error.yaml.duplicateName'),
      ).toBeInTheDocument();
    });
  });

  it('calls mutate and onClose on form submit', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit();

    await waitFor(() => {
      expect(createSecret).toHaveBeenCalledWith({
        project_ids: [],
        name: 'my-app-secrets',
        scope: SecretScope.ORGANIZATION,
        manifest: mockValidExternalSecretYAML,
        type: SecretType.EXTERNAL,
      });
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('calls mutate with correct project id when project is in props and onClose on form submit', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret
          secrets={[]}
          isOpen
          projects={projects}
          project={projects[0]}
          onClose={onClose}
        />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit();

    await waitFor(() => {
      expect(createSecret).toHaveBeenCalledWith({
        project_ids: [projects[0].id],
        name: 'my-app-secrets',
        scope: SecretScope.ORGANIZATION,
        manifest: mockValidExternalSecretYAML,
        type: SecretType.EXTERNAL,
      });
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast on mutation error', async () => {
    (createSecret as Mock).mockRejectedValueOnce(new Error('fail'));

    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit();

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'form.add.notification.error',
        expect.any(Error),
      );
    });
  });

  it('shows success toast on success create api call', async () => {
    (createSecret as Mock).mockResolvedValueOnce({});

    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret secrets={[]} isOpen projects={projects} onClose={onClose} />,
        {
          wrapper,
        },
      );
    });

    await fillFormAndSubmit();

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith(
        'form.add.notification.success',
      );
    });
  });
});
