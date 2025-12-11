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

import { createProjectSecret, createSecret } from '@/services/app/secrets';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';

import {
  SecretScope,
  SecretStatus,
  SecretType,
  SecretUseCase,
} from '@/types/enums/secrets';

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
  createProjectSecret: vi.fn(),
}));

// Test data
const projects = generateMockProjects(2);

const fillFormAndSubmit = async (
  secretYaml: string = mockValidExternalSecretYAML,
) => {
  // The type defaults to EXTERNAL_SECRET, so we don't need to change it
  // Just fill the manifest input directly

  // fill secret input
  await fireEvent.change(
    screen.getByRole('textbox', {
      name: /form.add.field.manifest.externalSecret.label/i,
    }),
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

    expect(screen.getByText('form.add.title.general')).toBeInTheDocument();
    expect(
      screen.getByText('form.add.field.manifest.externalSecret.label'),
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
        screen.getByText(
          /form\.add\.field\.manifest\.error\.yaml\.incorrectGroup/,
        ),
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
        screen.getByText(/form\.add\.field\.manifest\.error\.yaml\.noName/),
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
        screen.getByText(
          /form\.add\.field\.manifest\.error\.yaml\.invalidName/,
        ),
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
          /form\.add\.field\.manifest\.error\.yaml\.incorrectKind/,
        ),
      ).toBeInTheDocument();
    });
  });

  it('checks for duplicate secret name with same type (organization scope)', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret
          secrets={[
            {
              name: 'my-app-secrets',
              displayName: '',
              id: '',
              type: SecretType.EXTERNAL_SECRET,
              status: SecretStatus.UNASSIGNED,
              statusReason: null,
              scope: SecretScope.ORGANIZATION,
              projectSecrets: [],
              createdAt: '',
              updatedAt: '',
              createdBy: 'test@amd.com',
              updatedBy: 'test@amd.com',
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

  it('allows duplicate secret name with different type (organization scope)', async () => {
    const onClose = vi.fn();
    act(() => {
      render(
        <AddSecret
          secrets={[
            {
              name: 'my-app-secrets',
              displayName: '',
              id: '',
              type: SecretType.KUBERNETES_SECRET,
              status: SecretStatus.UNASSIGNED,
              statusReason: null,
              scope: SecretScope.ORGANIZATION,
              projectSecrets: [],
              createdAt: '',
              updatedAt: '',
              createdBy: 'test@amd.com',
              updatedBy: 'test@amd.com',
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
      expect(createSecret).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('checks for duplicate secret name and type in same project (project scope)', async () => {
    const onClose = vi.fn();
    const project = projects[0];
    act(() => {
      render(
        <AddSecret
          secrets={[
            {
              name: 'my-app-secrets',
              displayName: '',
              id: '',
              type: SecretType.EXTERNAL_SECRET,
              status: SecretStatus.UNASSIGNED,
              statusReason: null,
              scope: SecretScope.PROJECT,
              projectSecrets: [
                {
                  id: 'ps1',
                  projectId: project.id,
                  projectName: project.name,
                  scope: SecretScope.PROJECT,
                  status: 'Synced' as any,
                  statusReason: null,
                  createdAt: '',
                  createdBy: 'test@amd.com',
                  updatedAt: '',
                  updatedBy: 'test@amd.com',
                },
              ],
              createdAt: '',
              updatedAt: '',
              createdBy: 'test@amd.com',
              updatedBy: 'test@amd.com',
            },
          ]}
          isOpen
          project={project}
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
        type: SecretType.EXTERNAL_SECRET,
        use_case: 'Generic',
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
      expect(createProjectSecret).toHaveBeenCalledWith(projects[0].id, {
        name: 'my-app-secrets',
        manifest: mockValidExternalSecretYAML,
        type: SecretType.EXTERNAL_SECRET,
        use_case: 'Generic',
        scope: SecretScope.PROJECT,
        project_ids: [projects[0].id],
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

  describe('restrictToUseCases prop', () => {
    it('restricts context field to S3 when restrictToUseCases is [S3]', () => {
      act(() => {
        render(
          <AddSecret
            secrets={[]}
            isOpen
            projects={projects}
            onClose={vi.fn()}
            restrictToUseCases={[SecretUseCase.S3]}
          />,
          {
            wrapper,
          },
        );
      });

      // Should display S3 as the context
      expect(screen.getAllByText('useCase.S3').length).toBeGreaterThan(0);
    });

    it('restricts context field to HUGGING_FACE when restrictToUseCases is [HUGGING_FACE]', () => {
      act(() => {
        render(
          <AddSecret
            secrets={[]}
            isOpen
            projects={projects}
            onClose={vi.fn()}
            restrictToUseCases={[SecretUseCase.HUGGING_FACE]}
          />,
          {
            wrapper,
          },
        );
      });

      expect(screen.getAllByText('useCase.HuggingFace').length).toBeGreaterThan(
        0,
      );
    });

    it('submits with S3 use case when restricted to [S3]', async () => {
      (createSecret as Mock).mockResolvedValueOnce({});
      const onClose = vi.fn();

      act(() => {
        render(
          <AddSecret
            secrets={[]}
            isOpen
            projects={projects}
            onClose={onClose}
            restrictToUseCases={[SecretUseCase.S3]}
          />,
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
          type: SecretType.EXTERNAL_SECRET,
          use_case: SecretUseCase.S3,
        });
        expect(onClose).toHaveBeenCalled();
      });
    });

    it('allows all use cases when restrictToUseCases is not provided', () => {
      act(() => {
        render(
          <AddSecret
            secrets={[]}
            isOpen
            projects={projects}
            onClose={vi.fn()}
          />,
          {
            wrapper,
          },
        );
      });

      // Should show default Generic use case
      expect(screen.getAllByText('useCase.Generic').length).toBeGreaterThan(0);
    });

    it('allows multiple use cases when restrictToUseCases has multiple values', () => {
      act(() => {
        render(
          <AddSecret
            secrets={[]}
            isOpen
            projects={projects}
            onClose={vi.fn()}
            restrictToUseCases={[SecretUseCase.S3, SecretUseCase.DB]}
          />,
          {
            wrapper,
          },
        );
      });

      // Should show both S3 and Database options
      expect(screen.getAllByText('useCase.S3').length).toBeGreaterThan(0);
      expect(screen.getAllByText('useCase.Database').length).toBeGreaterThan(0);
    });

    it('submits with restricted use case for project secrets', async () => {
      (createProjectSecret as Mock).mockResolvedValueOnce({});
      const onClose = vi.fn();
      const project = projects[0];

      act(() => {
        render(
          <AddSecret
            secrets={[]}
            isOpen
            projects={projects}
            project={project}
            onClose={onClose}
            restrictToUseCases={[SecretUseCase.S3]}
          />,
          {
            wrapper,
          },
        );
      });

      await fillFormAndSubmit();

      await waitFor(() => {
        expect(createProjectSecret).toHaveBeenCalledWith(project.id, {
          name: 'my-app-secrets',
          manifest: mockValidExternalSecretYAML,
          type: SecretType.EXTERNAL_SECRET,
          use_case: SecretUseCase.S3,
          scope: SecretScope.PROJECT,
          project_ids: [project.id],
        });
        expect(onClose).toHaveBeenCalled();
      });
    });
  });
});
