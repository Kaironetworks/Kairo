# KAIRO Runtime Hotfix 2

- Removed the global Live Trust Signal rail from the application shell. It was a persistent inline status surface that could overflow/clamp on narrower layouts and visually compete with page content.
- System health is no longer polled on every page load. Operational status remains available through the dedicated system/trust surfaces.
- Removed remaining responsive references to the deleted rail.
- Current page is persisted in `localStorage` under `kairo_page`, so a browser refresh keeps the active KAIRO page instead of returning to Dashboard.
- Logout clears the remembered page and returns to the login screen.
- This is a UX/runtime correction; backend behavior is unchanged.
