package localsend

import (
	"container/list"
	"sync"
)

// NonceCache implements a thread-safe LRU cache for storing client nonces.
// Used in v3 protocol to cache nonces exchanged during authentication.
type NonceCache struct {
	capacity int
	mu       sync.Mutex
	cache    map[string]*list.Element
	lru      *list.List
}

// cacheEntry represents an entry in the LRU cache.
type cacheEntry struct {
	clientID string
	nonce    []byte
}

// NewNonceCache creates a new NonceCache with the specified capacity.
// When the cache exceeds capacity, the least recently used entry is evicted.
func NewNonceCache(capacity int) *NonceCache {
	return &NonceCache{
		capacity: capacity,
		cache:    make(map[string]*list.Element),
		lru:      list.New(),
	}
}

// Put stores a nonce for the given clientID.
// If the clientID already exists, its nonce is updated and moved to the front.
// If the cache is at capacity, the least recently used entry is evicted.
// The nonce is copied to prevent the caller from modifying the cached value.
func (nc *NonceCache) Put(clientID string, nonce []byte) {
	nc.mu.Lock()
	defer nc.mu.Unlock()

	// Make defensive copy to prevent caller from modifying cached value
	nonceCopy := make([]byte, len(nonce))
	copy(nonceCopy, nonce)

	// If entry exists, update it and move to front
	if elem, exists := nc.cache[clientID]; exists {
		nc.lru.MoveToFront(elem)
		if entry, ok := elem.Value.(*cacheEntry); ok {
			entry.nonce = nonceCopy
		}
		return
	}

	// Add new entry
	entry := &cacheEntry{
		clientID: clientID,
		nonce:    nonceCopy,
	}
	elem := nc.lru.PushFront(entry)
	nc.cache[clientID] = elem

	// Evict oldest if over capacity
	if nc.lru.Len() > nc.capacity {
		oldest := nc.lru.Back()
		if oldest != nil {
			nc.lru.Remove(oldest)
			if entry, ok := oldest.Value.(*cacheEntry); ok {
				delete(nc.cache, entry.clientID)
			}
		}
	}
}

// Get retrieves the nonce for the given clientID.
// Returns the nonce and true if found, nil and false otherwise.
// Accessing an entry moves it to the front (most recently used).
// The returned nonce is a copy to prevent the caller from modifying the cached value.
func (nc *NonceCache) Get(clientID string) ([]byte, bool) {
	nc.mu.Lock()
	defer nc.mu.Unlock()

	elem, exists := nc.cache[clientID]
	if !exists {
		return nil, false
	}

	nc.lru.MoveToFront(elem)
	if entry, ok := elem.Value.(*cacheEntry); ok {
		// Return defensive copy to prevent caller from modifying cached value
		result := make([]byte, len(entry.nonce))
		copy(result, entry.nonce)
		return result, true
	}
	return nil, false
}

// Delete removes the nonce for the given clientID.
func (nc *NonceCache) Delete(clientID string) {
	nc.mu.Lock()
	defer nc.mu.Unlock()

	if elem, exists := nc.cache[clientID]; exists {
		nc.lru.Remove(elem)
		delete(nc.cache, clientID)
	}
}
