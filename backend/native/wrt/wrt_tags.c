// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Valid WRT tag specification
 */

#include "wrt_internal.h"

/* ============================================================
 * TAG SPECIFICATION
 * ============================================================ */

const char *VALID_TAGS[] = {
    "b", "i", "u", "s", "code",
    "h1", "h2", "h3", "quote",
    "list", "table", "tr", "th", "td",
    "img", "link", "url", NULL
};

int is_known_tag(const char *tag) {
    for (int i = 0; VALID_TAGS[i]; i++) {
        if (strcasecmp(tag, VALID_TAGS[i]) == 0) return 1;
    }
    return 0;
}