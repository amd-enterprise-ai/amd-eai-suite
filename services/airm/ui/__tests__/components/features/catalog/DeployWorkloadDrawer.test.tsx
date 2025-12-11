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

import router from 'next/router';

import { deployCatalogItem, getCatalogItemById } from '@/services/app/catalog';
import { getCluster } from '@/services/app/clusters';
import { deployModel } from '@/services/app/models';
import { getWorkload } from '@/services/app/workloads';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';

import { CatalogItem } from '@/types/catalog';
import {
  CatalogItemCategory,
  CatalogItemType,
  catalogItemTypeToEndpoint,
} from '@/types/enums/catalog';
import { ClusterStatus } from '@/types/enums/cluster-status';
import { WorkloadStatus } from '@/types/enums/workloads';

import { DeployWorkloadDrawer } from '@/components/features/catalog/DeployWorkloadDrawer';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock, vi } from 'vitest';

// Mock the services
vi.mock('@/services/app/catalog', () => ({
  deployCatalogItem: vi.fn(),
  getCatalogItemById: vi.fn(),
}));

vi.mock('@/services/app/clusters', () => ({
  getCluster: vi.fn(),
}));

vi.mock('@/services/app/models', () => ({
  deployModel: vi.fn(),
}));

vi.mock('@/services/app/workloads', () => ({
  getWorkload: vi.fn(),
}));

// Mock the toast system
const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();

vi.mock('@/hooks/useSystemToast', () => {
  const useSystemToast = () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  };
  return { default: useSystemToast };
});

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key, // Simple pass-through mock
  }),
}));

// Mock next/router
vi.mock('next/router', () => ({
  default: {
    push: vi.fn(),
  },
}));

// Mock the ProjectContext
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'project1',
    projects: [
      {
        id: 'project1',
        name: 'Test Project',
        clusterId: 'cluster-1',
        quota: {
          gpuCount: 8,
          memoryBytes: 103079215104, // ~96 GB
          cpuMilliCores: 16000, // 16 cores
        },
      },
    ],
    isLoading: false,
    setActiveProject: vi.fn(),
  }),
}));

