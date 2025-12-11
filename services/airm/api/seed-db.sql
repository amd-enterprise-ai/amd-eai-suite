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
    workloads_base_url,
    kube_api_url
) VALUES (
    'Cluster_1',
    '08ccd4e0-3bef-480c-8e08-a21f47f51421',
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

-- Insert AIMs (AMD Inference Microservices)
INSERT INTO aims (
    id,
    resource_name,
    image_reference,
    labels,
    status,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'a1b2c3d4-5678-90ab-cdef-111111111111',
    'aim-meta-llama-llama-3-1-8b-instruct-0-8-4',
    'docker.io/amdenterpriseai/aim-meta-llama-llama-3-1-8b-instruct:0.8.4',
    '{
        "com.amd.aim.description.full": "The Meta Llama 3.1 collection, released by Meta on July 23, 2024, is a set of multilingual large language models available in 8B, 70B, and 405B parameter sizes. The models are offered in both pretrained and instruction-tuned versions, with the latter being optimized for dialogue use cases. Built on an auto-regressive transformer architecture with Grouped-Query Attention (GQA), the tuned models are refined using Supervised Fine-Tuning (SFT) and Reinforcement Learning with Human Feedback (RLHF). Llama 3.1 is intended for commercial and research applications. The instruction-tuned models are designed for assistant-like chat, while the pretrained models can be adapted for various natural language generation tasks. The custom commercial license also allows for using the model''s output for synthetic data generation and distillation to improve other models.",
        "com.amd.aim.hfToken.required": "True",
        "com.amd.aim.model.canonicalName": "meta-llama/Llama-3.1-8B-Instruct",
        "com.amd.aim.model.recommendedDeployments": "{''gpuModel'': ''MI300X'', ''gpuCount'': 1, ''precision'': ''fp8'', ''metric'': ''latency'', ''description'': ''Optimized for latency on MI300X using fp8 precision''}, {''gpuModel'': ''MI300X'', ''gpuCount'': 1, ''precision'': ''fp8'', ''metric'': ''throughput'', ''description'': ''Optimized for throughput on MI300X using fp8 precision''}",
        "com.amd.aim.model.source": "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        "com.amd.aim.model.tags": "text-generation, chat, instruction",
        "com.amd.aim.model.variants": "amd/Llama-3.1-8B-Instruct-FP8-KV, meta-llama/Llama-3.1-8B-Instruct",
        "com.amd.aim.release.notes": "",
        "com.amd.aim.title": "meta-llama/Llama-3.1-8B-Instruct",
        "org.opencontainers.image.authors": "",
        "org.opencontainers.image.created": "2025-11-11T10:45:11Z",
        "org.opencontainers.image.description": "Instruction-tuned version of Llama 3.1 8B optimized for chat and instruction following.",
        "org.opencontainers.image.documentation": "",
        "org.opencontainers.image.licenses": "llama3.1, MIT",
        "org.opencontainers.image.ref.name": "ubuntu",
        "org.opencontainers.image.revision": "bdba5c8c0a6be5962f098fa4bbe0ecbce9fdc07a",
        "org.opencontainers.image.source": "https://github.com/silogen/aim-build",
        "org.opencontainers.image.title": "meta-llama/Llama-3.1-8B-Instruct",
        "org.opencontainers.image.vendor": "AMD",
        "org.opencontainers.image.version": ""
    }',
    'Ready',
    TIMESTAMP '2025-11-11 00:00:00+00',
    TIMESTAMP '2025-11-11 00:00:00+00',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO aims (
    id,
    resource_name,
    image_reference,
    labels,
    status,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'a1b2c3d4-5678-90ab-cdef-222222222222',
    'aim-qwen-qwen3-32b-0-8-4',
    'docker.io/amdenterpriseai/aim-qwen-qwen3-32b:0.8.4',
    '{
        "com.amd.aim.description.full": "",
        "com.amd.aim.hfToken.required": "False",
        "com.amd.aim.model.canonicalName": "Qwen/Qwen3-32B",
        "com.amd.aim.model.recommendedDeployments": "{''gpuModel'': ''MI300X'', ''gpuCount'': 1, ''precision'': ''fp16'', ''metric'': ''latency'', ''description'': ''Optimized for latency on MI300X using fp16 precision''}, {''gpuModel'': ''MI300X'', ''gpuCount'': 1, ''precision'': ''fp16'', ''metric'': ''throughput'', ''description'': ''Optimized for throughput on MI300X using fp16 precision''}",
        "com.amd.aim.model.source": "https://huggingface.co/Qwen/Qwen3-32B",
        "com.amd.aim.model.tags": "text-generation, chat",
        "com.amd.aim.model.variants": "Qwen/Qwen3-32B, Qwen/Qwen3-32B-FP8",
        "com.amd.aim.release.notes": "",
        "com.amd.aim.title": "Qwen/Qwen3-32B",
        "org.opencontainers.image.authors": "",
        "org.opencontainers.image.created": "2025-11-11T10:45:11Z",
        "org.opencontainers.image.description": "Qwen is the large language model and large multimodal model series of the Qwen Team, Alibaba Group.",
        "org.opencontainers.image.documentation": "",
        "org.opencontainers.image.licenses": "Apache-2.0, MIT",
        "org.opencontainers.image.ref.name": "ubuntu",
        "org.opencontainers.image.revision": "bdba5c8c0a6be5962f098fa4bbe0ecbce9fdc07a",
        "org.opencontainers.image.source": "https://github.com/silogen/aim-build",
        "org.opencontainers.image.title": "Qwen/Qwen3-32B",
        "org.opencontainers.image.vendor": "AMD",
        "org.opencontainers.image.version": ""
    }',
    'Ready',
    TIMESTAMP '2025-11-11 00:00:00+00',
    TIMESTAMP '2025-11-11 00:00:00+00',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

INSERT INTO aims (
    id,
    resource_name,
    image_reference,
    labels,
    status,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'a1b2c3d4-5678-90ab-cdef-333333333333',
    'aim-mistralai-mistral-small-3-2-24b-instruct-2506-0-8-4',
    'docker.io/amdenterpriseai/aim-mistralai-mistral-small-3-2-24b-instruct-2506:0.8.4',
    '{
        "com.amd.aim.description.full": "",
        "com.amd.aim.hfToken.required": "False",
        "com.amd.aim.model.canonicalName": "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "com.amd.aim.model.recommendedDeployments": "{''gpuModel'': ''MI300X'', ''gpuCount'': 1, ''precision'': ''fp16'', ''metric'': ''latency'', ''description'': ''Optimized for latency on MI300X using fp16 precision''}, {''gpuModel'': ''MI300X'', ''gpuCount'': 1, ''precision'': ''fp16'', ''metric'': ''throughput'', ''description'': ''Optimized for throughput on MI300X using fp16 precision''}",
        "com.amd.aim.model.source": "https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "com.amd.aim.model.tags": "text-generation, chat",
        "com.amd.aim.model.variants": "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "com.amd.aim.release.notes": "",
        "com.amd.aim.title": "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "org.opencontainers.image.authors": "",
        "org.opencontainers.image.created": "2025-11-11T10:45:11Z",
        "org.opencontainers.image.description": "Mistral-Small-3.2-24B-Instruct-2506 is a minor update of Mistral-Small-3.1-24B-Instruct-2503. Small-3.2 improves in the following categories: - Instruction following: Small-3.2 is better at following precise instructions - Repetition errors: Small-3.2 produces less infinite generations or repetitive answers - Function calling: Small-3.2''s function calling template is more robust",
        "org.opencontainers.image.documentation": "",
        "org.opencontainers.image.licenses": "Apache-2.0, MIT",
        "org.opencontainers.image.ref.name": "ubuntu",
        "org.opencontainers.image.revision": "bdba5c8c0a6be5962f098fa4bbe0ecbce9fdc07a",
        "org.opencontainers.image.source": "https://github.com/silogen/aim-build",
        "org.opencontainers.image.title": "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "org.opencontainers.image.vendor": "AMD",
        "org.opencontainers.image.version": ""
    }',
    'Degraded',
    TIMESTAMP '2025-11-11 00:00:00+00',
    TIMESTAMP '2025-11-11 00:00:00+00',
    'system',
    'system'
) ON CONFLICT DO NOTHING;


