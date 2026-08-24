package utils

import (
	"errors"
	"path/filepath"
	"slices"
	"strings"
)

var (
	ErrAbsolutePath  = errors.New("absolute paths not allowed")
	ErrPathTraversal = errors.New("path traversal not allowed")
	ErrEmptyPath     = errors.New("empty path not allowed")
)

// SanitizeRelativePath validates a relative path from the LocalSend protocol.
// It allows subdirectory paths like "Photos/Summer/beach.jpg" but rejects
// directory traversal attacks like "../../../etc/passwd".
//
// The function:
//   - Converts protocol path separators (/) to OS-specific separators
//   - Cleans the path (resolves . and ..)
//   - Rejects absolute paths
//   - Rejects paths that would escape the root directory via ".."
//
// Returns the cleaned, OS-specific path or an error if the path is unsafe.
func SanitizeRelativePath(filename string) (string, error) {
	if filename == "" {
		return "", ErrEmptyPath
	}

	// Convert protocol separators (/) to OS-specific
	osPath := filepath.FromSlash(filename)

	// Clean the path (resolves . and ..)
	cleaned := filepath.Clean(osPath)

	// Reject empty or root-only results
	if cleaned == "" || cleaned == "." {
		return "", ErrEmptyPath
	}

	// Reject absolute paths
	if filepath.IsAbs(cleaned) {
		return "", ErrAbsolutePath
	}

	// Reject paths that escape upward (start with ".." after cleaning)
	// filepath.Clean normalizes "foo/../../../bar" to "../../bar"
	if strings.HasPrefix(cleaned, ".."+string(filepath.Separator)) || cleaned == ".." {
		return "", ErrPathTraversal
	}

	// Double-check: verify no path component is ".."
	// This catches edge cases that might slip through
	parts := strings.Split(cleaned, string(filepath.Separator))
	if slices.Contains(parts, "..") {
		return "", ErrPathTraversal
	}

	return cleaned, nil
}

// ToProtocolPath converts an OS-specific path to protocol format (forward slashes).
// This should be used when preparing filenames to send over the LocalSend protocol.
func ToProtocolPath(osPath string) string {
	return filepath.ToSlash(osPath)
}

// SanitizePathWithFallback sanitizes a path and falls back to the base filename
// if the path is unsafe. Returns an error only if the result is still invalid
// (empty, ".", or "/").
//
// This consolidates the common pattern used in both HTTP and WebRTC receivers:
//   - Try to sanitize the relative path
//   - If unsafe, fall back to just the base filename
//   - Reject completely invalid results
func SanitizePathWithFallback(filename string) (string, error) {
	sanitizedPath, err := SanitizeRelativePath(filename)
	if err != nil {
		// Fall back to base filename only if path is unsafe
		sanitizedPath = filepath.Base(filename)
	}

	// Reject invalid results including ".." which could come from base of "../.."
	if sanitizedPath == "." || sanitizedPath == "/" || sanitizedPath == "" || sanitizedPath == ".." {
		return "", ErrEmptyPath
	}

	return sanitizedPath, nil
}

// IsFolderTransfer checks if any filename in the list contains a subdirectory structure.
// Used to detect folder transfers which should bypass extension routing to keep
// folder contents together.
func IsFolderTransfer(filenames []string) bool {
	for _, filename := range filenames {
		if strings.Contains(filename, "/") {
			return true
		}
	}
	return false
}
