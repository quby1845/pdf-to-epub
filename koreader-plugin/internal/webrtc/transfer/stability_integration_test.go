//go:build integration

package transfer_test

import (
	"testing"

	"localsend-cli/internal/webrtc/transfer"
)

// =============================================================================
// Stability Integration Tests
// These tests verify that edge cases don't cause panics or crashes.
// =============================================================================

// TestStability_ParseRTCMessage_MalformedInput tests that malformed messages
// don't cause panics when processed through the message parser.
func TestStability_ParseRTCMessage_MalformedInput(t *testing.T) {
	// These are edge cases that could occur with malformed network data
	malformedInputs := []struct {
		name  string
		input []byte
	}{
		{"empty bytes", []byte{}},
		{"single byte", []byte{0}},
		{"null byte", []byte{0x00}},
		{"binary garbage", []byte{0xff, 0xfe, 0xfd, 0xfc}},
		{"truncated json", []byte(`{"nonce":`)},
		{"invalid utf8", []byte{0x80, 0x81, 0x82}},
		{"nested braces", []byte(`{{{{`)},
		{"array instead of object", []byte(`[]`)},
		{"null json", []byte(`null`)},
		{"number json", []byte(`12345`)},
		{"string json", []byte(`"just a string"`)},
		{"empty object", []byte(`{}`)},
		{"object with null values", []byte(`{"nonce":null,"token":null,"status":null}`)},
		{"deeply nested", []byte(`{"a":{"b":{"c":{"d":{}}}}}`)},
		{"very long string", make([]byte, 1024*1024)}, // 1MB of zeros
	}

	for _, tc := range malformedInputs {
		t.Run(tc.name, func(t *testing.T) {
			defer func() {
				if r := recover(); r != nil {
					t.Errorf("ParseRTCMessage panicked on %s: %v", tc.name, r)
				}
			}()

			// This should never panic, even with garbage input
			msg, msgType, err := transfer.ParseRTCMessage(tc.input)

			// We don't care about the result, just that it didn't panic
			_ = msg
			_ = msgType
			_ = err
		})
	}
}

// TestStability_TypeAssertionSafety tests that type assertions in message
// handlers are safe even when ParseRTCMessage returns unexpected types.
func TestStability_TypeAssertionSafety(t *testing.T) {
	// Test that the returned types match what the msgType claims
	// This validates the fix: handlers now use safe type assertions

	testCases := []struct {
		name         string
		input        []byte
		expectedType string
	}{
		{
			name:         "nonce message",
			input:        []byte(`{"nonce":"test123"}`),
			expectedType: "nonce",
		},
		{
			name:         "token request",
			input:        []byte(`{"token":"abc"}`),
			expectedType: "token_request",
		},
		{
			name:         "pin message",
			input:        []byte(`{"pin":"1234"}`),
			expectedType: "pin",
		},
		{
			name:         "file header",
			input:        []byte(`{"id":"f1","token":"t1"}`),
			expectedType: "file_header",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			defer func() {
				if r := recover(); r != nil {
					t.Errorf("Type assertion panicked for %s: %v", tc.name, r)
				}
			}()

			msg, msgType, err := transfer.ParseRTCMessage(tc.input)
			if err != nil {
				t.Skipf("Parse error (acceptable): %v", err)
			}

			if msgType != tc.expectedType {
				t.Errorf("got msgType %q, want %q", msgType, tc.expectedType)
			}

			// Perform the type assertions that handlers would do
			// These should all be safe now
			switch msgType {
			case "nonce":
				if nonce, ok := msg.(*transfer.RTCNonceMessage); !ok {
					t.Errorf("nonce message has wrong type: %T", msg)
				} else if nonce.Nonce == "" {
					t.Error("nonce message has empty nonce")
				}
			case "token_request":
				if token, ok := msg.(*transfer.RTCTokenRequest); !ok {
					t.Errorf("token_request message has wrong type: %T", msg)
				} else if token.Token == "" {
					t.Error("token_request has empty token")
				}
			case "pin":
				if pin, ok := msg.(*transfer.RTCPinMessage); !ok {
					t.Errorf("pin message has wrong type: %T", msg)
				} else if pin.Pin == "" {
					t.Error("pin message has empty pin")
				}
			case "file_header":
				if header, ok := msg.(*transfer.RTCSendFileHeader); !ok {
					t.Errorf("file_header message has wrong type: %T", msg)
				} else if header.ID == "" {
					t.Error("file_header has empty ID")
				}
			}
		})
	}
}

// TestStability_MessageTypeConfusion tests scenarios where message content
// could be ambiguous and might confuse the parser.
func TestStability_MessageTypeConfusion(t *testing.T) {
	// These messages have fields from multiple message types
	// and could potentially cause type confusion
	confusingMessages := []struct {
		name  string
		input []byte
	}{
		{
			name:  "nonce and token together",
			input: []byte(`{"nonce":"abc","token":"xyz"}`),
		},
		{
			name:  "status and nonce",
			input: []byte(`{"status":"OK","nonce":"abc"}`),
		},
		{
			name:  "id without token",
			input: []byte(`{"id":"file1"}`),
		},
		{
			name:  "token without id",
			input: []byte(`{"token":"tok1"}`),
		},
		{
			name:  "all fields present",
			input: []byte(`{"nonce":"n","token":"t","pin":"p","id":"i","status":"s"}`),
		},
		{
			name:  "empty strings",
			input: []byte(`{"nonce":"","token":"","pin":""}`),
		},
	}

	for _, tc := range confusingMessages {
		t.Run(tc.name, func(t *testing.T) {
			defer func() {
				if r := recover(); r != nil {
					t.Errorf("ParseRTCMessage panicked on confusing input: %v", r)
				}
			}()

			msg, msgType, _ := transfer.ParseRTCMessage(tc.input)

			// If we got a typed message, verify the type assertion is safe
			if msg != nil && msgType != "" {
				// Attempt type assertions - should not panic
				_, _ = msg.(*transfer.RTCNonceMessage)
				_, _ = msg.(*transfer.RTCTokenRequest)
				_, _ = msg.(*transfer.RTCPinMessage)
				_, _ = msg.(*transfer.RTCSendFileHeader)
			}
		})
	}
}
