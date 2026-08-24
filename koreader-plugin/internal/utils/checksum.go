// Package utils provides utility functions shared across the application.
package utils

import (
	"encoding/hex"
	"errors"
	"hash"
)

// ErrChecksumMismatch is returned when a file's checksum doesn't match the expected value.
var ErrChecksumMismatch = errors.New("checksum mismatch")

// VerifyChecksum compares the computed hash against an expected hex-encoded checksum.
// Returns nil if they match, ErrChecksumMismatch if they don't.
//
// This consolidates the checksum verification pattern used by both HTTP and WebRTC receivers.
//
// Parameters:
//   - expected: hex-encoded expected checksum (e.g., SHA256 from file metadata)
//   - hasher: hash.Hash that has been updated with the file contents
//
// Returns:
//   - nil if expected is empty (no checksum validation required)
//   - nil if the checksums match
//   - ErrChecksumMismatch if they don't match
func VerifyChecksum(expected string, hasher hash.Hash) error {
	if expected == "" {
		return nil // No checksum validation required
	}

	computed := hex.EncodeToString(hasher.Sum(nil))
	if computed != expected {
		return ErrChecksumMismatch
	}
	return nil
}

// ComputeChecksum returns the hex-encoded checksum from the hasher.
// This is a convenience function for getting the final checksum string.
func ComputeChecksum(hasher hash.Hash) string {
	return hex.EncodeToString(hasher.Sum(nil))
}
