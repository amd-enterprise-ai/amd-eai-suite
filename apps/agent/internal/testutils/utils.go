// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package testutils

// Ptr returns a pointer to v (e.g. for optional fields in table-driven tests).
func Ptr[T any](v T) *T {
	return &v
}
