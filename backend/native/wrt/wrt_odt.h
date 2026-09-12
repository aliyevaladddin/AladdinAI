// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C ODT <-> WRT Converter
 * High-performance bidirectional converter between OpenDocument .odt and .wrt
 */

#ifndef WRT_ODT_H
#define WRT_ODT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Convert in-memory .odt bytes to WRT text format (caller frees returned string) */
char *odt_to_wrt(const unsigned char *odt_data, size_t odt_len);

/* Convert in-memory WRT text to .odt binary bytes (caller frees returned buffer, out_len set) */
unsigned char *wrt_to_odt(const char *wrt_text, size_t *out_len);

/* File-based CLI helpers */
int odt_to_wrt_file(const char *odt_path, const char *wrt_path);
int wrt_to_odt_file(const char *wrt_path, const char *odt_path);

#ifdef __cplusplus
}
#endif

#endif /* WRT_ODT_H */
