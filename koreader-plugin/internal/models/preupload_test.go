package models

import (
	"encoding/json"
	"testing"
)

// =============================================================================
// PreUploadReq Tests
// =============================================================================

// TestPreUploadReq_JSONMarshaling verifies PreUploadReq JSON serialization
// matches protocol spec Section 4.1.
func TestPreUploadReq_JSONMarshaling(t *testing.T) {
	req := PreUploadReq{
		Info: &SenderInfo{
			DeviceInfo: DeviceInfo{
				Alias:   "Sender",
				Version: "2.3",
			},
			Port:     53317,
			Protocol: "https",
		},
		Files: FileMetas{
			"file1": {Id: "file1", Filename: "test.txt", Size: 100, FileMIME: "text/plain"},
		},
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("Failed to marshal PreUploadReq: %v", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("Failed to unmarshal to map: %v", err)
	}

	// Verify info and files are present
	if result["info"] == nil {
		t.Error("info field should be present")
	}
	if result["files"] == nil {
		t.Error("files field should be present")
	}
}

// =============================================================================
// PreUploadResp Tests
// =============================================================================

// TestPreUploadResp_JSONMarshaling verifies PreUploadResp JSON serialization.
func TestPreUploadResp_JSONMarshaling(t *testing.T) {
	resp := PreUploadResp{
		SessionId: "session-123",
		Tokens: FileTokens{
			"file1": "token-abc",
			"file2": "token-xyz",
		},
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("Failed to marshal PreUploadResp: %v", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("Failed to unmarshal to map: %v", err)
	}

	if result["sessionId"] != "session-123" {
		t.Errorf("sessionId = %v; want 'session-123'", result["sessionId"])
	}

	files, ok := result["files"].(map[string]interface{})
	if !ok {
		t.Fatal("files should be a map")
	}
	if files["file1"] != "token-abc" {
		t.Errorf("files[file1] = %v; want 'token-abc'", files["file1"])
	}
}

// =============================================================================
// FileMetas Tests
// =============================================================================

// TestFileMetas_IsFolderTransfer_WithSubdirectories_ReturnsTrue verifies
// that files with path separators are detected as folder transfer.
func TestFileMetas_IsFolderTransfer_WithSubdirectories_ReturnsTrue(t *testing.T) {
	files := FileMetas{
		"file1": {Id: "file1", Filename: "Photos/beach.jpg", Size: 100},
		"file2": {Id: "file2", Filename: "Photos/sunset.jpg", Size: 200},
	}

	if !files.IsFolderTransfer() {
		t.Error("Files with subdirectory paths should be detected as folder transfer")
	}
}

// TestFileMetas_IsFolderTransfer_FlatFiles_ReturnsFalse verifies that
// files without path separators are not detected as folder transfer.
func TestFileMetas_IsFolderTransfer_FlatFiles_ReturnsFalse(t *testing.T) {
	files := FileMetas{
		"file1": {Id: "file1", Filename: "beach.jpg", Size: 100},
		"file2": {Id: "file2", Filename: "sunset.jpg", Size: 200},
	}

	if files.IsFolderTransfer() {
		t.Error("Flat files should not be detected as folder transfer")
	}
}

// TestFileMetas_IsFolderTransfer_MixedFiles_ReturnsTrue verifies that
// if ANY file has a subdirectory, it's considered folder transfer.
func TestFileMetas_IsFolderTransfer_MixedFiles_ReturnsTrue(t *testing.T) {
	files := FileMetas{
		"file1": {Id: "file1", Filename: "readme.txt", Size: 100},
		"file2": {Id: "file2", Filename: "docs/manual.pdf", Size: 200},
	}

	if !files.IsFolderTransfer() {
		t.Error("Mixed files with at least one subdirectory should be folder transfer")
	}
}

// TestFileMetas_IsFolderTransfer_EmptyMap_ReturnsFalse verifies empty files.
func TestFileMetas_IsFolderTransfer_EmptyMap_ReturnsFalse(t *testing.T) {
	files := FileMetas{}

	if files.IsFolderTransfer() {
		t.Error("Empty file list should not be folder transfer")
	}
}

// TestFileMetas_IsFolderTransfer_DeepNesting_ReturnsTrue verifies deep nesting detection.
func TestFileMetas_IsFolderTransfer_DeepNesting_ReturnsTrue(t *testing.T) {
	files := FileMetas{
		"file1": {Id: "file1", Filename: "a/b/c/d/e/file.txt", Size: 100},
	}

	if !files.IsFolderTransfer() {
		t.Error("Deeply nested files should be detected as folder transfer")
	}
}

// TestFileMetas_IsFolderTransfer_TrailingSlash_ReturnsTrue verifies trailing slash handling.
func TestFileMetas_IsFolderTransfer_TrailingSlash_ReturnsTrue(t *testing.T) {
	files := FileMetas{
		"file1": {Id: "file1", Filename: "folder/", Size: 0}, // Directory entry
	}

	if !files.IsFolderTransfer() {
		t.Error("Paths with slashes should be detected as folder transfer")
	}
}

// =============================================================================
// PreDownloadResp Tests
// =============================================================================

// TestPreDownloadResp_JSONMarshaling verifies PreDownloadResp JSON serialization
// matches protocol spec Section 5.2.
func TestPreDownloadResp_JSONMarshaling(t *testing.T) {
	resp := PreDownloadResp{
		Info: &DeviceInfo{
			Alias:   "Receiver",
			Version: "2.3",
		},
		SessionId: "session-456",
		Files: FileMetas{
			"file1": {Id: "file1", Filename: "download.zip", Size: 5000},
		},
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("Failed to marshal PreDownloadResp: %v", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("Failed to unmarshal to map: %v", err)
	}

	// Verify required fields
	if result["sessionId"] != "session-456" {
		t.Errorf("sessionId = %v; want 'session-456'", result["sessionId"])
	}
	if result["info"] == nil {
		t.Error("info field should be present")
	}
	if result["files"] == nil {
		t.Error("files field should be present")
	}

	// Verify info does NOT include port and protocol (per Section 5.2)
	info, ok := result["info"].(map[string]interface{})
	if !ok {
		t.Fatal("info should be a map")
	}
	if _, hasPort := info["port"]; hasPort {
		t.Error("PreDownloadResp.Info should NOT include port (DeviceInfo, not SenderInfo)")
	}
	if _, hasProtocol := info["protocol"]; hasProtocol {
		t.Error("PreDownloadResp.Info should NOT include protocol (DeviceInfo, not SenderInfo)")
	}
}

// =============================================================================
// FileTokens Tests
// =============================================================================

// TestFileTokens_JSONMarshaling verifies FileTokens map serialization.
func TestFileTokens_JSONMarshaling(t *testing.T) {
	tokens := FileTokens{
		"file1": "token-aaa",
		"file2": "token-bbb",
		"file3": "token-ccc",
	}

	data, err := json.Marshal(tokens)
	if err != nil {
		t.Fatalf("Failed to marshal FileTokens: %v", err)
	}

	var result map[string]string
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("Failed to unmarshal FileTokens: %v", err)
	}

	if len(result) != 3 {
		t.Errorf("Expected 3 tokens, got %d", len(result))
	}
	if result["file1"] != "token-aaa" {
		t.Errorf("file1 token = %v; want 'token-aaa'", result["file1"])
	}
}

// TestFileTokens_Empty_MarshalsAsEmptyObject verifies empty tokens serialization.
func TestFileTokens_Empty_MarshalsAsEmptyObject(t *testing.T) {
	tokens := FileTokens{}

	data, err := json.Marshal(tokens)
	if err != nil {
		t.Fatalf("Failed to marshal empty FileTokens: %v", err)
	}

	if string(data) != "{}" {
		t.Errorf("Empty FileTokens should marshal as {}, got %s", string(data))
	}
}