-- Insert managed workloads for AIM inference
INSERT INTO workloads (
    id,
    status,
    cluster_id,
    project_id,
    created_at,
    updated_at,
    created_by,
    updated_by,
    display_name,
    type,
    kind,
    name,
    aim_id,
    chart_id,
    user_inputs,
    output,
    cluster_auth_group_id
) VALUES (
    '4bc350da-5031-410d-aca1-0a34cc21d085',
    'Pending',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    '79ae32ed-bb33-4e01-a30a-808201183905',
    TIMESTAMP '2025-11-17 08:41:08.018571+00',
    TIMESTAMP '2025-11-17 08:44:28.584381+00',
    'devuser@amd.com',
    'system',
    'aim-meta-llama-llama-3-1-8b-instruct-0.8.4-4bc350da',
    'INFERENCE',
    'managed',
    'mw-42d5e9e8',
    'a1b2c3d4-5678-90ab-cdef-111111111111',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '{"canonicalName": "meta-llama/Llama-3.1-8B-Instruct"}',
    '{"externalHost": "https://workloads.example.com/research-and-development/4bc350da-5031-410d-aca1-0a34cc21d085", "internalHost": "mw-42d5e9e8-predictor.research-and-development.svc.cluster.local"}',
    '891dfa25-f52b-c7f3-3e8b-69be9ad74e44'
) ON CONFLICT DO NOTHING;

INSERT INTO workloads (
    id,
    status,
    cluster_id,
    project_id,
    created_at,
    updated_at,
    created_by,
    updated_by,
    display_name,
    type,
    kind,
    name,
    aim_id,
    chart_id,
    user_inputs,
    output,
    cluster_auth_group_id
) VALUES (
    '0a4b3a17-9bd4-47cf-8ca3-47c3b0419185',
    'Running',
    '99a3f8c2-a23d-4ac6-b2a9-502305925ff3',
    '79ae32ed-bb33-4e01-a30a-808201183905',
    TIMESTAMP '2025-11-17 09:18:43.281242+00',
    TIMESTAMP '2025-11-17 09:21:07.569857+00',
    'devuser@amd.com',
    'system',
    'aim-mistralai-mistral-small-3-2-24b-instruct-2506-0.8.4-0a4b3a17',
    'INFERENCE',
    'managed',
    'mw-6797e6e7',
    'a1b2c3d4-5678-90ab-cdef-333333333333',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '{"canonicalName": "mistralai/Mistral-Small-3.2-24B-Instruct-2506"}',
    '{"externalHost": "https://workloads.example.com/research-and-development/0a4b3a17-9bd4-47cf-8ca3-47c3b0419185", "internalHost": "mw-6797e6e7-predictor.research-and-development.svc.cluster.local"}',
    'e9dfca34-314b-dd46-693d-b7b2cd656de2'
) ON CONFLICT DO NOTHING;
