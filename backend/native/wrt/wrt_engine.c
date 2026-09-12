// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Implementation of ultra-fast document parser, validator, and converter
 */

#include "wrt_engine.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
#include <poll.h>
#include <signal.h>
#include <dirent.h>
#include <time.h>
#include <errno.h>
#include <limits.h>

/* ============================================================
 * BUFFER UTILITIES (Dynamic String Builder)
 * ============================================================ */

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} str_buf_t;

static void buf_init(str_buf_t *b) {
    b->cap = 4096;
    b->data = malloc(b->cap);
    b->data[0] = '\0';
    b->len = 0;
}

static void buf_append_len(str_buf_t *b, const char *s, size_t n) {
    if (b->len + n + 1 >= b->cap) {
        while (b->len + n + 1 >= b->cap) {
            b->cap *= 2;
        }
        b->data = realloc(b->data, b->cap);
    }
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = '\0';
}

static void buf_append(str_buf_t *b, const char *s) {
    buf_append_len(b, s, strlen(s));
}

static void buf_append_c(str_buf_t *b, char c) {
    char s[2] = {c, '\0'};
    buf_append_len(b, s, 1);
}

static void buf_append_escaped_html(str_buf_t *b, const char *s, size_t n) {
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

/* ============================================================
 * TAG SPECIFICATION
 * ============================================================ */

static const char *VALID_TAGS[] = {
    "b", "i", "u", "s", "code",
    "h1", "h2", "h3", "quote",
    "list", "table", "tr", "th", "td",
    "img", "link", "url", NULL
};

static int is_known_tag(const char *tag) {
    for (int i = 0; VALID_TAGS[i]; i++) {
        if (strcasecmp(tag, VALID_TAGS[i]) == 0) return 1;
    }
    return 0;
}

/* ============================================================
 * VALIDATION
 * ============================================================ */

typedef struct {
    char tag[WRT_MAX_TAG_LEN];
    int line;
    int col;
} stack_entry_t;

void wrt_validate(const char *text, wrt_report_t *out) {
    memset(out, 0, sizeof(*out));
    out->valid = 1;

    stack_entry_t stack[WRT_MAX_STACK];
    int stack_top = 0;

    int line = 1;
    int col = 1;
    int in_word = 0;

    size_t i = 0;
    size_t len = strlen(text);
    out->char_count = (int)len;

    while (i < len) {
        char c = text[i];

        if (c == '\n') {
            line++;
            col = 1;
            out->line_count++;
            in_word = 0;
            i++;
            continue;
        }

        if (isspace((unsigned char)c)) {
            in_word = 0;
        } else if (!in_word) {
            in_word = 1;
            out->word_count++;
        }

        /* Check for empty brackets [] */
        if (c == '[' && i + 1 < len && text[i + 1] == ']') {
            if (out->issue_count < WRT_MAX_ISSUES) {
                wrt_issue_t *issue = &out->issues[out->issue_count++];
                issue->line = line;
                issue->col = col;
                issue->tag[0] = '\0';
                snprintf(issue->message, sizeof(issue->message), "Empty tag [] found");
                issue->severity = 1;
            }
            out->valid = 0;
            i += 2;
            col += 2;
            continue;
        }

        /* Tag detection */
        if (c == '[') {
            size_t j = i + 1;
            int is_close = 0;
            if (j < len && text[j] == '/') {
                is_close = 1;
                j++;
            }

            size_t tag_start = j;
            while (j < len && text[j] != ']' && text[j] != ' ' && text[j] != '\n') {
                j++;
            }

            if (j < len && (text[j] == ']' || text[j] == ' ')) {
                size_t tag_len = j - tag_start;
                if (tag_len > 0 && tag_len < WRT_MAX_TAG_LEN) {
                    char tag_name[WRT_MAX_TAG_LEN];
                    strncpy(tag_name, text + tag_start, tag_len);
                    tag_name[tag_len] = '\0';

                    // Convert to lowercase
                    for (size_t k = 0; k < tag_len; k++) {
                        tag_name[k] = (char)tolower((unsigned char)tag_name[k]);
                    }

                    // Find closing bracket
                    while (j < len && text[j] != ']') j++;
                    if (j < len && text[j] == ']') {
                        out->tag_count++;

                        if (!is_known_tag(tag_name)) {
                            if (out->issue_count < WRT_MAX_ISSUES) {
                                wrt_issue_t *issue = &out->issues[out->issue_count++];
                                issue->line = line;
                                issue->col = col;
                                snprintf(issue->tag, sizeof(issue->tag), "%s", tag_name);
                                snprintf(issue->message, sizeof(issue->message),
                                         "Unknown tag [%s]", tag_name);
                                issue->severity = 1;
                            }
                        } else if (strcmp(tag_name, "img") == 0) {
                            // Self-closing tag
                        } else if (!is_close) {
                            // Push opening tag
                            if (stack_top < WRT_MAX_STACK) {
                                snprintf(stack[stack_top].tag, sizeof(stack[stack_top].tag), "%s", tag_name);
                                stack[stack_top].line = line;
                                stack[stack_top].col = col;
                                stack_top++;
                            }
                        } else {
                            // Pop closing tag
                            if (stack_top == 0) {
                                if (out->issue_count < WRT_MAX_ISSUES) {
                                    wrt_issue_t *issue = &out->issues[out->issue_count++];
                                    issue->line = line;
                                    issue->col = col;
                                    snprintf(issue->tag, sizeof(issue->tag), "%s", tag_name);
                                    snprintf(issue->message, sizeof(issue->message),
                                             "Unmatched closing tag [/%s]", tag_name);
                                    issue->severity = 0;
                                }
                                out->valid = 0;
                            } else {
                                stack_top--;
                                if (strcmp(stack[stack_top].tag, tag_name) != 0) {
                                    if (out->issue_count < WRT_MAX_ISSUES) {
                                        wrt_issue_t *issue = &out->issues[out->issue_count++];
                                        issue->line = line;
                                        issue->col = col;
                                        snprintf(issue->tag, sizeof(issue->tag), "%s", tag_name);
                                        snprintf(issue->message, sizeof(issue->message),
                                                 "Mismatched tag: opened [%s] on line %d, closed with [/%s]",
                                                 stack[stack_top].tag, stack[stack_top].line, tag_name);
                                        issue->severity = 0;
                                    }
                                    out->valid = 0;
                                }
                            }
                        }

                        col += (int)(j - i + 1);
                        i = j + 1;
                        continue;
                    }
                }
            }
        }

        i++;
        col++;
    }

    if (len > 0 && text[len - 1] != '\n') {
        out->line_count++;
    }

    /* Check for unclosed tags remaining in stack */
    while (stack_top > 0) {
        stack_top--;
        out->valid = 0;
        if (out->issue_count < WRT_MAX_ISSUES) {
            wrt_issue_t *issue = &out->issues[out->issue_count++];
            issue->line = stack[stack_top].line;
            issue->col = stack[stack_top].col;
            snprintf(issue->tag, sizeof(issue->tag), "%s", stack[stack_top].tag);
            snprintf(issue->message, sizeof(issue->message),
                     "Unclosed tag [%s] opened on line %d",
                     stack[stack_top].tag, stack[stack_top].line);
            issue->severity = 0;
        }
    }
}

char *wrt_report_to_json(const wrt_report_t *rep) {
    str_buf_t b;
    buf_init(&b);

    char num_buf[32];
    buf_append(&b, "{\"valid\":");
    buf_append(&b, rep->valid ? "true" : "false");
    buf_append(&b, ",\"word_count\":");
    snprintf(num_buf, sizeof(num_buf), "%d", rep->word_count);
    buf_append(&b, num_buf);
    buf_append(&b, ",\"char_count\":");
    snprintf(num_buf, sizeof(num_buf), "%d", rep->char_count);
    buf_append(&b, num_buf);
    buf_append(&b, ",\"line_count\":");
    snprintf(num_buf, sizeof(num_buf), "%d", rep->line_count);
    buf_append(&b, num_buf);
    buf_append(&b, ",\"tag_count\":");
    snprintf(num_buf, sizeof(num_buf), "%d", rep->tag_count);
    buf_append(&b, num_buf);
    buf_append(&b, ",\"issues\":[");

    for (int i = 0; i < rep->issue_count; i++) {
        if (i > 0) buf_append(&b, ",");
        buf_append(&b, "{\"line\":");
        snprintf(num_buf, sizeof(num_buf), "%d", rep->issues[i].line);
        buf_append(&b, num_buf);
        buf_append(&b, ",\"col\":");
        snprintf(num_buf, sizeof(num_buf), "%d", rep->issues[i].col);
        buf_append(&b, num_buf);
        buf_append(&b, ",\"tag\":\"");
        buf_append(&b, rep->issues[i].tag);
        buf_append(&b, "\",\"message\":\"");
        buf_append(&b, rep->issues[i].message);
        buf_append(&b, "\",\"severity\":");
        snprintf(num_buf, sizeof(num_buf), "%d", rep->issues[i].severity);
        buf_append(&b, num_buf);
        buf_append(&b, "}");
    }

    buf_append(&b, "]}");
    return b.data;
}

/* ============================================================
 * TAG FIXER
 * ============================================================ */

char *wrt_fix(const char *text) {
    if (!text) return strdup("");

    char *md_fixed = NULL;
    if (wrt_has_markdown(text)) {
        md_fixed = wrt_markdown_to_wrt(text);
        if (md_fixed) text = md_fixed;
    }

    str_buf_t b;
    buf_init(&b);

    stack_entry_t stack[WRT_MAX_STACK];
    int stack_top = 0;

    size_t i = 0;
    size_t len = strlen(text);

    while (i < len) {
        /* Drop empty brackets [] */
        if (text[i] == '[' && i + 1 < len && text[i + 1] == ']') {
            i += 2;
            continue;
        }

        if (text[i] == '[') {
            size_t j = i + 1;
            int is_close = (j < len && text[j] == '/');
            if (is_close) j++;

            size_t tag_start = j;
            while (j < len && text[j] != ']' && text[j] != ' ' && text[j] != '\n') j++;

            if (j < len && (text[j] == ']' || text[j] == ' ')) {
                size_t tag_len = j - tag_start;
                if (tag_len > 0 && tag_len < WRT_MAX_TAG_LEN) {
                    char tag_name[WRT_MAX_TAG_LEN];
                    strncpy(tag_name, text + tag_start, tag_len);
                    tag_name[tag_len] = '\0';
                    for (size_t k = 0; k < tag_len; k++) {
                        tag_name[k] = (char)tolower((unsigned char)tag_name[k]);
                    }

                    while (j < len && text[j] != ']') j++;
                    if (j < len && text[j] == ']') {
                        if (is_known_tag(tag_name) && strcmp(tag_name, "img") != 0) {
                            if (!is_close) {
                                if (stack_top < WRT_MAX_STACK) {
                                    snprintf(stack[stack_top].tag, sizeof(stack[stack_top].tag), "%s", tag_name);
                                    stack_top++;
                                }
                            } else {
                                if (stack_top > 0) stack_top--;
                            }
                        }
                        buf_append_len(&b, text + i, j - i + 1);
                        i = j + 1;
                        continue;
                    }
                }
            }
        }

        buf_append_c(&b, text[i++]);
    }

    /* Auto-close remaining tags in reverse order */
    while (stack_top > 0) {
        stack_top--;
        buf_append(&b, "[/");
        buf_append(&b, stack[stack_top].tag);
        buf_append(&b, "]");
    }

    if (md_fixed) free(md_fixed);
    return b.data;
}

/* ============================================================
 * HTML CONVERTER
 * ============================================================ */

char *wrt_to_html(const char *text) {
    str_buf_t b;
    buf_init(&b);

    size_t i = 0;
    size_t len = strlen(text);
    int in_paragraph = 0;

    while (i < len) {
        /* Check for headings at start of line or text */
        if (text[i] == '[' && (strncmp(text + i, "[h1]", 4) == 0 ||
                               strncmp(text + i, "[h2]", 4) == 0 ||
                               strncmp(text + i, "[h3]", 4) == 0)) {
            char htag[3] = {text[i + 1], text[i + 2], '\0'};
            char close_tag[6];
            snprintf(close_tag, sizeof(close_tag), "[/%s]", htag);

            const char *end = strstr(text + i + 4, close_tag);
            if (end) {
                if (in_paragraph) {
                    buf_append(&b, "</p>\n");
                    in_paragraph = 0;
                }
                buf_append(&b, "<");
                buf_append(&b, htag);
                buf_append(&b, " class=\"wrt-heading\">");
                buf_append_escaped_html(&b, text + i + 4, end - (text + i + 4));
                buf_append(&b, "</");
                buf_append(&b, htag);
                buf_append(&b, ">\n");

                i = (end - text) + strlen(close_tag);
                if (i < len && text[i] == '\n') i++;
                continue;
            }
        }

        /* Check for quote */
        if (strncmp(text + i, "[quote]", 7) == 0) {
            const char *end = strstr(text + i + 7, "[/quote]");
            if (end) {
                if (in_paragraph) {
                    buf_append(&b, "</p>\n");
                    in_paragraph = 0;
                }
                buf_append(&b, "<blockquote class=\"wrt-quote border-l-4 border-sky-500 pl-4 my-3 text-slate-300 italic\">");
                buf_append_escaped_html(&b, text + i + 7, end - (text + i + 7));
                buf_append(&b, "</blockquote>\n");

                i = (end - text) + 8;
                if (i < len && text[i] == '\n') i++;
                continue;
            }
        }

        /* Check for table */
        if (strncmp(text + i, "[table]", 7) == 0) {
            const char *end = strstr(text + i + 7, "[/table]");
            if (end) {
                if (in_paragraph) {
                    buf_append(&b, "</p>\n");
                    in_paragraph = 0;
                }
                buf_append(&b, "<table class=\"wrt-table border-collapse border border-slate-700 my-4 w-full text-sm\">\n");
                
                // Parse rows separated by newlines
                const char *row_ptr = text + i + 7;
                int is_first_row = 1;

                while (row_ptr < end) {
                    while (row_ptr < end && (*row_ptr == '\r' || *row_ptr == '\n' || *row_ptr == ' ')) row_ptr++;
                    if (row_ptr >= end) break;

                    const char *row_end = row_ptr;
                    while (row_end < end && *row_end != '\n') row_end++;

                    if (*row_ptr == '|') {
                        buf_append(&b, "  <tr>\n");
                        const char *cell = row_ptr + 1;
                        while (cell < row_end) {
                            const char *cell_end = cell;
                            while (cell_end < row_end && *cell_end != '|') cell_end++;
                            if (cell_end <= row_end) {
                                const char *tag = is_first_row ? "th" : "td";
                                buf_append(&b, "    <");
                                buf_append(&b, tag);
                                buf_append(&b, " class=\"border border-slate-700 px-3 py-1.5\">");
                                // Trim cell whitespace
                                while (cell < cell_end && isspace((unsigned char)*cell)) cell++;
                                const char *trim_end = cell_end;
                                while (trim_end > cell && isspace((unsigned char)*(trim_end - 1))) trim_end--;
                                buf_append_escaped_html(&b, cell, trim_end - cell);
                                buf_append(&b, "</");
                                buf_append(&b, tag);
                                buf_append(&b, ">\n");
                            }
                            cell = cell_end + 1;
                        }
                        buf_append(&b, "  </tr>\n");
                        is_first_row = 0;
                    }

                    row_ptr = row_end + 1;
                }

                buf_append(&b, "</table>\n");
                i = (end - text) + 8;
                if (i < len && text[i] == '\n') i++;
                continue;
            }
        }

        /* Check for list */
        if (strncmp(text + i, "[list]", 6) == 0) {
            const char *end = strstr(text + i + 6, "[/list]");
            if (end) {
                if (in_paragraph) {
                    buf_append(&b, "</p>\n");
                    in_paragraph = 0;
                }
                buf_append(&b, "<ul class=\"wrt-list list-disc pl-6 my-3 space-y-1\">\n");

                const char *item = text + i + 6;
                while (item < end) {
                    while (item < end && (*item == '\r' || *item == '\n' || *item == ' ')) item++;
                    if (item >= end) break;

                    const char *item_end = item;
                    while (item_end < end && *item_end != '\n') item_end++;

                    if (*item == '*' || *item == '-') {
                        item++;
                        while (item < item_end && isspace((unsigned char)*item)) item++;
                    }

                    buf_append(&b, "  <li>");
                    buf_append_escaped_html(&b, item, item_end - item);
                    buf_append(&b, "</li>\n");

                    item = item_end + 1;
                }

                buf_append(&b, "</ul>\n");
                i = (end - text) + 7;
                if (i < len && text[i] == '\n') i++;
                continue;
            }
        }

        /* Check for inline tags */
        if (strncmp(text + i, "[b]", 3) == 0) { buf_append(&b, "<strong>"); i += 3; continue; }
        if (strncmp(text + i, "[/b]", 4) == 0) { buf_append(&b, "</strong>"); i += 4; continue; }
        if (strncmp(text + i, "[i]", 3) == 0) { buf_append(&b, "<em>"); i += 3; continue; }
        if (strncmp(text + i, "[/i]", 4) == 0) { buf_append(&b, "</em>"); i += 4; continue; }
        if (strncmp(text + i, "[u]", 3) == 0) { buf_append(&b, "<u>"); i += 3; continue; }
        if (strncmp(text + i, "[/u]", 4) == 0) { buf_append(&b, "</u>"); i += 4; continue; }
        if (strncmp(text + i, "[s]", 3) == 0) { buf_append(&b, "<s>"); i += 3; continue; }
        if (strncmp(text + i, "[/s]", 4) == 0) { buf_append(&b, "</s>"); i += 4; continue; }
        if (strncmp(text + i, "[code]", 6) == 0) { buf_append(&b, "<code class=\"bg-slate-800 px-1 py-0.5 rounded font-mono text-sm\">"); i += 6; continue; }
        if (strncmp(text + i, "[/code]", 7) == 0) { buf_append(&b, "</code>"); i += 7; continue; }

        /* Paragraph management on double newlines */
        if (text[i] == '\n') {
            if (i + 1 < len && text[i + 1] == '\n') {
                if (in_paragraph) {
                    buf_append(&b, "</p>\n");
                    in_paragraph = 0;
                }
                while (i < len && text[i] == '\n') i++;
                continue;
            }
            if (in_paragraph) {
                buf_append(&b, "<br />\n");
            }
            i++;
            continue;
        }

        if (!in_paragraph) {
            buf_append(&b, "<p class=\"my-2 leading-relaxed\">");
            in_paragraph = 1;
        }

        buf_append_escaped_html(&b, text + i, 1);
        i++;
    }

    if (in_paragraph) {
        buf_append(&b, "</p>\n");
    }

    return b.data;
}

/* ============================================================
 * JSON SERIALIZATION & PARSING HELPERS
 * ============================================================ */

static void buf_append_json_escaped(str_buf_t *b, const char *s) {
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

static char *extract_json_string(const char *json, const char *key) {
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

/* ============================================================
 * NATIVE FILE OPERATIONS
 * ============================================================ */

#define WRT_MAX_DIR_ENTRIES 2048
#define WRT_RECENT_FILE "/tmp/aladdin_wrt_recent.txt"

typedef struct {
    char name[256];
    char path[PATH_MAX + 512];
    int is_dir;
    long size;
    long mtime;
    char ext[32];
} wrt_file_entry_t;

static int compare_file_entries(const void *a, const void *b) {
    const wrt_file_entry_t *fa = (const wrt_file_entry_t *)a;
    const wrt_file_entry_t *fb = (const wrt_file_entry_t *)b;
    /* Directories first */
    if (fa->is_dir && !fb->is_dir) return -1;
    if (!fa->is_dir && fb->is_dir) return 1;
    return strcasecmp(fa->name, fb->name);
}

static const char *get_file_extension(const char *filename) {
    const char *dot = strrchr(filename, '.');
    if (!dot || dot == filename) return "";
    return dot + 1;
}

static void make_parent_dirs(const char *file_path) {
    char tmp[PATH_MAX];
    strncpy(tmp, file_path, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = '\0';
    char *slash = strrchr(tmp, '/');
    if (!slash) return;
    *slash = '\0';
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, 0755);
            *p = '/';
        }
    }
    mkdir(tmp, 0755);
}

void wrt_record_recent_file(const char *file_path) {
    if (!file_path || !file_path[0]) return;

    char resolved[PATH_MAX];
    if (realpath(file_path, resolved) == NULL) {
        strncpy(resolved, file_path, sizeof(resolved) - 1);
        resolved[sizeof(resolved) - 1] = '\0';
    }

    char *lines[25];
    int line_count = 0;

    FILE *f = fopen(WRT_RECENT_FILE, "r");
    if (f) {
        char buf[PATH_MAX];
        while (fgets(buf, sizeof(buf), f) && line_count < 20) {
            size_t l = strlen(buf);
            while (l > 0 && (buf[l - 1] == '\n' || buf[l - 1] == '\r')) buf[--l] = '\0';
            if (l == 0) continue;
            if (strcmp(buf, resolved) == 0) continue;
            lines[line_count++] = strdup(buf);
        }
        fclose(f);
    }

    FILE *out = fopen(WRT_RECENT_FILE, "w");
    if (out) {
        fprintf(out, "%s\n", resolved);
        for (int i = 0; i < line_count && i < 19; i++) {
            fprintf(out, "%s\n", lines[i]);
        }
        fclose(out);
    }

    for (int i = 0; i < line_count; i++) free(lines[i]);
}

char *wrt_get_recent_files_json(void) {
    str_buf_t b;
    buf_init(&b);
    buf_append(&b, "{\"type\":\"recent_files_result\",\"success\":true,\"files\":[");

    FILE *f = fopen(WRT_RECENT_FILE, "r");
    int count = 0;
    if (f) {
        char buf[PATH_MAX];
        while (fgets(buf, sizeof(buf), f) && count < 20) {
            size_t l = strlen(buf);
            while (l > 0 && (buf[l - 1] == '\n' || buf[l - 1] == '\r')) buf[--l] = '\0';
            if (l == 0) continue;

            struct stat st;
            int exists = (stat(buf, &st) == 0 && !S_ISDIR(st.st_mode));
            long size = exists ? (long)st.st_size : 0;
            long mtime = exists ? (long)st.st_mtime : 0;

            const char *base = strrchr(buf, '/');
            const char *name = base ? base + 1 : buf;

            if (count > 0) buf_append(&b, ",");
            buf_append(&b, "{\"name\":\"");
            buf_append_json_escaped(&b, name);
            buf_append(&b, "\",\"path\":\"");
            buf_append_json_escaped(&b, buf);
            buf_append(&b, "\",\"exists\":");
            buf_append(&b, exists ? "true" : "false");
            buf_append(&b, ",\"size\":");
            char num[32];
            snprintf(num, sizeof(num), "%ld", size);
            buf_append(&b, num);
            buf_append(&b, ",\"mtime\":");
            snprintf(num, sizeof(num), "%ld", mtime);
            buf_append(&b, num);
            buf_append(&b, "}");
            count++;
        }
        fclose(f);
    }

    buf_append(&b, "]}\n");
    return b.data;
}

char *wrt_list_files_json(const char *dir_path) {
    const char *target_dir = dir_path;
    if (!target_dir || !target_dir[0]) {
        target_dir = "/workspaces/AladdinAI";
    }

    char resolved[PATH_MAX];
    if (realpath(target_dir, resolved) == NULL) {
        strncpy(resolved, target_dir, sizeof(resolved) - 1);
        resolved[sizeof(resolved) - 1] = '\0';
    }

    DIR *dir = opendir(resolved);
    if (!dir) {
        str_buf_t err;
        buf_init(&err);
        buf_append(&err, "{\"type\":\"list_files_result\",\"success\":false,\"error\":\"Cannot open directory\",\"path\":\"");
        buf_append_json_escaped(&err, resolved);
        buf_append(&err, "\",\"files\":[]}\n");
        return err.data;
    }

    wrt_file_entry_t *entries = malloc(WRT_MAX_DIR_ENTRIES * sizeof(wrt_file_entry_t));
    int count = 0;

    struct dirent *de;
    while ((de = readdir(dir)) != NULL && count < WRT_MAX_DIR_ENTRIES) {
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0) continue;
        if (strcmp(de->d_name, ".git") == 0) continue;

        wrt_file_entry_t *e = &entries[count];
        strncpy(e->name, de->d_name, sizeof(e->name) - 1);
        e->name[sizeof(e->name) - 1] = '\0';

        snprintf(e->path, sizeof(e->path), "%s/%s", resolved, de->d_name);

        struct stat st;
        if (stat(e->path, &st) == 0) {
            e->is_dir = S_ISDIR(st.st_mode) ? 1 : 0;
            e->size = (long)st.st_size;
            e->mtime = (long)st.st_mtime;
        } else {
            e->is_dir = 0;
            e->size = 0;
            e->mtime = 0;
        }

        const char *ext = get_file_extension(e->name);
        strncpy(e->ext, ext, sizeof(e->ext) - 1);
        e->ext[sizeof(e->ext) - 1] = '\0';

        count++;
    }
    closedir(dir);

    qsort(entries, count, sizeof(wrt_file_entry_t), compare_file_entries);

    str_buf_t b;
    buf_init(&b);
    buf_append(&b, "{\"type\":\"list_files_result\",\"success\":true,\"path\":\"");
    buf_append_json_escaped(&b, resolved);
    buf_append(&b, "\",\"count\":");
    char num[32];
    snprintf(num, sizeof(num), "%d", count);
    buf_append(&b, num);
    buf_append(&b, ",\"files\":[");

    for (int i = 0; i < count; i++) {
        if (i > 0) buf_append(&b, ",");
        buf_append(&b, "{\"name\":\"");
        buf_append_json_escaped(&b, entries[i].name);
        buf_append(&b, "\",\"path\":\"");
        buf_append_json_escaped(&b, entries[i].path);
        buf_append(&b, "\",\"is_dir\":");
        buf_append(&b, entries[i].is_dir ? "true" : "false");
        buf_append(&b, ",\"size\":");
        snprintf(num, sizeof(num), "%ld", entries[i].size);
        buf_append(&b, num);
        buf_append(&b, ",\"mtime\":");
        snprintf(num, sizeof(num), "%ld", entries[i].mtime);
        buf_append(&b, num);
        buf_append(&b, ",\"ext\":\"");
        buf_append_json_escaped(&b, entries[i].ext);
        buf_append(&b, "\"}");
    }

    buf_append(&b, "]}\n");
    free(entries);
    return b.data;
}

