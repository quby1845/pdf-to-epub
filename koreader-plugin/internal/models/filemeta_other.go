//go:build !darwin && !linux

package models

import (
	"os"
	"time"
)

// getAccessTime extracts the access time from FileInfo
// Falls back to modification time on unsupported platforms
func getAccessTime(fi os.FileInfo) time.Time {
	return fi.ModTime()
}
