//go:build darwin

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
		return time.Unix(stat.Atimespec.Sec, stat.Atimespec.Nsec)
	}
	// Fallback to modification time
	return fi.ModTime()
}
