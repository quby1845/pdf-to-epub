package signaling

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

func TestConnectWithContext_TruncatesHelloPeersToMax(t *testing.T) {
	upgrader := websocket.Upgrader{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer func() { _ = conn.Close() }()

		peers := make([]ClientInfo, 0, MaxPeers+25)
		for i := 0; i < MaxPeers+25; i++ {
			peers = append(peers, ClientInfo{
				ID:         uuid.New(),
				Alias:      fmt.Sprintf("peer-%d", i),
				Version:    "2.3",
				DeviceType: "desktop",
			})
		}

		hello := WsServerMessage{
			Type: "HELLO",
			Client: &ClientInfo{
				ID:         uuid.New(),
				Alias:      "self",
				Version:    "2.3",
				DeviceType: "desktop",
			},
			Peers: &peers,
		}

		_ = conn.WriteJSON(hello)
		time.Sleep(100 * time.Millisecond)
	}))
	defer server.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	info := NewClientInfo("test", "token")
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")
	client, err := ConnectWithContext(ctx, wsURL, info)
	if err != nil {
		t.Fatalf("ConnectWithContext failed: %v", err)
	}
	defer func() { _ = client.Close() }()

	if got := len(client.GetPeers()); got != MaxPeers {
		t.Fatalf("peer count = %d; want %d", got, MaxPeers)
	}
}

func TestConnectWithContext_RejectsOversizedHelloMessage(t *testing.T) {
	upgrader := websocket.Upgrader{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer func() { _ = conn.Close() }()

		hugeAlias := strings.Repeat("x", maxSignalingMessageBytes)
		hello := WsServerMessage{
			Type: "HELLO",
			Client: &ClientInfo{
				ID:         uuid.New(),
				Alias:      hugeAlias,
				Version:    "2.3",
				DeviceType: "desktop",
			},
		}

		payload, err := json.Marshal(hello)
		if err != nil {
			return
		}
		if len(payload) <= maxSignalingMessageBytes {
			return
		}
		_ = conn.WriteMessage(websocket.TextMessage, payload)
		time.Sleep(100 * time.Millisecond)
	}))
	defer server.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	info := NewClientInfo("test", "token")
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")
	if _, err := ConnectWithContext(ctx, wsURL, info); err == nil {
		t.Fatal("expected ConnectWithContext to fail for oversized HELLO message")
	}
}

func TestDecompressSDP_RejectsOversizedPayload(t *testing.T) {
	oversized := strings.Repeat("a", maxDecompressedSDPBytes+1)
	compressed, err := CompressSDP(oversized)
	if err != nil {
		t.Fatalf("CompressSDP failed: %v", err)
	}

	if _, err := DecompressSDP(compressed); err == nil {
		t.Fatal("expected oversized decompressed SDP to fail")
	}
}
