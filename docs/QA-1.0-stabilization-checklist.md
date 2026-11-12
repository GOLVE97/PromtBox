# PromptBox 1.0 — Stabilization checklist

This checklist is for the `release/1.0-stabilization` branch. Version 0.5.0 remains the known-good baseline on `main`. Do not merge or publish until the checks below pass.

## Findings addressed in this branch

- [x] Include user-created categories in the New Prompt and Edit Prompt category selectors.
- [x] Prevent duplicate custom category names regardless of letter case (for example, `Ideas` and `ideas`).
- [x] Keep custom category names sorted after creation.

## Manual regression checks on Windows

### Data safety
- [ ] Launch with an existing PromptBox 0.5 database; confirm all prompts, timestamps, tags, categories, and favorites remain.
- [ ] Create, edit, and delete a prompt; restart the app and confirm the expected state.
- [ ] Export JSON, import it into a test profile, and verify prompt text, category, tags, and favorite state.
- [ ] Try importing malformed JSON; confirm an error is shown and existing data remains unchanged.
- [ ] Confirm the database remains under `%LOCALAPPDATA%\PromptBox\prompts.db` (the app currently uses `%USERPROFILE%\AppData\Local\PromptBox\prompts.db`).

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
- [ ] Build through GitHub Actions from this branch.
- [ ] Download and extract the artifact on Windows.
- [ ] Launch the EXE on a machine/profile without Python installed, if available.
- [ ] Confirm app icon, logo, and database persistence.
- [ ] Confirm Windows SmartScreen behavior is documented; the EXE is not code-signed.

## Release gates

- No known data-loss or startup defects.
- All manual regression checks completed.
- Build workflow succeeds from the stabilization branch.
- README, changelog, and version number updated together for the final 1.0 release.
- Release remains unpublished until explicitly approved.
