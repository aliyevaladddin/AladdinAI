// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C Markdown <-> WRT Converter
 * High-performance, zero-dependency Markdown parser & generator
 */

#include "wrt_markdown.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* ============================================================
 * DYNAMIC STRING BUFFER
 * ============================================================ */

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} m_buf_t;

static void mbuf_init(m_buf_t *b) {
    b->cap = 4096;
    b->data = (char *)malloc(b->cap);
    b->data[0] = '\0';
    b->len = 0;
}

static void mbuf_append_len(m_buf_t *b, const char *s, size_t n) {
    if (!s || n == 0) return;
    if (b->len + n + 1 >= b->cap) {
        while (b->len + n + 1 >= b->cap) {
            b->cap *= 2;
        }
        b->data = (char *)realloc(b->data, b->cap);
    }
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = '\0';
}

static void mbuf_append(m_buf_t *b, const char *s) {
    if (!s) return;
    mbuf_append_len(b, s, strlen(s));
}

static void mbuf_append_c(m_buf_t *b, char c) {
    char buf[2] = {c, '\0'};
    mbuf_append_len(b, buf, 1);
}

/* Check if text contains Markdown syntax markers */
int wrt_has_markdown(const char *text) {
    if (!text) return 0;
    if (strstr(text, "**")) return 1;
    if (strstr(text, "~~")) return 1;
    if (strstr(text, "![")) return 1;
    if (strstr(text, "```")) return 1;
    if (strstr(text, "\n# ") || strncmp(text, "# ", 2) == 0) return 1;
    if (strstr(text, "\n## ") || strncmp(text, "## ", 3) == 0) return 1;
    if (strstr(text, "\n### ") || strncmp(text, "### ", 4) == 0) return 1;
    if (strstr(text, "\n> ") || strncmp(text, "> ", 2) == 0) return 1;
    if (strstr(text, "\n- ") || strncmp(text, "- ", 2) == 0) return 1;
    if (strstr(text, "|---|") || strstr(text, "|:--") || strstr(text, "| --")) return 1;
    return 0;
}

/* ============================================================
 * INLINE MARKDOWN -> WRT PARSER
 * ============================================================ */

/* Check if substring at pos starts a known WRT tag */
static int match_existing_wrt_tag(const char *text, size_t len, size_t pos, size_t *out_tag_len) {
    if (text[pos] != '[') return 0;
    size_t end = pos + 1;
    while (end < len && text[end] != ']' && text[end] != '\n') end++;
    if (end < len && text[end] == ']') {
        size_t tlen = end - pos + 1;
        const char *inner = text + pos + 1;
        if (*inner == '/') inner++;
        if (strncmp(inner, "b]", 2) == 0 || strncmp(inner, "i]", 2) == 0 ||
            strncmp(inner, "u]", 2) == 0 || strncmp(inner, "s]", 2) == 0 ||
            strncmp(inner, "code]", 5) == 0 || strncmp(inner, "quote]", 6) == 0 ||
            strncmp(inner, "h1]", 3) == 0 || strncmp(inner, "h2]", 3) == 0 ||
            strncmp(inner, "h3]", 3) == 0 || strncmp(inner, "table]", 6) == 0 ||
            strncmp(inner, "list]", 5) == 0 || strncmp(inner, "img ", 4) == 0 ||
            strncmp(inner, "img]", 4) == 0) {
            *out_tag_len = tlen;
            return 1;
        }
    }
    return 0;
}

