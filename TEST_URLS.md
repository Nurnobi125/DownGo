# DownGo 4.0.7 QA URLs

## Official/current test endpoints
- PDF: https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf
- MP4: https://mdn.github.io/learning-area/html/multimedia-and-embedding/video-and-audio-content/rabbit320.mp4
- Large binary: https://fsn1-speed.hetzner.com/100MB.bin

## Local automated tests
Run `python QA_FILE_TYPES_4_0_4.py` to test PDF/MP3/MP4/ZIP/JPG/PNG/TXT using a local range-capable HTTP server.

Note: generic public MP3 hosts change frequently; the automated test uses a local deterministic MP3 fixture instead of relying on a third-party media host.
