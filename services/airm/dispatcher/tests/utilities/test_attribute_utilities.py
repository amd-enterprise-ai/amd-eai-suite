# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

import pytest

from app.utilities.attribute_utils import extract_label_id, get_attr_or_key


class Dummy:
    def __init__(self):
        self.foo = "bar"
        self.value = 42


def test_get_from_dict_existing_key():
    d = {"foo": "bar", "value": 42}
    assert get_attr_or_key(d, "foo") == "bar"
    assert get_attr_or_key(d, "value") == 42


def test_get_from_dict_missing_key_with_default():
    d = {"foo": "bar"}
    assert get_attr_or_key(d, "missing", default="default") == "default"


def test_get_from_dict_missing_key_without_default():
    d = {"foo": "bar"}
    assert get_attr_or_key(d, "missing") is None


def test_get_from_object_existing_attr():
    obj = Dummy()
    assert get_attr_or_key(obj, "foo") == "bar"
    assert get_attr_or_key(obj, "value") == 42


def test_get_from_object_missing_attr_with_default():
    obj = Dummy()
    assert get_attr_or_key(obj, "missing", default="default") == "default"


def test_get_from_object_missing_attr_without_default():
    obj = Dummy()
    assert get_attr_or_key(obj, "missing") is None


def test_get_from_object_and_dict_priority():
    class Both(Dummy, dict):
        def __init__(self):
            Dummy.__init__(self)
            dict.__init__(self, foo="dict_bar")

    both = Both()
    # Should prefer dict value
    assert get_attr_or_key(both, "foo") == "dict_bar"


@pytest.mark.parametrize(
    "item, label_key, expected",
    [
        # Successful case: Valid UUID in labels
        (
            {"metadata": {"labels": {"test-label": "12345678-1234-5678-1234-567812345678"}}},
            "test-label",
            UUID("12345678-1234-5678-1234-567812345678"),
        ),
        # Missing metadata
        ({"other": "data"}, "test-label", None),
        # Missing labels in metadata
        ({"metadata": {"other": "data"}}, "test-label", None),
        # Missing label_key in labels
        ({"metadata": {"labels": {"other-label": "value"}}}, "test-label", None),
        # Invalid UUID string
        ({"metadata": {"labels": {"test-label": "invalid-uuid"}}}, "test-label", None),
        # None label_value
        ({"metadata": {"labels": {"test-label": None}}}, "test-label", None),
        # Empty string label_value
        ({"metadata": {"labels": {"test-label": ""}}}, "test-label", None),
    ],
)
def test_extract_label_id(item, label_key, expected):
    result = extract_label_id(item, label_key)
    assert result == expected
