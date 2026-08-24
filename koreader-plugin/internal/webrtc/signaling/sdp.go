package signaling

import (
	"bytes"
	"compress/zlib"
	"encoding/base64"
	"fmt"
	"io"
)

const maxDecompressedSDPBytes = 512 * 1024

// CompressSDP compresses an SDP string using zlib and encodes it as base64.
// Uses URL-safe base64 without padding to match official LocalSend protocol.
func CompressSDP(sdp string) (string, error) {
	var buf bytes.Buffer
	w := zlib.NewWriter(&buf)
	if _, err := w.Write([]byte(sdp)); err != nil {
		return "", err
	}
	if err := w.Close(); err != nil {
		return "", err
	}
	// Use URL-safe base64 without padding (matches official Rust implementation)
	return base64.RawURLEncoding.EncodeToString(buf.Bytes()), nil
}

// DecompressSDP decodes base64 and decompresses a zlib-compressed SDP string.
// Uses URL-safe base64 without padding to match official LocalSend protocol.
func DecompressSDP(compressed string) (string, error) {
	// Use URL-safe base64 without padding (matches official Rust implementation)
	data, err := base64.RawURLEncoding.DecodeString(compressed)
	if err != nil {
		return "", err
	}

	r, err := zlib.NewReader(bytes.NewReader(data))
	if err != nil {
		return "", err
	}
	defer func() { _ = r.Close() }()

	result, err := io.ReadAll(io.LimitReader(r, maxDecompressedSDPBytes+1))
	if err != nil {
		return "", err
	}
	if len(result) > maxDecompressedSDPBytes {
		return "", fmt.Errorf("decompressed SDP exceeds %d bytes", maxDecompressedSDPBytes)
	}

	return string(result), nil
}
