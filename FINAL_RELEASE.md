# KAIRO Final Production Candidate

This package is a complete KAIRO project tree, not an overlay patch.

## Core stabilization
- Fixed evidence ingestion modal state bug that caused uploads to fail at the UI layer.
- Added client-side upload validation and clearer API/network errors.
- Added request timeout handling and automatic session invalidation on HTTP 401.
- Logout now clears the authenticated session and resets navigation.
- Default UI theme is light, with persistent light/dark switching.
- Added a restrained live trust-status rail for the operations console.
- Navigation is role-aware so users do not see controls their role cannot use.
- Backend evidence/version writes now clean up object-storage writes if the database transaction fails.
- Fabric Gateway launcher resolves the real WSL Fabric samples tree automatically.

## Core principle
KAIRO remains a government/legal investigation operations console: direct authenticated access, no sales/product/pricing surfaces.

## Important
The Hyperledger Fabric network is intentionally not started by the application. Start it only when you are ready to verify the blockchain anchor path. The core KAIRO application remains independently usable.
