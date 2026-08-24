// Package transfer provides WebRTC-based file transfer functionality.
package transfer

// WebRTC protocol status constants.
// These are used in responses during the WebRTC handshake and transfer process.
const (
	// StatusOK indicates success or acceptance.
	StatusOK = "OK"

	// StatusPINRequired indicates the receiver requires a PIN.
	StatusPINRequired = "PIN_REQUIRED"

	// StatusTooManyAttempts indicates the client has exceeded the max PIN attempts.
	StatusTooManyAttempts = "TOO_MANY_ATTEMPTS"

	// StatusInvalidSignature indicates token signature verification failed.
	StatusInvalidSignature = "INVALID_SIGNATURE"

	// StatusDeclined indicates the transfer was declined by the user.
	StatusDeclined = "DECLINED"

	// StatusPair indicates the receiver wants to initiate device pairing.
	StatusPair = "PAIR"

	// StatusPairDeclined indicates the user declined the pairing request.
	StatusPairDeclined = "PAIR_DECLINED"
)
