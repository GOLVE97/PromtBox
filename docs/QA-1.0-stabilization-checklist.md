# PromptBox 1.0 — Stabilization checklist

This checklist is for the `release/1.0-stabilization` branch. Version 0.5.0 remains the known-good baseline on `main`. Do not merge or publish until the required checks pass and the destination is confirmed.

## Findings addressed in this branch

- [x] Include user-created categories in the New Prompt and Edit Prompt category selectors.
- [x] Prevent duplicate category names regardless of letter case when creating, renaming, editing, or importing.
- [x] Preserve empty custom categories across restart and JSON backup/restore.
- [x] Keep deleted or renamed default categories hidden across restart.
- [x] Sanitize settings and replace JSON files atomically.
- [x] Reject malformed backup roots and skip malformed prompt fields without changing existing prompts.

## Automated verification

- [x] Run the complete unit suite on the stabilization working copy (17 tests passed locally).
- [x] Build the Windows executable from the same source tree with `build.bat` (Windows 11 x64, Python 3.15.2, PyInstaller 6.22.3).
- [x] Start the resulting executable with an isolated profile and confirm it creates `AppData\Local\PromptBox\prompts.db` (12,288 bytes).
- [x] Confirm `main` is unchanged; stabilization is five commits ahead of the 0.5.0 baseline at the time this checklist was written.

### Local build evidence (2026-11-12)

- Portable EXE SHA-256: `0255E8AE162CE4751938B1B3C6DA61A4960AA0F2E4C76915EA9B622E24CAC308`.
- PyInstaller reported optional Unix-only modules and optional `darkdetect`; the Windows build completed and the isolated-profile app window opened.
- The temporary test profile is separate from the user profile and ignored by Git.

## Publishing destination

- [x] Verify the exact destination and account: `https://tinydock.pro`, signed-in profile `@golve97`. TinyDock is a project directory, not an executable host.
- [x] Inspect the listing form: title (120 chars), summary (300), description (10,000), up to 10 comma-separated tags, platform, category, website/demo/repository/download/license fields, cover and optional icon/gallery. TinyDock terms say projects link externally and TinyDock does not host or distribute executables.
- [ ] Publish a stable public download URL for the ZIP and ensure the public repository points to the final stabilization commit.
- [ ] Confirm the listing copy and assets, then obtain explicit approval before submitting publicly.

## Manual regression checks on Windows

### Data safety
- [ ] Launch with an existing PromptBox 0.5 database; confirm all prompts, timestamps, tags, categories, and favorites remain.
- [ ] Create, edit, and delete a prompt; restart the app and confirm the expected state.
- [ ] Export JSON, import it into a test profile, and verify prompt text, category, tags, and favorite state.
- [ ] Try importing malformed JSON; confirm an error is shown and existing data remains unchanged.
- [ ] Confirm the database remains under `%USERPROFILE%\AppData\Local\PromptBox`.

### Categories
- [ ] Create a custom category and confirm it appears in the library filter and both prompt editor dialogs.
- [ ] Try creating the same category with different capitalization; it should be rejected.
- [ ] Rename an empty custom category and confirm it remains available.
- [ ] Delete a category with prompts; confirm prompts move to General without being deleted.
- [ ] Confirm General cannot be deleted.

### User experience
- [ ] Verify light and dark themes; verify automatic theme behavior on Windows.
- [ ] Verify search by title, content, and tags.
- [ ] Verify favorites view and favorite toggle.
- [ ] Verify copy-to-clipboard feedback.
- [ ] Verify dialogs can be cancelled without saving unintended changes.
- [ ] Verify app closes cleanly and can reopen the database.

### Windows executable
- [ ] Build through GitHub Actions from the final stabilization commit.
- [ ] Download and extract the artifact on Windows.
- [ ] Launch the EXE on a machine/profile without Python installed, if available.
- [ ] Confirm app icon, logo, and database persistence.
- [x] Document that the portable EXE is unsigned and may trigger a Windows SmartScreen warning.

## Release gates

- No known data-loss or startup defects.
- All manual regression checks completed.
- Build workflow succeeds from the stabilization branch.
- README, changelog, and version number updated together for the final 1.0 release.
- Package type matches the confirmed distribution portal.
- Release remains unpublished until explicitly approved.