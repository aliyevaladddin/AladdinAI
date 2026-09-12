// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C PPTX <-> WRT Converter
 * High-performance bidirectional converter between PowerPoint .pptx and .wrt
 */

#ifndef WRT_PPTX_H
#define WRT_PPTX_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Convert in-memory .pptx bytes to WRT text format (caller frees returned string) */
char *pptx_to_wrt(const unsigned char *pptx_data, size_t pptx_len);

/* Convert in-memory WRT text to .pptx binary bytes (caller frees returned buffer, out_len set) */
unsigned char *wrt_to_pptx(const char *wrt_text, size_t *out_len);

/* File-based CLI helpers */
int pptx_to_wrt_file(const char *pptx_path, const char *wrt_path);
int wrt_to_pptx_file(const char *wrt_path, const char *pptx_path);

#ifdef __cplusplus
}
#endif

#endif /* WRT_PPTX_H */
