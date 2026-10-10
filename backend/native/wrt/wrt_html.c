// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * HTML conversion
 */

#include "wrt_internal.h"
#include "wrt_engine.h"

/* ============================================================
 * HTML CONVERTER
 * ============================================================ */

/* Locate the ']' that closes a WRT self-closing tag such as
 *   [img src="data:image/png;base64,..." alt="logo"]
 * `start` points at the opening '['. The scan is quote-aware so a ']' inside an
 * attribute value cannot truncate the tag, and it refuses to cross a newline —
 * these tags are single-line by construction. Returns NULL if unterminated. */
static const char *find_self_closing_tag_end(const char *start, const char *limit) {
    int in_quote = 0;
    for (const char *q = start + 1; q < limit; q++) {
        if (*q == '\n') return NULL;
        if (*q == '"') { in_quote = !in_quote; continue; }
        if (!in_quote && *q == ']') return q;
    }
    return NULL;
}

/* Append the attributes of a WRT self-closing tag as escaped HTML attributes.
 * `p` points just past the tag name, `limit` at the closing ']'. The WRT
 * attribute syntax is already `name="value"`, so each value is re-escaped on the
 * way out rather than the raw region being pasted in — pasting it would turn the
 * value's own quotes into &quot; and corrupt the URL. */
static void append_wrt_attrs_as_html(str_buf_t *b, const char *p, const char *limit) {
    while (p < limit) {
        while (p < limit && isspace((unsigned char)*p)) p++;
        if (p >= limit) break;

        const char *name = p;
        while (p < limit && *p != '=' && !isspace((unsigned char)*p)) p++;
        size_t nlen = (size_t)(p - name);
        if (nlen == 0) { p++; continue; }

        while (p < limit && isspace((unsigned char)*p)) p++;
        if (p >= limit || *p != '=') {
            buf_append_c(b, ' ');
            buf_append_len(b, name, nlen);
            continue;
        }
        p++; /* '=' */
        while (p < limit && isspace((unsigned char)*p)) p++;

        if (p < limit && (*p == '"' || *p == '\'')) {
            char quote = *p++;
            buf_append_c(b, ' ');
            buf_append_len(b, name, nlen);
            buf_append(b, "=\"");
            while (p < limit && *p != quote) {
                buf_append_escaped_html(b, p, 1);
                p++;
            }
            buf_append(b, "\"");
            if (p < limit) p++; /* closing quote */
        } else {
            buf_append_c(b, ' ');
            buf_append_len(b, name, nlen);
            buf_append(b, "=\"");
            while (p < limit && !isspace((unsigned char)*p)) {
                buf_append_escaped_html(b, p, 1);
                p++;
            }
            buf_append(b, "\"");
        }
    }
}

/* Append the decoded value of HTML attribute `name` found in the tag body
 * [p, limit) to `b`. Returns 1 when the attribute was present. Entity
 * references inside the value are decoded so the reconstructed WRT tag carries
 * the original characters, not their HTML spelling. */
static int append_html_attr_value(str_buf_t *b, const char *p, const char *limit, const char *name) {
    size_t nlen = strlen(name);
    for (const char *q = p; q < limit; q++) {
        /* Require whitespace before the name so "src" cannot match inside
         * "data-src" or inside another attribute's value. */
        if (q != p && !isspace((unsigned char)q[-1])) continue;
        if (strncmp(q, name, nlen) != 0) continue;

        const char *r = q + nlen;
        while (r < limit && isspace((unsigned char)*r)) r++;
        if (r >= limit || *r != '=') continue;
        r++;
        while (r < limit && isspace((unsigned char)*r)) r++;
        if (r >= limit || (*r != '"' && *r != '\'')) continue;

        char quote = *r++;
        while (r < limit && *r != quote) {
            if (*r == '&') {
                if (strncmp(r, "&amp;", 5) == 0)       { buf_append_c(b, '&');  r += 5; continue; }
                if (strncmp(r, "&lt;", 4) == 0)        { buf_append_c(b, '<');  r += 4; continue; }
                if (strncmp(r, "&gt;", 4) == 0)        { buf_append_c(b, '>');  r += 4; continue; }
                if (strncmp(r, "&quot;", 6) == 0)      { buf_append_c(b, '"');  r += 6; continue; }
                if (strncmp(r, "&#39;", 5) == 0)       { buf_append_c(b, '\''); r += 5; continue; }
            }
            buf_append_c(b, *r);
            r++;
        }
        return 1;
    }
    return 0;
}