char *wrt_read_file_json(const char *file_path) {
    str_buf_t b;
    buf_init(&b);

    if (!file_path || !file_path[0]) {
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"No path provided\"}\n");
        return b.data;
    }

    struct stat st;
    if (stat(file_path, &st) != 0) {
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"File not found: ");
        buf_append_json_escaped(&b, file_path);
        buf_append(&b, "\"}\n");
        return b.data;
    }

    if (S_ISDIR(st.st_mode)) {
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"Path is a directory\"}\n");
        return b.data;
    }

    FILE *fp = fopen(file_path, "rb");
    if (!fp) {
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"Cannot open file\"}\n");
        return b.data;
    }

    str_buf_t content;
    buf_init(&content);
    char chunk[4096];
    size_t n;
    int line_count = 1;
    while ((n = fread(chunk, 1, sizeof(chunk), fp)) > 0) {
        for (size_t i = 0; i < n; i++) {
            if (chunk[i] == '\n') line_count++;
        }
        buf_append_len(&content, chunk, n);
    }
    fclose(fp);

    wrt_record_recent_file(file_path);

    buf_append(&b, "{\"type\":\"read_file_result\",\"success\":true,\"path\":\"");
    buf_append_json_escaped(&b, file_path);
    buf_append(&b, "\",\"size\":");
    char num[32];
    snprintf(num, sizeof(num), "%ld", (long)content.len);
    buf_append(&b, num);
    buf_append(&b, ",\"lines\":");
    snprintf(num, sizeof(num), "%d", line_count);
    buf_append(&b, num);
    buf_append(&b, ",\"content\":\"");
    buf_append_json_escaped(&b, content.data);
    buf_append(&b, "\"}\n");

    free(content.data);
    return b.data;
}

