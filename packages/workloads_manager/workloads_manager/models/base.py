# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Base models and enums for workloads manager."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ProcessingStatus(StrEnum):
    """Status enum for file processing operations."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FileProcessingResult(BaseModel):
    """Result of processing a single file."""

    path: str = Field(..., description="Relative path of the file")
    status: ProcessingStatus = Field(..., description="Processing status")
    id: str = Field("", description="ID returned from API (if applicable)")
    error_message: str | None = Field(None, description="Error message if processing failed")


class ProcessingStats(BaseModel):
    """Statistics for file processing operations."""

    total: int = Field(0, description="Total number of files processed")
    success: int = Field(0, description="Number of successfully processed files")
    failed: int = Field(0, description="Number of failed files")
    skipped: int = Field(0, description="Number of skipped files")

    def increment(self, status: ProcessingStatus) -> None:
        """Increment the counter for the given status."""
        self.total += 1
        if status == ProcessingStatus.SUCCESS:
            self.success += 1
        elif status == ProcessingStatus.FAILED:
            self.failed += 1
        elif status == ProcessingStatus.SKIPPED:
            self.skipped += 1
