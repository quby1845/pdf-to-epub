package session

import (
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"localsend-cli/internal/localsend/constants"
	"localsend-cli/internal/models"
)

// TestRecvSessManagerLifecycle tests session manager lifecycle to prevent goroutine leaks
func TestRecvSessManagerLifecycle(t *testing.T) {
	t.Run("Start and Stop work correctly", func(t *testing.T) {
		mgr := NewRecvSessManager()

		// Start should not panic
		mgr.Start()

		// Give the goroutine time to start
		time.Sleep(10 * time.Millisecond)

		// Stop should not panic and should return promptly
		done := make(chan struct{})
		go func() {
			mgr.Stop()
			close(done)
		}()

		select {
		case <-done:
			// Success - Stop returned
		case <-time.After(1 * time.Second):
			t.Error("Stop did not return within 1 second - possible goroutine leak")
		}
	})

	t.Run("done channel is properly initialized", func(t *testing.T) {
		mgr := NewRecvSessManager()

		if mgr.done == nil {
			t.Error("done channel should be initialized")
		}
	})
}

// TestRecvSessManagerNewSession tests session creation
func TestRecvSessManagerNewSession(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	files := models.FileMetas{
		"file1": {Id: "file1", Filename: "test1.txt", Size: 100},
		"file2": {Id: "file2", Filename: "test2.txt", Size: 200},
	}

	sessionId, err := mgr.NewSession(files, "192.168.1.1")
	if err != nil {
		t.Fatalf("NewSession failed: %v", err)
	}

	if sessionId == "" {
		t.Error("session ID should not be empty")
	}

	// Verify session exists
	sess, err := mgr.GetSession(sessionId)
	if err != nil {
		t.Fatalf("GetSession failed: %v", err)
	}

	// Verify session is started
	if sess.Stopped() {
		t.Error("newly created session should not be stopped")
	}

	// Verify tokens were generated
	tokens := sess.FileTokens()
	if len(tokens) != 2 {
		t.Errorf("expected 2 tokens, got %d", len(tokens))
	}
}

// TestRecvSessManagerGetSession tests session retrieval
func TestRecvSessManagerGetSession(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	t.Run("returns error for non-existent session", func(t *testing.T) {
		_, err := mgr.GetSession("non-existent")
		if err == nil {
			t.Error("should return error for non-existent session")
		}
	})

	t.Run("returns session for valid ID", func(t *testing.T) {
		files := models.FileMetas{
			"file1": {Id: "file1", Filename: "test.txt", Size: 100},
		}
		sessionId, _ := mgr.NewSession(files, "192.168.1.1")

		sess, err := mgr.GetSession(sessionId)
		if err != nil {
			t.Fatalf("GetSession failed: %v", err)
		}
		if sess == nil {
			t.Error("session should not be nil")
		}
	})
}

// TestRecvSessManagerKillSession tests session termination
func TestRecvSessManagerKillSession(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	files := models.FileMetas{
		"file1": {Id: "file1", Filename: "test.txt", Size: 100},
	}
	sessionId, _ := mgr.NewSession(files, "192.168.1.1")

	// Verify session exists
	_, err := mgr.GetSession(sessionId)
	if err != nil {
		t.Fatalf("session should exist before kill")
	}

	// Kill the session
	mgr.KillSession(sessionId)

	// Verify session is gone
	_, err = mgr.GetSession(sessionId)
	if err == nil {
		t.Error("session should not exist after kill")
	}

	// Killing non-existent session should not panic
	mgr.KillSession("non-existent")
}

// TestRecvSessManagerHasActiveSessions tests active session detection
func TestRecvSessManagerHasActiveSessions(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	t.Run("returns false with no sessions", func(t *testing.T) {
		if mgr.HasActiveSessions() {
			t.Error("should return false with no sessions")
		}
	})

	t.Run("returns true with active session", func(t *testing.T) {
		files := models.FileMetas{
			"file1": {Id: "file1", Filename: "test.txt", Size: 100},
		}
		_, _ = mgr.NewSession(files, "192.168.1.1")

		if !mgr.HasActiveSessions() {
			t.Error("should return true with active session")
		}
	})

	t.Run("returns false after session ends", func(t *testing.T) {
		mgr2 := NewRecvSessManager()
		defer mgr2.Stop()

		files := models.FileMetas{
			"file1": {Id: "file1", Filename: "test.txt", Size: 100},
		}
		sessionId, _ := mgr2.NewSession(files, "192.168.1.1")
		sess, _ := mgr2.GetSession(sessionId)

		// End the session
		sess.End()

		if mgr2.HasActiveSessions() {
			t.Error("should return false after session ends")
		}
	})
}

// TestRecvSessManagerGeneratePreUploadResp tests pre-upload response generation
func TestRecvSessManagerGeneratePreUploadResp(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	files := models.FileMetas{
		"file1": {Id: "file1", Filename: "test.txt", Size: 100},
	}
	sessionId, _ := mgr.NewSession(files, "192.168.1.1")

	t.Run("generates valid response", func(t *testing.T) {
		resp, err := mgr.GeneratePreUploadResp(sessionId)
		if err != nil {
			t.Fatalf("GeneratePreUploadResp failed: %v", err)
		}

		if resp.SessionId != sessionId {
			t.Errorf("expected session ID %q, got %q", sessionId, resp.SessionId)
		}

		if len(resp.Tokens) != 1 {
			t.Errorf("expected 1 token, got %d", len(resp.Tokens))
		}

		if resp.Tokens["file1"] == "" {
			t.Error("token for file1 should not be empty")
		}
	})

	t.Run("returns error for non-existent session", func(t *testing.T) {
		_, err := mgr.GeneratePreUploadResp("non-existent")
		if err == nil {
			t.Error("should return error for non-existent session")
		}
	})
}