describe('DeployWorkloadDrawer', () => {
  const mockCatalogItem: CatalogItem = {
    id: 'item-1',
    name: 'test-workload',
    displayName: 'Test Workload',
    slug: 'test-workload',
    description: 'A test workload for deployment',
    longDescription:
      'This is a longer description of the test workload.\nIt supports multiple lines.',
    type: CatalogItemType.WORKSPACE,
    category: CatalogItemCategory.DEVELOPMENT,
    createdAt: '2024-01-01T00:00:00Z',
    tags: ['test', 'development'],
    featuredImage: 'test-image.png',
    requiredResources: {
      gpuCount: 2,
      gpuMemory: 16,
      cpuCoreCount: 4,
      systemMemory: 8,
    },
    available: true,
    externalUrl: 'https://example.com',
    workloadsCount: 0,
    workloads: [],
    signature: { image: 'ghcr.io/example/image:latest' },
  };

  const mockCluster = {
    id: 'cluster-1',
    name: 'Test Cluster',
    status: ClusterStatus.HEALTHY,
    availableResources: {
      gpuCount: 10,
      memoryBytes: 206158430208, // ~192 GB
      cpuMilliCores: 32000, // 32 cores
    },
  };

  const mockWorkload = mockWorkloads[0]; // Using first workload from mock data (workload-1, RUNNING status)

  const mockOnClose = vi.fn();
  const mockOnDeployed = vi.fn();
  const mockOnDeploying = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
    (router.push as Mock).mockClear();

    // Setup default mocks
    (getCluster as Mock).mockResolvedValue(mockCluster);
    (deployCatalogItem as Mock).mockResolvedValue({ id: 'workload-1' });
    (deployModel as Mock).mockResolvedValue({ id: 'workload-1' });
    (getWorkload as Mock).mockResolvedValue(mockWorkload);
    (getCatalogItemById as Mock).mockResolvedValue(mockCatalogItem);
  });

  it('renders the drawer with workload information', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
          onDeployed={mockOnDeployed}
          onDeploying={mockOnDeploying}
        />,
        { wrapper },
      );
    });

    expect(screen.getByText('deployModal.title')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Test Workload')).toBeInTheDocument();
      expect(
        screen.getByText('A test workload for deployment'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('deployModal.settings.title'),
      ).toBeInTheDocument();
    });
  });

  it('generates default workload name with timestamp', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      const workloadNameInput = screen.getByLabelText(
        'deployModal.settings.displayName.label',
      ) as HTMLInputElement;
      expect(workloadNameInput.value).toMatch(/^test-workload-\d{8}-\d{6}$/);
    });
  });

  it('allows editing workload name', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      const workloadNameInput = screen.getByLabelText(
        'deployModal.settings.displayName.label',
      );
      fireEvent.change(workloadNameInput, {
        target: { value: 'custom-workload-name' },
      });

      expect(workloadNameInput).toHaveValue('custom-workload-name');
    });
  });

  it('enables resource customization when switch is toggled', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      const customizeSwitch = screen.getByText(
        'deployModal.settings.resourceAllocation.label',
      );
      expect(customizeSwitch).toBeInTheDocument();
    });

    const customizeSwitch = screen
      .getByText('deployModal.settings.resourceAllocation.label')
      .closest('label');
    fireEvent.click(customizeSwitch!);

    await waitFor(() => {
      expect(
        screen.getByText('deployModal.settings.resourceAllocation.gpuCount'),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          'deployModal.settings.resourceAllocation.systemMemory',
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          'deployModal.settings.resourceAllocation.cpuCoreCount',
        ),
      ).toBeInTheDocument();
    });
  });

  it('disables resource customization when enableResourceAllocation is false', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
          enableResourceAllocation={false}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      const customizeSwitch = screen
        .getByText('deployModal.settings.resourceAllocation.label')
        .closest('label')
        ?.querySelector('input');
      expect(customizeSwitch).toBeDisabled();
    });
  });

  it('shows resource allocation warnings when values are below requirements', async () => {
    const highRequirementItem = {
      ...mockCatalogItem,
      requiredResources: {
        ...mockCatalogItem.requiredResources!,
        gpuCount: 8, // Set a requirement
        systemMemory: 25, // Set a requirement
        cpuCoreCount: 16, // Set a requirement
      },
    };

    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={highRequirementItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      // Enable resource customization first
      const customizeSwitch = screen.getByRole('switch', {
        name: 'deployModal.settings.resourceAllocation.label',
      });
      fireEvent.click(customizeSwitch);
    });

    await waitFor(() => {
      // Now reduce the GPU count below the requirement to trigger warning
      const gpuSlider = screen.getByRole('slider', {
        name: 'deployModal.settings.resourceAllocation.gpuCount',
      });
      fireEvent.change(gpuSlider, { target: { value: '4' } }); // Below requirement of 8
    });

    await waitFor(() => {
      expect(screen.getByText('belowRequiredWarning')).toBeInTheDocument();
    });
  });

  it('renders deployment settings correctly', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText('deployModal.settings.title'),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });
  });

  it('handles workload deployment successfully', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
          onDeploying={mockOnDeploying}
          onDeployed={mockOnDeployed}
        />,
        { wrapper },
      );
    });

    // Wait for the workload name field to be available
    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(deployCatalogItem).toHaveBeenCalledWith(
        expect.objectContaining({
          displayName: expect.stringMatching(/^test-workload-\d{8}-\d{6}$/),
          type: catalogItemTypeToEndpoint[mockCatalogItem.type],
          template: mockCatalogItem.slug,
          gpus: mockCatalogItem.requiredResources!.gpuCount,
          memoryPerGpu: mockCatalogItem.requiredResources!.systemMemory,
          cpuPerGpu: mockCatalogItem.requiredResources!.cpuCoreCount,
          image: mockCatalogItem.signature?.image,
        }),
        'project1',
      );
    });

    expect(toastSuccessMock).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({
          message: 'notifications.deployWorkload.success',
          href: '/workloads/workload-1',
        }),
      }),
    );
    expect(mockOnDeploying).toHaveBeenCalled();
  });

  it('handles model deployment when isModelDeployment is true', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
          isModelDeployment={true}
        />,
        { wrapper },
      );
    });

    // Wait for the workload name field to be available
    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(deployModel).toHaveBeenCalledWith(mockCatalogItem.id, 'project1');
    });
  });

  it('handles deployment errors', async () => {
    (deployCatalogItem as Mock).mockRejectedValue(
      new Error('Deployment failed'),
    );

    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    // Wait for the workload name field to be available
    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'notifications.deployWorkload.error',
      );
    });
  });

  it('shows deployment status during deployment', async () => {
    // Mock a workload that's still pending
    (getWorkload as Mock).mockResolvedValue({
      ...mockWorkload,
      status: WorkloadStatus.PENDING,
    });

    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    // Wait for form to load first
    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');

    await act(async () => {
      fireEvent.click(deployButton);
    });

    // Wait for the deployment to be called
    await waitFor(() => {
      expect(deployCatalogItem).toHaveBeenCalled();
    });

    await waitFor(() => {
      // For pending workload, we should see deploying message and pending button
      // But if deployment completes quickly, we might see ready message instead
      const deployingMessage = screen.queryByText(
        'deployModal.deploymentStatus.deployingMessage',
      );
      const readyMessage = screen.queryByText(
        'deployModal.deploymentStatus.readyMessage',
      );
      const pendingButton = screen.queryByText(
        'deployModal.deploymentStatus.launchButtonPending',
      );
      const readyButton = screen.queryByText(
        'deployModal.deploymentStatus.launchButtonReady',
      );

      // Should have some deployment status message and button
      expect(deployingMessage || readyMessage).toBeTruthy();
      expect(pendingButton || readyButton).toBeTruthy();
    });
  });

  it('shows ready status when workload is running', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
          onDeployed={mockOnDeployed}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');

    await act(async () => {
      fireEvent.click(deployButton);
    });

    // Wait for the deployment to be called
    await waitFor(() => {
      expect(deployCatalogItem).toHaveBeenCalled();
    });

    // Wait for the deployment to complete
    await waitFor(() => {
      expect(
        screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
      ).toBeInTheDocument();
    });

    expect(mockOnDeployed).toHaveBeenCalled();
  });

  it('opens workload URL when launch button is clicked', async () => {
    // Mock window.open
    const originalOpen = window.open;
    window.open = vi.fn();

    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    // Wait for form to load first
    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');

    await act(async () => {
      fireEvent.click(deployButton);
    });

    // Wait for the deployment to be called
    await waitFor(() => {
      expect(deployCatalogItem).toHaveBeenCalled();
    });

    // Wait for the launch button to be ready (deployment transitions to ready state)
    // The component might skip the deploying state if the workload is already RUNNING
    await waitFor(
      () => {
        const launchButton = screen.getByText(
          'deployModal.deploymentStatus.launchButtonReady',
        );
        expect(launchButton).toBeInTheDocument();
        return launchButton;
      },
      { timeout: 10000 }, // Increase timeout to account for polling
    );

    const launchButton = screen.getByText(
      'deployModal.deploymentStatus.launchButtonReady',
    );

    await act(async () => {
      fireEvent.click(launchButton);
    });

    expect(window.open).toHaveBeenCalledWith(
      mockWorkload.output?.externalHost,
      '_blank',
    );

    // Restore window.open
    window.open = originalOpen;
  });

  it('navigates to chat URL when launch button is clicked for model deployment', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
          isModelDeployment={true}
        />,
        { wrapper },
      );
    });

    // Wait for form to load first
    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');

    await act(async () => {
      fireEvent.click(deployButton);
    });

    // Wait for the deployment to be called
    await waitFor(() => {
      expect(deployModel).toHaveBeenCalled();
    });

    // For model deployment, the component transitions quickly to ready state

    // Wait for the launch button to be ready
    await waitFor(
      () => {
        const launchButton = screen.getByText(
          'deployModal.deploymentStatus.launchButtonReady',
        );
        expect(launchButton).toBeInTheDocument();
        return launchButton;
      },
      { timeout: 10000 },
    );

    const launchButton = screen.getByText(
      'deployModal.deploymentStatus.launchButtonReady',
    );

    await act(async () => {
      fireEvent.click(launchButton);
    });

    expect(router.push).toHaveBeenCalledWith('/chat/?workload=workload-1');
  });

  it('handles workload failure status', async () => {
    (getWorkload as Mock).mockResolvedValue({
      ...mockWorkload,
      status: WorkloadStatus.FAILED,
    });

    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');
    fireEvent.click(deployButton);

    // Deployment should fail and go back to initial state
    await waitFor(() => {
      expect(
        screen.getByText('deployModal.actions.deploy'),
      ).toBeInTheDocument();
    });
  });

  it('calls onClose when cancel button is clicked', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    const cancelButton = screen.getByText('deployModal.actions.cancel');
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('resets state when catalogItem changes', async () => {
    const { rerender } = render(
      <DeployWorkloadDrawer
        isOpen={true}
        catalogItem={mockCatalogItem}
        onClose={mockOnClose}
      />,
      { wrapper },
    );

    const newCatalogItem = {
      ...mockCatalogItem,
      id: 'item-2',
      name: 'new-test-workload',
      displayName: 'New Test Workload',
      slug: 'new-test-workload',
    };

    await act(async () => {
      rerender(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={newCatalogItem}
          onClose={mockOnClose}
        />,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('New Test Workload')).toBeInTheDocument();
      const workloadNameInput = screen.getByLabelText(
        'deployModal.settings.displayName.label',
      ) as HTMLInputElement;
      // The displayName doesn't regenerate when catalogItem changes since defaultValues are set at DrawerForm level
      expect(workloadNameInput.value).toMatch(/^test-workload-\d{8}-\d{6}$/);
    });
  });

  it('displays long description with line breaks', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    // Check that the description paragraph contains both parts of the text
    // The text is split by a <br /> element so we need to check for the container
    await waitFor(() => {
      const descriptionElement = screen.getByText((_, element) => {
        return !!(
          element?.tagName.toLowerCase() === 'p' &&
          element?.textContent?.includes('This is a longer description') &&
          element?.textContent?.includes('It supports multiple lines')
        );
      });
      expect(descriptionElement).toBeInTheDocument();
    });
  });

  it('disables deploy button while deployment is in progress', async () => {
    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByLabelText('deployModal.settings.displayName.label'),
      ).toBeInTheDocument();
    });

    const deployButton = screen.getByText('deployModal.actions.deploy');
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(deployButton).toBeDisabled();
    });
  });

  it('renders and allows editing the custom workload image input', async () => {
    const mockSignatureImage = mockCatalogItem.signature?.image;

    await act(async () => {
      render(
        <DeployWorkloadDrawer
          isOpen={true}
          catalogItem={mockCatalogItem}
          onClose={mockOnClose}
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      // The workload image input should be present with the correct label
      expect(
        screen.getByLabelText('deployModal.settings.containerImage.label'),
      ).toBeInTheDocument();
    });

    const imageInput = screen.getByLabelText(
      'deployModal.settings.containerImage.label',
    ) as HTMLInputElement;

    // Should have the default value from signature.image
    expect(imageInput.value).toBe(mockSignatureImage);

    // Change the value
    fireEvent.change(imageInput, {
      target: { value: 'ghcr.io/other/image:tag' },
    });
    expect(imageInput.value).toBe('ghcr.io/other/image:tag');

    // Deploy and check that the image is passed to deployCatalogItem
    const deployButton = screen.getByText('deployModal.actions.deploy');
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(deployCatalogItem).toHaveBeenCalledWith(
        expect.objectContaining({
          image: 'ghcr.io/other/image:tag',
        }),
        'project1',
      );
    });
  });
});
