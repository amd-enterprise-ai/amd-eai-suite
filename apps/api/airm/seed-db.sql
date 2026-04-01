-- Copyright © Advanced Micro Devices, Inc., or its affiliates.
--
-- SPDX-License-Identifier: MIT

INSERT INTO clusters(
    name,
    id,
    created_at,
    updated_at,
    created_by,
    updated_by,
    last_heartbeat_at,
    workloads_base_url,
    kube_api_url
) VALUES (
    'Cluster_1',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system',
    now() + interval '5 years',
    'http://workloads.localhost',
    'http://k8s.localhost'
) ON CONFLICT DO NOTHING;

INSERT INTO projects(
    name,
    cluster_id,
    description,
    id,
    status,
    status_reason,
    keycloak_group_id,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'research-and-development',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    'For R&D Work within AMD',
    '79ae32ed-bb33-4e01-a30a-808201183905',
    'Pending',
    NULL,
    'e0c53b4b-9f76-4aa4-801b-06abdca55ca4',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO users (
    email,
    keycloak_user_id,
    id,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'devuser@amd.com',
    '487590ed-165c-44d5-b686-1aff81cca298',
    '487590ed-165c-44d5-b686-1aff81cca298',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

-- Insert managed workload with custom type
INSERT INTO workloads (
    status,
    cluster_id,
    id,
    project_id,
    created_at,
    updated_at,
    created_by,
    updated_by,
    display_name,
    type
) VALUES (
    'Pending',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    'facb2e58-a757-4e49-aee7-88e2ba85f59f',
    '79ae32ed-bb33-4e01-a30a-808201183905',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system',
    'Custom Application Demo',
    'CUSTOM'
) ON CONFLICT DO NOTHING;

-- Insert workload component for the custom workload
INSERT INTO workload_components (
    id,
    name,
    kind,
    api_version,
    workload_id,
    status,
    status_reason,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'c1d2e3f4-a5b6-7890-cdef-123456789abc',
    'custom-app-demo',
    'Deployment',
    'apps/v1',
    'facb2e58-a757-4e49-aee7-88e2ba85f59f',
    'Running',
    'Deployment has minimum availability',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO cluster_nodes (
    id,
    cluster_id,
    name,
    cpu_milli_cores,
    memory_bytes,
    ephemeral_storage_bytes,
    gpu_count,
    gpu_type,
    gpu_vendor,
    gpu_vram_bytes_per_device,
    gpu_product_name,
    status,
    is_ready,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    '7157d3e2-300d-40b1-b39b-2b600b178c71',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    'dummy-gpu-node',
    8000,
    214748364800,
    107374182400,
    8,
    '740c',
    'AMD',
    68719476736,
    'Instinct MI250X',
    'Ready',
    TRUE,
    TIMESTAMP '2025-02-19 10:23:54+02',
    TIMESTAMP '2025-02-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO quotas (
    id,
    cluster_id,
    project_id,
    cpu_milli_cores,
    memory_bytes,
    ephemeral_storage_bytes,
    gpu_count,
    status,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'f5a56f5b-8742-4b6d-bc67-89de30ba3abc',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    '79ae32ed-bb33-4e01-a30a-808201183905',
    2000,
    10737418240,
    10737418240,
    2,
    'Ready',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO namespaces (
    id,
    name,
    cluster_id,
    project_id,
    status,
    status_reason,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    '2c8a9f3e-1b7d-4e5f-9c2a-8d6b3e4f7a1c',
    'research-and-development',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    '79ae32ed-bb33-4e01-a30a-808201183905',
    'Pending',
    'Creating',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO secrets (
    id,
    name,
    type,
    scope,
    manifest,
    status,
    status_reason,
    created_at,
    updated_at,
    created_by,
    updated_by,
    use_case
) VALUES (
    '0fe6afa0-435d-4736-9201-1ae916e3c53c',
    'my-app-secrets',
    'ExternalSecret',
    'Organization',
    'apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: my-app-secrets
  labels:
    airm.silogen.com/use-case: generic
    airm.silogen.ai/secret-scope: organization
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
      key: test
      property: secret1
  - secretKey: secret2
    remoteRef:
      key: test
      property: secret2
',
    'Unassigned',
    NULL,
    '2025-12-17 09:51:24.116632+00',
    '2025-12-17 09:55:33.762408+00',
    'devuser@amd.com',
    'system',
    'Generic'
) ON CONFLICT DO NOTHING;
