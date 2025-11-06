# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Tests for S3 error mapping functionality.
"""

from minio.error import S3Error

from app.utilities.exceptions import (
    ExternalServiceError,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.utilities.minio import map_s3_error_to_domain_exception


class TestS3ErrorMapping:
    """Tests for the map_s3_error_to_domain_exception function."""

    def test_no_such_key_maps_to_not_found(self):
        """Test that NoSuchKey S3 error maps to NotFoundException."""
        s3_error = S3Error(
            code="NoSuchKey",
            message="The specified key does not exist",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, NotFoundException)
        assert "File not found in storage" in exception.message
        assert "s3://bucket/path/file.txt" in exception.message
        assert str(s3_error) in exception.detail

    def test_no_such_bucket_maps_to_not_found(self):
        """Test that NoSuchBucket S3 error maps to NotFoundException."""
        s3_error = S3Error(
            code="NoSuchBucket",
            message="The specified bucket does not exist",
            resource="/bucket",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, NotFoundException)
        assert "File not found in storage" in exception.message

    def test_access_denied_maps_to_forbidden(self):
        """Test that AccessDenied S3 error maps to ForbiddenException."""
        s3_error = S3Error(
            code="AccessDenied",
            message="Access Denied",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, ForbiddenException)
        assert "Access denied to storage" in exception.message
        assert "s3://bucket/path/file.txt" in exception.message

    def test_invalid_request_maps_to_validation(self):
        """Test that InvalidRequest S3 error maps to ValidationException."""
        s3_error = S3Error(
            code="InvalidRequest",
            message="Invalid request",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, ValidationException)
        assert "Invalid storage request" in exception.message

    def test_malformed_xml_maps_to_validation(self):
        """Test that MalformedXML S3 error maps to ValidationException."""
        s3_error = S3Error(
            code="MalformedXML",
            message="The XML provided was not well-formed",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, ValidationException)
        assert "Invalid storage request" in exception.message

    def test_invalid_argument_maps_to_validation(self):
        """Test that InvalidArgument S3 error maps to ValidationException."""
        s3_error = S3Error(
            code="InvalidArgument",
            message="Invalid argument",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, ValidationException)
        assert "Invalid storage request" in exception.message

    def test_internal_error_maps_to_external_service(self):
        """Test that InternalError S3 error maps to ExternalServiceError."""
        s3_error = S3Error(
            code="InternalError",
            message="We encountered an internal error",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, ExternalServiceError)
        assert "Storage service error" in exception.message

    def test_unknown_error_maps_to_external_service(self):
        """Test that unknown S3 error codes map to ExternalServiceError."""
        s3_error = S3Error(
            code="UnknownError",
            message="Something went wrong",
            resource="/bucket/path/file.txt",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, "s3://bucket/path/file.txt")

        assert isinstance(exception, ExternalServiceError)
        assert "Storage service error" in exception.message

    def test_context_included_in_all_mappings(self):
        """Test that context string is included in all mapped exceptions."""
        context = "s3://my-bucket/datasets/important-file.jsonl"

        s3_error = S3Error(
            code="NoSuchKey",
            message="Not found",
            resource="/bucket/path",
            request_id="123",
            host_id="host",
            response="response",
        )

        exception = map_s3_error_to_domain_exception(s3_error, context)

        assert context in exception.message
