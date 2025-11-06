# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import yaml

from airm.messaging.schemas import (
    AIMServiceStatus,
    CommonComponentStatus,
    DeploymentStatus,
    JobStatus,
    KaiwoJobStatus,
    KaiwoServiceStatus,
    WorkloadComponentKind,
    WorkloadStatus,
)
from app.projects.models import Project
from app.utilities.exceptions import ValidationException
from app.workloads.models import WorkloadComponent
from app.workloads.utils import (
    extract_workload_components_from_manifest,
    inject_workload_metadata_to_manifest,
    resolve_workload_status,
    validate_and_parse_workload_manifest,
)

project = Project(
    id="d330e767-f120-430e-854f-f28277f04de5", name="new-project", cluster_id="1234e767-f120-430e-854f-f28277f04de5"
)


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest():
    # Create a mock for the file object
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: Deployment
    metadata:
        name: test-deploy
    spec:
        containers:
        - name: test-container
        image: test-image
    """
    mock_file.read.return_value = yaml_content.encode()

    # Call the function
    result = await validate_and_parse_workload_manifest(mock_file)

    # Assert the mock was called
    mock_file.read.assert_called_once()

    # Assert the result is as expected
    assert result[0]["apiVersion"] == "v1"
    assert result[0]["kind"] == "Deployment"

    assert result[0]["metadata"]["name"] == "test-deploy"
    assert result[0]["spec"]["containers"][0]["name"] == "test-container"


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_missing_name_property_in_metadata():
    # Create a mock for the file object
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: Deployment
    spec:
        containers:
        - name: test-container
        image: test-image
    """

    mock_file.read.return_value = yaml_content.encode()

    # Call the function
    with pytest.raises(ValidationException, match="Deployment metadata must contain 'name' attribute"):
        await validate_and_parse_workload_manifest(mock_file)

    # Assert the mock was called
    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_namespace_property_in_metadata():
    # Create a mock for the file object
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: Deployment
    metadata:
        name: test-deploy
        namespace: some-namespace
    spec:
        containers:
        - name: test-container
        image: test-image
    """

    mock_file.read.return_value = yaml_content.encode()

    # Call the function
    with pytest.raises(ValidationException, match="Workload components must not contain the 'namespace' attribute"):
        await validate_and_parse_workload_manifest(mock_file)

    # Assert the mock was called
    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_multiple_definitions():
    # Create a mock for the file object
    mock_file = AsyncMock()
    yaml_content = """
apiVersion: v1
kind: Deployment
metadata:
    name: test-deploy-1
spec:
    containers:
    - name: test-container
    image: test-image
---
apiVersion: v1
kind: Deployment
metadata:
    name: test-deploy-2
    namespace: test-namespace
spec:
    containers:
    - name: test-container
    image: test-image
    """

    mock_file.read.return_value = yaml_content.encode()

    # Call the function
    with pytest.raises(
        ValidationException, match="Workload components must not contain the 'namespace' attribute, it will be injected"
    ):
        await validate_and_parse_workload_manifest(mock_file)

    # Assert the mock was called
    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_multiple_definitions_valid_mixed_service_deployment():
    # Create a mock for the file object
    mock_file = AsyncMock()
    yaml_content = """
apiVersion: v1
kind: Deployment
metadata:
    name: test-deploy-1
spec:
    containers:
    - name: test-container
    image: test-image
---
apiVersion: v1
kind: Service
metadata:
    name: test-deploy-2
