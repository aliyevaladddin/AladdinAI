# PR: WRT Editor Visual Mode

## Description
This Pull Request introduces a **Visual editing mode** for WRT (Word Rich Text) documents in the AladdinAI Dashboard. Previously, users had to manage raw WRT markup (`[b]`, `[i]`, etc.) directly. This change provides a familiar, word-processor-like experience while maintaining the canonical WRT format for agents and backend storage.

## Key Changes
- **Visual Editor:** Added a `contentEditable` surface that renders WRT as formatted HTML.
- **Bi-directional Sync:** Implemented `wrtToEditableHtml` and `editableElementToWrt` to synchronize the visual DOM with the canonical WRT source.
- **UI Redesign:**
    - Centered the document canvas (`max-w-3xl`) for better readability.
    - Moved Version History and Audit Timeline into a collapsible right-hand drawer.
    - Added a mode toggle (Visual / Code) to keep advanced WRT control accessible.
- **Infrastructure:**
    - Added comprehensive unit tests in `frontend/src/__tests__/wrt.test.ts`.
    - Added ADR 0014 to document the architectural decision.

## Verification
- Run `npm test` in the `frontend` directory to ensure all 59 tests pass.
- Run `pytest backend/tests/test_files_workspace.py` to confirm workspace integrity.
- Verified manual document editing, saving, and version history in the browser.

## Checklist
- [x] Visual mode implemented
- [x] Bi-directional WRT ↔ HTML parser working
- [x] Centered UI/UX design implemented
- [x] Side drawer for versions/timeline
- [x] Unit tests passing
- [x] Documentation updated (including ADR 0014)
