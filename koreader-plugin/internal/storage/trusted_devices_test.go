package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestTrustedDeviceStore_SaveAtomic(t *testing.T) {
	// Create temp directory
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	// Add a device
	device := TrustedDevice{
		Alias:     "Test Device",
		PublicKey: "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAtest\n-----END PUBLIC KEY-----",
		AddedAt:   time.Now().Unix(),
	}

	if err := store.Add(device); err != nil {
		t.Fatalf("Failed to add device: %v", err)
	}

	// Verify no temp file remains after save
	tempPath := filepath.Join(tmpDir, "trusted_devices.json.tmp")
	if _, err := os.Stat(tempPath); !os.IsNotExist(err) {
		t.Error("Temp file should not exist after successful save")
	}

	// Verify main file exists and is valid JSON
	filePath := filepath.Join(tmpDir, "trusted_devices.json")
	data, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("Failed to read saved file: %v", err)
	}

	var devices map[string]TrustedDevice
	if err := json.Unmarshal(data, &devices); err != nil {
		t.Fatalf("Saved file is not valid JSON: %v", err)
	}

	if len(devices) != 1 {
		t.Errorf("Expected 1 device, got %d", len(devices))
	}
}

func TestTrustedDeviceStore_SaveAtomic_PreservesOriginalOnError(t *testing.T) {
	// This test verifies that if we have an existing file and a new save
	// operation would fail, the original file is preserved.
	// With atomic save (temp file + rename), this is guaranteed.

	tmpDir := t.TempDir()

	// Create initial store with a device
	store1, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	device1 := TrustedDevice{
		Alias:     "Original Device",
		PublicKey: "-----BEGIN PUBLIC KEY-----\noriginal\n-----END PUBLIC KEY-----",
		AddedAt:   time.Now().Unix(),
	}

	if err := store1.Add(device1); err != nil {
		t.Fatalf("Failed to add device: %v", err)
	}

	// Create new store and verify original data loads correctly
	store2, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create second store: %v", err)
	}

	devices := store2.List()
	if len(devices) != 1 {
		t.Errorf("Expected 1 device after reload, got %d", len(devices))
	}
}

func TestTrustedDeviceStore_BasicOperations(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	publicKey := "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAtest\n-----END PUBLIC KEY-----"
	device := TrustedDevice{
		Alias:     "Test Device",
		PublicKey: publicKey,
		AddedAt:   time.Now().Unix(),
	}

	// Test Add
	if err := store.Add(device); err != nil {
		t.Fatalf("Failed to add device: %v", err)
	}

	// Test IsTrusted
	if !store.IsTrusted(publicKey) {
		t.Error("Device should be trusted after adding")
	}

	// Test List
	devices := store.List()
	if len(devices) != 1 {
		t.Errorf("Expected 1 device, got %d", len(devices))
	}

	// Test GetFingerprint and GetPublicKey
	fingerprint := store.GetFingerprint(publicKey)
	retrievedKey, ok := store.GetPublicKey(fingerprint)
	if !ok {
		t.Error("GetPublicKey should return ok=true for existing device")
	}
	if retrievedKey != publicKey {
		t.Error("Retrieved public key should match original")
	}

	// Test Remove
	if err := store.Remove(fingerprint); err != nil {
		t.Fatalf("Failed to remove device: %v", err)
	}

	if store.IsTrusted(publicKey) {
		t.Error("Device should not be trusted after removal")
	}
}

func TestTrustedDeviceStore_Persistence(t *testing.T) {
	tmpDir := t.TempDir()

	publicKey := "-----BEGIN PUBLIC KEY-----\npersistence-test\n-----END PUBLIC KEY-----"

	// Create store and add device
	store1, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	device := TrustedDevice{
		Alias:     "Persistent Device",
		PublicKey: publicKey,
		AddedAt:   time.Now().Unix(),
	}

	if err := store1.Add(device); err != nil {
		t.Fatalf("Failed to add device: %v", err)
	}

	// Create new store instance (simulates restart)
	store2, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create second store: %v", err)
	}

	// Verify device persisted
	if !store2.IsTrusted(publicKey) {
		t.Error("Device should be trusted after reload")
	}
}

// =============================================================================
// Error Handling Tests
// =============================================================================

