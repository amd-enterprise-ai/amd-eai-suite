# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import pytest

from app.kubernetes import load_k8s_config


def test_load_k8s_config():
    with patch("kubernetes.config.load_incluster_config") as mock_load_incluster_config:
        load_k8s_config()

        mock_load_incluster_config.assert_called_once()


def test_load_k8s_config_exception():
    with pytest.raises(Exception):
        with patch(
            "kubernetes.config.load_incluster_config", side_effect=Exception("Config error")
        ) as mock_load_incluster_config:
            load_k8s_config()

            mock_load_incluster_config.assert_called_once()
