# DownGo 4.0 QA / Microsoft Store certification checklist

## URL/Add URL
- [ ] Valid HTTPS direct file URL adds without an immediate UI error.
- [ ] HTTP URL works where the server permits it.
- [ ] Redirected URL resolves.
- [ ] `Content-Disposition` filename is used.
- [ ] URLs containing query strings are handled.
- [ ] Invalid URL is rejected before creating a task.
- [ ] HTML/media page produces a clear message or resolves through supported yt-dlp extractor.
- [ ] Expired/403/404/429 URLs show actionable errors instead of an unhandled exception.

## Download engine
- [ ] 1, 4, 8 and 16 connections tested with a server supporting byte ranges.
- [ ] Server without Range falls back to single connection.
- [ ] Pause/resume works.
- [ ] Interrupted multi-part download resumes from `.parts` files.
- [ ] Each byte-range response is validated with `206` and `Content-Range`.
- [ ] Failed connections retry up to 4 attempts.
- [ ] SHA-256 matches the source file.
- [ ] Downloaded files are stored under a safe, normalized filename.
- [ ] Aggregate speed limit works across connections.

## Windows
- [ ] Windows 10 22H2 clean VM.
- [ ] Windows 11 clean VM.
- [ ] Non-admin install works.
- [ ] App can be closed to tray and exited cleanly.
- [ ] Startup option works.
- [ ] Browser bridge only listens on 127.0.0.1.
- [ ] Windows Defender scan is optional and does not block normal downloads when Defender is unavailable.

## Store
- [ ] Test with the exact package intended for submission.
- [ ] No developer mode or test license is enabled in the release build.
- [ ] Privacy Policy URL is live and accurate.
- [ ] Store screenshots show working Add URL flow.
- [ ] App description does not promise unsupported features.
- [ ] All third-party licenses/notices are included where required.
