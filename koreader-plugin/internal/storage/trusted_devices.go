// Package storage provides persistent storage for LocalSend CLI.
//
// TrustedDeviceStore manages trusted devices for the PAIR flow defined in
// the LocalSend protocol specification (Section 6: Device Pairing).
// When pairing is enabled, devices exchange Ed25519 public keys and store
// them for future authentication. This allows skipping PIN verification
// for previously paired devices.
//
// Integration Status: TrustedDeviceStore is currently not integrated into
// the main application commands. WebRTC receiver (internal/webrtc/transfer/receiver.go)
// has partial PAIR flow support that can be connected to this store.
//
// Usage:
//
//	store, err := storage.NewTrustedDeviceStore(configDir)
//	if err != nil {
//	    // handle error
//	}
//	if store.IsTrusted(senderPublicKey) {
//	    // Skip PIN verification
//	}
package storage

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"sync"
)

// MaxTrustedDevices is the maximum number of devices that can be stored.
// This limit protects memory on resource-constrained e-readers (64MB RAM).
const MaxTrustedDevices = 100

// TrustedDevice represents a device that has been paired and trusted.
type TrustedDevice struct {
	Alias     string `json:"alias"`
	PublicKey string `json:"publicKey"` // PEM-encoded Ed25519 public key
	AddedAt   int64  `json:"addedAt"`   // Unix timestamp
}

// TrustedDeviceStore manages the storage of trusted devices.
type TrustedDeviceStore struct {
	configDir string
	devices   map[string]TrustedDevice // keyed by fingerprint
	mu        sync.RWMutex
}

// NewTrustedDeviceStore creates a new store and loads existing devices from trusted_devices.json.
func NewTrustedDeviceStore(configDir string) (*TrustedDeviceStore, error) {
	store := &TrustedDeviceStore{
		configDir: configDir,
		devices:   make(map[string]TrustedDevice),
	}

	if err := store.load(); err != nil {
		return nil, err
	}

	return store, nil
}

// Add adds a device to the store and saves it to disk.
func (s *TrustedDeviceStore) Add(device TrustedDevice) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	fingerprint := s.GetFingerprint(device.PublicKey)

	// If device already exists (re-pairing), just update it
	if _, exists := s.devices[fingerprint]; !exists {
		// If at capacity, evict the oldest device
		if len(s.devices) >= MaxTrustedDevices {
			s.evictOldest()
		}
	}

	s.devices[fingerprint] = device

	return s.save()
}

// Remove removes a device from the store by its fingerprint.
func (s *TrustedDeviceStore) Remove(fingerprint string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.devices, fingerprint)

	return s.save()
}

// IsTrusted checks if a public key is in the trusted devices list.
func (s *TrustedDeviceStore) IsTrusted(publicKey string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	fingerprint := s.GetFingerprint(publicKey)
	_, ok := s.devices[fingerprint]
	return ok
}

// GetPublicKey retrieves the public key for a given fingerprint.
func (s *TrustedDeviceStore) GetPublicKey(fingerprint string) (string, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	device, ok := s.devices[fingerprint]
	if !ok {
		return "", false
	}
	return device.PublicKey, true
}

// List returns a list of all trusted devices.
func (s *TrustedDeviceStore) List() []TrustedDevice {
	s.mu.RLock()
	defer s.mu.RUnlock()

	list := make([]TrustedDevice, 0, len(s.devices))
	for _, device := range s.devices {
		list = append(list, device)
	}
	return list
}

// ListPublicKeys returns a map of fingerprint to public key PEM for all trusted devices.
// This is used for token-based lookup where we need to try verifying against all keys.
func (s *TrustedDeviceStore) ListPublicKeys() map[string]string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	keys := make(map[string]string, len(s.devices))
	for fingerprint, device := range s.devices {
		keys[fingerprint] = device.PublicKey
	}
	return keys
}

// GetFingerprint computes the SHA256 fingerprint of a public key.
func (s *TrustedDeviceStore) GetFingerprint(publicKey string) string {
	hash := sha256.Sum256([]byte(publicKey))
	return hex.EncodeToString(hash[:])
}

// evictOldest removes the device with the oldest AddedAt timestamp.
// Must be called with s.mu held.
func (s *TrustedDeviceStore) evictOldest() {
	var oldestKey string
	var oldestTime int64 = math.MaxInt64

	for key, device := range s.devices {
		if device.AddedAt < oldestTime {
			oldestTime = device.AddedAt
			oldestKey = key
		}
	}

	if oldestKey != "" {
		delete(s.devices, oldestKey)
	}
}

func (s *TrustedDeviceStore) load() error {
	filePath := filepath.Join(s.configDir, "trusted_devices.json")
	file, err := os.Open(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	defer func() { _ = file.Close() }()

	return json.NewDecoder(file).Decode(&s.devices)
}

// save writes devices to disk atomically using temp file + rename.
// This ensures the original file is preserved if encoding fails mid-write.
func (s *TrustedDeviceStore) save() error {
	if err := os.MkdirAll(s.configDir, 0755); err != nil {
		return err
	}

	filePath := filepath.Join(s.configDir, "trusted_devices.json")
	tempPath := filePath + ".tmp"

	// Write to temp file first
	file, err := os.Create(tempPath)
	if err != nil {
		return err
	}

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(s.devices); err != nil {
		_ = file.Close()
		_ = os.Remove(tempPath)
		return err
	}

	// Sync to ensure data is flushed to disk before rename
	if err := file.Sync(); err != nil {
		_ = file.Close()
		_ = os.Remove(tempPath)
		return err
	}

	if err := file.Close(); err != nil {
		_ = os.Remove(tempPath)
		return err
	}

	// Atomic rename (on POSIX systems)
	return os.Rename(tempPath, filePath)
}
