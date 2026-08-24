package utils

import (
	"path/filepath"
	"runtime"
	"testing"
)

func TestSanitizeRelativePath(t *testing.T) {
	testCases := []struct {
		name       string
		input      string
		want       string
		wantErr    error
		skipOnWin  bool // Skip on Windows (path separator differences)
		skipOnUnix bool // Skip on Unix (path separator differences)
	}{
		// Valid subdirectory paths
		{
			name:  "simple subdirectory",
			input: "Photos/beach.jpg",
			want:  filepath.Join("Photos", "beach.jpg"),
		},
		{
			name:  "deep subdirectory",
			input: "Photos/Summer/2024/beach.jpg",
			want:  filepath.Join("Photos", "Summer", "2024", "beach.jpg"),
		},
		{
			name:  "flat file",
			input: "document.pdf",
			want:  "document.pdf",
		},
		{
			name:  "file with spaces",
			input: "My Photos/vacation pic.jpg",
			want:  filepath.Join("My Photos", "vacation pic.jpg"),
		},

		// Paths with . that are valid after cleaning
		{
			name:  "current dir prefix",
			input: "./file.txt",
			want:  "file.txt",
		},
		{
			name:  "current dir in middle",
			input: "foo/./bar/file.txt",
			want:  filepath.Join("foo", "bar", "file.txt"),
		},

		// Paths with .. that resolve safely (stay within root)
		{
			name:  "safe parent traversal",
			input: "foo/bar/../baz.txt",
			want:  filepath.Join("foo", "baz.txt"),
		},
		{
			name:  "safe nested parent traversal",
			input: "a/b/c/../../d.txt",
			want:  filepath.Join("a", "d.txt"),
		},

		// Edge cases - filenames that look dangerous but aren't
		{
			name:  "filename starting with dots",
			input: "..hidden/file.txt",
			want:  filepath.Join("..hidden", "file.txt"),
		},
		{
			name:  "filename with double dots in name",
			input: "foo..bar.txt",
			want:  "foo..bar.txt",
		},

		// === ATTACKS - should be rejected ===

		// Simple parent traversal
		{
			name:    "simple parent traversal",
			input:   "../evil.txt",
			wantErr: ErrPathTraversal,
		},
		{
			name:    "deep parent traversal",
			input:   "../../../etc/passwd",
			wantErr: ErrPathTraversal,
		},
		{
			name:    "just double dot",
			input:   "..",
			wantErr: ErrPathTraversal,
		},

		// Mixed traversal that escapes after cleaning
		{
			name:    "escape via excess parent refs",
			input:   "foo/../../../bar.txt",
			wantErr: ErrPathTraversal,
		},
		{
			name:    "hidden escape",
			input:   "a/b/c/../../../../etc/passwd",
			wantErr: ErrPathTraversal,
		},

		// Absolute paths
		{
			name:      "absolute unix path",
			input:     "/etc/passwd",
			wantErr:   ErrAbsolutePath,
			skipOnWin: true, // On Windows, /etc/passwd is relative
		},
		{
			name:       "absolute windows path",
			input:      "C:\\Windows\\System32\\config",
			wantErr:    ErrAbsolutePath,
			skipOnUnix: true, // On Unix, this is a valid filename with backslashes
		},

		// Empty and invalid
		{
			name:    "empty string",
			input:   "",
			wantErr: ErrEmptyPath,
		},
		{
			name:    "just dot",
			input:   ".",
			wantErr: ErrEmptyPath,
		},
		{
			name:      "just slash",
			input:     "/",
			wantErr:   ErrAbsolutePath,
			skipOnWin: true,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if tc.skipOnWin && runtime.GOOS == "windows" {
				t.Skip("Skipping test on Windows")
			}
			if tc.skipOnUnix && runtime.GOOS != "windows" {
				t.Skip("Skipping test on Unix")
			}

			got, err := SanitizeRelativePath(tc.input)

			if tc.wantErr != nil {
				if err == nil {
					t.Errorf("expected error %v, got nil (result: %q)", tc.wantErr, got)
					return
				}
				if err != tc.wantErr {
					t.Errorf("expected error %v, got %v", tc.wantErr, err)
				}
				return
			}

			if err != nil {
				t.Errorf("unexpected error: %v", err)
				return
			}

			if got != tc.want {
				t.Errorf("got %q, want %q", got, tc.want)
			}
		})
	}
}

