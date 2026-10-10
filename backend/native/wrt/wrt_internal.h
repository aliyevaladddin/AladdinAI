// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Internal declarations shared between engine source files
 */

#ifndef WRT_INTERNAL_H
#define WRT_INTERNAL_H

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>
#include <strings.h>

/* ============================================================
 * BUFFER UTILITIES (Dynamic String Builder)
 * ============================================================ */

/* str_buf_t is defined in wrt_internal.h */
typedef struct {
    char *data;
    size_t len;
    size_t cap;
} str_buf_t;

/* Initialize a buffer */
void buf_init(str_buf_t *b);

/* Append a length-limited string */
void buf_append_len(str_buf_t *b, const char *s, size_t n);

/* Append a null-terminated string */
void buf_append(str_buf_t *b, const char *s);

/* Append a single character */
void buf_append_c(str_buf_t *b, char c);

/* Append escaped HTML characters */
void buf_append_escaped_html(str_buf_t *b, const char *s, size_t n);

/* ============================================================
 * TAG SPECIFICATION
 * ============================================================ */

/* Valid WRT tag names */
extern const char *VALID_TAGS[];

/* Check if a tag name is valid */
int is_known_tag(const char *tag);

/* ============================================================
 * JSON SERIALIZATION & PARSING HELPERS
 * ============================================================ */

/* Append JSON-escaped string */
void buf_append_json_escaped(str_buf_t *b, const char *s);

/* Extract JSON string value from key */
char *extract_json_string(const char *json, const char *key);

#endif /* WRT_INTERNAL_H */