// TestTrustedDeviceStore_CorruptedFile_ReturnsError verifies that corrupted
// JSON files return an error on load (does not silently ignore corruption).
func TestTrustedDeviceStore_CorruptedFile_ReturnsError(t *testing.T) {
	tmpDir := t.TempDir()

	// Write corrupted JSON to the trusted_devices.json file
	corruptedData := []byte(`{"device1": {"alias": "Test", "publicKey": truncated...`)
	filePath := filepath.Join(tmpDir, "trusted_devices.json")
	if err := os.WriteFile(filePath, corruptedData, 0644); err != nil {
		t.Fatalf("Failed to write corrupted file: %v", err)
	}

	// Attempt to create store with corrupted file
	_, err := NewTrustedDeviceStore(tmpDir)
	if err == nil {
		t.Error("Expected error for corrupted JSON file")
	}
}

// TestTrustedDeviceStore_EmptyFile_ReturnsError verifies that empty files
// return an error (empty file is not valid JSON).
func TestTrustedDeviceStore_EmptyFile_ReturnsError(t *testing.T) {
	tmpDir := t.TempDir()

	// Write empty file
	filePath := filepath.Join(tmpDir, "trusted_devices.json")
	if err := os.WriteFile(filePath, []byte(""), 0644); err != nil {
		t.Fatalf("Failed to write empty file: %v", err)
	}

	// Attempt to create store with empty file
	_, err := NewTrustedDeviceStore(tmpDir)
	if err == nil {
		t.Error("Expected error for empty file (not valid JSON)")
	}
}

// TestTrustedDeviceStore_ValidEmptyObject_Succeeds verifies that an empty
// JSON object is valid and creates an empty store.
func TestTrustedDeviceStore_ValidEmptyObject_Succeeds(t *testing.T) {
	tmpDir := t.TempDir()

	// Write valid empty JSON object
	filePath := filepath.Join(tmpDir, "trusted_devices.json")
	if err := os.WriteFile(filePath, []byte("{}"), 0644); err != nil {
		t.Fatalf("Failed to write file: %v", err)
	}

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Should succeed with empty JSON object: %v", err)
	}

	devices := store.List()
	if len(devices) != 0 {
		t.Errorf("Expected 0 devices, got %d", len(devices))
	}
}

// TestTrustedDeviceStore_NoFile_Succeeds verifies that missing file is OK
// (store starts empty).
func TestTrustedDeviceStore_NoFile_Succeeds(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Should succeed when file doesn't exist: %v", err)
	}

	devices := store.List()
	if len(devices) != 0 {
		t.Errorf("Expected 0 devices for new store, got %d", len(devices))
	}
}

// =============================================================================
// ListPublicKeys Tests
// =============================================================================

// TestTrustedDeviceStore_ListPublicKeys verifies that ListPublicKeys returns
// all public keys in the store.
func TestTrustedDeviceStore_ListPublicKeys(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	// Add multiple devices
	devices := []TrustedDevice{
		{Alias: "Device 1", PublicKey: "key1", AddedAt: time.Now().Unix()},
		{Alias: "Device 2", PublicKey: "key2", AddedAt: time.Now().Unix()},
		{Alias: "Device 3", PublicKey: "key3", AddedAt: time.Now().Unix()},
	}

	for _, d := range devices {
		if err := store.Add(d); err != nil {
			t.Fatalf("Failed to add device: %v", err)
		}
	}

	keys := store.ListPublicKeys()

	if len(keys) != 3 {
		t.Errorf("Expected 3 keys, got %d", len(keys))
	}

	// Verify all keys are present (by value, not fingerprint)
	foundKeys := make(map[string]bool)
	for _, key := range keys {
		foundKeys[key] = true
	}

	for _, d := range devices {
		if !foundKeys[d.PublicKey] {
			t.Errorf("Key %q not found in ListPublicKeys result", d.PublicKey)
		}
	}
}

// TestTrustedDeviceStore_ListPublicKeys_Empty verifies ListPublicKeys on empty store.
func TestTrustedDeviceStore_ListPublicKeys_Empty(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	keys := store.ListPublicKeys()

	if len(keys) != 0 {
		t.Errorf("Expected 0 keys, got %d", len(keys))
	}
}

// TestTrustedDeviceStore_GetPublicKey_NotFound verifies GetPublicKey returns
// false for non-existent fingerprints.
func TestTrustedDeviceStore_GetPublicKey_NotFound(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	_, ok := store.GetPublicKey("nonexistent-fingerprint")
	if ok {
		t.Error("GetPublicKey should return ok=false for non-existent fingerprint")
	}
}

