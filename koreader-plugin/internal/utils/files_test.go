package utils

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// =============================================================================
// FindUniqueFolderName Tests
// =============================================================================

// TestFindUniqueFolderName_NewFolder_ReturnsAsIs verifies that new folders
// are returned without modification.
func TestFindUniqueFolderName_NewFolder_ReturnsAsIs(t *testing.T) {
	tmpDir := t.TempDir()

	result, err := FindUniqueFolderName(tmpDir, "NewFolder")
	if err != nil {
		t.Fatalf("FindUniqueFolderName failed: %v", err)
	}

	if result != "NewFolder" {
		t.Errorf("Expected 'NewFolder', got %q", result)
	}
}

// TestFindUniqueFolderName_ExistingFolder_AppendsNumber verifies that existing
// folders get a numeric suffix.
func TestFindUniqueFolderName_ExistingFolder_AppendsNumber(t *testing.T) {
	tmpDir := t.TempDir()

	// Create existing folder
	existingFolder := filepath.Join(tmpDir, "Photos")
	if err := os.MkdirAll(existingFolder, 0755); err != nil {
		t.Fatalf("Failed to create test folder: %v", err)
	}

	result, err := FindUniqueFolderName(tmpDir, "Photos")
	if err != nil {
		t.Fatalf("FindUniqueFolderName failed: %v", err)
	}

	expected := "Photos (1)"
	if result != expected {
		t.Errorf("Expected %q, got %q", expected, result)
	}
}

// TestFindUniqueFolderName_MultipleExisting_IncrementsNumber verifies that
// the counter increments correctly when multiple conflicts exist.
func TestFindUniqueFolderName_MultipleExisting_IncrementsNumber(t *testing.T) {
	tmpDir := t.TempDir()

	// Create Photos, Photos (1), Photos (2)
	folders := []string{"Photos", "Photos (1)", "Photos (2)"}
	for _, folder := range folders {
		path := filepath.Join(tmpDir, folder)
		if err := os.MkdirAll(path, 0755); err != nil {
			t.Fatalf("Failed to create test folder: %v", err)
		}
	}

	result, err := FindUniqueFolderName(tmpDir, "Photos")
	if err != nil {
		t.Fatalf("FindUniqueFolderName failed: %v", err)
	}

	expected := "Photos (3)"
	if result != expected {
		t.Errorf("Expected %q, got %q", expected, result)
	}
}

