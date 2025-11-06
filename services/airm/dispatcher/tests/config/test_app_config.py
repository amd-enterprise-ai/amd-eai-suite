# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from app.config.app_config import AppConfig


def test_singleton_behavior():
    instance1 = AppConfig()
    instance2 = AppConfig()
    assert instance1 is instance2, "AppConfig is not a singleton."


def test_set_config():
    config = AppConfig()
    config.set_config("TestOrg", "TestCluster")
    assert config.org_name == "TestOrg", "org_name was not set correctly."
    assert config.cluster_name == "TestCluster", "cluster_name was not set correctly."


def test_get_org_name():
    config = AppConfig()
    config.set_config("TestOrg", "TestCluster")
    assert config.get_org_name() == "TestOrg", "get_org_name did not return the correct value."


def test_get_cluster_name():
    config = AppConfig()
    config.set_config("TestOrg", "TestCluster")
    assert config.get_cluster_name() == "TestCluster", "get_cluster_name did not return the correct value."
