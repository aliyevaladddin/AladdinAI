// NOTICE: This file is protected under RCF-PL 
/*
 * AladdinAI — Native C ODT <-> WRT Converter
 * Ultra-fast bidirectional OpenDocument .odt <-> .wrt converter using libzip
 */

#include "wrt_odt.h"
#include "wrt_markdown.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <zip.h>
#include <sys/stat.h>

/* ============================================================
 * DYNAMIC STRING BUFFER
 * ============================================================ */

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} d_buf_t;

static void dbuf_init(d_buf_t *b) {
    b->cap = 4096;
    b->data = (char *)malloc(b->cap);
    if (b->data) b->data[0] = '\0';
    b->len = 0;
}

static void dbuf_append_len(d_buf_t *b, const char *s, size_t n) {
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

static void dbuf_append(d_buf_t *b, const char *s) {
    if (s) dbuf_append_len(b, s, strlen(s));
}

static void dbuf_append_c(d_buf_t *b, char c) {
    char str[2] = {c, '\0'};
    dbuf_append_len(b, str, 1);
}

static void dbuf_append_xml_escaped(d_buf_t *b, const char *s, size_t n) {
    if (!s) return;
    for (size_t i = 0; i < n; i++) {
        switch (s[i]) {
            case '&':  dbuf_append(b, "&amp;"); break;
            case '<':  dbuf_append(b, "&lt;"); break;
            case '>':  dbuf_append(b, "&gt;"); break;
            case '"':  dbuf_append(b, "&quot;"); break;
            case '\'': dbuf_append(b, "&apos;"); break;
            default:   dbuf_append_c(b, s[i]); break;
        }
    }
}

/* ============================================================
 * STATIC ODF ASSETS
 * ============================================================ */

static const char MIMETYPE_CONTENT[] = "application/vnd.oasis.opendocument.text";

static const char MANIFEST_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<manifest:manifest xmlns:manifest=\"urn:oasis:names:tc:opendocument:xmlns:manifest:1.0\" manifest:version=\"1.2\">\n"
    "  <manifest:file-entry manifest:full-path=\"/\" manifest:version=\"1.2\" manifest:media-type=\"application/vnd.oasis.opendocument.text\"/>\n"
    "  <manifest:file-entry manifest:full-path=\"content.xml\" manifest:media-type=\"text/xml\"/>\n"
    "  <manifest:file-entry manifest:full-path=\"styles.xml\" manifest:media-type=\"text/xml\"/>\n"
    "</manifest:manifest>\n";

static const char STYLES_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<office:document-styles xmlns:office=\"urn:oasis:names:tc:opendocument:xmlns:office:1.0\" "
    "xmlns:style=\"urn:oasis:names:tc:opendocument:xmlns:style:1.0\" "
    "xmlns:text=\"urn:oasis:names:tc:opendocument:xmlns:text:1.0\" "
    "xmlns:fo=\"urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0\" "
    "office:version=\"1.2\">\n"
    "  <office:styles>\n"
    "    <style:style style:name=\"Standard\" style:family=\"paragraph\"/>\n"
    "    <style:style style:name=\"Heading\" style:family=\"paragraph\"/>\n"
    "    <style:style style:name=\"Heading_1\" style:display-name=\"Heading 1\" style:family=\"paragraph\" style:parent-style-name=\"Heading\">\n"
    "      <style:text-properties fo:font-size=\"20pt\" fo:font-weight=\"bold\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Heading_2\" style:display-name=\"Heading 2\" style:family=\"paragraph\" style:parent-style-name=\"Heading\">\n"
    "      <style:text-properties fo:font-size=\"16pt\" fo:font-weight=\"bold\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Heading_3\" style:display-name=\"Heading 3\" style:family=\"paragraph\" style:parent-style-name=\"Heading\">\n"
    "      <style:text-properties fo:font-size=\"13pt\" fo:font-weight=\"bold\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Bold\" style:family=\"text\">\n"
    "      <style:text-properties fo:font-weight=\"bold\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Italic\" style:family=\"text\">\n"
    "      <style:text-properties fo:font-style=\"italic\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Underline\" style:family=\"text\">\n"
    "      <style:text-properties style:text-underline-style=\"solid\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Strike\" style:family=\"text\">\n"
    "      <style:text-properties style:text-line-through-style=\"solid\"/>\n"
    "    </style:style>\n"
    "    <style:style style:name=\"Code\" style:family=\"text\">\n"
    "      <style:text-properties fo:font-family=\"monospace\"/>\n"
    "    </style:style>\n"
    "  </office:styles>\n"
    "</office:document-styles>\n";

/* ============================================================
 * INLINE WRT TAG EMITTER FOR ODF
 * ============================================================ */

static void parse_and_emit_odt_inline_runs(d_buf_t *out, const char *text) {
    if (!text) return;
    const char *p = text;

    while (*p) {
        if (*p == '[') {
            if (strncmp(p, "[b]", 3) == 0) {
                const char *close = strstr(p + 3, "[/b]");
                if (close) {
                    dbuf_append(out, "<text:span text:style-name=\"Bold\">");
                    parse_and_emit_odt_inline_runs(out, strndup(p + 3, close - (p + 3)));
                    dbuf_append(out, "</text:span>");
                    p = close + 4;
                    continue;
                }
            } else if (strncmp(p, "[i]", 3) == 0) {
                const char *close = strstr(p + 3, "[/i]");
                if (close) {
                    dbuf_append(out, "<text:span text:style-name=\"Italic\">");
                    parse_and_emit_odt_inline_runs(out, strndup(p + 3, close - (p + 3)));
                    dbuf_append(out, "</text:span>");
                    p = close + 4;
                    continue;
                }
            } else if (strncmp(p, "[u]", 3) == 0) {
                const char *close = strstr(p + 3, "[/u]");
                if (close) {
                    dbuf_append(out, "<text:span text:style-name=\"Underline\">");
                    parse_and_emit_odt_inline_runs(out, strndup(p + 3, close - (p + 3)));
                    dbuf_append(out, "</text:span>");
                    p = close + 4;
                    continue;
                }
            } else if (strncmp(p, "[s]", 3) == 0) {
                const char *close = strstr(p + 3, "[/s]");
                if (close) {
                    dbuf_append(out, "<text:span text:style-name=\"Strike\">");
                    parse_and_emit_odt_inline_runs(out, strndup(p + 3, close - (p + 3)));
                    dbuf_append(out, "</text:span>");
                    p = close + 4;
                    continue;
                }
            } else if (strncmp(p, "[code]", 6) == 0) {
                const char *close = strstr(p + 6, "[/code]");
                if (close) {
                    dbuf_append(out, "<text:span text:style-name=\"Code\">");
                    dbuf_append_xml_escaped(out, p + 6, close - (p + 6));
                    dbuf_append(out, "</text:span>");
                    p = close + 7;
                    continue;
                }
            }
        }

        const char *next_tag = strchr(p, '[');
        if (!next_tag) {
            dbuf_append_xml_escaped(out, p, strlen(p));
            break;
        } else {
            if (next_tag > p) {
                dbuf_append_xml_escaped(out, p, next_tag - p);
            }
            p = next_tag;
            if (strncmp(p, "[b]", 3) != 0 && strncmp(p, "[i]", 3) != 0 &&
                strncmp(p, "[u]", 3) != 0 && strncmp(p, "[s]", 3) != 0 &&
                strncmp(p, "[code]", 6) != 0) {
                dbuf_append_xml_escaped(out, p, 1);
                p++;
            }
        }
    }
}

/* ============================================================
 * WRT -> ODT CONVERTER
 * ============================================================ */

unsigned char *wrt_to_odt(const char *wrt_text, size_t *out_len) {
    if (!wrt_text) wrt_text = "";

    char *md_converted = NULL;
    if (wrt_has_markdown(wrt_text)) {
        md_converted = wrt_markdown_to_wrt(wrt_text);
        if (md_converted) wrt_text = md_converted;
    }

    d_buf_t content_xml;
    dbuf_init(&content_xml);
    dbuf_append(&content_xml,
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<office:document-content xmlns:office=\"urn:oasis:names:tc:opendocument:xmlns:office:1.0\" "
        "xmlns:style=\"urn:oasis:names:tc:opendocument:xmlns:style:1.0\" "
        "xmlns:text=\"urn:oasis:names:tc:opendocument:xmlns:text:1.0\" "
        "xmlns:table=\"urn:oasis:names:tc:opendocument:xmlns:table:1.0\" "
        "xmlns:fo=\"urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0\" "
        "office:version=\"1.2\">\n"
        "  <office:automatic-styles>\n"
        "    <style:style style:name=\"Bold\" style:family=\"text\">\n"
        "      <style:text-properties fo:font-weight=\"bold\"/>\n"
        "    </style:style>\n"
        "    <style:style style:name=\"Italic\" style:family=\"text\">\n"
        "      <style:text-properties fo:font-style=\"italic\"/>\n"
        "    </style:style>\n"
        "    <style:style style:name=\"Underline\" style:family=\"text\">\n"
        "      <style:text-properties style:text-underline-style=\"solid\"/>\n"
        "    </style:style>\n"
        "    <style:style style:name=\"Strike\" style:family=\"text\">\n"
        "      <style:text-properties style:text-line-through-style=\"solid\"/>\n"
        "    </style:style>\n"
        "    <style:style style:name=\"Code\" style:family=\"text\">\n"
        "      <style:text-properties fo:font-family=\"monospace\"/>\n"
        "    </style:style>\n"
        "  </office:automatic-styles>\n"
        "  <office:body>\n"
        "    <office:text>\n");

    const char *p = wrt_text;
    int in_table = 0;
    int in_list = 0;

    while (*p) {
        const char *line_start = p;
        while (*p && *p != '\n') p++;
        size_t line_len = p - line_start;
        if (*p == '\n') p++;

        while (line_len > 0 && isspace((unsigned char)*line_start)) {
            line_start++;
            line_len--;
        }
        while (line_len > 0 && isspace((unsigned char)line_start[line_len - 1])) {
            line_len--;
        }

        if (line_len == 0) continue;

        char *line = (char *)malloc(line_len + 1);
        if (!line) continue;
        memcpy(line, line_start, line_len);
        line[line_len] = '\0';

        if (strcmp(line, "[table]") == 0) {
            in_table = 1;
            dbuf_append(&content_xml, "      <table:table>\n");
        } else if (strcmp(line, "[/table]") == 0) {
            in_table = 0;
            dbuf_append(&content_xml, "      </table:table>\n");
        } else if (in_table && line[0] == '|') {
            dbuf_append(&content_xml, "        <table:table-row>\n");
            char *row_copy = strdup(line);
            char *cell = strtok(row_copy + 1, "|");
            while (cell) {
                while (*cell && isspace((unsigned char)*cell)) cell++;
                size_t clen = strlen(cell);
                while (clen > 0 && isspace((unsigned char)cell[clen - 1])) clen--;
                cell[clen] = '\0';

                dbuf_append(&content_xml, "          <table:table-cell><text:p>");
                parse_and_emit_odt_inline_runs(&content_xml, cell);
                dbuf_append(&content_xml, "</text:p></table:table-cell>\n");
                cell = strtok(NULL, "|");
            }
            free(row_copy);
            dbuf_append(&content_xml, "        </table:table-row>\n");
        } else if (strcmp(line, "[list]") == 0) {
            in_list = 1;
            dbuf_append(&content_xml, "      <text:list>\n");
        } else if (strcmp(line, "[/list]") == 0) {
            in_list = 0;
            dbuf_append(&content_xml, "      </text:list>\n");
        } else if (in_list && line[0] == '*' && line[1] == ' ') {
            dbuf_append(&content_xml, "        <text:list-item><text:p>");
            parse_and_emit_odt_inline_runs(&content_xml, line + 2);
            dbuf_append(&content_xml, "</text:p></text:list-item>\n");
        } else if (strncmp(line, "[h1]", 4) == 0) {
            char *end_tag = strstr(line + 4, "[/h1]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&content_xml, "      <text:h text:outline-level=\"1\">");
            parse_and_emit_odt_inline_runs(&content_xml, line + 4);
            dbuf_append(&content_xml, "</text:h>\n");
        } else if (strncmp(line, "[h2]", 4) == 0) {
            char *end_tag = strstr(line + 4, "[/h2]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&content_xml, "      <text:h text:outline-level=\"2\">");
            parse_and_emit_odt_inline_runs(&content_xml, line + 4);
            dbuf_append(&content_xml, "</text:h>\n");
        } else if (strncmp(line, "[h3]", 4) == 0) {
            char *end_tag = strstr(line + 4, "[/h3]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&content_xml, "      <text:h text:outline-level=\"3\">");
            parse_and_emit_odt_inline_runs(&content_xml, line + 4);
            dbuf_append(&content_xml, "</text:h>\n");
        } else if (strncmp(line, "[quote]", 7) == 0) {
            char *end_tag = strstr(line + 7, "[/quote]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&content_xml, "      <text:p text:style-name=\"Quote\">");
            parse_and_emit_odt_inline_runs(&content_xml, line + 7);
            dbuf_append(&content_xml, "</text:p>\n");
        } else {
            dbuf_append(&content_xml, "      <text:p>");
            parse_and_emit_odt_inline_runs(&content_xml, line);
            dbuf_append(&content_xml, "</text:p>\n");
        }
        free(line);
    }

    dbuf_append(&content_xml,
        "    </office:text>\n"
        "  </office:body>\n"
        "</office:document-content>\n");

    // Package into ZIP using libzip
    char tmp_zip_path[64];
    snprintf(tmp_zip_path, sizeof(tmp_zip_path), "/tmp/wrt_odt_%d_%u.odt", getpid(), (unsigned)rand());

    int zip_err = 0;
    zip_t *za = zip_open(tmp_zip_path, ZIP_CREATE | ZIP_TRUNCATE, &zip_err);
    if (!za) {
        free(content_xml.data);
        if (md_converted) free(md_converted);
        *out_len = 0;
        return NULL;
    }

    // 1. mimetype (first entry, uncompressed)
    zip_source_t *s_mime = zip_source_buffer(za, MIMETYPE_CONTENT, strlen(MIMETYPE_CONTENT), 0);
    zip_int64_t idx = zip_file_add(za, "mimetype", s_mime, ZIP_FL_OVERWRITE);
    if (idx >= 0) {
        zip_set_file_compression(za, idx, ZIP_CM_STORE, 0);
    }

    // 2. META-INF/manifest.xml
    zip_source_t *s_man = zip_source_buffer(za, MANIFEST_XML, strlen(MANIFEST_XML), 0);
    zip_file_add(za, "META-INF/manifest.xml", s_man, ZIP_FL_OVERWRITE);

    // 3. styles.xml
    zip_source_t *s_sty = zip_source_buffer(za, STYLES_XML, strlen(STYLES_XML), 0);
    zip_file_add(za, "styles.xml", s_sty, ZIP_FL_OVERWRITE);

    // 4. content.xml
    zip_source_t *s_cnt = zip_source_buffer(za, content_xml.data, content_xml.len, 0);
    zip_file_add(za, "content.xml", s_cnt, ZIP_FL_OVERWRITE);

    zip_close(za);
    free(content_xml.data);

    FILE *f = fopen(tmp_zip_path, "rb");
    if (!f) {
        if (md_converted) free(md_converted);
        unlink(tmp_zip_path);
        *out_len = 0;
        return NULL;
    }
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    unsigned char *res = (unsigned char *)malloc(fsize > 0 ? fsize : 1);
    if (fsize > 0) {
        fread(res, 1, fsize, f);
    }
    fclose(f);
    unlink(tmp_zip_path);

    if (md_converted) free(md_converted);
    *out_len = (size_t)fsize;
    return res;
}

/* ============================================================
 * ODT -> WRT PARSER
 * ============================================================ */

static void parse_odt_paragraph_runs(d_buf_t *out, const char *p_content, size_t len) {
    const char *p_end = p_content + len;
    const char *scan = p_content;

    while (scan < p_end) {
        const char *tag_start = strchr(scan, '<');
        if (!tag_start || tag_start >= p_end) {
            dbuf_append_len(out, scan, p_end - scan);
            break;
        }

        if (tag_start > scan) {
            dbuf_append_len(out, scan, tag_start - scan);
        }

        const char *tag_end = strchr(tag_start, '>');
        if (!tag_end || tag_end >= p_end) break;

        size_t tname_len = tag_end - tag_start + 1;
        char *tag = strndup(tag_start, tname_len);

        if (strncmp(tag, "<text:span", 10) == 0) {
            int is_bold = (strstr(tag, "Bold") != NULL || strstr(tag, "bold") != NULL);
            int is_italic = (strstr(tag, "Italic") != NULL || strstr(tag, "italic") != NULL);
            int is_underline = (strstr(tag, "Underline") != NULL || strstr(tag, "underline") != NULL);
            int is_strike = (strstr(tag, "Strike") != NULL || strstr(tag, "strike") != NULL);
            int is_code = (strstr(tag, "Code") != NULL || strstr(tag, "monospace") != NULL || strstr(tag, "Courier") != NULL || strstr(tag, "Consolas") != NULL);

            const char *span_end = strstr(tag_end + 1, "</text:span>");
            if (span_end && span_end < p_end) {
                if (is_bold) dbuf_append(out, "[b]");
                if (is_italic) dbuf_append(out, "[i]");
                if (is_underline) dbuf_append(out, "[u]");
                if (is_strike) dbuf_append(out, "[s]");
                if (is_code) dbuf_append(out, "[code]");

                parse_odt_paragraph_runs(out, tag_end + 1, span_end - (tag_end + 1));

                if (is_code) dbuf_append(out, "[/code]");
                if (is_strike) dbuf_append(out, "[/s]");
                if (is_underline) dbuf_append(out, "[/u]");
                if (is_italic) dbuf_append(out, "[/i]");
                if (is_bold) dbuf_append(out, "[/b]");

                scan = span_end + 12; // strlen("</text:span>")
                free(tag);
                continue;
            }
        } else if (strncmp(tag, "<text:s", 7) == 0) {
            // Space element
            int count = 1;
            const char *c_attr = strstr(tag, "text:c=\"");
            if (c_attr) count = atoi(c_attr + 8);
            for (int k = 0; k < count; k++) dbuf_append_c(out, ' ');
        } else if (strncmp(tag, "<text:tab", 9) == 0) {
            dbuf_append(out, "    ");
        } else if (strncmp(tag, "<text:line-break", 16) == 0) {
            dbuf_append_c(out, '\n');
        }

        scan = tag_end + 1;
        free(tag);
    }
}

char *odt_to_wrt(const unsigned char *odt_data, size_t odt_len) {
    if (!odt_data || odt_len == 0) return strdup("");

    zip_error_t zerr;
    zip_error_init(&zerr);
    zip_source_t *src = zip_source_buffer_create(odt_data, odt_len, 0, &zerr);
    if (!src) return strdup("");

    zip_t *za = zip_open_from_source(src, ZIP_RDONLY, &zerr);
    if (!za) {
        zip_source_free(src);
        return strdup("");
    }

    // Locate content.xml
    zip_file_t *zf = zip_fopen(za, "content.xml", 0);
    if (!zf) {
        zip_close(za);
        return strdup("");
    }

    d_buf_t content_buf;
    dbuf_init(&content_buf);
    char buf[4096];
    zip_int64_t nread = 0;
    while ((nread = zip_fread(zf, buf, sizeof(buf))) > 0) {
        dbuf_append_len(&content_buf, buf, nread);
    }
    zip_fclose(zf);
    zip_close(za);

    d_buf_t out;
    dbuf_init(&out);

    const char *scan = content_buf.data;
    while (*scan) {
        // Find next XML element
        const char *elem_start = strchr(scan, '<');
        if (!elem_start) break;

        // 1. Heading: <text:h ...>
        if (strncmp(elem_start, "<text:h ", 8) == 0 || strncmp(elem_start, "<text:h>", 8) == 0) {
            const char *elem_close = strchr(elem_start, '>');
            if (!elem_close) break;

            int level = 1;
            const char *lvl = strstr(elem_start, "outline-level=\"");
            if (lvl && lvl < elem_close) {
                level = atoi(lvl + 15);
                if (level < 1) level = 1;
                if (level > 3) level = 3;
            }

            const char *tag_end = strstr(elem_close, "</text:h>");
            if (tag_end) {
                char h_open[16], h_close[16];
                snprintf(h_open, sizeof(h_open), "[h%d]", level);
                snprintf(h_close, sizeof(h_close), "[/h%d]\n\n", level);

                dbuf_append(&out, h_open);
                parse_odt_paragraph_runs(&out, elem_close + 1, tag_end - (elem_close + 1));
                dbuf_append(&out, h_close);
                scan = tag_end + 9;
                continue;
            }
        }

        // 2. Table: <table:table ...>
        if (strncmp(elem_start, "<table:table ", 13) == 0 || strncmp(elem_start, "<table:table>", 13) == 0) {
            const char *tbl_end = strstr(elem_start, "</table:table>");
            if (tbl_end) {
                dbuf_append(&out, "[table]\n");
                const char *row_scan = elem_start;
                while ((row_scan = strstr(row_scan, "<table:table-row")) != NULL && row_scan < tbl_end) {
                    const char *row_end = strstr(row_scan, "</table:table-row>");
                    if (!row_end || row_end > tbl_end) break;

                    dbuf_append(&out, "|");
                    const char *cell_scan = row_scan;
                    while ((cell_scan = strstr(cell_scan, "<table:table-cell")) != NULL && cell_scan < row_end) {
                        const char *cell_end = strstr(cell_scan, "</table:table-cell>");
                        if (!cell_end || cell_end > row_end) break;

                        const char *p_tag = strstr(cell_scan, "<text:p");
                        dbuf_append(&out, " ");
                        if (p_tag && p_tag < cell_end) {
                            const char *p_close = strchr(p_tag, '>');
                            const char *p_end = strstr(p_close, "</text:p>");
                            if (p_close && p_end && p_end < cell_end) {
                                parse_odt_paragraph_runs(&out, p_close + 1, p_end - (p_close + 1));
                            }
                        }
                        dbuf_append(&out, " |");
                        cell_scan = cell_end + 19;
                    }
                    dbuf_append(&out, "\n");
                    row_scan = row_end + 18;
                }
                dbuf_append(&out, "[/table]\n\n");
                scan = tbl_end + 14;
                continue;
            }
        }

        // 3. List: <text:list ...>
        if (strncmp(elem_start, "<text:list ", 11) == 0 || strncmp(elem_start, "<text:list>", 11) == 0) {
            const char *list_end = strstr(elem_start, "</text:list>");
            if (list_end) {
                dbuf_append(&out, "[list]\n");
                const char *item_scan = elem_start;
                while ((item_scan = strstr(item_scan, "<text:list-item")) != NULL && item_scan < list_end) {
                    const char *item_end = strstr(item_scan, "</text:list-item>");
                    if (!item_end || item_end > list_end) break;

                    const char *p_tag = strstr(item_scan, "<text:p");
                    if (p_tag && p_tag < item_end) {
                        const char *p_close = strchr(p_tag, '>');
                        const char *p_end = strstr(p_close, "</text:p>");
                        if (p_close && p_end && p_end < item_end) {
                            dbuf_append(&out, "* ");
                            parse_odt_paragraph_runs(&out, p_close + 1, p_end - (p_close + 1));
                            dbuf_append(&out, "\n");
                        }
                    }
                    item_scan = item_end + 17;
                }
                dbuf_append(&out, "[/list]\n\n");
                scan = list_end + 12;
                continue;
            }
        }

        // 4. Paragraph: <text:p ...>
        if (strncmp(elem_start, "<text:p ", 8) == 0 || strncmp(elem_start, "<text:p>", 8) == 0) {
            const char *elem_close = strchr(elem_start, '>');
            if (!elem_close) break;

            const char *p_end = strstr(elem_close, "</text:p>");
            if (p_end) {
                d_buf_t para;
                dbuf_init(&para);
                parse_odt_paragraph_runs(&para, elem_close + 1, p_end - (elem_close + 1));

                // Trim leading/trailing spaces from paragraph
                char *p_text = para.data;
                while (*p_text && isspace((unsigned char)*p_text)) p_text++;
                size_t plen = strlen(p_text);
                while (plen > 0 && isspace((unsigned char)p_text[plen - 1])) plen--;
                p_text[plen] = '\0';

                if (plen > 0) {
                    if (strstr(elem_start, "style-name=\"Quote\"") && strstr(elem_start, "style-name=\"Quote\"") < elem_close) {
                        dbuf_append(&out, "[quote]");
                        dbuf_append(&out, p_text);
                        dbuf_append(&out, "[/quote]\n\n");
                    } else {
                        dbuf_append(&out, p_text);
                        dbuf_append(&out, "\n\n");
                    }
                }
                free(para.data);
                scan = p_end + 9;
                continue;
            }
        }

        scan = elem_start + 1;
    }

    free(content_buf.data);

    // Auto-detect and convert Markdown formatting if present in the extracted text
    if (wrt_has_markdown(out.data)) {
        char *converted = wrt_markdown_to_wrt(out.data);
        if (converted) {
            free(out.data);
            return converted;
        }
    }

    return out.data;
}

/* ============================================================
 * FILE HELPERS
 * ============================================================ */

int odt_to_wrt_file(const char *odt_path, const char *wrt_path) {
    FILE *f = fopen(odt_path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    unsigned char *data = (unsigned char *)malloc(fsize > 0 ? fsize : 1);
    if (fsize > 0) fread(data, 1, fsize, f);
    fclose(f);

    char *wrt = odt_to_wrt(data, fsize);
    free(data);
    if (!wrt) return -1;

    FILE *out = fopen(wrt_path, "w");
    if (!out) {
        free(wrt);
        return -1;
    }
    fputs(wrt, out);
    fclose(out);
    free(wrt);
    return 0;
}

int wrt_to_odt_file(const char *wrt_path, const char *odt_path) {
    FILE *f = fopen(wrt_path, "r");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *data = (char *)malloc(fsize + 1);
    if (fsize > 0) fread(data, 1, fsize, f);
    data[fsize] = '\0';
    fclose(f);

    size_t out_len = 0;
    unsigned char *odt_bytes = wrt_to_odt(data, &out_len);
    free(data);
    if (!odt_bytes) return -1;

    FILE *out = fopen(odt_path, "wb");
    if (!out) {
        free(odt_bytes);
        return -1;
    }
    fwrite(odt_bytes, 1, out_len, out);
    fclose(out);
    free(odt_bytes);
    return 0;
}
