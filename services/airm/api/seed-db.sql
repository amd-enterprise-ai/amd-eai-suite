-- Copyright © Advanced Micro Devices, Inc., or its affiliates.
--
-- SPDX-License-Identifier: MIT

-- Create an organization
INSERT INTO organizations (
    name,
    id,
    created_at,
    updated_at,
    created_by,
    updated_by,
    keycloak_organization_id,
    keycloak_group_id
) VALUES (
    'AMD',
    '08ccd4e0-3bef-480c-8e08-a21f47f51421',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system',
    '8f6178e7-7da2-433a-a0df-3c8cf4547829',
    'a6d5420b-665a-4245-959e-b2b91fb9a399'
) ON CONFLICT DO NOTHING;

INSERT INTO clusters(
    name,
    organization_id,
    id,
    created_at,
    updated_at,
    created_by,
    updated_by,
    last_heartbeat_at,
    base_url
) VALUES (
    'Cluster_1',
    '08ccd4e0-3bef-480c-8e08-a21f47f51421',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system',
    now() + interval '5 years',
    'http://localhost'
) ON CONFLICT DO NOTHING;

INSERT INTO projects(
    name,
    organization_id,
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
    '08ccd4e0-3bef-480c-8e08-a21f47f51421',
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
    organization_id,
    keycloak_user_id,
    id,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'devuser@amd.com',
    '08ccd4e0-3bef-480c-8e08-a21f47f51421',
    '487590ed-165c-44d5-b686-1aff81cca298',
    '487590ed-165c-44d5-b686-1aff81cca298',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

-- Insert a chart for custom workloads
INSERT INTO charts (
    id,
    name,
    type,
    signature,
    description,
    long_description,
    category,
    tags,
    featured_image,
    required_resources,
    external_url,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'custom-workload-chart',
    'CUSTOM',
    '{"inputs": {"name": {"type": "string", "required": true}, "image": {"type": "string", "required": true}, "replicas": {"type": "integer", "default": 1}}}',
    'Custom Workload Chart',
    'A flexible chart for deploying custom workloads with configurable parameters',
    'Custom Applications',
    '["custom", "generic", "deployment"]',
    'https://example.com/custom-chart-image.png',
    '{"cpu": "100m", "memory": "128Mi"}',
    'https://github.com/example/custom-workload-chart',
    TIMESTAMP '2025-01-19 10:23:54+02',
    TIMESTAMP '2025-01-19 10:23:54+02',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

-- Insert chart files for the custom workload chart
INSERT INTO chart_files (
    id,
    path,
    content,
    chart_id,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'f1e2d3c4-b5a6-9807-dcba-fe9876543210',
    'templates/deployment.yaml',
    'apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.name }}
  namespace: {{ .Release.Namespace }}
spec:
  replicas: {{ .Values.replicas | default 1 }}
  selector:
    matchLabels:
      app: {{ .Values.name }}
  template:
    metadata:
      labels:
        app: {{ .Values.name }}
    spec:
      containers:
      - name: {{ .Values.name }}
        image: {{ .Values.image }}
        resources:
          requests:
            cpu: {{ .Values.resources.cpu | default "100m" }}
            memory: {{ .Values.resources.memory | default "128Mi" }}',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
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
    type,
    kind,
    name,
    chart_id,
    user_inputs
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
    'CUSTOM',
    'managed',
    'custom-app-demo',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '{"name": "custom-app-demo", "image": "nginx:latest", "replicas": 2}'
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