char *wrt_save_file_json(const char *file_path, const char *content) {
    str_buf_t b;
    buf_init(&b);

    if (!file_path || !file_path[0]) {
        buf_append(&b, "{\"type\":\"save_file_result\",\"success\":false,\"error\":\"No path specified\"}\n");
        return b.data;
    }

    make_parent_dirs(file_path);

    FILE *fp = fopen(file_path, "wb");
    if (!fp) {
        buf_append(&b, "{\"type\":\"save_file_result\",\"success\":false,\"error\":\"Cannot open file for writing: ");
        buf_append_json_escaped(&b, file_path);
        buf_append(&b, "\"}\n");
        return b.data;
    }

    size_t len = content ? strlen(content) : 0;
    if (len > 0) {
        size_t written = fwrite(content, 1, len, fp);
        if (written != len) {
            fclose(fp);
            buf_append(&b, "{\"type\":\"save_file_result\",\"success\":false,\"error\":\"Write failed\"}\n");
            return b.data;
        }
    }
    fclose(fp);

    wrt_record_recent_file(file_path);

    buf_append(&b, "{\"type\":\"save_file_result\",\"success\":true,\"path\":\"");
    buf_append_json_escaped(&b, file_path);
    buf_append(&b, "\",\"bytes_written\":");
    char num[32];
    snprintf(num, sizeof(num), "%zu", len);
    buf_append(&b, num);
    buf_append(&b, "}\n");
    return b.data;
}