// TestRecvSessManagerVacuumTask tests automatic cleanup of stopped sessions
func TestRecvSessManagerVacuumTask(t *testing.T) {
	// Skip in short mode as this test requires waiting
	if testing.Short() {
		t.Skip("skipping vacuum task test in short mode")
	}

	t.Run("cleans up stopped sessions", func(t *testing.T) {
		mgr := NewRecvSessManager()
		mgr.Start()
		defer mgr.Stop()

		// Create a session
		files := models.FileMetas{
			"file1": {Id: "file1", Filename: "test.txt", Size: 100},
		}
		sessionId, _ := mgr.NewSession(files, "192.168.1.1")

		// Verify it exists
		_, err := mgr.GetSession(sessionId)
		if err != nil {
			t.Fatalf("session should exist")
		}

		// End the session (making it stopped)
		sess, _ := mgr.GetSession(sessionId)
		sess.End()

		// Wait for vacuum task to run (it runs every 5 seconds)
		// We wait a bit longer to ensure it has time to clean up
		time.Sleep(6 * time.Second)

		// Session should be cleaned up
		_, err = mgr.GetSession(sessionId)
		if err == nil {
			t.Error("stopped session should be cleaned up by vacuum task")
		}
	})
}

// TestRecvSessManagerConcurrency tests thread safety
func TestRecvSessManagerConcurrency(t *testing.T) {
	mgr := NewRecvSessManager()
	mgr.Start()
	defer mgr.Stop()

	const numGoroutines = 50
	var wg sync.WaitGroup
	wg.Add(numGoroutines * 3)

	sessionIds := make(chan string, numGoroutines)

	// Concurrent session creation
	for i := 0; i < numGoroutines; i++ {
		go func(idx int) {
			defer wg.Done()
			files := models.FileMetas{
				"file1": {Id: "file1", Filename: "test.txt", Size: 100},
			}
			id, err := mgr.NewSession(files, "192.168.1.1")
			if err != nil {
				t.Errorf("NewSession failed: %v", err)
				return
			}
			sessionIds <- id
		}(i)
	}

	// Wait a bit for sessions to be created
	time.Sleep(100 * time.Millisecond)

	// Concurrent session reads
	for i := 0; i < numGoroutines; i++ {
		go func() {
			defer wg.Done()
			mgr.HasActiveSessions()
		}()
	}

	// Concurrent session kills
	for i := 0; i < numGoroutines; i++ {
		go func() {
			defer wg.Done()
			select {
			case id := <-sessionIds:
				mgr.KillSession(id)
			default:
				// No session available, that's fine
			}
		}()
	}

	wg.Wait()
	close(sessionIds)
}

// TestRecvSessManagerMultipleSessions tests managing multiple sessions
func TestRecvSessManagerMultipleSessions(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	// Create multiple sessions
	var sessionIds []string
	for i := 0; i < 5; i++ {
		files := models.FileMetas{
			"file1": {Id: "file1", Filename: "test.txt", Size: 100},
		}
		id, err := mgr.NewSession(files, "192.168.1."+string(rune('1'+i)))
		if err != nil {
			t.Fatalf("NewSession failed: %v", err)
		}
		sessionIds = append(sessionIds, id)
	}

	// All sessions should be unique
	seen := make(map[string]bool)
	for _, id := range sessionIds {
		if seen[id] {
			t.Error("session IDs should be unique")
		}
		seen[id] = true
	}

	// All sessions should be retrievable
	for _, id := range sessionIds {
		_, err := mgr.GetSession(id)
		if err != nil {
			t.Errorf("GetSession(%s) failed: %v", id, err)
		}
	}

	// HasActiveSessions should be true
	if !mgr.HasActiveSessions() {
		t.Error("should have active sessions")
	}

	// Kill one session
	mgr.KillSession(sessionIds[0])

	// Other sessions should still exist
	for _, id := range sessionIds[1:] {
		_, err := mgr.GetSession(id)
		if err != nil {
			t.Errorf("GetSession(%s) failed after killing another session: %v", id, err)
		}
	}
}

func TestCreateSessionIfAllowed_ConcurrentSingleAdmission(t *testing.T) {
	mgr := NewRecvSessManager()
	defer mgr.Stop()

	files := models.FileMetas{
		"file1": {Id: "file1", Filename: "test.txt", Size: 100},
	}

	const workers = 40
	var wg sync.WaitGroup
	wg.Add(workers)

	var successCount int32
	var blockedCount int32

	for i := 0; i < workers; i++ {
		go func() {
			defer wg.Done()

			_, err := mgr.CreateSessionIfAllowed(files, "192.168.1.10")
			switch err {
			case nil:
				atomic.AddInt32(&successCount, 1)
			case constants.ErrBlockedByOthers:
				atomic.AddInt32(&blockedCount, 1)
			default:
				t.Errorf("unexpected error: %v", err)
			}
		}()
	}

	wg.Wait()

	if got := atomic.LoadInt32(&successCount); got != 1 {
		t.Fatalf("successful admissions = %d; want 1", got)
	}
	if got := atomic.LoadInt32(&blockedCount); got == 0 {
		t.Fatalf("blocked admissions = %d; want > 0", got)
	}
}
