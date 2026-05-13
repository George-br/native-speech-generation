# Changelog

## version 1.7.0

- Compatibility: Added support for NVDA 2026.1.
- Dependencies: Added verified, NVDA-version-aware library downloads that select `lib.zip` for older NVDA versions and `lib64.zip` for NVDA 2026.1 and newer.
- Dependencies: Added SHA-256 verification and safe archive extraction before replacing the add-on library folder.
- Speech Generation: Added `gemini-3.1-flash-tts-preview` as the default model.
- Speech Generation: Captured dialog values before background generation to avoid reading wx controls from worker threads.
- Speech Generation: Saved generated audio outside the add-on folder so runtime output is not bundled accidentally.
- Security: Fixed the Windows DPAPI ctypes fallback to keep input buffers alive during encryption and decryption.
- Maintenance: Removed the direct `requests` dependency, tightened package exclusions, and refreshed NVDA-style naming/type hints.

## version 1.6.0

- Security: Gemini API keys are now stored with Windows DPAPI instead of plaintext config.
- Stability: Preserved add-on configuration across updates so API keys are no longer wiped by uninstall/update flow.
- Deployment: Added `GEMINI_API_KEY` environment variable fallback for managed or institutional setups.
- Talk With AI: Migrated to `gemini-3.1-flash-live-preview` with the current Live API flow.
- Talk With AI: Replaced the memory UI with `No Thinking`, `Low`, `Medium`, and `High` reasoning controls.
- Talk With AI: Kept reconnect conversation continuity internally by replaying recent transcript history after reconnects.
- Talk With AI: Preserved style instructions as the Live API system instruction and kept optional Google Search grounding.
- Talk With AI: Improved streaming stability with better reconnection handling (backoff + retry) and adaptive audio buffering.
- UI: Simplified Generate Speech status behavior back to the standard `Generating...` flow.
- Documentation: Added Spanish-language documentation.
