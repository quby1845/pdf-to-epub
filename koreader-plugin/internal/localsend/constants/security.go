// Package constants contains shared constants for the LocalSend protocol.
package constants

import "time"

// Security constants - shared between HTTP and WebRTC receivers
const (
	// MaxPINAttempts is the maximum number of incorrect PIN attempts before blocking.
	MaxPINAttempts = 3

	// PINBlockDuration is how long a client is blocked after max PIN attempts.
	// Applies to both HTTP (by IP) and WebRTC (by signaling ID).
	PINBlockDuration = 30 * time.Second

	// PINCleanupInterval is how often expired PIN attempt entries are cleaned up.
	PINCleanupInterval = 5 * time.Minute

	// MaxFilesPerSession is the maximum number of files per transfer session.
	// This prevents DoS attacks via excessive file metadata entries.
	// Applies to both HTTP and WebRTC receivers.
	MaxFilesPerSession = 10000
)
