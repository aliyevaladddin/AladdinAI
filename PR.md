## 📝 Summary

Introduces a **Visual editing mode** for WRT (Word Rich Text) documents in the AladdinAI Dashboard. Users no longer need to edit raw WRT markup (`[b]`, `[i]`, …) — they get a word-processor-like experience, while WRT remains the canonical format for agents and backend storage.

## 🏷️ Type of Change

- [ ] 🐛 Bug fix
- [x] ✨ New feature
- [ ] 💥 Breaking change
- [x] 🎨 UI / UX
- [ ] ♻️ Refactor
- [x] 📚 Documentation
- [x] ✅ Tests

## 🔗 Related

- ADR: `docs/adr/0014-*.md`
- Issue: closes #___

## 🔧 Changes

### Frontend
- **Visual Editor** — `contentEditable` surface rendering WRT as formatted HTML.
- **Bi-directional sync** — `wrtToEditableHtml` / `editableElementToWrt` keep the visual DOM and WRT source in sync.
- **Mode toggle** — Visual / Code switch keeps advanced WRT control accessible.

### UI / UX
- Centered document canvas (`max-w-3xl`) for readability.
- Version History and Audit Timeline moved into a collapsible right-hand drawer.

### Tests & Docs
- Unit tests: `frontend/src/__tests__/wrt.test.ts`.
- ADR 0014 documents the architectural decision.

## 📸 Screenshots

| Before | After |
|--------|-------|
| _screenshot_ | _screenshot_ |

## 🧪 How to Test

```bash
# Frontend unit tests (59 tests)
cd frontend && npm test

# Backend workspace integrity
pytest backend/tests/test_files_workspace.py
```

**Manual:**
1. Open a document in the Dashboard.
2. Edit in **Visual** mode (bold, italic, lists) → save.
3. Switch to **Code** mode → verify WRT markup is correct.
4. Open the drawer → verify Version History and Audit Timeline.

## ✅ Checklist

- [x] Code follows project style guidelines
- [x] Self-review completed
- [x] Tests added / updated and passing
- [x] Documentation updated (ADR 0014)
- [x] No new warnings or console errors
- [ ] Screenshots attached
- [ ] Linked issue

## ⚠️ Notes for Reviewers

- WRT stays the single source of truth — HTML is only a view layer.
- Pay attention to edge cases in `editableElementToWrt` (nested formatting, paste from external sources).
