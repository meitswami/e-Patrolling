# Instagram session files

`instagram_state.json` and `instagram_meta.json` are tracked in git so deploys (EC2, Hostinger VPS, portable builds) can reuse the same logged-in Instagram session without manual copy.

**Security**

- Keep this repository **private**. These files contain live session cookies.
- If the repo is ever leaked, disconnect Instagram in the app and reconnect to rotate cookies.
- Prefer GitHub Actions secrets `INSTAGRAM_STATE_B64` / `INSTAGRAM_META_B64` for production if you do not want sessions in git (the deploy workflow restores them when set).
