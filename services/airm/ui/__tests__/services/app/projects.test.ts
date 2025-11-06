// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  addUsersToProject,
  createProject,
  deleteProject,
  deleteUserFromProject,
  fetchProject,
  fetchProjectAverageGPUIdleTime,
  fetchProjectAverageWaitTime,
  fetchProjectGPUDeviceUtilization,
  fetchProjectGPUMemoryUtilization,
  fetchProjectWorkloadsMetrics,
  fetchProjectWorkloadsStatuses,
  fetchProjects,
  fetchSubmittableProjects,
  getClusterProjects,
  updateProject,
} from '@/services/app/projects';

import { APIRequestError } from '@/utils/app/errors';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

globalThis.fetch = mockFetch as any;

beforeEach(() => {
  vi.clearAllMocks();
  mockJson.mockClear();
});

describe('projects service', () => {
  it('fetchProject success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await fetchProject('proj1');
    expect(mockFetch).toHaveBeenCalledWith('/api/projects/proj1');
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProject error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(fetchProject('proj1')).rejects.toThrow(APIRequestError);
  });

  it('fetchSubmittableProjects success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await fetchSubmittableProjects();
    expect(mockFetch).toHaveBeenCalledWith('/api/projects/submittable');
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchSubmittableProjects error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 400 });
    await expect(fetchSubmittableProjects()).rejects.toThrow(APIRequestError);
  });

  it('fetchProjects success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await fetchProjects();
    expect(mockFetch).toHaveBeenCalledWith('/api/projects');
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProjects error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });
    await expect(fetchProjects()).rejects.toThrow(APIRequestError);
  });

  it('createProject success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await createProject({
      name: 'test',
      description: 'desc',
      quota: {
        cpu_milli_cores: 0,
        gpu_count: 0,
        memory_bytes: 0,
        ephemeral_storage_bytes: 0,
      },
      cluster_id: 'cid',
    });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/projects',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(mockJson).toHaveBeenCalled();
  });

  it('createProject error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 400 });
    await expect(
      createProject({
        name: 'test',
        description: 'desc',
        quota: {
          cpu_milli_cores: 0,
          gpu_count: 0,
          memory_bytes: 0,
          ephemeral_storage_bytes: 0,
        },
        cluster_id: 'cid',
      }),
    ).rejects.toThrow(APIRequestError);
  });

  it('updateProject success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await updateProject({
      id: 'id1',
      description: 'desc',
      quota: {
        cpu_milli_cores: 0,
        gpu_count: 0,
        memory_bytes: 0,
        ephemeral_storage_bytes: 0,
      },
    });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/projects/id1',
      expect.objectContaining({ method: 'PUT' }),
    );
    expect(mockJson).toHaveBeenCalled();
  });

  it('updateProject error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 400 });
    await expect(
      updateProject({
        id: 'id1',
        description: 'desc',
        quota: {
          cpu_milli_cores: 0,
          gpu_count: 0,
          memory_bytes: 0,
          ephemeral_storage_bytes: 0,
        },
      }),
    ).rejects.toThrow(APIRequestError);
  });

  it('deleteProject success', async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await deleteProject('id1');
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/projects/id1',
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('deleteProject error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(deleteProject('id1')).rejects.toThrow(APIRequestError);
  });

  it('getClusterProjects success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await getClusterProjects('cluster1');
    expect(mockFetch).toHaveBeenCalledWith('/api/clusters/cluster1/projects');
    expect(mockJson).toHaveBeenCalled();
  });

  it('getClusterProjects error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(getClusterProjects('cluster1')).rejects.toThrow(
      /^Failed to get cluster projects/,
    );
  });

  it('addUsersToProject success', async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await addUsersToProject({ userIds: ['u1'], projectId: 'p1' });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/projects/p1/users',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('addUsersToProject error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 400 });
    await expect(
      addUsersToProject({ userIds: ['u1'], projectId: 'p1' }),
    ).rejects.toThrow(APIRequestError);
  });

  it('deleteUserFromProject success', async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await deleteUserFromProject({ userId: 'u1', projectId: 'p1' });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/projects/p1/users/u1',
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('deleteUserFromProject error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(
      deleteUserFromProject({ userId: 'u1', projectId: 'p1' }),
    ).rejects.toThrow(APIRequestError);
  });

  it('fetchProjectWorkloadsMetrics success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await fetchProjectWorkloadsMetrics('pid', {
      page: 1,
      pageSize: 10,
      filter: [],
      sort: [],
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/projects/pid/workloads/metrics?page=1&page_size=10&sort=%5B%5D&filter=%5B%5D',
    );
  });

  it('fetchProjectWorkloadsMetrics error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(
      fetchProjectWorkloadsMetrics('pid', {
        page: 1,
        pageSize: 10,
        filter: [],
        sort: [],
      }),
    ).rejects.toThrow(/^Failed to get Project Workloads Metrics/);
  });

  it('fetchProjectWorkloadsStatuses success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    await fetchProjectWorkloadsStatuses('pid');
    expect(mockFetch).toHaveBeenCalledWith('/api/projects/pid/workloads/stats');
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProjectWorkloadsStatuses error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(fetchProjectWorkloadsStatuses('pid')).rejects.toThrow(
      /^Failed to get Project Workloads Statuses/,
    );
  });

  it('fetchProjectGPUDeviceUtilization success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    await fetchProjectGPUDeviceUtilization('pid', start, end);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/projects/pid/metrics/gpu-device-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProjectGPUDeviceUtilization error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const start = new Date();
    const end = new Date();
    await expect(
      fetchProjectGPUDeviceUtilization('pid', start, end),
    ).rejects.toThrow(/^Failed to get project GPU Device Utilization/);
  });

  it('fetchProjectGPUMemoryUtilization success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    await fetchProjectGPUMemoryUtilization('pid', start, end);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/projects/pid/metrics/gpu-memory-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProjectGPUMemoryUtilization error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const start = new Date();
    const end = new Date();
    await expect(
      fetchProjectGPUMemoryUtilization('pid', start, end),
    ).rejects.toThrow(/^Failed to get project GPU Memory Utilization/);
  });

  it('fetchProjectAverageWaitTime success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    await fetchProjectAverageWaitTime('pid', start, end);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/projects/pid/metrics/average-wait-time/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProjectAverageWaitTime error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const start = new Date();
    const end = new Date();
    await expect(
      fetchProjectAverageWaitTime('pid', start, end),
    ).rejects.toThrow(/^Failed to get project Average Wait Time/);
  });

  it('fetchProjectAverageGPUIdleTime success', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: mockJson });
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    await fetchProjectAverageGPUIdleTime('pid', start, end);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/projects/pid/metrics/average-gpu-idle-time/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
    expect(mockJson).toHaveBeenCalled();
  });

  it('fetchProjectAverageGPUIdleTime error', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const start = new Date();
    const end = new Date();
    await expect(
      fetchProjectAverageGPUIdleTime('pid', start, end),
    ).rejects.toThrow(/^Failed to get project GPU Idle Time/);
  });
});
