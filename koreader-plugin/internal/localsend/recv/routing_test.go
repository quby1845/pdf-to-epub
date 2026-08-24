package recv

import (
	"os"
	"path/filepath"
	"testing"
)

func TestExtensionRouter_GetSaveDir(t *testing.T) {
	router := NewExtensionRouter("/default")
	router.routes["epub"] = "/books"
	router.routes["pdf"] = "/pdfs"

	tests := []struct {
		filename string
		want     string
	}{
		{"book.epub", "/books"},
		{"book.EPUB", "/books"}, // case insensitive
		{"document.pdf", "/pdfs"},
		{"document.PDF", "/pdfs"},
		{"image.png", "/default"},   // no route, use default
		{"noextension", "/default"}, // no extension, use default
		{"file.unknown", "/default"},
		{"file.", "/default"}, // trailing dot, no extension
	}

	for _, tt := range tests {
		t.Run(tt.filename, func(t *testing.T) {
			got := router.GetSaveDir(tt.filename)
			if got != tt.want {
				t.Errorf("GetSaveDir(%q) = %q, want %q", tt.filename, got, tt.want)
			}
		})
	}
}

func TestExtensionRouter_LoadFromFile(t *testing.T) {
	// Create temp config file
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "ext_routing.json")

	config := `{
		"epub": "/mnt/books",
		"pdf": "/mnt/pdfs",
		"default": "/mnt/downloads"
	}`

	if err := os.WriteFile(configPath, []byte(config), 0644); err != nil {
		t.Fatalf("Failed to write config: %v", err)
	}

	router := NewExtensionRouter("/original-default")
	if err := router.LoadFromFile(configPath); err != nil {
		t.Fatalf("LoadFromFile failed: %v", err)
	}

	// Check routes were loaded
	if !router.HasRoutes() {
		t.Error("Expected HasRoutes() to be true")
	}

	// Check specific routes
	if got := router.GetSaveDir("book.epub"); got != "/mnt/books" {
		t.Errorf("GetSaveDir(book.epub) = %q, want /mnt/books", got)
	}

	if got := router.GetSaveDir("doc.pdf"); got != "/mnt/pdfs" {
		t.Errorf("GetSaveDir(doc.pdf) = %q, want /mnt/pdfs", got)
	}

	// Check default was overridden
	if got := router.GetSaveDir("file.unknown"); got != "/mnt/downloads" {
		t.Errorf("GetSaveDir(file.unknown) = %q, want /mnt/downloads", got)
	}
}

func TestExtensionRouter_HasRoutes(t *testing.T) {
	router := NewExtensionRouter("/default")
	if router.HasRoutes() {
		t.Error("Expected HasRoutes() to be false for empty router")
	}

	router.routes["epub"] = "/books"
	if !router.HasRoutes() {
		t.Error("Expected HasRoutes() to be true after adding route")
	}
}

func TestExtensionRouter_CompoundExtensions(t *testing.T) {
	router := NewExtensionRouter("/default")
	router.routes["pdf"] = "/pdfs"
	router.routes["safari.pdf"] = "/safari"
	router.routes["work.report.pdf"] = "/work"

	tests := []struct {
		name     string
		filename string
		want     string
	}{
		// Compound extension matches
		{"compound safari.pdf", "document.safari.pdf", "/safari"},
		{"compound case insensitive", "document.Safari.PDF", "/safari"},
		{"triple compound", "quarterly.work.report.pdf", "/work"},

		// Falls back to simple extension when no compound match
		{"fallback to pdf", "document.unknown.pdf", "/pdfs"},
		{"simple pdf still works", "document.pdf", "/pdfs"},

		// No match at all
		{"no match uses default", "document.safari.docx", "/default"},

		// Edge cases
		{"path with compound", "/path/to/file.safari.pdf", "/safari"},
		{"dotfile with extension", ".hidden.pdf", "/pdfs"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := router.GetSaveDir(tt.filename)
			if got != tt.want {
				t.Errorf("GetSaveDir(%q) = %q, want %q", tt.filename, got, tt.want)
			}
		})
	}
}

// =============================================================================
// Security Tests - Path Traversal
// =============================================================================

// TestLoadFromFile_PathTraversal tests that LoadFromFile rejects paths
// containing path traversal sequences like "..".
//
// Currently, the code does NOT validate paths from JSON config, allowing
// an attacker to specify paths like "../../../etc/" which could write
// files outside the intended directory.
//
// This test SHOULD FAIL on the current codebase (paths are accepted).
func TestLoadFromFile_PathTraversal(t *testing.T) {
	tmpDir := t.TempDir()

	testCases := []struct {
		name        string
		config      string
		shouldError bool
		description string
	}{
		{
			name: "path traversal in extension route",
			config: `{
				"epub": "/safe/path",
				"pdf": "../../../etc/passwd"
			}`,
			shouldError: true,
			description: "relative path with .. should be rejected",
		},
		{
			name: "path traversal in default",
			config: `{
				"default": "/tmp/../../../etc"
			}`,
			shouldError: true,
			description: "path containing .. should be rejected even if starts with /",
		},
		{
			name: "relative path without leading slash",
			config: `{
				"epub": "relative/path/here"
			}`,
			shouldError: true,
			description: "relative paths should be rejected (must be absolute)",
		},
		{
			name: "valid absolute paths",
			config: `{
				"epub": "/mnt/books",
				"pdf": "/home/user/documents",
				"default": "/tmp/downloads"
			}`,
			shouldError: false,
			description: "valid absolute paths should be accepted",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			configPath := filepath.Join(tmpDir, "config.json")
			if err := os.WriteFile(configPath, []byte(tc.config), 0644); err != nil {
				t.Fatalf("Failed to write config: %v", err)
			}

			router := NewExtensionRouter("/default")
			err := router.LoadFromFile(configPath)

			if tc.shouldError && err == nil {
				t.Errorf("LoadFromFile should have returned an error: %s", tc.description)
			}
			if !tc.shouldError && err != nil {
				t.Errorf("LoadFromFile should have succeeded: %v", err)
			}
		})
	}
}

// TestLoadFromFile_PathTraversal_DirectManipulation tests the vulnerability
// by directly checking what paths get stored in the router.
func TestLoadFromFile_PathTraversal_DirectManipulation(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "malicious.json")

	// A malicious config that tries to escape to /etc
	maliciousConfig := `{
		"epub": "/tmp/../../../etc",
		"pdf": "../../sensitive/data"
	}`

	if err := os.WriteFile(configPath, []byte(maliciousConfig), 0644); err != nil {
		t.Fatalf("Failed to write config: %v", err)
	}

	router := NewExtensionRouter("/safe/default")
	err := router.LoadFromFile(configPath)

	// Current behavior: no error, paths are stored as-is
	// Expected behavior: should return error for path traversal

	if err == nil {
		// Check what paths were actually stored
		epubDir := router.GetSaveDir("test.epub")
		pdfDir := router.GetSaveDir("test.pdf")

		// If these contain ".." they are vulnerable
		if filepath.Clean(epubDir) != epubDir || filepath.Clean(pdfDir) != pdfDir {
			t.Logf("WARNING: Path traversal detected!")
			t.Logf("  epub route: %q (cleaned: %q)", epubDir, filepath.Clean(epubDir))
			t.Logf("  pdf route: %q (cleaned: %q)", pdfDir, filepath.Clean(pdfDir))
		}

		// The real vulnerability: files could be written to /etc
		t.Error("LoadFromFile accepted path traversal paths - this is a security vulnerability")
	}
}