/* ============================================================
 * UNIX DOMAIN SOCKET DAEMON
 * ============================================================ */

static volatile int g_daemon_running = 1;
static void daemon_sig_handler(int sig) {
    (void)sig;
    g_daemon_running = 0;
}

static void handle_daemon_request(int client_fd, const char *req) {
    char *action = extract_json_string(req, "action");
    char *content = extract_json_string(req, "content");
    char *path = extract_json_string(req, "path");
    const char *doc = content ? content : "";

    str_buf_t resp;
    buf_init(&resp);

    if (action && strcmp(action, "validate") == 0) {
        wrt_report_t rep;
        wrt_validate(doc, &rep);
        char *json = wrt_report_to_json(&rep);
        buf_append(&resp, "{\"type\":\"validate_result\",\"data\":");
        buf_append(&resp, json);
        buf_append(&resp, "}\n");
        free(json);
    } else if (action && strcmp(action, "fix") == 0) {
        char *fixed = wrt_fix(doc);
        buf_append(&resp, "{\"type\":\"fix_result\",\"content\":\"");
        buf_append_json_escaped(&resp, fixed);
        buf_append(&resp, "\"}\n");
        free(fixed);
    } else if (action && strcmp(action, "to-html") == 0) {
        char *html = wrt_to_html(doc);
        buf_append(&resp, "{\"type\":\"to_html_result\",\"html\":\"");
        buf_append_json_escaped(&resp, html);
        buf_append(&resp, "\"}\n");
        free(html);
    } else if (action && strcmp(action, "stats") == 0) {
        wrt_report_t rep;
        wrt_validate(doc, &rep);
        char num[32];
        buf_append(&resp, "{\"type\":\"stats_result\",\"lines\":");
        snprintf(num, sizeof(num), "%d", rep.line_count); buf_append(&resp, num);
        buf_append(&resp, ",\"words\":");
        snprintf(num, sizeof(num), "%d", rep.word_count); buf_append(&resp, num);
        buf_append(&resp, ",\"chars\":");
        snprintf(num, sizeof(num), "%d", rep.char_count); buf_append(&resp, num);
        buf_append(&resp, ",\"tags\":");
        snprintf(num, sizeof(num), "%d", rep.tag_count); buf_append(&resp, num);
        buf_append(&resp, ",\"valid\":");
        buf_append(&resp, rep.valid ? "true" : "false");
        buf_append(&resp, "}\n");
    } else if (action && strcmp(action, "list_files") == 0) {
        char *json = wrt_list_files_json(path);
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "read_file") == 0) {
        char *json = wrt_read_file_json(path);
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "save_file") == 0) {
        char *json = wrt_save_file_json(path, doc);
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "recent_files") == 0) {
        char *json = wrt_get_recent_files_json();
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "docx_to_wrt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing path parameter for docx_to_wrt\"}\n");
        } else {
            FILE *f = fopen(path, "rb");
            if (!f) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Cannot open docx file\"}\n");
            } else {
                fseek(f, 0, SEEK_END);
                long sz = ftell(f);
                fseek(f, 0, SEEK_SET);
                unsigned char *data = (unsigned char *)malloc(sz);
                if (fread(data, 1, sz, f) != (size_t)sz) {
                    free(data); fclose(f);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed reading docx file\"}\n");
                } else {
                    fclose(f);
                    char *wrt = docx_to_wrt(data, sz);
                    free(data);
                    if (!wrt) {
                        buf_append(&resp, "{\"type\":\"error\",\"message\":\"docx conversion failed\"}\n");
                    } else {
                        buf_append(&resp, "{\"type\":\"docx_to_wrt_result\",\"content\":\"");
                        buf_append_json_escaped(&resp, wrt);
                        buf_append(&resp, "\"}\n");
                        free(wrt);
                    }
                }
            }
        }
    } else if (action && strcmp(action, "wrt_to_docx") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing output path parameter for wrt_to_docx\"}\n");
        } else {
            size_t out_len = 0;
            unsigned char *docx_bytes = wrt_to_docx(doc, &out_len);
            if (!docx_bytes || out_len == 0) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed converting wrt to docx\"}\n");
            } else {
                FILE *f = fopen(path, "wb");
                if (!f) {
                    free(docx_bytes);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed opening output docx file\"}\n");
                } else {
                    fwrite(docx_bytes, 1, out_len, f);
                    fclose(f);
                    free(docx_bytes);
                    char num[32];
                    snprintf(num, sizeof(num), "%zu", out_len);
                    buf_append(&resp, "{\"type\":\"wrt_to_docx_result\",\"bytes\":");
                    buf_append(&resp, num);
                    buf_append(&resp, ",\"path\":\"");
                    buf_append_json_escaped(&resp, path);
                    buf_append(&resp, "\"}\n");
                }
            }
        }
    } else if (action && strcmp(action, "md_to_wrt") == 0) {
        char *wrt = wrt_markdown_to_wrt(doc);
        buf_append(&resp, "{\"type\":\"md_to_wrt_result\",\"content\":\"");
        buf_append_json_escaped(&resp, wrt ? wrt : "");
        buf_append(&resp, "\"}\n");
        free(wrt);
    } else if (action && strcmp(action, "wrt_to_md") == 0) {
        char *md = wrt_to_markdown(doc);
        buf_append(&resp, "{\"type\":\"wrt_to_md_result\",\"content\":\"");
        buf_append_json_escaped(&resp, md ? md : "");
        buf_append(&resp, "\"}\n");
        free(md);
    } else if (action && strcmp(action, "odt_to_wrt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing path parameter for odt_to_wrt\"}\n");
        } else {
            FILE *f = fopen(path, "rb");
            if (!f) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Cannot open odt file\"}\n");
            } else {
                fseek(f, 0, SEEK_END);
                long sz = ftell(f);
                fseek(f, 0, SEEK_SET);
                unsigned char *data = (unsigned char *)malloc(sz);
                if (fread(data, 1, sz, f) != (size_t)sz) {
                    free(data); fclose(f);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed reading odt file\"}\n");
                } else {
                    fclose(f);
                    char *wrt = odt_to_wrt(data, sz);
                    free(data);
                    if (!wrt) {
                        buf_append(&resp, "{\"type\":\"error\",\"message\":\"odt conversion failed\"}\n");
                    } else {
                        buf_append(&resp, "{\"type\":\"odt_to_wrt_result\",\"content\":\"");
                        buf_append_json_escaped(&resp, wrt);
                        buf_append(&resp, "\"}\n");
                        free(wrt);
                    }
                }
            }
        }
    } else if (action && strcmp(action, "wrt_to_odt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing output path parameter for wrt_to_odt\"}\n");
        } else {
            size_t out_len = 0;
            unsigned char *odt_bytes = wrt_to_odt(doc, &out_len);
            if (!odt_bytes || out_len == 0) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed converting wrt to odt\"}\n");
            } else {
                FILE *f = fopen(path, "wb");
                if (!f) {
                    free(odt_bytes);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed opening output odt file\"}\n");
                } else {
                    fwrite(odt_bytes, 1, out_len, f);
                    fclose(f);
                    free(odt_bytes);
                    char num[32];
                    snprintf(num, sizeof(num), "%zu", out_len);
                    buf_append(&resp, "{\"type\":\"wrt_to_odt_result\",\"bytes\":");
                    buf_append(&resp, num);
                    buf_append(&resp, ",\"path\":\"");
                    buf_append_json_escaped(&resp, path);
                    buf_append(&resp, "\"}\n");
                }
            }
        }
    } else if (action && strcmp(action, "pptx_to_wrt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing path parameter for pptx_to_wrt\"}\n");
        } else {
            FILE *f = fopen(path, "rb");
            if (!f) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Cannot open pptx file\"}\n");
            } else {
                fseek(f, 0, SEEK_END);
                long sz = ftell(f);
                fseek(f, 0, SEEK_SET);
                unsigned char *data = (unsigned char *)malloc(sz);
                if (fread(data, 1, sz, f) != (size_t)sz) {
                    free(data); fclose(f);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed reading pptx file\"}\n");
                } else {
                    fclose(f);
                    char *wrt = pptx_to_wrt(data, sz);
                    free(data);
                    if (!wrt) {
                        buf_append(&resp, "{\"type\":\"error\",\"message\":\"pptx conversion failed\"}\n");
                    } else {
                        buf_append(&resp, "{\"type\":\"pptx_to_wrt_result\",\"content\":\"");
                        buf_append_json_escaped(&resp, wrt);
                        buf_append(&resp, "\"}\n");
                        free(wrt);
                    }
                }
            }
        }
    } else if (action && strcmp(action, "wrt_to_pptx") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing output path parameter for wrt_to_pptx\"}\n");
        } else {
            size_t out_len = 0;
            unsigned char *pptx_bytes = wrt_to_pptx(doc, &out_len);
            if (!pptx_bytes || out_len == 0) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed converting wrt to pptx\"}\n");
            } else {
                FILE *f = fopen(path, "wb");
                if (!f) {
                    free(pptx_bytes);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed opening output pptx file\"}\n");
                } else {
                    fwrite(pptx_bytes, 1, out_len, f);
                    fclose(f);
                    free(pptx_bytes);
                    char num[32];
                    snprintf(num, sizeof(num), "%zu", out_len);
                    buf_append(&resp, "{\"type\":\"wrt_to_pptx_result\",\"bytes\":");
                    buf_append(&resp, num);
                    buf_append(&resp, ",\"path\":\"");
                    buf_append_json_escaped(&resp, path);
                    buf_append(&resp, "\"}\n");
                }
            }
        }
    } else if (action && strcmp(action, "ping") == 0) {
        buf_append(&resp, "{\"type\":\"pong\",\"version\":\"" WRT_ENGINE_VERSION "\"}\n");
    } else {
        buf_append(&resp, "{\"type\":\"error\",\"message\":\"Unknown or missing action\"}\n");
    }

    if (resp.len > 0) {
        ssize_t written = 0;
        while (written < (ssize_t)resp.len) {
            ssize_t n = write(client_fd, resp.data + written, resp.len - written);
            if (n <= 0) break;
            written += n;
        }
    }

    free(action);
    free(content);
    free(path);
    free(resp.data);
}

