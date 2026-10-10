// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * JSON serialization and parsing helpers
 */

#include "wrt_internal.h"

/* ============================================================
 * JSON SERIALIZATION & PARSING HELPERS
 * ============================================================ */

/* Append JSON-escaped string */
void buf_append_json_escaped(str_buf_t *b, const char *s) {
    if (!s) return;
    for (size_t i = 0; s[i]; i++) {
        unsigned char c = (unsigned char)s[i];
        switch (c) {
            case '"': buf_append(b, "\\\""); break;
            case '\\': buf_append(b, "\\\\"); break;
            case '\n': buf_append(b, "\\n"); break;
            case '\r': buf_append(b, "\\r"); break;
            case '\t': buf_append(b, "\\t"); break;
            case '\b': buf_append(b, "\\b"); break;
            case '\f': buf_append(b, "\\f"); break;
            default:
                if (c < 0x20) {
                    char hex[8];
                    snprintf(hex, sizeof(hex), "\\u%04x", c);
                    buf_append(b, hex);
                } else {
                    buf_append_c(b, (char)c);
                }
                break;
        }
    }
}

/* Extract JSON string value from key */
char *extract_json_string(const char *json, const char *key) {
    char search[64];
    snprintf(search, sizeof(search), "\"%s\"", key);
    const char *p = strstr(json, search);
    if (!p) return NULL;
    p = strchr(p + strlen(search), ':');
    if (!p) return NULL;
    p++; // skip ':'
    while (*p && isspace((unsigned char)*p)) p++;
    if (*p != '"') return NULL;
    p++; // skip opening quote

    str_buf_t b;
    buf_init(&b);

    while (*p && *p != '"') {
        if (*p == '\\') {
            p++;
            if (!*p) break;
            if (*p == 'n') buf_append_c(&b, '\n');
            else if (*p == 'r') buf_append_c(&b, '\r');
            else if (*p == 't') buf_append_c(&b, '\t');
            else if (*p == 'b') buf_append_c(&b, '\b');
            else if (*p == 'f') buf_append_c(&b, '\f');
            else if (*p == '"') buf_append_c(&b, '"');
            else if (*p == '\\') buf_append_c(&b, '\\');
            else if (*p == '/') buf_append_c(&b, '/');
            else buf_append_c(&b, *p);
        } else {
            buf_append_c(&b, *p);
        }
        p++;
    }
    return b.data;
}