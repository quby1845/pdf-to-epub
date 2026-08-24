package recv

import "context"

// Receiver defines the interface for a LocalSend file receiver.
// This interface allows for testing and mocking of the receiver component.
type Receiver interface {
	// Init initializes the receiver (creates directories, loads certificates, etc.)
	Init() error

	// Start starts the receiver server. Blocks until the context is cancelled.
	Start(ctx context.Context) error

	// Stop stops the receiver and releases resources.
	Stop() error

	// SetPIN sets the PIN code for authentication.
	SetPIN(pin string)

	// SetListenAddr sets the listen address for the server.
	SetListenAddr(addr string)

	// SetAllowedExtensions sets the list of allowed file extensions.
	SetAllowedExtensions(extensions []string)

	// SetTransferLog sets the path for the transfer log file.
	SetTransferLog(path string)

	// SetOnTransferCmd sets a shell command to run after each transfer.
	SetOnTransferCmd(cmd string)
}

// Compile-time check that FileReceiver implements Receiver.
var _ Receiver = (*FileReceiver)(nil)