/* If `*p` points at an <img> element, append the equivalent WRT [img] tag to
 * `b` and advance `*p` past the element, returning 1. Returns 0 when `*p` is
 * some other tag and 1 is not the right handler. Shared by the main parse loop
 * and the heading collector, which sees inline elements before the main loop
 * does. */
static int consume_img_element(str_buf_t *b, const char **p) {
    const char *cur = *p;
    if (strncmp(cur, "<img", 4) != 0) return 0;
    if (!(cur[4] == '>' || cur[4] == ' ' || cur[4] == '/')) return 0;

    const char *tag_end = strchr(cur, '>');
    if (!tag_end) return 0; /* unterminated: leave it to the caller's skip logic */

    str_buf_t src, alt;
    buf_init(&src);
    buf_init(&alt);
    int has_src = append_html_attr_value(&src, cur + 4, tag_end, "src");
    int has_alt = append_html_attr_value(&alt, cur + 4, tag_end, "alt");

    /* Without a src there is no image data to preserve, so emitting a bare
     * [img] would only add a tag the validator flags as malformed. */
    if (has_src && src.len > 0) {
        buf_append(b, "[img src=\"");
        buf_append(b, src.data);
        if (has_alt && alt.len > 0) {
            buf_append(b, "\" alt=\"");
            buf_append(b, alt.data);
        }
        buf_append(b, "\"]");
    }
    free(src.data);
    free(alt.data);
    *p = tag_end + 1;
    return 1;
}

/* Emit a run of WRT as HTML: text escaped as usual, except [img ...], which
 * becomes a real <img> element. Needed wherever a block body (heading, quote,
 * list item, table cell) is copied in one go -- a blanket escape renders an
 * image as visible markup inside the block. */
static void append_wrt_inline_to_html(str_buf_t *b, const char *s, size_t n) {
    for (size_t i = 0; i < n; i++) {
        if (s[i] == '[' && n - i >= 5 && strncmp(s + i, "[img ", 5) == 0) {
            const char *tag_end = find_self_closing_tag_end(s + i, s + n);
            if (tag_end) {
                buf_append(b, "<img");
                append_wrt_attrs_as_html(b, s + i + 5, tag_end);
                buf_append(b, " class=\"wrt-image max-w-full rounded my-2\" />");
                i = (size_t)(tag_end - s); /* loop's i++ steps past the ']' */
                continue;
            }
        }
        buf_append_escaped_html(b, s + i, 1);
    }
}

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
                append_wrt_inline_to_html(&b, text + i + 4, end - (text + i + 4));
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
                append_wrt_inline_to_html(&b, text + i + 7, end - (text + i + 7));
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
                                append_wrt_inline_to_html(&b, cell, trim_end - cell);
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
                    append_wrt_inline_to_html(&b, item, item_end - item);
                    buf_append(&b, "</li>\n");

                    item = item_end + 1;
                }

                buf_append(&b, "</ul>\n");
                i = (end - text) + 7;
                if (i < len && text[i] == '\n') i++;
                continue;
            }
        }

        /* Check for inline image: [img src="data:image/png;base64,..." alt="logo"].
         * Previously unhandled, so the tag fell through to the escaping branch
         * and rendered as literal text — and on the way back the parser skipped
         * the <img> element entirely, dropping the image from the file. */
        if (strncmp(text + i, "[img ", 5) == 0) {
            const char *tag_end = find_self_closing_tag_end(text + i, text + len);
            if (tag_end) {
                if (!in_paragraph) {
                    buf_append(&b, "<p class=\"my-2 leading-relaxed\">");
                    in_paragraph = 1;
                }
                buf_append(&b, "<img");
                append_wrt_attrs_as_html(&b, text + i + 5, tag_end);
                buf_append(&b, " class=\"wrt-image max-w-full rounded my-2\" />");
                i = (tag_end - text) + 1;
                continue;
            }
        }

        /* Check for inline tags */
        int is_inline_open = (strncmp(text + i, "[b]", 3) == 0 ||
                              strncmp(text + i, "[i]", 3) == 0 ||
                              strncmp(text + i, "[u]", 3) == 0 ||
                              strncmp(text + i, "[s]", 3) == 0 ||
                              strncmp(text + i, "[code]", 6) == 0);
        if (is_inline_open && !in_paragraph) {
            buf_append(&b, "<p class=\"my-2 leading-relaxed\">");
            in_paragraph = 1;
        }

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
 * EDITABLE HTML CONVERTER
 * For contentEditable WYSIWYG mode
 * ============================================================ */

