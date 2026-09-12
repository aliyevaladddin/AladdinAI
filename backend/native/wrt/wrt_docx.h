// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C DOCX <-> WRT Converter
 * High-performance bidirectional converter between Word .docx and .wrt
 */

#ifndef WRT_DOCX_H
#define WRT_DOCX_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Convert in-memory .docx bytes to WRT text format (caller frees returned string) */
char *docx_to_wrt(const unsigned char *docx_data, size_t docx_len);

/* Convert in-memory WRT text to .docx binary bytes (caller frees returned buffer, out_len set) */
unsigned char *wrt_to_docx(const char *wrt_text, size_t *out_len);

/* File-based CLI helpers */
int docx_to_wrt_file(const char *docx_path, const char *wrt_path);
int wrt_to_docx_file(const char *wrt_path, const char *docx_path);

#ifdef __cplusplus
}
#endif

#endif /* WRT_DOCX_H */
