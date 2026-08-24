//go:build linux

package models

import (
	"os"
	"syscall"
	"time"
)

// getAccessTime extracts the access time from FileInfo
// Falls back to modification time if access time cannot be retrieved
func getAccessTime(fi os.FileInfo) time.Time {
	if stat, ok := fi.Sys().(*syscall.Stat_t); ok {
		return time.Unix(int64(stat.Atim.Sec), int64(stat.Atim.Nsec))
	}
	// Fallback to modification time
	return fi.ModTime()
}
