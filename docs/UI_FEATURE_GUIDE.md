# 🎨 AladdinAI — UI/UX, Command Palette & Chat Architecture Documentation

This document provides a comprehensive technical overview of the modern UI/UX enhancements, the global **Command Palette (`Cmd+K`)**, keyboard shortcuts registry, and the modular chat component architecture implemented in AladdinAI.

---

## 📑 Table of Contents
1. [Overview & New Dependencies](#1-overview--new-dependencies)
2. [Global Command Palette (`Cmd+K`) & Registry](#2-global-command-palette-cmdk--registry)
3. [Modular Chat Architecture (Decomposed `chat/page.tsx`)](#3-modular-chat-architecture)
4. [Real-Time Streaming & Thinking Process UX](#4-real-time-streaming--thinking-process-ux)
5. [Telegram-Style Voice Player & Media Attachments](#5-telegram-style-voice-player--media-attachments)
6. [GFM Markdown Tables Auto-Parsing](#6-gfm-markdown-tables-auto-parsing)
7. [Global Fluidity & Smooth Animations](#7-global-fluidity--smooth-animations)
8. [Chat Session UX Improvements](#8-chat-session-ux-improvements)
9. [Orders & Product Catalog UI](#9-orders--product-catalog-ui)

---

## 1. Overview & New Dependencies

The frontend architecture was enhanced with modern production libraries to elevate performance, responsiveness, and developer experience:

| Package | Version | Purpose |
| :--- | :--- | :--- |
| **`cmdk`** | `^1.1.1` | Fast, accessible command palette engine powered by Vercel |
| **`framer-motion`** | `^12.42.2` | Fluid physics-based micro-animations and modal transitions (`AnimatePresence`) |
| **`canvas-confetti`** | `^1.9.4` | Particle celebration animations for goal completions and shortcuts |
| **`@tanstack/react-table`** | `^8.21.3` | Headless, virtualized data tables for CRM pipeline and agent logging |
| **`@monaco-editor/react`** | `^4.7.0` | Browser-based VS Code editor component for code artifact viewing |

---

## 2. Global Command Palette (`Cmd+K`) & Registry

AladdinAI features a keyboard-first **Command Palette** accessible from anywhere in the application by pressing `Cmd + K` (Mac) or `Ctrl + K` (Windows/Linux).

### Key Files:
- **`src/lib/commands-registry.ts`**: The central registry defining all commands across 5 categories:
  - 💬 **Navigation**: AI Chat (`Alt+1`), Agents (`Alt+2`), CRM (`Alt+3`), Analytics (`Alt+4`), Settings (`Alt+5`).
  - 🤖 **AI & Agents**: Start New Chat (`Alt+N`), Create Custom Agent (`Alt+A`), Toggle Voice Reply (`Alt+V`).
  - 👥 **CRM & Sales**: Add Lead (`Alt+L`), Export CRM Data (`Alt+E`).
  - ⚡ **Developer & System**: Toggle Terminal Drawer (`Alt+T`), Copy JWT Token (`Alt+K`), Flush API Cache (`Alt+R`).
  - 🎉 **Fun & Utilities**: Celebrate Achievement (`Alt+C`), Keyboard Shortcuts Guide (`Alt+H`).
- **`src/components/CommandPalette.tsx`**: Modal dialog executing fuzzy search, filtering, shortcut badges, and actions.
- **`src/components/settings/ShortcutsSettings.tsx`**: Dedicated documentation tab located in `/dashboard/settings?tab=shortcuts`.

---

## 3. Modular Chat Architecture

The original `chat/page.tsx` monolith (1,650+ lines) has been decomposed into 5 modular, single-responsibility files located directly in `src/app/(dashboard)/dashboard/chat/`:

```
src/app/(dashboard)/dashboard/chat/
├── VoicePlayer.tsx      # Autonomous Telegram-style dark glass audio player
├── AuthAttachment.tsx   # JWT-authenticated image, audio & document previews
├── ChatMessageItem.tsx  # Message bubble, markdown, GFM tables & action bars
├── ChatSidebar.tsx      # History sidebar, agent dropdown & search filter
└── page.tsx             # Lean page controller (~500 lines) managing SSE streams
```

---

## 4. Real-Time Streaming & Thinking Process UX

- **Inline Pulsing Cursor (`▋`)**: Attached directly to the end of live assistant streams for instant visual feedback.
- **Inline Status Indicator (`Thinking •`)**: Replaces heavy loading boxes with a compact status pill displaying active execution thoughts with a pulsing neon dot.
- **`<think>` Tag Stripping**: `parseThoughtsAndCleanText` utility extracts closed/unclosed `<think>` blocks into an interactive "Thought Process" accordion while keeping raw XML tags out of user messages.
- **Send ➔ Stop Button Morphing**: Morphs the submit button into a pulsing red Stop button (`Square`) during streaming, linked to an `AbortController`.
- **Message Action Control Bars**:
  - **User Messages**: `✏️ Edit` (reloads prompt text into textarea) and `📋 Copy` prompt buttons.
  - **Assistant Messages**: `📋 Copy` response button alongside feedback controls (`ThumbsUp`/`ThumbsDown`).

---

## 5. Telegram-Style Voice Player & Media Attachments

- **`VoicePlayer.tsx`**: Autonomous `#11111a` dark glass card with neon-violet equalizer bars (`bg-violet-400`), duration timestamps, seeking bar, and play/pause state. 100% readable in Light & Dark themes.
- **Compact Input Thumbnails**: `AuthAttachment` supports a `compact` mode rendering pending prompt file previews as clean `64x64px` thumbnails in the toolbar.

---

## 6. GFM Markdown Tables Auto-Parsing

- **`parseMarkdownTables`**: Automatically detects Markdown tables (even when LLMs stream rows without newlines), repairs missing row breaks (`|\n|`), and renders responsive, styled HTML tables with hover highlights.

---

## 7. Global Fluidity & Smooth Animations

- **Smooth Scrolling & Font Antialiasing**: Configured in `globals.css` with custom rounded glass scrollbars (`::-webkit-scrollbar`).
- **300ms Smooth Sidebar Collapse**: The history sidebar smoothly animates its width (`w-72` ➔ `w-0`) and opacity (`opacity-100` ➔ `opacity-0`) over 300ms without layout jumps.
- **Route Fade-In**: Applied `.smooth-fade-in` transition utility across main dashboard routes.

---

## 8. Chat Session UX Improvements

- **Session rename**: hover a session in `ChatSidebar` ➔ pencil icon reveals an inline input (`Enter`/blur saves, `Esc` cancels), backed by `PATCH /api/chat/sessions/{id}`.
- **Auto-title from first message**: new sessions are named from the first user message (first 60 characters), with fallbacks — `Voice message` for audio, `Image` for image-only prompts, `Attachment` for other files.
- **Regenerate last reply**: a `RotateCw` button on the last assistant message re-sends the last user prompt. The old reply is kept on purpose — thumbs up/down feedback on it is labeled training data for the self-forging loop.
- **Smart scroll + scroll-down button**: the feed auto-scrolls only while the reader is pinned to the bottom; scrolling up to review history keeps the position, and a floating `ArrowDown` button appears to jump back down.
- **Per-session input drafts**: unfinished composer text persists to `localStorage` per session (including the new-chat composer) and is restored when the session is reopened.

Key files: `ChatSidebar.tsx` (rename), `ChatMessageItem.tsx` (regenerate), `page.tsx` (scroll, drafts, auto-title), backend `app/routers/chat.py` (`PATCH /sessions/{id}`, `_auto_session_title`).

---

## 9. Orders & Product Catalog UI

The `/dashboard/orders` page is split into two tabs:

- **Orders** — metrics band, new-order form (only *active* catalog products are listed, with a hint linking to the catalog when none exist), per-order status dropdown offering legal next-states only.
- **Product Catalog** (`ProductsCatalog.tsx`) — full catalog management without leaving the page:
  - Instant client-side search by SKU or name
  - Add/edit form (SKU, name, price, currency, description, active flag) with inline validation; backend errors such as a duplicate SKU surface inside the form instead of a raw alert
  - Row actions: edit, activate/deactivate, delete (with a confirmation noting that placed orders keep their item snapshots)
  - Active/Inactive status badges; inactive rows are dimmed

Deleting a product that appears in placed orders detaches the reference (`order_items.product_id` ➔ `null`) instead of failing on the foreign key — order lines keep their snapshotted name and price. See `docs/guides/ORDERS.md` for the snapshot design.