// TestFindUniqueFolderName_FileExistsWithSameName verifies that files
// (not just directories) with the same name trigger renaming.
func TestFindUniqueFolderName_FileExistsWithSameName(t *testing.T) {
	tmpDir := t.TempDir()

	// Create a file with the same name as the folder
	filePath := filepath.Join(tmpDir, "Photos")
	if err := os.WriteFile(filePath, []byte("test"), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	result, err := FindUniqueFolderName(tmpDir, "Photos")
	if err != nil {
		t.Fatalf("FindUniqueFolderName failed: %v", err)
	}

	expected := "Photos (1)"
	if result != expected {
		t.Errorf("Expected %q, got %q", expected, result)
	}
}

// =============================================================================
// CreateUniqueFile Tests
// =============================================================================

// TestCreateUniqueFile_NewFile_CreatesSuccessfully verifies that new files
// are created at the expected path.
func TestCreateUniqueFile_NewFile_CreatesSuccessfully(t *testing.T) {
	tmpDir := t.TempDir()

	file, path, err := CreateUniqueFile(tmpDir, "test.txt")
	if err != nil {
		t.Fatalf("CreateUniqueFile failed: %v", err)
	}
	defer func() {
		_ = file.Close()
		_ = os.Remove(path)
	}()

	expectedPath := filepath.Join(tmpDir, "test.txt")
	if path != expectedPath {
		t.Errorf("Path = %q; want %q", path, expectedPath)
	}

	// Verify file exists and is writable
	if _, err := file.Write([]byte("test content")); err != nil {
		t.Errorf("Failed to write to file: %v", err)
	}
}

// TestCreateUniqueFile_ExistingFile_AppendsNumber verifies that existing files
// get a numeric suffix.
func TestCreateUniqueFile_ExistingFile_AppendsNumber(t *testing.T) {
	tmpDir := t.TempDir()

	// Create existing file
	existingFile := filepath.Join(tmpDir, "test.txt")
	if err := os.WriteFile(existingFile, []byte("existing"), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	file, path, err := CreateUniqueFile(tmpDir, "test.txt")
	if err != nil {
		t.Fatalf("CreateUniqueFile failed: %v", err)
	}
	defer func() {
		_ = file.Close()
		_ = os.Remove(path)
	}()

	expectedPath := filepath.Join(tmpDir, "test (1).txt")
	if path != expectedPath {
		t.Errorf("Path = %q; want %q", path, expectedPath)
	}
}

// TestCreateUniqueFile_MultipleExisting_IncrementsNumber verifies correct
// increment behavior with multiple existing files.
func TestCreateUniqueFile_MultipleExisting_IncrementsNumber(t *testing.T) {
	tmpDir := t.TempDir()

	// Create test.txt, test (1).txt, test (2).txt
	files := []string{"test.txt", "test (1).txt", "test (2).txt"}
	for _, f := range files {
		path := filepath.Join(tmpDir, f)
		if err := os.WriteFile(path, []byte("existing"), 0644); err != nil {
			t.Fatalf("Failed to create test file: %v", err)
		}
	}

	file, path, err := CreateUniqueFile(tmpDir, "test.txt")
	if err != nil {
		t.Fatalf("CreateUniqueFile failed: %v", err)
	}
	defer func() {
		_ = file.Close()
		_ = os.Remove(path)
	}()

	expectedPath := filepath.Join(tmpDir, "test (3).txt")
	if path != expectedPath {
		t.Errorf("Path = %q; want %q", path, expectedPath)
	}
}

// TestCreateUniqueFile_NoExtension_AppendsNumberCorrectly verifies files
// without extensions are handled correctly.
func TestCreateUniqueFile_NoExtension_AppendsNumberCorrectly(t *testing.T) {
	tmpDir := t.TempDir()

	// Create existing file without extension
	existingFile := filepath.Join(tmpDir, "README")
	if err := os.WriteFile(existingFile, []byte("existing"), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	file, path, err := CreateUniqueFile(tmpDir, "README")
	if err != nil {
		t.Fatalf("CreateUniqueFile failed: %v", err)
	}
	defer func() {
		_ = file.Close()
		_ = os.Remove(path)
	}()

	expectedPath := filepath.Join(tmpDir, "README (1)")
	if path != expectedPath {
		t.Errorf("Path = %q; want %q", path, expectedPath)
	}
}

// TestCreateUniqueFile_UsesOEXCL_AtomicCreation verifies atomic file creation
// using O_EXCL flag (prevents race conditions).
func TestCreateUniqueFile_UsesOEXCL_AtomicCreation(t *testing.T) {
	tmpDir := t.TempDir()

	// Create first file
	file1, path1, err := CreateUniqueFile(tmpDir, "atomic.txt")
	if err != nil {
		t.Fatalf("First CreateUniqueFile failed: %v", err)
	}
	// Don't close file1 yet - keep it open

	// Second call should get a different path because first file exists
	file2, path2, err := CreateUniqueFile(tmpDir, "atomic.txt")
	if err != nil {
		t.Fatalf("Second CreateUniqueFile failed: %v", err)
	}

	// Close both files
	defer func() {
		_ = file1.Close()
		_ = file2.Close()
		_ = os.Remove(path1)
		_ = os.Remove(path2)
	}()

	if path1 == path2 {
		t.Error("Both files got the same path - atomic creation not working")
	}
}

// TestCreateUniqueFile_NonexistentDirectory_ReturnsError verifies error handling
// for invalid directories.
func TestCreateUniqueFile_NonexistentDirectory_ReturnsError(t *testing.T) {
	_, _, err := CreateUniqueFile("/nonexistent/directory", "test.txt")
	if err == nil {
		t.Error("Expected error for non-existent directory")
	}
}

// TestCreateUniqueFile_PermissionDenied_ReturnsError verifies error handling
// for permission issues (skipped if running as root).
func TestCreateUniqueFile_PermissionDenied_ReturnsError(t *testing.T) {
	// Skip on systems where we can't test permissions
	if os.Getuid() == 0 {
		t.Skip("Skipping permission test when running as root")
	}

	tmpDir := t.TempDir()

	// Create read-only directory
	readOnlyDir := filepath.Join(tmpDir, "readonly")
	if err := os.MkdirAll(readOnlyDir, 0555); err != nil {
		t.Fatalf("Failed to create read-only dir: %v", err)
	}
	defer func() { _ = os.Chmod(readOnlyDir, 0755) }()

	_, _, err := CreateUniqueFile(readOnlyDir, "test.txt")
	if err == nil {
		t.Error("Expected error for permission denied")
	}
}

// TestCreateUniqueFile_SpecialCharactersInFilename verifies handling of special characters.
func TestCreateUniqueFile_SpecialCharactersInFilename(t *testing.T) {
	tmpDir := t.TempDir()

	testCases := []struct {
		name     string
		filename string
	}{
		{"spaces", "my file.txt"},
		{"unicode", "文档.txt"},
		{"dots", "file.name.txt"},
		{"hyphen", "my-file.txt"},
		{"underscore", "my_file.txt"},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			file, path, err := CreateUniqueFile(tmpDir, tc.filename)
			if err != nil {
				t.Fatalf("CreateUniqueFile failed for %q: %v", tc.filename, err)
			}
			defer func() {
				_ = file.Close()
				_ = os.Remove(path)
			}()

			if !strings.HasSuffix(path, tc.filename) {
				t.Errorf("Path %q should end with %q", path, tc.filename)
			}
		})
	}
}

// =============================================================================
// MaxUniquePathAttempts Boundary Tests
// =============================================================================

// TestMaxUniquePathAttempts_ConstantValue verifies the constant value.
func TestMaxUniquePathAttempts_ConstantValue(t *testing.T) {
	if MaxUniquePathAttempts != 10000 {
		t.Errorf("MaxUniquePathAttempts = %d; want 10000", MaxUniquePathAttempts)
	}
}
