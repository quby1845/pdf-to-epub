// Package utils provides LocalSend-specific utility functions.
//
// This package contains helpers that are specific to the LocalSend protocol
// and application:
//
//   - Device alias generation (hostname-based)
//   - TLS certificate loading and generation
//   - SHA256 fingerprint computation for certs
//   - Web server factory (gofiber configuration)
//
// For general-purpose utilities (path sanitization, file operations,
// extension parsing), see the internal/utils package instead.
package utils
