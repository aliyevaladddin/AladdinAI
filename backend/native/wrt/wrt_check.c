// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Validation and tag fixing
 */

#include "wrt_internal.h"
#include "wrt_engine.h"

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
                issue->severity = 0;
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
                                issue->severity = 0;
                            }
                            out->valid = 0;
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
        buf_append_json_escaped(&b, rep->issues[i].tag);
        buf_append(&b, "\",\"message\":\"");
        buf_append_json_escaped(&b, rep->issues[i].message);
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