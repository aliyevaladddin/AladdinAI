// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Buffer utilities implementation
 */

#include "wrt_internal.h"

/* ============================================================
 * BUFFER UTILITIES (Dynamic String Builder)
 * ============================================================ */

/* Initialize a dynamic string buffer. */
void buf_init(str_buf_t *b) {
    b->cap = 4096;
    b->data = malloc(b->cap);
    if (!b->data) {
        b->cap = 0;
        b->len = 0;
        return;
    }
    b->data[0] = '\0';
    b->len = 0;
}

/* Append n characters from s to b */
void buf_append_len(str_buf_t *b, const char *s, size_t n) {
    if (!b || !b->data || !s || n == 0) return;

    if (b->len + n + 1 >= b->cap) {
        size_t new_cap = b->cap ? b->cap : 4096;
        while (b->len + n + 1 >= new_cap) {
            new_cap *= 2;
        }
        char *tmp = realloc(b->data, new_cap);
        if (!tmp) {
            return; /* Allocation failed — keep existing buffer, do not crash */
        }
        b->data = tmp;
        b->cap = new_cap;
    }
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = '\0';
}

/* Append a null-terminated string to b */
void buf_append(str_buf_t *b, const char *s) {
    buf_append_len(b, s, strlen(s));
}

/* Append a single character to b */
void buf_append_c(str_buf_t *b, char c) {
    char s[2] = {c, '\0'};
    buf_append_len(b, s, 1);
}

/* Append n characters of s with HTML escaping */
void buf_append_escaped_html(str_buf_t *b, const char *s, size_t n) {
    for (size_t i = 0; i < n; i++) {
        switch (s[i]) {
            case '&': buf_append(b, "&amp;"); break;
            case '<': buf_append(b, "&lt;"); break;
            case '>': buf_append(b, "&gt;"); break;
            case '"': buf_append(b, "&quot;"); break;
            case '\'': buf_append(b, "&#39;"); break;
            default: buf_append_c(b, s[i]); break;
        }
    }
}