spec:
    containers:
    - name: test-container
    image: test-image
    """

    mock_file.read.return_value = yaml_content.encode()

    # Call the function
    result = await validate_and_parse_workload_manifest(mock_file)

    mock_file.read.assert_called_once()

    # Assert the result is as expected
    assert result[0]["apiVersion"] == "v1"
    assert result[0]["kind"] == "Deployment"

    assert result[0]["metadata"]["name"] == "test-deploy-1"
    assert result[0]["spec"]["containers"][0]["name"] == "test-container"


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_invalid_yaml():
    # Create a mock for the file object
    mock_file = AsyncMock()
    invalid_yaml = "invalid: - yaml: content"
    mock_file.read.return_value = invalid_yaml.encode()

    # Call the function and expect a YAML parsing error
    with pytest.raises(yaml.YAMLError):
        await validate_and_parse_workload_manifest(mock_file)

    # Assert the mock was called
    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_service_account_in_job():
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: Job
    metadata:
        name: test-job
    spec:
        template:
            spec:
                serviceAccountName: some-service-account
                containers:
                - name: test-container
                  image: test-image
    """
    mock_file.read.return_value = yaml_content.encode()

    with pytest.raises(ValidationException, match="Service account is not allowed for the supplied workload"):
        await validate_and_parse_workload_manifest(mock_file)

    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_without_serviceAccount_in_job():
    # Mock file with Job manifest that doesn't specify serviceAccountName
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: Job
    metadata:
        name: test-job
    spec:
        template:
            spec:
                containers:
                - name: test-container
                  image: test-image
    """
    mock_file.read.return_value = yaml_content.encode()

    await validate_and_parse_workload_manifest(mock_file)
    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_serviceAccount_in_deployment():
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: Deployment
    metadata:
        name: test-deployment
    spec:
        template:
            spec:
                serviceAccountName: some-service-account
                containers:
                - name: test-container
                  image: test-image
    """
    mock_file.read.return_value = yaml_content.encode()

    with pytest.raises(ValidationException, match="Service account is not allowed for the supplied workload"):
        await validate_and_parse_workload_manifest(mock_file)

    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_serviceAccount_in_kaiwojob():
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: KaiwoJob
    metadata:
        name: test-kaiwojob
    spec:
        serviceAccountName: some-service-account
        containers:
        - name: test-container
          image: test-image
    """
    mock_file.read.return_value = yaml_content.encode()

    with pytest.raises(ValidationException, match="Service account is not allowed for the supplied workload"):
        await validate_and_parse_workload_manifest(mock_file)

    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_validate_and_parse_workload_manifest_with_serviceAccount_in_kaiwoservice():
    mock_file = AsyncMock()
    yaml_content = """
    apiVersion: v1
    kind: KaiwoService
    metadata:
        name: test-kaiwoservice
    spec:
        serviceAccountName: some-service-account
        containers:
        - name: test-container
          image: test-image
    """
    mock_file.read.return_value = yaml_content.encode()

    with pytest.raises(ValidationException, match="Service account is not allowed for the supplied workload"):
        await validate_and_parse_workload_manifest(mock_file)

    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_deployment_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: Deployment
    metadata:
        name: test-deploy
    spec:
        template:
            spec:
                containers:
                - name: test-container
                  image: test-image
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974c"),
                name="test-deploy",
                kind="Deployment",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: Deployment
    metadata:
      labels:
        airm.silogen.ai/workload-id: '{workload_id}'
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974c
        airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
        kueue.x-k8s.io/queue-name: new-project
      name: test-deploy
      namespace: new-project
    spec:
      template:
        metadata:
          labels:
            airm.silogen.ai/workload-id: '{workload_id}'
            airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
            airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974c
        spec:
          containers:
          - image: test-image
            name: test-container
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_job_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: Job
    metadata:
        name: test-deploy
    spec:
        containers:
        - name: test-container
        image: test-image
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974c"),
                name="test-deploy",
                kind="Job",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: Job
    metadata:
      labels:
        airm.silogen.ai/workload-id: '{workload_id}'
        airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
        kueue.x-k8s.io/queue-name: new-project
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974c
      name: test-deploy
      namespace: new-project
    spec:
      template:
        metadata:
          labels:
            airm.silogen.ai/workload-id: '{workload_id}'
            airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
            airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974c
      containers:
      - name: test-container
      image: test-image
        """
    )
    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_no_deployment():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: Service
    metadata:
        name: test-service
        namespace: some-namespace
    spec:
        ports:
        - port: 80
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="test-service",
                kind="Service",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)
    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: Service
    metadata:
        labels:
            airm.silogen.ai/component-id: '2aa18e92-002c-45b7-a06e-dcdb0277974d'
            airm.silogen.ai/workload-id: '{workload_id}'
            airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
        name: test-service
        namespace: new-project
    spec:
        ports:
            - port: 80
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_kaiwojob_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: KaiwoJob
    metadata:
        name: test-deploy
    spec:
        containers:
        - name: test-container
        image: test-image
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="test-deploy",
                kind="KaiwoJob",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: KaiwoJob
    metadata:
      labels:
        airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
        airm.silogen.ai/workload-id: '{workload_id}'
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
      name: test-deploy
      namespace: new-project
    spec:
      clusterQueue: new-project
      containers:
      - name: test-container
      image: test-image
        """
    )
    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_kaiwoservice_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: KaiwoService
    metadata:
        name: test-deploy
    spec:
        containers:
        - name: test-container
        image: test-image
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="test-deploy",
                kind="KaiwoService",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)
    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: KaiwoService
    metadata:
        labels:
            airm.silogen.ai/component-id: '2aa18e92-002c-45b7-a06e-dcdb0277974d'
            airm.silogen.ai/workload-id: '{workload_id}'
            airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
        name: test-deploy
        namespace: new-project
    spec:
        clusterQueue: new-project
        containers:
        - name: test-container
        image: test-image
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_stateful_set_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: example-statefulset
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: example
      template:
        metadata:
          labels:
            app: example
        spec:
          containers:
          - name: example-container
            image: nginx:1.25
            ports:
            - containerPort: 80
              name: http
      volumeClaimTemplates:
      - metadata:
          name: data
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 1Gi
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="statefulset",
                kind="StatefulSet",
                api_version="apps/v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      labels:
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
        airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
        airm.silogen.ai/workload-id: {workload_id}
        kueue.x-k8s.io/queue-name: new-project
      name: example-statefulset
      namespace: new-project
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: example
      template:
        metadata:
          labels:
            airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
            airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
            airm.silogen.ai/workload-id: {workload_id}
            app: example
        spec:
          containers:
          - image: nginx:1.25
            name: example-container
            ports:
            - containerPort: 80
              name: http
      volumeClaimTemplates:
      - metadata:
          name: data
        spec:
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 1Gi
"""
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_daemon_set_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: apps/v1
    kind: DaemonSet
    metadata:
      name: example-daemonset
      namespace: default
    spec:
      selector:
        matchLabels:
          app: example-ds
      template:
        metadata:
          labels:
            app: example-ds
        spec:
          containers:
          - name: nginx
            image: nginx:1.25
            ports:
            - containerPort: 80

    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="example-daemonset",
                kind="Daemonset",
                api_version="apps/v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: apps/v1
    kind: DaemonSet
    metadata:
      labels:
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
        airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
        airm.silogen.ai/workload-id: {workload_id}
      name: example-daemonset
      namespace: new-project
    spec:
      selector:
        matchLabels:
          app: example-ds
      template:
        metadata:
          labels:
            airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
            airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
            airm.silogen.ai/workload-id: {workload_id}
            app: example-ds
            kueue.x-k8s.io/queue-name: new-project
        spec:
          containers:
          - image: nginx:1.25
            name: nginx
            ports:
            - containerPort: 80
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_cron_job_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: example-cronjob
      namespace: default
    spec:
      schedule: "*/5 * * * *"   # runs every 5 minutes
      jobTemplate:
        spec:
          template:
            spec:
              containers:
              - name: hello
                image: busybox
                args:
                - /bin/sh
                - -c
                - echo "Hello from CronJob at $(date)"
              restartPolicy: OnFailure

    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="example-cronjob",
                kind="CronJob",
                api_version="batch/v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      labels:
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
        airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
        airm.silogen.ai/workload-id: {workload_id}
      name: example-cronjob
      namespace: new-project
    spec:
      jobTemplate:
        metadata:
          labels:
            airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
            airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
            airm.silogen.ai/workload-id: {workload_id}
            kueue.x-k8s.io/queue-name: new-project
        spec:
          template:
            metadata:
              labels:
                airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
                airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
                airm.silogen.ai/workload-id: {workload_id}
            spec:
              containers:
              - args:
                - /bin/sh
                - -c
                - echo "Hello from CronJob at $(date)"
                image: busybox
                name: hello
              restartPolicy: OnFailure
      schedule: '*/5 * * * *'
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_pod_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: Pod
    metadata:
      name: example-pod
      namespace: default
      labels:
        app: example-pod
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="example-pod",
                kind="Pod",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: Pod
    metadata:
      labels:
        airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974d
        airm.silogen.ai/project-id: d330e767-f120-430e-854f-f28277f04de5
        airm.silogen.ai/workload-id: {workload_id}
        app: example-pod
        kueue.x-k8s.io/queue-name: new-project
      name: example-pod
      namespace: new-project
    spec:
      containers:
      - image: nginx:1.25
        name: nginx
        ports:
        - containerPort: 80
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_inject_workload_metadata_to_manifest_with_configmap_type():
    # Create a mock for the file object
    yaml_content = """
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: my-configmap
    data:
      key1: value1
      key2: value2
    """
    workload_id = uuid4()
    components_with_manifest = [
        (
            WorkloadComponent(
                id=UUID("2aa18e92-002c-45b7-a06e-dcdb0277974d"),
                name="my-configmap",
                kind="ConfigMap",
                api_version="v1",
                workload_id=workload_id,
            ),
            yaml.safe_load(yaml_content.encode()),
        )
    ]

    # Call the function
    result = inject_workload_metadata_to_manifest(workload_id, project, components_with_manifest)

    actual = yaml.safe_load(result)
    expected = yaml.safe_load(
        f"""
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: my-configmap
      namespace: new-project
      labels:
          airm.silogen.ai/component-id: '2aa18e92-002c-45b7-a06e-dcdb0277974d'
          airm.silogen.ai/workload-id: {workload_id}
          airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
    data:
      key1: value1
      key2: value2
    """
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_extract_workload_components_from_manifest():
    # Arrange
    yaml_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dispatcher
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dispatcher
  template:
    metadata:
      labels:
        app: dispatcher
    spec:
      containers:
        - name: dispatcher
          image: dispatcher:latest
          imagePullPolicy: Never
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: dispatcher
spec:
  type: LoadBalancer
  selector:
    app: dispatcher
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 8080
    """
    manifest = list(yaml.safe_load_all(yaml_content.encode()))
    workload_id = uuid4()

    components = extract_workload_components_from_manifest(manifest, workload_id)

    assert len(components) == 2

    assert components[0][0].name == "dispatcher"
    assert components[0][0].kind == WorkloadComponentKind.DEPLOYMENT.value
    assert components[0][0].api_version == "apps/v1"
    assert components[0][0].workload_id == workload_id

    assert components[1][0].name == "dispatcher"
    assert components[1][0].kind == WorkloadComponentKind.SERVICE.value
    assert components[1][0].api_version == "v1"
    assert components[1][0].workload_id == workload_id


@pytest.mark.parametrize(
    "prev_status,statuses,expected_status",
    [
        # Test case: Any component is in a Failed state
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.DEPLOYMENT, CommonComponentStatus.CREATE_FAILED),
                (WorkloadComponentKind.JOB, JobStatus.FAILED),
            ],
            WorkloadStatus.FAILED,
        ),
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.DEPLOYMENT, CommonComponentStatus.CREATE_FAILED)],
            WorkloadStatus.FAILED,
        ),
        # Test case: Any component is in a Pending state
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.PENDING),
                (WorkloadComponentKind.JOB, JobStatus.SUSPENDED),
            ],
            WorkloadStatus.PENDING,
        ),
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.PENDING)],
            WorkloadStatus.PENDING,
        ),
        # Test case: All components are in a Running state
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.RUNNING),
                (WorkloadComponentKind.JOB, JobStatus.RUNNING),
            ],
            WorkloadStatus.RUNNING,
        ),
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.RUNNING)],
            WorkloadStatus.RUNNING,
        ),
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.RUNNING),
                (WorkloadComponentKind.JOB, JobStatus.RUNNING),
            ],
            WorkloadStatus.RUNNING,
        ),
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.JOB, JobStatus.COMPLETE),
                (WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.RUNNING),
            ],
            WorkloadStatus.RUNNING,
        ),
        # Test case: All components are in a Terminated state
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.DEPLOYMENT, CommonComponentStatus.DELETED),
                (WorkloadComponentKind.JOB, CommonComponentStatus.DELETED),
                (WorkloadComponentKind.KAIWO_JOB, KaiwoJobStatus.COMPLETE),
            ],
            WorkloadStatus.TERMINATED,
        ),
        # Test case: All components are in a Deleted state
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.DEPLOYMENT, CommonComponentStatus.DELETED),
                (WorkloadComponentKind.JOB, CommonComponentStatus.DELETED),
            ],
            WorkloadStatus.DELETED,
        ),
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.DEPLOYMENT, CommonComponentStatus.DELETED)],
            WorkloadStatus.DELETED,
        ),
        # Test case: All Kaiwo components are TERMINATED - should map to TERMINATED
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.KAIWO_JOB, KaiwoJobStatus.TERMINATED),
                (WorkloadComponentKind.KAIWO_SERVICE, KaiwoServiceStatus.TERMINATED),
            ],
            WorkloadStatus.TERMINATED,
        ),
        # Test case: Single Kaiwo component is TERMINATED
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.KAIWO_JOB, KaiwoJobStatus.TERMINATED)],
            WorkloadStatus.TERMINATED,
        ),
        # Test case: Any component is DOWNLOADING - should map to DOWNLOADING
        (
            WorkloadStatus.PENDING,
            [
                (WorkloadComponentKind.KAIWO_JOB, KaiwoJobStatus.DOWNLOADING),
                (WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.PENDING),
            ],
            WorkloadStatus.DOWNLOADING,
        ),
        # Test case: Single component is DOWNLOADING
        (
            WorkloadStatus.RUNNING,
            [(WorkloadComponentKind.KAIWO_SERVICE, KaiwoServiceStatus.DOWNLOADING)],
            WorkloadStatus.DOWNLOADING,
        ),
        # Test case: Component is TERMINATING - should map to PENDING
        (
            WorkloadStatus.RUNNING,
            [(WorkloadComponentKind.KAIWO_JOB, KaiwoJobStatus.TERMINATING)],
            WorkloadStatus.PENDING,
        ),
        # Test case: AIMService statuses - PENDING
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.AIM_SERVICE, AIMServiceStatus.PENDING)],
            WorkloadStatus.PENDING,
        ),
        # Test case: AIMService statuses - STARTING
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.AIM_SERVICE, AIMServiceStatus.STARTING)],
            WorkloadStatus.PENDING,
        ),
        # Test case: AIMService statuses - RUNNING
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.AIM_SERVICE, AIMServiceStatus.RUNNING)],
            WorkloadStatus.RUNNING,
        ),
        # Test case: AIMService statuses - DEGRADED (should be PENDING)
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.AIM_SERVICE, AIMServiceStatus.DEGRADED)],
            WorkloadStatus.PENDING,
        ),
        # Test case: AIMService statuses - FAILED
        (
            WorkloadStatus.PENDING,
            [(WorkloadComponentKind.AIM_SERVICE, AIMServiceStatus.FAILED)],
            WorkloadStatus.FAILED,
        ),
        # Test case: All components COMPLETE
        (
            WorkloadStatus.RUNNING,
            [
                (WorkloadComponentKind.JOB, JobStatus.COMPLETE),
                (WorkloadComponentKind.KAIWO_JOB, KaiwoJobStatus.COMPLETE),
            ],
            WorkloadStatus.COMPLETE,
        ),
        # Test case: DELETE_FAILED takes precedence
        (
            WorkloadStatus.RUNNING,
            [
                (WorkloadComponentKind.DEPLOYMENT, CommonComponentStatus.DELETE_FAILED),
                (WorkloadComponentKind.JOB, JobStatus.RUNNING),
            ],
            WorkloadStatus.DELETE_FAILED,
        ),
        # Test case: DELETING status is preserved
        (
            WorkloadStatus.DELETING,
            [
                (WorkloadComponentKind.DEPLOYMENT, DeploymentStatus.RUNNING),
                (WorkloadComponentKind.JOB, JobStatus.RUNNING),
            ],
            WorkloadStatus.DELETING,
        ),
        # Test case: No matching rule (Unknown state)
        (WorkloadStatus.PENDING, [(WorkloadComponentKind.DEPLOYMENT, "Unknown Status")], WorkloadStatus.UNKNOWN),
    ],
)
def test_resolve_workload_status(prev_status, statuses: list[tuple[WorkloadComponentKind, str]], expected_status):
    """Test resolve_workload_status with various component statuses."""
    components = [WorkloadComponent(status=status, kind=kind) for kind, status in statuses]
    assert resolve_workload_status(prev_status, components) == expected_status
