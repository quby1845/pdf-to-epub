package recv

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ExtensionRouter routes files to different directories based on their extension.
type ExtensionRouter struct {
	routes     map[string]string // lowercase ext (without dot) -> directory
	defaultDir string
}

// NewExtensionRouter creates a new router with the given default directory.
func NewExtensionRouter(defaultDir string) *ExtensionRouter {
	return &ExtensionRouter{
		routes:     make(map[string]string),
		defaultDir: defaultDir,
	}
}

// LoadFromFile loads routing configuration from a JSON file.
// The JSON should be an object mapping extensions to directories:
//
//	{
//	  "epub": "/path/to/books",
//	  "pdf": "/path/to/pdfs",
//	  "default": "/path/to/default"
//	}
func (r *ExtensionRouter) LoadFromFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	var config map[string]string
	if err := json.Unmarshal(data, &config); err != nil {
		return err
	}

	for ext, dir := range config {
		ext = strings.ToLower(strings.TrimPrefix(ext, "."))

		// Validate path: must be absolute and not contain path traversal
		if !filepath.IsAbs(dir) {
			return fmt.Errorf("extension route for %q must be absolute path: %s", ext, dir)
		}

		// Check for traversal attempts in the raw path before cleaning
		if strings.Contains(dir, "..") {
			return fmt.Errorf("extension route for %q contains path traversal: %s", ext, dir)
		}

		// Clean the path for consistent storage
		cleaned := filepath.Clean(dir)

		if ext == "default" {
			r.defaultDir = cleaned
		} else {
			r.routes[ext] = cleaned
		}
	}

	return nil
}

// GetSaveDir returns the appropriate save directory for a file based on its extension.
// Supports compound extensions like "safari.pdf" for category-based routing.
// For "file.safari.pdf", it tries "safari.pdf" first, then falls back to "pdf".
// Falls back to the default directory if no specific route is configured.
func (r *ExtensionRouter) GetSaveDir(filename string) string {
	// Get base name without path
	base := filepath.Base(filename)

	// Find first dot (for compound extension like "safari.pdf")
	idx := strings.Index(base, ".")
	if idx == -1 || idx >= len(base)-1 {
		return r.defaultDir
	}

	compound := strings.ToLower(base[idx+1:]) // "safari.pdf" from "file.safari.pdf"

	// Try compound extension first
	if dir, ok := r.routes[compound]; ok {
		return dir
	}

	// Fall back to simple extension (last segment)
	if lastDot := strings.LastIndex(compound, "."); lastDot != -1 && lastDot < len(compound)-1 {
		simple := compound[lastDot+1:] // "pdf" from "safari.pdf"
		if dir, ok := r.routes[simple]; ok {
			return dir
		}
	} else {
		// No compound, just a simple extension
		if dir, ok := r.routes[compound]; ok {
			return dir
		}
	}

	return r.defaultDir
}

// HasRoutes returns true if any extension-specific routes are configured.
func (r *ExtensionRouter) HasRoutes() bool {
	return len(r.routes) > 0
}

// EnsureDirectories creates all configured directories if they don't exist.
func (r *ExtensionRouter) EnsureDirectories() error {
	dirs := make(map[string]bool)
	dirs[r.defaultDir] = true
	for _, dir := range r.routes {
		dirs[dir] = true
	}

	for dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}

	return nil
}
