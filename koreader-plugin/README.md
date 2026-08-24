# PDF to EPUB Receiver for KOReader

This is the official KOReader receiver companion for PDF to EPUB OCR. It receives EPUB, MOBI,
PDF, and other allowed files directly over the local network. No cloud service is involved.

The receiver uses the open LocalSend v2.2 protocol, so it remains interoperable while being
built, versioned, documented, and released from the PDF to EPUB OCR repository.

## Install

1. Download the ZIP matching the e-reader from the latest PDF to EPUB OCR release:
   - `armv7`: current Kindle, Kobo, PocketBook, and reMarkable 2 devices.
   - `arm64`: reMarkable Paper Pro and other ARM64 KOReader devices.
   - `arm-legacy`: Kindle 3, Kindle DX, and older ARM devices.
2. Extract `pdf_to_epub_receiver.koplugin` into KOReader's `plugins` directory.
3. Restart KOReader.
4. Open **Menu → Network → PDF to EPUB Receiver**, choose the save directory, and select
   **Start server**.
5. Keep the e-reader and computer on the same Wi-Fi network, then use **Send to KOReader** in
   PDF to EPUB OCR.

If automatic discovery is blocked by a VPN, guest network, or router setting, enter the
e-reader's IP address manually in the desktop app.

## Development

The Go receiver and KOReader Lua integration live together in this directory. Release builds
cross-compile the receiver for `arm-legacy`, `armv7`, and `arm64`, then package the Lua files and
licenses into architecture-specific ZIP files.

See `THIRD_PARTY_NOTICES.md` and `LICENSE.upstream` for attribution.