static void append_markdown_inline(m_buf_t *out, const char *text, size_t len) {
    size_t i = 0;
    while (i < len) {
        // 1. Preserve existing WRT tags untouched
        size_t wrt_tag_len = 0;
        if (match_existing_wrt_tag(text, len, i, &wrt_tag_len)) {
            mbuf_append_len(out, text + i, wrt_tag_len);
            i += wrt_tag_len;
            continue;
        }

        // 2. Images: ![alt](url)
        if (text[i] == '!' && i + 1 < len && text[i + 1] == '[') {
            size_t b_end = i + 2;
            while (b_end < len && text[b_end] != ']' && text[b_end] != '\n') b_end++;
            if (b_end < len && text[b_end] == ']' && b_end + 1 < len && text[b_end + 1] == '(') {
                size_t u_start = b_end + 2;
                size_t u_end = u_start;
                while (u_end < len && text[u_end] != ')' && text[u_end] != '\n') u_end++;
                if (u_end < len && text[u_end] == ')') {
                    char alt[256];
                    size_t alt_len = b_end - (i + 2);
                    if (alt_len >= sizeof(alt)) alt_len = sizeof(alt) - 1;
                    strncpy(alt, text + i + 2, alt_len);
                    alt[alt_len] = '\0';

                    char url[1024];
                    size_t url_len = u_end - u_start;
                    if (url_len >= sizeof(url)) url_len = sizeof(url) - 1;
                    strncpy(url, text + u_start, url_len);
                    url[url_len] = '\0';

                    mbuf_append(out, "[img src=\"");
                    mbuf_append(out, url);
                    mbuf_append(out, "\" alt=\"");
                    mbuf_append(out, alt);
                    mbuf_append(out, "\"]");
                    i = u_end + 1;
                    continue;
                }
            }
        }

        // 3. Inline code: `code`
        if (text[i] == '`') {
            size_t c_end = i + 1;
            while (c_end < len && text[c_end] != '`' && text[c_end] != '\n') c_end++;
            if (c_end < len && text[c_end] == '`') {
                mbuf_append(out, "[code]");
                mbuf_append_len(out, text + i + 1, c_end - i - 1);
                mbuf_append(out, "[/code]");
                i = c_end + 1;
                continue;
            }
        }

        // 4. Bold + Italic: ***text***
        if (i + 2 < len && text[i] == '*' && text[i + 1] == '*' && text[i + 2] == '*') {
            const char *match = strstr(text + i + 3, "***");
            if (match && (size_t)(match - text) <= len) {
                size_t inner_len = match - (text + i + 3);
                mbuf_append(out, "[b][i]");
                append_markdown_inline(out, text + i + 3, inner_len);
                mbuf_append(out, "[/i][/b]");
                i = (match - text) + 3;
                continue;
            }
        }

        // 5. Bold: **text**
        if (i + 1 < len && text[i] == '*' && text[i + 1] == '*') {
            const char *match = strstr(text + i + 2, "**");
            if (match && (size_t)(match - text) <= len) {
                size_t inner_len = match - (text + i + 2);
                mbuf_append(out, "[b]");
                append_markdown_inline(out, text + i + 2, inner_len);
                mbuf_append(out, "[/b]");
                i = (match - text) + 2;
                continue;
            }
        }

        // 6. Bold: __text__
        if (i + 1 < len && text[i] == '_' && text[i + 1] == '_') {
            const char *match = strstr(text + i + 2, "__");
            if (match && (size_t)(match - text) <= len) {
                size_t inner_len = match - (text + i + 2);
                mbuf_append(out, "[b]");
                append_markdown_inline(out, text + i + 2, inner_len);
                mbuf_append(out, "[/b]");
                i = (match - text) + 2;
                continue;
            }
        }

        // 7. Strikethrough: ~~text~~
        if (i + 1 < len && text[i] == '~' && text[i + 1] == '~') {
            const char *match = strstr(text + i + 2, "~~");
            if (match && (size_t)(match - text) <= len) {
                size_t inner_len = match - (text + i + 2);
                mbuf_append(out, "[s]");
                append_markdown_inline(out, text + i + 2, inner_len);
                mbuf_append(out, "[/s]");
                i = (match - text) + 2;
                continue;
            }
        }

        // 8. Italic: *text* (not followed by space or another *)
        if (text[i] == '*' && i + 1 < len && text[i + 1] != ' ' && text[i + 1] != '*') {
            size_t c_end = i + 1;
            while (c_end < len && text[c_end] != '*' && text[c_end] != '\n') c_end++;
            if (c_end < len && text[c_end] == '*' && c_end > i + 1 && text[c_end - 1] != ' ') {
                mbuf_append(out, "[i]");
                append_markdown_inline(out, text + i + 1, c_end - i - 1);
                mbuf_append(out, "[/i]");
                i = c_end + 1;
                continue;
            }
        }

        // 9. Italic: _text_ (ensure not snake_case in words)
        if (text[i] == '_' && (i == 0 || !isalnum((unsigned char)text[i - 1]))) {
            if (i + 1 < len && text[i + 1] != ' ' && text[i + 1] != '_') {
                size_t c_end = i + 1;
                while (c_end < len && text[c_end] != '_' && text[c_end] != '\n') c_end++;
                if (c_end < len && text[c_end] == '_' && c_end > i + 1 &&
                    (c_end + 1 == len || !isalnum((unsigned char)text[c_end + 1]))) {
                    mbuf_append(out, "[i]");
                    append_markdown_inline(out, text + i + 1, c_end - i - 1);
                    mbuf_append(out, "[/i]");
                    i = c_end + 1;
                    continue;
                }
            }
        }

        mbuf_append_c(out, text[i++]);
    }
}

