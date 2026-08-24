//go:build integration

package signaling_test

import (
	"sync"
	"testing"
)

// =============================================================================
// Stability Integration Tests - Signaling Client
// =============================================================================

// TestStability_DoubleCloseChannel demonstrates the panic that occurs when
// closing a channel twice, which is what would happen if SignalingClient.Close()
// was called twice before the sync.Once fix.
//
// This test demonstrates the pattern, not the actual SignalingClient (which
// requires a real WebSocket connection to test).
func TestStability_DoubleCloseChannel(t *testing.T) {
	t.Run("without sync.Once - panics", func(t *testing.T) {
		// This demonstrates what WOULD happen without the fix
		// We don't actually run this as it would panic
		t.Log("Without sync.Once, calling close() twice on a channel panics")

		// Uncomment to see the panic:
		// done := make(chan struct{})
		// close(done)
		// close(done) // PANIC: close of closed channel
	})

	t.Run("with sync.Once - safe", func(t *testing.T) {
		defer func() {
			if r := recover(); r != nil {
				t.Errorf("Double close with sync.Once panicked: %v", r)
			}
		}()

		// This is the pattern we now use in SignalingClient
		done := make(chan struct{})
		var closeOnce sync.Once

		// First close
		closeOnce.Do(func() {
			close(done)
		})

		// Second close - should not panic
		closeOnce.Do(func() {
			close(done)
		})

		t.Log("Double close with sync.Once is safe")
	})

	t.Run("concurrent close - safe with sync.Once", func(t *testing.T) {
		defer func() {
			if r := recover(); r != nil {
				t.Errorf("Concurrent close panicked: %v", r)
			}
		}()

		done := make(chan struct{})
		var closeOnce sync.Once

		// Spawn many goroutines all trying to close at once
		var wg sync.WaitGroup
		for i := 0; i < 100; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				closeOnce.Do(func() {
					close(done)
				})
			}()
		}

		wg.Wait()
		t.Log("Concurrent close with sync.Once is safe")
	})
}