int wrt_engine_daemon(const char *socket_path) {
    if (!socket_path) socket_path = DEFAULT_WRT_SOCKET_PATH;

    signal(SIGINT, daemon_sig_handler);
    signal(SIGTERM, daemon_sig_handler);
    signal(SIGPIPE, SIG_IGN);

    unlink(socket_path);

    int server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("unix socket failed");
        return 1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socket_path, sizeof(addr.sun_path) - 1);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("unix bind failed");
        close(server_fd);
        return 1;
    }

    chmod(socket_path, 0666);

    if (listen(server_fd, 32) < 0) {
        perror("unix listen failed");
        close(server_fd);
        return 1;
    }

    printf("[Aladdin WRT Engine Daemon] Listening on Unix Socket: %s\n", socket_path);
    fflush(stdout);

    while (g_daemon_running) {
        struct pollfd pfd;
        pfd.fd = server_fd;
        pfd.events = POLLIN;
        int ret = poll(&pfd, 1, 1000);
        if (ret <= 0) continue;

        int client_fd = accept(server_fd, NULL, NULL);
        if (client_fd < 0) continue;

        str_buf_t in;
        buf_init(&in);
        char chunk[4096];
        ssize_t n;
        while ((n = read(client_fd, chunk, sizeof(chunk))) > 0) {
            buf_append_len(&in, chunk, (size_t)n);
            if (strchr(chunk, '\n')) break;
        }

        if (in.len > 0) {
            handle_daemon_request(client_fd, in.data);
        }

        free(in.data);
        close(client_fd);
    }

    close(server_fd);
    unlink(socket_path);
    return 0;
}

