# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import pytest

from airm.messaging.schemas import ClusterQuotasStatusMessage
from app.quotas.service import __process_kaiwo_queue_config_event


@pytest.mark.asyncio
async def test_processes_kaiwo_queue_config_event_deleted():
    resource = {"status": {"status": "DELETED"}}
    event_type = "DELETED"
    with patch("app.quotas.service.__publish_quotas_allocations_status_message") as mock_publish:
        await __process_kaiwo_queue_config_event(resource, event_type)
        mock_publish.assert_called_once()
        message = mock_publish.call_args[0][0]
        assert isinstance(message, ClusterQuotasStatusMessage)
        assert message.quota_allocations == []


@pytest.mark.asyncio
async def test_processes_kaiwo_queue_config_event_ready():
    resource = {
        "apiVersion": "kaiwo.silogen.ai/v1alpha1",
        "kind": "KaiwoQueueConfig",
        "metadata": {
            "annotations": {
                "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"kaiwo.silogen.ai/v1alpha1","kind":"KaiwoQueueConfig","metadata":{"annotations":{},"name":"kaiwo-queue-config"},"spec":{"clusterQueues":[{"name":"kaiwo","spec":{"cohort":"kaiwo-cohort","flavorFungibility":{"whenCanBorrow":"Borrow","whenCanPreempt":"TryNextFlavor"},"namespaceSelector":{},"preemption":{"borrowWithinCohort":{"policy":"Never"},"reclaimWithinCohort":"Any","withinClusterQueue":"Never"},"queueingStrategy":"BestEffortFIFO","resourceGroups":[{"coveredResources":["memory","amd.com/gpu","cpu"],"flavors":[{"name":"default","resources":[{"name":"cpu","nominalQuota":"120"},{"name":"memory","nominalQuota":"1885506646000"},{"name":"amd.com/gpu","nominalQuota":"8"}]}]}],"stopPolicy":"None"}},{"name":"kaiwo-new","spec":{"cohort":"kaiwo-cohort","flavorFungibility":{"whenCanBorrow":"Borrow","whenCanPreempt":"TryNextFlavor"},"namespaceSelector":{},"preemption":{"borrowWithinCohort":{"policy":"Never"},"reclaimWithinCohort":"Any","withinClusterQueue":"Never"},"queueingStrategy":"BestEffortFIFO","resourceGroups":[{"coveredResources":["cpu","memory","amd.com/gpu"],"flavors":[{"name":"default","resources":[{"name":"cpu","nominalQuota":"0"},{"name":"memory","nominalQuota":"0"},{"name":"amd.com/gpu","nominalQuota":"0"}]}]}],"stopPolicy":"None"}}],"resourceFlavors":[{"name":"default"}]}}\n'
            },
            "creationTimestamp": "2025-03-19T22:43:26Z",
            "generation": 1,
            "managedFields": [
                {
                    "apiVersion": "kaiwo.silogen.ai/v1alpha1",
                    "fieldsType": "FieldsV1",
                    "fieldsV1": {
                        "f:metadata": {
                            "f:annotations": {
                                ".": {},
                                "f:kubectl.kubernetes.io/last-applied-configuration": {},
                            }
                        },
                        "f:spec": {".": {}, "f:clusterQueues": {}, "f:resourceFlavors": {}},
                    },
                    "manager": "kubectl-client-side-apply",
                    "operation": "Update",
                    "time": "2025-03-19T22:43:26Z",
                },
                {
                    "apiVersion": "kaiwo.silogen.ai/v1alpha1",
                    "fieldsType": "FieldsV1",
                    "fieldsV1": {"f:status": {".": {}, "f:Status": {}}},
                    "manager": "manager",
                    "operation": "Update",
                    "subresource": "status",
                    "time": "2025-03-19T22:43:26Z",
                },
            ],
            "name": "kaiwo",
            "resourceVersion": "125573307",
            "uid": "e0b398cd-ee2a-43f9-acaf-bf737ec7ec0c",
        },
        "spec": {
            "clusterQueues": [
                {
                    "name": "queue-1",
                    "namespaces": ["kaiwo"],
                    "spec": {
                        "cohort": "kaiwo-cohort",
                        "flavorFungibility": {
                            "whenCanBorrow": "Borrow",
                            "whenCanPreempt": "TryNextFlavor",
                        },
                        "namespaceSelector": {},
                        "preemption": {
                            "borrowWithinCohort": {"policy": "Never"},
                            "reclaimWithinCohort": "Any",
                            "withinClusterQueue": "Never",
                        },
                        "queueingStrategy": "BestEffortFIFO",
                        "resourceGroups": [
                            {
                                "coveredResources": ["memory", "amd.com/gpu", "cpu"],
                                "flavors": [
                                    {
                                        "name": "default",
                                        "resources": [
                                            {"name": "cpu", "nominalQuota": "120m"},
                                            {
                                                "name": "memory",
                                                "nominalQuota": "1885506646000",
                                            },
                                            {"name": "amd.com/gpu", "nominalQuota": "8"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "stopPolicy": "None",
                    },
                },
                {
                    "name": "queue-2",
                    "namespaces": ["kaiwo"],
                    "spec": {
                        "cohort": "kaiwo-cohort",
                        "flavorFungibility": {
                            "whenCanBorrow": "Borrow",
                            "whenCanPreempt": "TryNextFlavor",
                        },
                        "namespaceSelector": {},
                        "preemption": {
                            "borrowWithinCohort": {"policy": "Never"},
                            "reclaimWithinCohort": "Any",
                            "withinClusterQueue": "Never",
                        },
                        "queueingStrategy": "BestEffortFIFO",
                        "resourceGroups": [
                            {
                                "coveredResources": ["cpu", "memory", "amd.com/gpu"],
                                "flavors": [
                                    {
                                        "name": "default",
                                        "resources": [
                                            {"name": "cpu", "nominalQuota": "0"},
                                            {"name": "memory", "nominalQuota": "0"},
                                            {"name": "amd.com/gpu", "nominalQuota": "0"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "stopPolicy": "None",
                    },
                },
            ],
            "resourceFlavors": [{"name": "default"}],
            "workloadPriorityClasses": [
                {"metadata": {"name": "high-priority"}, "value": 1000, "description": "High priority class"},
                {"metadata": {"name": "low-priority"}, "value": 100, "description": "Low priority class"},
            ],
        },
        "status": {"status": "READY"},
    }
    event_type = "MODIFIED"
    quotas = [{"quota": "test_quota"}]
    with (
        patch("app.quotas.service.convert_to_cluster_quotas_allocations", return_value=quotas),
        patch("app.quotas.service.__publish_quotas_allocations_status_message") as mock_publish,
    ):
        await __process_kaiwo_queue_config_event(resource, event_type)
        mock_publish.assert_called_once()
        message = mock_publish.call_args[0][0]
        assert isinstance(message, ClusterQuotasStatusMessage)
        assert message.quota_allocations == quotas


@pytest.mark.asyncio
async def test_processes_kaiwo_queue_config_event_other_status():
    resource = {"status": {"status": "PENDING"}}
    event_type = "MODIFIED"
    with patch("app.quotas.service.__publish_quotas_allocations_status_message") as mock_publish:
        await __process_kaiwo_queue_config_event(resource, event_type)
        mock_publish.assert_not_called()