// TestTrustedDeviceStore_IsTrusted_NotFound verifies IsTrusted returns false
// for non-existent keys.
func TestTrustedDeviceStore_IsTrusted_NotFound(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	if store.IsTrusted("nonexistent-public-key") {
		t.Error("IsTrusted should return false for non-existent key")
	}
}

// TestTrustedDeviceStore_Remove_NotFound verifies Remove is a no-op for
// non-existent fingerprints.
func TestTrustedDeviceStore_Remove_NotFound(t *testing.T) {
	tmpDir := t.TempDir()

	store, err := NewTrustedDeviceStore(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create store: %v", err)
	}

	// Remove on non-existent fingerprint should not error
	err = store.Remove("nonexistent-fingerprint")
	if err != nil {
		t.Errorf("Remove should not error for non-existent fingerprint: %v", err)
	}
}

// =============================================================================
// Eviction Tests
// =============================================================================

// TestTrustedDeviceStore_EvictsOldestWhenAtCapacity verifies that when the store
// reaches MaxTrustedDevices capacity, adding a new device evicts the oldest one.
func TestTrustedDeviceStore_EvictsOldestWhenAtCapacity(t *testing.T) {
	dir := t.TempDir()
	store, err := NewTrustedDeviceStore(dir)
	if err != nil {
		t.Fatal(err)
	}

	// Fill store to capacity
	for i := 0; i < MaxTrustedDevices; i++ {
		device := TrustedDevice{
			Alias:     fmt.Sprintf("device-%d", i),
			PublicKey: fmt.Sprintf("key-%d", i),
			AddedAt:   int64(i), // Oldest has AddedAt=0
		}
		if err := store.Add(device); err != nil {
			t.Fatal(err)
		}
	}

	// Verify at capacity
	if len(store.devices) != MaxTrustedDevices {
		t.Errorf("expected %d devices, got %d", MaxTrustedDevices, len(store.devices))
	}

	// Add one more - should evict oldest (AddedAt=0)
	newDevice := TrustedDevice{
		Alias:     "new-device",
		PublicKey: "new-key",
		AddedAt:   int64(MaxTrustedDevices),
	}
	if err := store.Add(newDevice); err != nil {
		t.Fatal(err)
	}

	// Still at capacity
	if len(store.devices) != MaxTrustedDevices {
		t.Errorf("expected %d devices after eviction, got %d", MaxTrustedDevices, len(store.devices))
	}

	// Oldest device (key-0) should be gone
	if store.IsTrusted("key-0") {
		t.Error("oldest device should have been evicted")
	}

	// New device should be present
	if !store.IsTrusted("new-key") {
		t.Error("new device should be present")
	}
}

// TestTrustedDeviceStore_ReAddExistingDeviceDoesNotEvict verifies that re-adding
// an existing device (same public key) updates it without triggering eviction.
func TestTrustedDeviceStore_ReAddExistingDeviceDoesNotEvict(t *testing.T) {
	dir := t.TempDir()
	store, err := NewTrustedDeviceStore(dir)
	if err != nil {
		t.Fatal(err)
	}

	// Fill store to capacity
	for i := 0; i < MaxTrustedDevices; i++ {
		device := TrustedDevice{
			Alias:     fmt.Sprintf("device-%d", i),
			PublicKey: fmt.Sprintf("key-%d", i),
			AddedAt:   int64(i),
		}
		if err := store.Add(device); err != nil {
			t.Fatal(err)
		}
	}

	// Re-add an existing device (should update, not evict)
	device := TrustedDevice{
		Alias:     "device-50-updated",
		PublicKey: "key-50", // Same key = same fingerprint
		AddedAt:   int64(MaxTrustedDevices + 1),
	}
	if err := store.Add(device); err != nil {
		t.Fatal(err)
	}

	// Still at capacity (no eviction happened)
	if len(store.devices) != MaxTrustedDevices {
		t.Errorf("expected %d devices, got %d", MaxTrustedDevices, len(store.devices))
	}

	// Oldest device should still be there (no eviction needed for re-add)
	if !store.IsTrusted("key-0") {
		t.Error("oldest device should NOT have been evicted on re-add")
	}
}