/* ============================================================
 * FULL MARKDOWN -> WRT CONVERTER
 * ============================================================ */

/* Check if a line is a markdown table separator e.g. |---|---| or |:---|:---:| */
static int is_table_separator(const char *line, size_t len) {
    if (len == 0 || line[0] != '|') return 0;
    int hyphen_found = 0;
    for (size_t i = 0; i < len; i++) {
        char c = line[i];
        if (c == '-') hyphen_found = 1;
        else if (c != '|' && c != ':' && !isspace((unsigned char)c)) {
            return 0;
        }
    }
    return hyphen_found;
}

char *wrt_markdown_to_wrt(const char *md_text) {
    if (!md_text) return strdup("");

    m_buf_t out;
    mbuf_init(&out);

    const char *p = md_text;
    int in_code_fence = 0;
    int in_table = 0;
    int in_list = 0;

    while (*p) {
        const char *line_start = p;
        while (*p && *p != '\n') p++;
        size_t raw_len = p - line_start;
        if (*p == '\n') p++;

        // Strip carriage return
        if (raw_len > 0 && line_start[raw_len - 1] == '\r') {
            raw_len--;
        }

        // Trim leading and trailing whitespace for detection
        const char *trim_start = line_start;
        size_t trim_len = raw_len;
        while (trim_len > 0 && isspace((unsigned char)*trim_start)) {
            trim_start++;
            trim_len--;
        }
        while (trim_len > 0 && isspace((unsigned char)trim_start[trim_len - 1])) {
            trim_len--;
        }

        // 1. Code Fence ```
        if (trim_len >= 3 && strncmp(trim_start, "```", 3) == 0) {
            if (!in_code_fence) {
                in_code_fence = 1;
                mbuf_append(&out, "[code]\n");
            } else {
                in_code_fence = 0;
                mbuf_append(&out, "[/code]\n\n");
            }
            continue;
        }

        if (in_code_fence) {
            mbuf_append_len(&out, line_start, raw_len);
            mbuf_append_c(&out, '\n');
            continue;
        }

        // Blank lines
        if (trim_len == 0) {
            if (in_table) {
                in_table = 0;
                mbuf_append(&out, "[/table]\n\n");
            }
            if (in_list) {
                in_list = 0;
                mbuf_append(&out, "[/list]\n\n");
            } else {
                mbuf_append_c(&out, '\n');
            }
            continue;
        }

        // 2. Table row & separator detection
        if (trim_start[0] == '|') {
            if (is_table_separator(trim_start, trim_len)) {
                // Table separator line -> ensure table opened, skip line
                if (!in_table) {
                    in_table = 1;
                    mbuf_append(&out, "[table]\n");
                }
                continue;
            } else {
                if (!in_table) {
                    // Check if already has [table] tag
                    if (strncmp(trim_start, "[table]", 7) != 0) {
                        in_table = 1;
                        mbuf_append(&out, "[table]\n");
                    }
                }
                append_markdown_inline(&out, trim_start, trim_len);
                mbuf_append_c(&out, '\n');
                continue;
            }
        } else if (in_table) {
            in_table = 0;
            mbuf_append(&out, "[/table]\n\n");
        }

        // 3. Headings: #, ##, ###
        if (trim_start[0] == '#') {
            int level = 0;
            const char *hp = trim_start;
            while (*hp == '#') { level++; hp++; }
            if (*hp == ' ') {
                hp++;
                while (*hp == ' ') hp++;
                size_t title_len = trim_len - (hp - trim_start);
                char htag[8];
                int hval = (level > 3) ? 3 : level;
                snprintf(htag, sizeof(htag), "h%d", hval);

                mbuf_append(&out, "[");
                mbuf_append(&out, htag);
                mbuf_append(&out, "]");
                append_markdown_inline(&out, hp, title_len);
                mbuf_append(&out, "[/");
                mbuf_append(&out, htag);
                mbuf_append(&out, "]\n\n");
                continue;
            }
        }

        // 4. Blockquotes: > Quote
        if (trim_start[0] == '>') {
            const char *qp = trim_start + 1;
            while (*qp == ' ') qp++;
            size_t qlen = trim_len - (qp - trim_start);
            mbuf_append(&out, "[quote]");
            append_markdown_inline(&out, qp, qlen);
            mbuf_append(&out, "[/quote]\n\n");
            continue;
        }

        // 5. Unordered list: - item or + item
        if ((trim_start[0] == '-' || trim_start[0] == '+') && trim_len >= 2 && trim_start[1] == ' ') {
            const char *lp = trim_start + 2;
            while (*lp == ' ') lp++;
            size_t llen = trim_len - (lp - trim_start);
            if (!in_list) {
                in_list = 1;
                mbuf_append(&out, "[list]\n");
            }
            mbuf_append(&out, "* ");
            append_markdown_inline(&out, lp, llen);
            mbuf_append_c(&out, '\n');
            continue;
        }

        // 6. Ordered list: 1. item
        if (isdigit((unsigned char)trim_start[0])) {
            const char *dot = trim_start;
            while (isdigit((unsigned char)*dot)) dot++;
            if (*dot == '.' && dot[1] == ' ') {
                const char *lp = dot + 2;
                while (*lp == ' ') lp++;
                size_t llen = trim_len - (lp - trim_start);
                if (!in_list) {
                    in_list = 1;
                    mbuf_append(&out, "[list]\n");
                }
                mbuf_append(&out, "* ");
                append_markdown_inline(&out, lp, llen);
                mbuf_append_c(&out, '\n');
                continue;
            }
        }

        // Close list if we encounter regular paragraph
        if (in_list) {
            in_list = 0;
            mbuf_append(&out, "[/list]\n\n");
        }

        // 7. Regular paragraph with inline Markdown
        append_markdown_inline(&out, trim_start, trim_len);
        mbuf_append(&out, "\n\n");
    }

    if (in_code_fence) {
        mbuf_append(&out, "[/code]\n");
    }
    if (in_table) {
        mbuf_append(&out, "[/table]\n");
    }
    if (in_list) {
        mbuf_append(&out, "[/list]\n");
    }

    return out.data;
}