/* ============================================================
 * CLI ENTRY POINT
 * ============================================================ */

static char *read_file_or_stdin(const char *path) {
    FILE *f = (!path || strcmp(path, "-") == 0) ? stdin : fopen(path, "r");
    if (!f) return NULL;

    str_buf_t b;
    buf_init(&b);

    char chunk[4096];
    size_t n;
    while ((n = fread(chunk, 1, sizeof(chunk), f)) > 0) {
        buf_append_len(&b, chunk, n);
    }

    if (f != stdin) fclose(f);
    return b.data;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "AladdinAI Native C WRT Engine v%s\n", WRT_ENGINE_VERSION);
        fprintf(stderr, "Usage: %s <validate|fix|to-html|stats> [file|-]\n", argv[0]);
        fprintf(stderr, "       %s <list-files> [dir_path]\n", argv[0]);
        fprintf(stderr, "       %s <read-file> <file_path>\n", argv[0]);
        fprintf(stderr, "       %s <save-file> <file_path> [content_file|-]\n", argv[0]);
        fprintf(stderr, "       %s <recent-files>\n", argv[0]);
        fprintf(stderr, "       %s --daemon [socket_path]\n", argv[0]);
        return 1;
    }

    const char *cmd = argv[1];

    if (strcmp(cmd, "--daemon") == 0) {
        const char *socket_path = (argc >= 3) ? argv[2] : DEFAULT_WRT_SOCKET_PATH;
        return wrt_engine_daemon(socket_path);
    }

    if (strcmp(cmd, "list-files") == 0) {
        const char *dir = (argc >= 3) ? argv[2] : "/workspaces/AladdinAI";
        char *json = wrt_list_files_json(dir);
        fputs(json, stdout);
        free(json);
        return 0;
    } else if (strcmp(cmd, "read-file") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s read-file <file_path>\n", argv[0]);
            return 1;
        }
        char *json = wrt_read_file_json(argv[2]);
        fputs(json, stdout);
        free(json);
        return 0;
    } else if (strcmp(cmd, "save-file") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s save-file <file_path> [content_file|-]\n", argv[0]);
            return 1;
        }
        const char *file_path = argv[2];
        const char *src = (argc >= 4) ? argv[3] : "-";
        char *data = read_file_or_stdin(src);
        if (!data) data = strdup("");
        char *json = wrt_save_file_json(file_path, data);
        fputs(json, stdout);
        free(json);
        free(data);
        return 0;
    } else if (strcmp(cmd, "recent-files") == 0) {
        char *json = wrt_get_recent_files_json();
        fputs(json, stdout);
        free(json);
        return 0;
    } else if (strcmp(cmd, "docx-to-wrt") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s docx-to-wrt <input.docx> [output.wrt|-]\n", argv[0]);
            return 1;
        }
        const char *docx_in = argv[2];
        const char *wrt_out = (argc >= 4) ? argv[3] : "-";
        FILE *f = fopen(docx_in, "rb");
        if (!f) {
            fprintf(stderr, "Error: Cannot open docx '%s'\n", docx_in);
            return 1;
        }
        fseek(f, 0, SEEK_END);
        long fsize = ftell(f);
        fseek(f, 0, SEEK_SET);
        unsigned char *data = (unsigned char *)malloc(fsize);
        if (fread(data, 1, fsize, f) != (size_t)fsize) {
            free(data); fclose(f);
            fprintf(stderr, "Error reading docx '%s'\n", docx_in);
            return 1;
        }
        fclose(f);
        char *wrt = docx_to_wrt(data, fsize);
        free(data);
        if (!wrt) {
            fprintf(stderr, "Error converting docx to wrt\n");
            return 1;
        }
        if (strcmp(wrt_out, "-") == 0) {
            fputs(wrt, stdout);
        } else {
            FILE *of = fopen(wrt_out, "w");
            if (!of) { free(wrt); fprintf(stderr, "Cannot write to '%s'\n", wrt_out); return 1; }
            fputs(wrt, of);
            fclose(of);
        }
        free(wrt);
        return 0;
    } else if (strcmp(cmd, "wrt-to-docx") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Usage: %s wrt-to-docx <input.wrt> <output.docx>\n", argv[0]);
            return 1;
        }
        const char *wrt_in = argv[2];
        const char *docx_out = argv[3];
        char *text = read_file_or_stdin(wrt_in);
        if (!text) {
            fprintf(stderr, "Error reading wrt '%s'\n", wrt_in);
            return 1;
        }
        size_t out_len = 0;
        unsigned char *docx_bytes = wrt_to_docx(text, &out_len);
        free(text);
        if (!docx_bytes || out_len == 0) {
            fprintf(stderr, "Error converting wrt to docx\n");
            return 1;
        }
        FILE *of = fopen(docx_out, "wb");
        if (!of) {
            free(docx_bytes);
            fprintf(stderr, "Cannot write to '%s'\n", docx_out);
            return 1;
        }
        fwrite(docx_bytes, 1, out_len, of);
        fclose(of);
        free(docx_bytes);
        return 0;
    } else if (strcmp(cmd, "md-to-wrt") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s md-to-wrt <input.md> [output.wrt|-]\n", argv[0]);
            return 1;
        }
        const char *md_in = argv[2];
        const char *wrt_out = (argc >= 4) ? argv[3] : "-";
        char *text = read_file_or_stdin(md_in);
        if (!text) {
            fprintf(stderr, "Error reading md '%s'\n", md_in);
            return 1;
        }
        char *wrt = wrt_markdown_to_wrt(text);
        free(text);
        if (!wrt) return 1;
        if (strcmp(wrt_out, "-") == 0) {
            fputs(wrt, stdout);
        } else {
            FILE *of = fopen(wrt_out, "w");
            if (!of) { free(wrt); return 1; }
            fputs(wrt, of);
            fclose(of);
        }
        free(wrt);
        return 0;
    } else if (strcmp(cmd, "wrt-to-md") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s wrt-to-md <input.wrt> [output.md|-]\n", argv[0]);
            return 1;
        }
        const char *wrt_in = argv[2];
        const char *md_out = (argc >= 4) ? argv[3] : "-";
        char *text = read_file_or_stdin(wrt_in);
        if (!text) {
            fprintf(stderr, "Error reading wrt '%s'\n", wrt_in);
            return 1;
        }
        char *md = wrt_to_markdown(text);
        free(text);
        if (!md) return 1;
        if (strcmp(md_out, "-") == 0) {
            fputs(md, stdout);
        } else {
            FILE *of = fopen(md_out, "w");
            if (!of) { free(md); return 1; }
            fputs(md, of);
            fclose(of);
        }
        free(md);
        return 0;
    } else if (strcmp(cmd, "odt-to-wrt") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s odt-to-wrt <input.odt> [output.wrt|-]\n", argv[0]);
            return 1;
        }
        const char *odt_in = argv[2];
        const char *wrt_out = (argc >= 4) ? argv[3] : "-";
        FILE *f = fopen(odt_in, "rb");
        if (!f) {
            fprintf(stderr, "Error: Cannot open odt '%s'\n", odt_in);
            return 1;
        }
        fseek(f, 0, SEEK_END);
        long fsize = ftell(f);
        fseek(f, 0, SEEK_SET);
        unsigned char *data = (unsigned char *)malloc(fsize);
        if (fread(data, 1, fsize, f) != (size_t)fsize) {
            free(data); fclose(f);
            fprintf(stderr, "Error reading odt '%s'\n", odt_in);
            return 1;
        }
        fclose(f);
        char *wrt = odt_to_wrt(data, fsize);
        free(data);
        if (!wrt) {
            fprintf(stderr, "Error converting odt to wrt\n");
            return 1;
        }
        if (strcmp(wrt_out, "-") == 0) {
            fputs(wrt, stdout);
        } else {
            FILE *of = fopen(wrt_out, "w");
            if (!of) { free(wrt); return 1; }
            fputs(wrt, of);
            fclose(of);
        }
        free(wrt);
        return 0;
    } else if (strcmp(cmd, "wrt-to-odt") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Usage: %s wrt-to-odt <input.wrt> <output.odt>\n", argv[0]);
            return 1;
        }
        const char *wrt_in = argv[2];
        const char *odt_out = argv[3];
        char *text = read_file_or_stdin(wrt_in);
        if (!text) {
            fprintf(stderr, "Error reading wrt '%s'\n", wrt_in);
            return 1;
        }
        size_t out_len = 0;
        unsigned char *odt_bytes = wrt_to_odt(text, &out_len);
        free(text);
        if (!odt_bytes || out_len == 0) {
            fprintf(stderr, "Error converting wrt to odt\n");
            return 1;
        }
        FILE *of = fopen(odt_out, "wb");
        if (!of) {
            free(odt_bytes);
            fprintf(stderr, "Cannot write to '%s'\n", odt_out);
            return 1;
        }
        fwrite(odt_bytes, 1, out_len, of);
        fclose(of);
        free(odt_bytes);
        return 0;
    } else if (strcmp(cmd, "pptx-to-wrt") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s pptx-to-wrt <input.pptx> [output.wrt|-]\n", argv[0]);
            return 1;
        }
        const char *pptx_in = argv[2];
        const char *wrt_out = (argc >= 4) ? argv[3] : "-";
        FILE *f = fopen(pptx_in, "rb");
        if (!f) {
            fprintf(stderr, "Error: Cannot open pptx '%s'\n", pptx_in);
            return 1;
        }
        fseek(f, 0, SEEK_END);
        long fsize = ftell(f);
        fseek(f, 0, SEEK_SET);
        unsigned char *data = (unsigned char *)malloc(fsize);
        if (fread(data, 1, fsize, f) != (size_t)fsize) {
            free(data); fclose(f);
            fprintf(stderr, "Error reading pptx '%s'\n", pptx_in);
            return 1;
        }
        fclose(f);
        char *wrt = pptx_to_wrt(data, fsize);
        free(data);
        if (!wrt) {
            fprintf(stderr, "Error converting pptx to wrt\n");
            return 1;
        }
        if (strcmp(wrt_out, "-") == 0) {
            fputs(wrt, stdout);
        } else {
            FILE *of = fopen(wrt_out, "w");
            if (!of) { free(wrt); return 1; }
            fputs(wrt, of);
            fclose(of);
        }
        free(wrt);
        return 0;
    } else if (strcmp(cmd, "wrt-to-pptx") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Usage: %s wrt-to-pptx <input.wrt> <output.pptx>\n", argv[0]);
            return 1;
        }
        const char *wrt_in = argv[2];
        const char *pptx_out = argv[3];
        char *text = read_file_or_stdin(wrt_in);
        if (!text) {
            fprintf(stderr, "Error reading wrt '%s'\n", wrt_in);
            return 1;
        }
        size_t out_len = 0;
        unsigned char *pptx_bytes = wrt_to_pptx(text, &out_len);
        free(text);
        if (!pptx_bytes || out_len == 0) {
            fprintf(stderr, "Error converting wrt to pptx\n");
            return 1;
        }
        FILE *of = fopen(pptx_out, "wb");
        if (!of) {
            free(pptx_bytes);
            fprintf(stderr, "Cannot write to '%s'\n", pptx_out);
            return 1;
        }
        fwrite(pptx_bytes, 1, out_len, of);
        fclose(of);
        free(pptx_bytes);
        return 0;
    }

    const char *file = (argc >= 3) ? argv[2] : "-";

    char *text = read_file_or_stdin(file);
    if (!text) {
        fprintf(stderr, "Error: Unable to read input '%s'\n", file);
        return 1;
    }

    if (strcmp(cmd, "validate") == 0) {
        wrt_report_t rep;
        wrt_validate(text, &rep);
        char *json = wrt_report_to_json(&rep);
        printf("%s\n", json);
        free(json);
        free(text);
        return rep.valid ? 0 : 2;
    } else if (strcmp(cmd, "fix") == 0) {
        char *fixed = wrt_fix(text);
        fputs(fixed, stdout);
        free(fixed);
        free(text);
        return 0;
    } else if (strcmp(cmd, "to-html") == 0) {
        char *html = wrt_to_html(text);
        fputs(html, stdout);
        free(html);
        free(text);
        return 0;
    } else if (strcmp(cmd, "stats") == 0) {
        wrt_report_t rep;
        wrt_validate(text, &rep);
        printf("Lines:      %d\n", rep.line_count);
        printf("Words:      %d\n", rep.word_count);
        printf("Characters: %d\n", rep.char_count);
        printf("Tags:       %d\n", rep.tag_count);
        printf("Status:     %s (%d issues)\n", rep.valid ? "VALID" : "INVALID", rep.issue_count);
        free(text);
        return 0;
    } else {
        fprintf(stderr, "Unknown command: %s\n", cmd);
        free(text);
        return 1;
    }
}
