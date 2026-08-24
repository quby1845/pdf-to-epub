package storage

// DeviceStore defines the interface for trusted device storage.
// This interface allows for testing and mocking of the storage layer.
type DeviceStore interface {
	// Add adds a trusted device to the store.
	Add(device TrustedDevice) error

	// Remove removes a device by its fingerprint.
	Remove(fingerprint string) error

	// IsTrusted returns true if the given public key belongs to a trusted device.
	IsTrusted(publicKey string) bool

	// GetPublicKey returns the public key for a given fingerprint.
	GetPublicKey(fingerprint string) (string, bool)

	// List returns all trusted devices.
	List() []TrustedDevice

	// ListPublicKeys returns a map of fingerprint -> publicKey for all trusted devices.
	ListPublicKeys() map[string]string

	// GetFingerprint returns the fingerprint for a given public key.
	GetFingerprint(publicKey string) string
}

// Compile-time check that TrustedDeviceStore implements DeviceStore.
var _ DeviceStore = (*TrustedDeviceStore)(nil)