char *wrt_to_editable_html(const char *text) {
    if (!text || !text[0]) {
        /* Return non-empty HTML so contentEditable has a valid cursor position */
        return strdup("<p><br></p>\n");
    }

    /* First convert WRT to HTML, then ensure it starts with a block element */
    char *html = wrt_to_html(text);
    if (!html || !html[0]) {
        free(html);
        return strdup("<p><br></p>\n");
    }

    /* Ensure the HTML has a wrapping div with contentEditable-compatible structure */
    str_buf_t b;
    buf_init(&b);
    buf_append(&b, "<div class=\"wrt-editable\">\n");
    buf_append(&b, html);
    /* Ensure ends with a paragraph for cursor placement */
    size_t len = strlen(b.data);
    if (len < 5 || strcmp(b.data + len - 5, "</p>\n") != 0) {
        buf_append(&b, "<p><br></p>\n");
    }
    buf_append(&b, "</div>\n");
    free(html);
    return b.data;
}

char *wrt_from_editable_html(const char *html) {
    if (!html || !html[0]) {
        return strdup("");
    }

    str_buf_t b;
    buf_init(&b);

    /* Simple HTML → WRT converter for contentEditable output.
     * Handles: <p>, <strong>, <em>, <u>, <s>, <code>, <blockquote>,
     *          <ul>/<li>, <h1>-<h3>, <table>/<tr>/<th>/<td>, <br> */
    const char *p = html;
    int in_list = 0;
    int in_table = 0;
    int in_tr = 0;
    int in_td = 0;
    int in_blockquote = 0;
    int first_text = 1;

    while (*p) {
        /* Skip whitespace and newlines outside tags */
        if (*p == '\n' || *p == '\r') {
            p++;
            continue;
        }

        /* Skip the wrapper div */
        if (strncmp(p, "<div", 4) == 0) {
            const char *end = strchr(p, '>');
            if (end) p = end + 1;
            else { p++; continue; }
            continue;
        }

        /* Skip closing wrapper div */
        if (strncmp(p, "</div>", 6) == 0) {
            p += 6;
            continue;
        }

        /* <p> tags — open paragraph (handle as text separator) — skip entire opening tag including attributes */
        if (strncmp(p, "<p", 2) == 0 && (p[2] == '>' || p[2] == ' ')) {
            p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            /* If there was content before this p, add newline */
            if (!first_text && b.len > 0) {
                /* Check if last char isn't already a newline */
                if (b.len > 0 && b.data[b.len - 1] != '\n') {
                    buf_append_c(&b, '\n');
                }
            }
            continue;
        }

        /* </p> — paragraph separator */
        if (strncmp(p, "</p>", 4) == 0) {
            p += 4;
            if (b.len > 0 && b.data[b.len - 1] != '\n') {
                buf_append_c(&b, '\n');
            }
            first_text = 0;
            continue;
        }

        /* <br> or <br/> */
        if (strncmp(p, "<br", 3) == 0) {
            p += 3;
            if (*p == ' ' || *p == '/') {
                while (*p && *p != '>') p++;
            }
            if (*p == '>') p++;
            buf_append_c(&b, '\n');
            continue;
        }

        /* <strong> or <b> — handle attributes; boundary check to avoid matching <blockquote> etc. */
        if (strncmp(p, "<strong", 7) == 0 || (strncmp(p, "<b", 2) == 0 && (p[2] == '>' || p[2] == ' '))) {
            if (strncmp(p, "<strong", 7) == 0) {
                p += 7;
            } else {
                p += 2;
            }
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[b]");
            continue;
        }

        /* </strong> or </b> */
        if (strncmp(p, "</strong>", 9) == 0 || strncmp(p, "</b>", 4) == 0) {
            p += (strncmp(p, "</strong>", 9) == 0) ? 9 : 4;
            buf_append(&b, "[/b]");
            continue;
        }

        /* <em> or <i> — handle attributes; boundary check to avoid matching <input> etc. */
        if (strncmp(p, "<em", 3) == 0 || (strncmp(p, "<i", 2) == 0 && (p[2] == '>' || p[2] == ' '))) {
            if (strncmp(p, "<em", 3) == 0) {
                p += 3;
            } else {
                p += 2;
            }
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[i]");
            continue;
        }

        /* </em> or </i> */
        if (strncmp(p, "</em>", 5) == 0 || strncmp(p, "</i>", 4) == 0) {
            p += (strncmp(p, "</em>", 5) == 0) ? 5 : 4;
            buf_append(&b, "[/i]");
            continue;
        }

        /* <u> — handle attributes; boundary check to avoid matching <ul> etc. */
        if (strncmp(p, "<u", 2) == 0 && (p[2] == '>' || p[2] == ' ')) {
            p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[u]");
            continue;
        }

        /* </u> */
        if (strncmp(p, "</u>", 4) == 0) {
            p += 4;
            buf_append(&b, "[/u]");
            continue;
        }

        /* <s> — boundary check to avoid matching <span>, <style> etc. */
        if (strncmp(p, "<s", 2) == 0 && (p[2] == '>' || p[2] == ' ')) {
            p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[s]");
            continue;
        }

        /* </s> */
        if (strncmp(p, "</s>", 4) == 0) {
            p += 4;
            buf_append(&b, "[/s]");
            continue;
        }

        /* <code> */
        if (strncmp(p, "<code", 5) == 0) {
            p += 5;
            if (*p == ' ' || *p == '>') {
                while (*p && *p != '>') p++;
                if (*p == '>') p++;
            }
            buf_append(&b, "[code]");
            continue;
        }

        /* </code> */
        if (strncmp(p, "</code>", 7) == 0) {
            p += 7;
            buf_append(&b, "[/code]");
            continue;
        }

        /* <blockquote> */
        if (strncmp(p, "<blockquote", 11) == 0) {
            p += 11;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            (void)in_blockquote;
            buf_append(&b, "[quote]");
            continue;
        }

        /* </blockquote> */
        if (strncmp(p, "</blockquote>", 13) == 0) {
            p += 13;
            buf_append(&b, "[/quote]");
            if (b.len > 0 && b.data[b.len - 1] != '\n') {
                buf_append_c(&b, '\n');
            }
            continue;
        }

        /* <h1>, <h2>, <h3> */
        if (strncmp(p, "<h1", 3) == 0 || strncmp(p, "<h2", 3) == 0 || strncmp(p, "<h3", 3) == 0) {
            char htag = p[2]; /* '1', '2', or '3' */
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            char htag_close[6];
            snprintf(htag_close, sizeof(htag_close), "</h%c>", htag);
            /* Collect content until HTML closing tag */
            str_buf_t hcontent;
            buf_init(&hcontent);
            while (*p && strncmp(p, htag_close, strlen(htag_close)) != 0) {
                if (*p == '<') {
                    /* An image carries data, so it must not be lumped in with the
                     * inline tags that are simply dropped here. */
                    if (consume_img_element(&hcontent, &p)) continue;
                    /* Skip inline tags inside heading */
                    p++;
                    while (*p && *p != '>') p++;
                    if (*p == '>') p++;
                    continue;
                }
                buf_append_c(&hcontent, *p);
                p++;
            }
            if (*p) p += strlen(htag_close);
            buf_append(&b, "[h");
            buf_append_c(&b, htag);
            buf_append(&b, "]");
            buf_append(&b, hcontent.data);
            buf_append(&b, "[/h");
            buf_append_c(&b, htag);
            buf_append(&b, "]");
            if (b.len > 0 && b.data[b.len - 1] != '\n') {
                buf_append_c(&b, '\n');
            }
            free(hcontent.data);
            continue;
        }

        /* <ul> */
        if (strncmp(p, "<ul", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            in_list = 1;
            buf_append(&b, "[list]\n");
            continue;
        }

        /* </ul> */
        if (strncmp(p, "</ul>", 5) == 0) {
            p += 5;
            in_list = 0;
            buf_append(&b, "[/list]\n");
            continue;
        }

        /* <li> */
        if (strncmp(p, "<li", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "- ");
            continue;
        }

        /* </li> */
        if (strncmp(p, "</li>", 5) == 0) {
            p += 5;
            buf_append_c(&b, '\n');
            continue;
        }

        /* <table> */
        if (strncmp(p, "<table", 6) == 0) {
            p += 6;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            (void)in_table;
            buf_append(&b, "[table]\n");
            continue;
        }

        /* </table> */
        if (strncmp(p, "</table>", 8) == 0) {
            p += 8;
            buf_append(&b, "[/table]\n");
            continue;
        }

        /* <tr> */
        if (strncmp(p, "<tr", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            (void)in_tr;
            buf_append_c(&b, '|');
            continue;
        }

        /* </tr> */
        if (strncmp(p, "</tr>", 5) == 0) {
            p += 5;
            buf_append_c(&b, '|');
            buf_append_c(&b, '\n');
            continue;
        }

        /* <th> */
        if (strncmp(p, "<th", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            (void)in_td;
            buf_append_c(&b, '|');
            continue;
        }

        /* </th> */
        if (strncmp(p, "</th>", 5) == 0) {
            p += 5;
            buf_append_c(&b, '|');
            continue;
        }

        /* <td> */
        if (strncmp(p, "<td", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            (void)in_td;
            buf_append_c(&b, '|');
            continue;
        }

        /* </td> */
        if (strncmp(p, "</td>", 5) == 0) {
            p += 5;
            buf_append_c(&b, '|');
            continue;
        }

        /* <img ...> — round-trip back to a WRT [img] tag. This must precede the
         * generic "skip remaining tags" branch below, which swallowed the element
         * whole: every save from Visual mode silently deleted the image. */
        if (consume_img_element(&b, &p)) {
            continue;
        }

        /* Skip remaining tags (class attributes, etc.) */
        if (*p == '<') {
            p++;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            continue;
        }

        /* Skip HTML entities */
        if (*p == '&') {
            /* Convert common entities */
            if (strncmp(p, "&amp;", 5) == 0) {
                buf_append_c(&b, '&');
                p += 5;
            } else if (strncmp(p, "&lt;", 4) == 0) {
                buf_append_c(&b, '<');
                p += 4;
            } else if (strncmp(p, "&gt;", 4) == 0) {
                buf_append_c(&b, '>');
                p += 4;
            } else if (strncmp(p, "&quot;", 6) == 0) {
                buf_append_c(&b, '"');
                p += 6;
            } else if (strncmp(p, "&#39;", 5) == 0) {
                buf_append_c(&b, '\'');
                p += 5;
            } else {
                /* Unknown entity — emit literally, bounded scan */
                const char *semi = p;
                int i = 0;
                while (semi[i] && semi[i] != ';' && semi[i] != '<' && semi[i] != ' ' && i < 10) i++;
                if (semi[i] == ';') {
                    buf_append_len(&b, p, i + 1);
                    p += i + 1;
                } else {
                    buf_append_c(&b, '&');
                    p++;
                }
            }
            continue;
        }

        /* Regular text — extract until next '<' or '&' */
        const char *text_start = p;
        while (*p && *p != '<' && *p != '&') p++;
        if (p > text_start) {
            /* Trim leading whitespace from list items */
            if (in_list && first_text == 0) {
                while (text_start < p && isspace((unsigned char)*text_start)) text_start++;
            }
            if (p > text_start) {
                buf_append_len(&b, text_start, p - text_start);
            }
        }
        first_text = 0;
    }

    /* Ensure ends with newline */
    if (b.len > 0 && b.data[b.len - 1] != '\n') {
        buf_append_c(&b, '\n');
    }

    return b.data;
}