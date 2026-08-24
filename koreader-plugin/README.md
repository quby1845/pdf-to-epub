# PDF to EPUB Receiver for KOReader

This is the official KOReader receiver companion for PDF to EPUB OCR. It receives EPUB, MOBI,
PDF, and other allowed files directly over the local network. No cloud service is involved.

The receiver uses the open LocalSend v2.2 protocol, so it remains interoperable while being
built, versioned, documented, and released from the PDF to EPUB OCR repository.

## Install

1. Download the matching ZIP from the latest PDF to EPUB OCR release: `armv7` for current
   Kindle/Kobo/PocketBook/reMarkable 2 devices, `arm64` for ARM64 readers such as reMarkable
   Paper Pro, or `arm-legacy` for Kindle 3/DX and older ARM devices.
2. Close KOReader. Extract `pdf_to_epub_receiver.koplugin` into KOReader's `plugins` directory
   (`koreader/plugins` on Kindle or `.adds/koreader/plugins` on Kobo).
3. Confirm the final path contains `plugins/pdf_to_epub_receiver.koplugin/main.lua`, then restart
   KOReader completely.
4. Open **Menu → Network → PDF to EPUB Receiver** and choose the save directory.
5. Under **Settings**, keep **Allowed extensions (all)** and **Use HTTPS** enabled. Optionally set
   a PIN, enable **Start with KOReader**, or configure file type routing.
6. Return to the receiver menu and select **Start server**.
7. Keep the reader and computer on the same Wi-Fi network. Use **Send a file** for any existing
   file or **Send to KOReader** after a conversion, then approve the request on KOReader.

If automatic discovery is blocked by a VPN, guest network, or router setting, enter the
e-reader's IP address manually in the desktop app.

## Development

The Go receiver and KOReader Lua integration live together in this directory. Release builds
cross-compile the receiver for `arm-legacy`, `armv7`, and `arm64`, then package the Lua files and
licenses into architecture-specific ZIP files.

See `THIRD_PARTY_NOTICES.md` and `LICENSE.upstream` for attribution.
