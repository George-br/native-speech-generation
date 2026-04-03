# Changelog

## version 1.5.6

- Security: Gemini API keys are now stored with Windows DPAPI instead of plaintext config.
- Stability: Preserved add-on configuration across updates so API keys are no longer wiped by uninstall/update flow.
- Deployment: Added `GEMINI_API_KEY` environment variable fallback for managed or institutional setups.
- Talk With AI: Added optional session memory to keep temporary conversation context during an active voice session.
- Talk With AI: Added a clear-memory control to reset temporary session context on demand.
- Talk With AI: Improved streaming stability with better reconnection handling (backoff + retry) and adaptive audio buffering.
- UI: Simplified Generate Speech status behavior back to the standard `Generating...` flow.
- Documentation: Added Spanish-language documentation.