/* ============================================================
 * WRT -> MARKDOWN CONVERTER
 * ============================================================ */

char *wrt_to_markdown(const char *wrt_text) {
    if (!wrt_text) return strdup("");

    m_buf_t out;
    mbuf_init(&out);

    size_t len = strlen(wrt_text);
    size_t i = 0;
    int in_table = 0;
    int table_row_idx = 0;

    while (i < len) {
        // Tag conversion
        if (wrt_text[i] == '[') {
            if (strncmp(wrt_text + i, "[h1]", 4) == 0) {
                mbuf_append(&out, "# "); i += 4; continue;
            } else if (strncmp(wrt_text + i, "[/h1]", 5) == 0) {
                mbuf_append(&out, "\n\n"); i += 5; continue;
            } else if (strncmp(wrt_text + i, "[h2]", 4) == 0) {
                mbuf_append(&out, "## "); i += 4; continue;
            } else if (strncmp(wrt_text + i, "[/h2]", 5) == 0) {
                mbuf_append(&out, "\n\n"); i += 5; continue;
            } else if (strncmp(wrt_text + i, "[h3]", 4) == 0) {
                mbuf_append(&out, "### "); i += 4; continue;
            } else if (strncmp(wrt_text + i, "[/h3]", 5) == 0) {
                mbuf_append(&out, "\n\n"); i += 5; continue;
            } else if (strncmp(wrt_text + i, "[b]", 3) == 0 || strncmp(wrt_text + i, "[/b]", 4) == 0) {
                mbuf_append(&out, "**"); i += (wrt_text[i + 1] == '/') ? 4 : 3; continue;
            } else if (strncmp(wrt_text + i, "[i]", 3) == 0 || strncmp(wrt_text + i, "[/i]", 4) == 0) {
                mbuf_append(&out, "*"); i += (wrt_text[i + 1] == '/') ? 4 : 3; continue;
            } else if (strncmp(wrt_text + i, "[s]", 3) == 0 || strncmp(wrt_text + i, "[/s]", 4) == 0) {
                mbuf_append(&out, "~~"); i += (wrt_text[i + 1] == '/') ? 4 : 3; continue;
            } else if (strncmp(wrt_text + i, "[u]", 3) == 0) {
                mbuf_append(&out, "<u>"); i += 3; continue;
            } else if (strncmp(wrt_text + i, "[/u]", 4) == 0) {
                mbuf_append(&out, "</u>"); i += 4; continue;
            } else if (strncmp(wrt_text + i, "[code]", 6) == 0 || strncmp(wrt_text + i, "[/code]", 7) == 0) {
                mbuf_append(&out, "`"); i += (wrt_text[i + 1] == '/') ? 7 : 6; continue;
            } else if (strncmp(wrt_text + i, "[quote]", 7) == 0) {
                mbuf_append(&out, "> "); i += 7; continue;
            } else if (strncmp(wrt_text + i, "[/quote]", 8) == 0) {
                mbuf_append(&out, "\n\n"); i += 8; continue;
            } else if (strncmp(wrt_text + i, "[list]", 6) == 0) {
                i += 6; continue;
            } else if (strncmp(wrt_text + i, "[/list]", 7) == 0) {
                i += 7; continue;
            } else if (strncmp(wrt_text + i, "[table]", 7) == 0) {
                in_table = 1;
                table_row_idx = 0;
                i += 7;
                continue;
            } else if (strncmp(wrt_text + i, "[/table]", 8) == 0) {
                in_table = 0;
                i += 8;
                mbuf_append(&out, "\n");
                continue;
            } else if (strncmp(wrt_text + i, "[img ", 5) == 0) {
                // Parse [img src="..." alt="..."] -> ![alt](src)
                const char *tag_end = strchr(wrt_text + i, ']');
                if (tag_end) {
                    char alt[256] = "image";
                    char src[1024] = "";
                    const char *alt_ptr = strstr(wrt_text + i, "alt=\"");
                    if (alt_ptr && alt_ptr < tag_end) {
                        alt_ptr += 5;
                        const char *ae = strchr(alt_ptr, '"');
                        if (ae && ae < tag_end) {
                            size_t alen = ae - alt_ptr;
                            if (alen >= sizeof(alt)) alen = sizeof(alt) - 1;
                            strncpy(alt, alt_ptr, alen);
                            alt[alen] = '\0';
                        }
                    }
                    const char *src_ptr = strstr(wrt_text + i, "src=\"");
                    if (src_ptr && src_ptr < tag_end) {
                        src_ptr += 5;
                        const char *se = strchr(src_ptr, '"');
                        if (se && se < tag_end) {
                            size_t slen = se - src_ptr;
                            if (slen >= sizeof(src)) slen = sizeof(src) - 1;
                            strncpy(src, src_ptr, slen);
                            src[slen] = '\0';
                        }
                    }

                    mbuf_append(&out, "![");
                    mbuf_append(&out, alt);
                    mbuf_append(&out, "](");
                    mbuf_append(&out, src);
                    mbuf_append(&out, ")");
                    i = (tag_end - wrt_text) + 1;
                    continue;
                }
            }
        }

        // Table separator insertion after first row
        if (in_table && wrt_text[i] == '\n') {
            mbuf_append_c(&out, '\n');
            if (table_row_idx == 0) {
                table_row_idx++;
                // Count columns in previous row
                mbuf_append(&out, "|---|---|---|\n");
            }
            i++;
            continue;
        }

        mbuf_append_c(&out, wrt_text[i++]);
    }

    return out.data;
}

