package localsend

import (
	"bytes"
	"testing"
)

func TestNonceCacheBasicOps(t *testing.T) {
	cache := NewNonceCache(3)

	// Test Put and Get
	nonce1 := []byte("nonce1")
	cache.Put("client1", nonce1)

	retrieved, found := cache.Get("client1")
	if !found {
		t.Fatal("expected to find client1")
	}
	if !bytes.Equal(retrieved, nonce1) {
		t.Errorf("expected %v, got %v", nonce1, retrieved)
	}

	// Test Get non-existent
	_, found = cache.Get("nonexistent")
	if found {
		t.Error("expected not to find nonexistent client")
	}

	// Test Update existing
	nonce1Updated := []byte("nonce1-updated")
	cache.Put("client1", nonce1Updated)

	retrieved, found = cache.Get("client1")
	if !found {
		t.Fatal("expected to find client1 after update")
	}
	if !bytes.Equal(retrieved, nonce1Updated) {
		t.Errorf("expected %v, got %v", nonce1Updated, retrieved)
	}
}

func TestNonceCacheLRUEviction(t *testing.T) {
	cache := NewNonceCache(3)

	// Fill cache to capacity
	cache.Put("client1", []byte("nonce1"))
	cache.Put("client2", []byte("nonce2"))
	cache.Put("client3", []byte("nonce3"))

	// All should be present
	for i := 1; i <= 3; i++ {
		clientID := string(rune('0' + i))
		clientID = "client" + clientID
		if _, found := cache.Get(clientID); !found {
			t.Errorf("expected to find %s", clientID)
		}
	}

	// Add one more - should evict client1 (least recently used)
	cache.Put("client4", []byte("nonce4"))

	// client1 should be evicted
	if _, found := cache.Get("client1"); found {
		t.Error("client1 should have been evicted")
	}

	// Others should still be present
	for i := 2; i <= 4; i++ {
		clientID := string(rune('0' + i))
		clientID = "client" + clientID
		if _, found := cache.Get(clientID); !found {
			t.Errorf("expected to find %s", clientID)
		}
	}

	// Test LRU ordering: access client2 to make it most recent
	cache.Get("client2")

	// Add client5 - should evict client3 (now least recent)
	cache.Put("client5", []byte("nonce5"))

	if _, found := cache.Get("client3"); found {
		t.Error("client3 should have been evicted")
	}

	// client2, client4, client5 should remain
	expectedPresent := []string{"client2", "client4", "client5"}
	for _, clientID := range expectedPresent {
		if _, found := cache.Get(clientID); !found {
			t.Errorf("expected to find %s", clientID)
		}
	}
}

func TestNonceCacheDelete(t *testing.T) {
	cache := NewNonceCache(5)

	// Add some entries
	cache.Put("client1", []byte("nonce1"))
	cache.Put("client2", []byte("nonce2"))
	cache.Put("client3", []byte("nonce3"))

	// Verify all exist
	for _, id := range []string{"client1", "client2", "client3"} {
		if _, found := cache.Get(id); !found {
			t.Errorf("expected to find %s before delete", id)
		}
	}

	// Delete client2
	cache.Delete("client2")

	// Verify client2 is gone
	if _, found := cache.Get("client2"); found {
		t.Error("client2 should have been deleted")
	}

	// Verify others still exist
	if _, found := cache.Get("client1"); !found {
		t.Error("client1 should still exist after deleting client2")
	}
	if _, found := cache.Get("client3"); !found {
		t.Error("client3 should still exist after deleting client2")
	}

	// Delete non-existent key (should not panic)
	cache.Delete("nonexistent")

	// Delete already deleted key (should not panic)
	cache.Delete("client2")

	// Add new entry after deletion - capacity should not be affected
	cache.Put("client4", []byte("nonce4"))
	cache.Put("client5", []byte("nonce5"))

	// We now have client1, client3, client4, client5 (4 entries, capacity 5)
	if _, found := cache.Get("client1"); !found {
		t.Error("client1 should still exist")
	}
	if _, found := cache.Get("client4"); !found {
		t.Error("client4 should exist")
	}
	if _, found := cache.Get("client5"); !found {
		t.Error("client5 should exist")
	}
}
