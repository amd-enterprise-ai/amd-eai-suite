# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Robot Framework library for creating KEDA-compatible autoscaling payloads.

Provides structured creation of autoscaling policy configurations matching
the format from apps/ui/aiwb/lib/app/aims.ts::createAimScalingPolicyConfig.
"""


class AutoscalingPayload:
    """Creates KEDA-compatible autoscaling policy configurations."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def create_keda_policy_config(
        self,
        metric_query: str = "vllm:num_requests_running",
        operation_over_time: str = "max",
        target_type: str = "Value",
        target_value: int = 10,
    ) -> dict:
        """Create KEDA-compatible autoscaling policy configuration.

        This structure MUST match the output of createAimScalingPolicyConfig
        from apps/ui/aiwb/lib/app/aims.ts.

        Args:
            metric_query: OpenTelemetry metric query string
            operation_over_time: Aggregation operation (avg, sum, min, max)
            target_type: KEDA target type (AverageValue, Value, Utilization)
            target_value: Target value for scaling (MUST be string in final payload)

        Returns:
            dict: KEDA policy configuration with metrics array
        """
        return {
            "metrics": [
                {
                    "type": "PodMetric",
                    "podmetric": {
                        "metric": {
                            "backend": "opentelemetry",
                            "metricNames": [
                                "vllm:num_requests_running",
                                "vllm:num_requests_waiting",
                            ],
                            "query": metric_query,
                            "operationOverTime": operation_over_time,
                        },
                        "target": {
                            "type": target_type,
                            "value": str(target_value),  # MUST be string
                        },
                    },
                }
            ]
        }

    def map_metric_to_query(self, metric: str) -> str:
        """Map user-friendly metric names to KEDA query strings.

        Args:
            metric: User-friendly metric name (running_requests, waiting_requests, total_requests)

        Returns:
            str: OpenTelemetry query string
        """
        mapping = {
            "running_requests": "vllm:num_requests_running",
            "waiting_requests": "vllm:num_requests_waiting",
            "total_requests": "vllm:num_requests_running + vllm:num_requests_waiting",
        }
        if metric not in mapping:
            raise ValueError(f"Unknown metric '{metric}'. Valid metrics: {', '.join(mapping)}")
        return mapping[metric]