func TestToProtocolPath(t *testing.T) {
	testCases := []struct {
		name  string
		input string
		want  string
	}{
		{
			name:  "already forward slashes",
			input: "Photos/Summer/beach.jpg",
			want:  "Photos/Summer/beach.jpg",
		},
		{
			name:  "simple filename",
			input: "file.txt",
			want:  "file.txt",
		},
	}

	// Add OS-specific test
	if runtime.GOOS == "windows" {
		testCases = append(testCases, struct {
			name  string
			input string
			want  string
		}{
			name:  "backslashes to forward slashes",
			input: "Photos\\Summer\\beach.jpg",
			want:  "Photos/Summer/beach.jpg",
		})
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			got := ToProtocolPath(tc.input)
			if got != tc.want {
				t.Errorf("got %q, want %q", got, tc.want)
			}
		})
	}
}

// TestSanitizeRelativePathSecurityVectors tests specific attack vectors
// to ensure they are always blocked.
func TestSanitizeRelativePathSecurityVectors(t *testing.T) {
	// These should ALWAYS be rejected regardless of platform
	attackVectors := []string{
		"../evil.txt",
		"../../evil.txt",
		"../../../etc/passwd",
		"foo/../../../etc/passwd",
		"foo/bar/../../../etc/passwd",
		"a/b/c/d/../../../../../../../../etc/passwd",
		"..",
		"../..",
		"../.ssh/id_rsa",
	}

	for _, attack := range attackVectors {
		t.Run(attack, func(t *testing.T) {
			result, err := SanitizeRelativePath(attack)
			if err == nil {
				t.Errorf("attack vector %q should have been rejected, got result: %q", attack, result)
			}
			if err != ErrPathTraversal {
				t.Errorf("attack vector %q: expected ErrPathTraversal, got: %v", attack, err)
			}
		})
	}
}

// TestSanitizePathWithFallback tests the fallback path sanitization.
func TestSanitizePathWithFallback(t *testing.T) {
	testCases := []struct {
		name    string
		input   string
		want    string
		wantErr bool
	}{
		// Valid paths should work as-is
		{
			name:  "simple file",
			input: "document.pdf",
			want:  "document.pdf",
		},
		{
			name:  "subdirectory",
			input: "Photos/beach.jpg",
			want:  "Photos/beach.jpg",
		},

		// Path traversal should fall back to base name
		{
			name:  "path traversal falls back",
			input: "../../../etc/passwd",
			want:  "passwd",
		},
		{
			name:  "deep traversal falls back",
			input: "foo/../../../bar/secret.txt",
			want:  "secret.txt",
		},

		// Invalid paths that can't be recovered
		{
			name:    "empty string",
			input:   "",
			wantErr: true,
		},
		{
			name:    "just dots",
			input:   "..",
			wantErr: true,
		},
		{
			name:    "dot slash dot",
			input:   "../.",
			wantErr: true,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := SanitizePathWithFallback(tc.input)

			if tc.wantErr {
				if err == nil {
					t.Errorf("expected error, got nil (result: %q)", got)
				}
				return
			}

			if err != nil {
				t.Errorf("unexpected error: %v", err)
				return
			}

			// Normalize slashes for comparison
			want := tc.want
			if runtime.GOOS == "windows" {
				want = filepath.FromSlash(want)
			}

			if got != want {
				t.Errorf("got %q, want %q", got, want)
			}
		})
	}
}

// TestIsFolderTransfer tests folder transfer detection.
func TestIsFolderTransfer(t *testing.T) {
	testCases := []struct {
		name      string
		filenames []string
		want      bool
	}{
		{
			name:      "empty list",
			filenames: []string{},
			want:      false,
		},
		{
			name:      "single flat file",
			filenames: []string{"document.pdf"},
			want:      false,
		},
		{
			name:      "multiple flat files",
			filenames: []string{"a.txt", "b.txt", "c.pdf"},
			want:      false,
		},
		{
			name:      "single folder path",
			filenames: []string{"Photos/beach.jpg"},
			want:      true,
		},
		{
			name:      "mixed flat and folder",
			filenames: []string{"readme.txt", "Photos/beach.jpg"},
			want:      true,
		},
		{
			name:      "deep folder",
			filenames: []string{"a/b/c/d.txt"},
			want:      true,
		},
		{
			name:      "multiple folders",
			filenames: []string{"a/1.txt", "b/2.txt"},
			want:      true,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			got := IsFolderTransfer(tc.filenames)
			if got != tc.want {
				t.Errorf("IsFolderTransfer = %v; want %v", got, tc.want)
			}
		})
	}
}