/* File helpers */
int wrt_md_to_wrt_file(const char *md_path, const char *wrt_path) {
    FILE *f = fopen(md_path, "r");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *buf = (char *)malloc(fsize + 1);
    if (fread(buf, 1, fsize, f) != (size_t)fsize) {
        free(buf); fclose(f); return -1;
    }
    buf[fsize] = '\0';
    fclose(f);

    char *wrt = wrt_markdown_to_wrt(buf);
    free(buf);
    if (!wrt) return -1;

    FILE *out = fopen(wrt_path, "w");
    if (!out) { free(wrt); return -1; }
    fputs(wrt, out);
    fclose(out);
    free(wrt);
    return 0;
}

int wrt_wrt_to_md_file(const char *wrt_path, const char *md_path) {
    FILE *f = fopen(wrt_path, "r");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *buf = (char *)malloc(fsize + 1);
    if (fread(buf, 1, fsize, f) != (size_t)fsize) {
        free(buf); fclose(f); return -1;
    }
    buf[fsize] = '\0';
    fclose(f);

    char *md = wrt_to_markdown(buf);
    free(buf);
    if (!md) return -1;

    FILE *out = fopen(md_path, "w");
    if (!out) { free(md); return -1; }
    fputs(md, out);
    fclose(out);
    free(md);
    return 0;
}
