// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C Markdown <-> WRT Converter
 * Bidirectional, high-performance Markdown and WRT syntax converter
 */

#ifndef WRT_MARKDOWN_H
#define WRT_MARKDOWN_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Returns 1 if text contains Markdown syntax markers, 0 otherwise */
int wrt_has_markdown(const char *text);

/* Converts Markdown text (or text containing mixed Markdown markers) into pure WRT format.
 * Existing WRT tags are preserved untouched. Caller must free returned string. */
char *wrt_markdown_to_wrt(const char *md_text);

/* Converts WRT format text to standard Markdown format. Caller must free returned string. */
char *wrt_to_markdown(const char *wrt_text);

/* File conversion helpers */
int wrt_md_to_wrt_file(const char *md_path, const char *wrt_path);
int wrt_wrt_to_md_file(const char *wrt_path, const char *md_path);

#ifdef __cplusplus
}
#endif

#endif /* WRT_MARKDOWN_H */
