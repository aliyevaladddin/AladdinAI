// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C DOCX <-> WRT Converter
 * Ultra-fast bidirectional Word .docx <-> .wrt converter using libzip
 */

#include "wrt_docx.h"
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
    b->data[0] = '\0';
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
 * BASE64 ENCODER & DECODER
 * ============================================================ */

static const char B64_TABLE[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static char *base64_encode(const unsigned char *src, size_t len) {
    size_t out_len = 4 * ((len + 2) / 3);
    char *out = (char *)malloc(out_len + 1);
    if (!out) return NULL;

    size_t i = 0, j = 0;
    while (i < len) {
        uint32_t octet_a = i < len ? src[i++] : 0;
        uint32_t octet_b = i < len ? src[i++] : 0;
        uint32_t octet_c = i < len ? src[i++] : 0;

        uint32_t triple = (octet_a << 16) + (octet_b << 8) + octet_c;

        out[j++] = B64_TABLE[(triple >> 18) & 0x3F];
        out[j++] = B64_TABLE[(triple >> 12) & 0x3F];
        out[j++] = (i > len + 1) ? '=' : B64_TABLE[(triple >> 6) & 0x3F];
        out[j++] = (i > len) ? '=' : B64_TABLE[triple & 0x3F];
    }
    out[j] = '\0';
    return out;
}

static int b64_char_value(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

static unsigned char *base64_decode(const char *src, size_t *out_len) {
    *out_len = 0;
    if (!src) return NULL;
    size_t len = strlen(src);
    if (len == 0) return (unsigned char *)strdup("");

    // Validate characters: all chars must be valid base64, '=', or whitespace
    for (size_t i = 0; i < len; i++) {
        char c = src[i];
        if (c == '=' || isspace((unsigned char)c)) continue;
        if (b64_char_value(c) < 0) {
            return NULL; // Invalid base64 character
        }
    }

    size_t cap = (len * 3) / 4 + 4;
    unsigned char *out = (unsigned char *)malloc(cap);
    if (!out) return NULL;
    size_t j = 0;

    int buf = 0, bits = 0;
    for (size_t i = 0; i < len; i++) {
        char c = src[i];
        if (c == '=' || isspace((unsigned char)c)) continue;
        int val = b64_char_value(c);
        if (val < 0) continue;

        buf = (buf << 6) | val;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out[j++] = (unsigned char)((buf >> bits) & 0xFF);
        }
    }

    *out_len = j;
    return out;
}

/* ============================================================
 * XML ENTITY UNESCAPING
 * ============================================================ */

static void unescape_xml_into(d_buf_t *b, const char *text, size_t len) {
    size_t i = 0;
    while (i < len) {
        if (text[i] == '&') {
            if (i + 4 <= len && strncmp(text + i, "&amp;", 5) == 0) {
                dbuf_append_c(b, '&'); i += 5; continue;
            }
            if (i + 3 <= len && strncmp(text + i, "&lt;", 4) == 0) {
                dbuf_append_c(b, '<'); i += 4; continue;
            }
            if (i + 3 <= len && strncmp(text + i, "&gt;", 4) == 0) {
                dbuf_append_c(b, '>'); i += 4; continue;
            }
            if (i + 5 <= len && strncmp(text + i, "&quot;", 6) == 0) {
                dbuf_append_c(b, '"'); i += 6; continue;
            }
            if (i + 5 <= len && strncmp(text + i, "&apos;", 6) == 0) {
                dbuf_append_c(b, '\''); i += 6; continue;
            }
        }
        dbuf_append_c(b, text[i]);
        i++;
    }
}

/* ============================================================
 * OPENXML TEMPLATES FOR WRT -> DOCX
 * ============================================================ */

static const char CONTENT_TYPES_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n"
    "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n"
    "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n"
    "  <Default Extension=\"png\" ContentType=\"image/png\"/>\n"
    "  <Default Extension=\"jpeg\" ContentType=\"image/jpeg\"/>\n"
    "  <Default Extension=\"jpg\" ContentType=\"image/jpeg\"/>\n"
    "  <Default Extension=\"gif\" ContentType=\"image/gif\"/>\n"
    "  <Default Extension=\"bmp\" ContentType=\"image/bmp\"/>\n"
    "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\n"
    "  <Override PartName=\"/word/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml\"/>\n"
    "</Types>\n";

static const char ROOT_RELS_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
    "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>\n"
    "</Relationships>\n";

static const char STYLES_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<w:styles xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\n"
    "  <w:style w:type=\"paragraph\" w:default=\"1\" w:styleId=\"Normal\">\n"
    "    <w:name w:val=\"Normal\"/>\n"
    "    <w:qFormat/>\n"
    "  </w:style>\n"
    "  <w:style w:type=\"paragraph\" w:styleId=\"Heading1\">\n"
    "    <w:name w:val=\"heading 1\"/>\n"
    "    <w:basedOn w:val=\"Normal\"/>\n"
    "    <w:next w:val=\"Normal\"/>\n"
    "    <w:qFormat/>\n"
    "    <w:pPr><w:spacing w:before=\"240\" w:after=\"120\"/></w:pPr>\n"
    "    <w:rPr><w:b/><w:sz w:val=\"40\"/></w:rPr>\n"
    "  </w:style>\n"
    "  <w:style w:type=\"paragraph\" w:styleId=\"Heading2\">\n"
    "    <w:name w:val=\"heading 2\"/>\n"
    "    <w:basedOn w:val=\"Normal\"/>\n"
    "    <w:next w:val=\"Normal\"/>\n"
    "    <w:qFormat/>\n"
    "    <w:pPr><w:spacing w:before=\"180\" w:after=\"100\"/></w:pPr>\n"
    "    <w:rPr><w:b/><w:sz w:val=\"32\"/></w:rPr>\n"
    "  </w:style>\n"
    "  <w:style w:type=\"paragraph\" w:styleId=\"Heading3\">\n"
    "    <w:name w:val=\"heading 3\"/>\n"
    "    <w:basedOn w:val=\"Normal\"/>\n"
    "    <w:next w:val=\"Normal\"/>\n"
    "    <w:qFormat/>\n"
    "    <w:pPr><w:spacing w:before=\"140\" w:after=\"80\"/></w:pPr>\n"
    "    <w:rPr><w:b/><w:sz w:val=\"26\"/></w:rPr>\n"
    "  </w:style>\n"
    "  <w:style w:type=\"paragraph\" w:styleId=\"ListBullet\">\n"
    "    <w:name w:val=\"List Bullet\"/>\n"
    "    <w:basedOn w:val=\"Normal\"/>\n"
    "    <w:qFormat/>\n"
    "  </w:style>\n"
    "  <w:style w:type=\"paragraph\" w:styleId=\"Quote\">\n"
    "    <w:name w:val=\"Quote\"/>\n"
    "    <w:basedOn w:val=\"Normal\"/>\n"
    "    <w:qFormat/>\n"
    "    <w:rPr><w:i/><w:color w:val=\"555555\"/></w:rPr>\n"
    "  </w:style>\n"
    "</w:styles>\n";

/* ============================================================
 * WRT -> DOCX CONVERSION
 * ============================================================ */

typedef struct {
    char r_id[32];
    char filename[64];
    unsigned char *bytes;
    size_t size;
    char alt[256];
} docx_image_t;

#define MAX_DOCX_IMAGES 128

static void append_run_with_formatting(d_buf_t *out, const char *text, size_t len,
                                      int bold, int italic, int underline, int strike, int code) {
    if (len == 0) return;
    dbuf_append(out, "<w:r>");
    if (bold || italic || underline || strike || code) {
        dbuf_append(out, "<w:rPr>");
        if (bold) dbuf_append(out, "<w:b/>");
        if (italic) dbuf_append(out, "<w:i/>");
        if (underline) dbuf_append(out, "<w:u w:val=\"single\"/>");
        if (strike) dbuf_append(out, "<w:strike/>");
        if (code) dbuf_append(out, "<w:rFonts w:ascii=\"Courier New\" w:hAnsi=\"Courier New\"/><w:sz w:val=\"18\"/>");
        dbuf_append(out, "</w:rPr>");
    }
    dbuf_append(out, "<w:t xml:space=\"preserve\">");
    dbuf_append_xml_escaped(out, text, len);
    dbuf_append(out, "</w:t></w:r>");
}

static void parse_and_emit_inline_runs(d_buf_t *out, const char *text) {
    size_t len = strlen(text);
    size_t pos = 0;
    size_t seg_start = 0;

    int b = 0, i_tag = 0, u = 0, s = 0, code = 0;

    while (pos < len) {
        if (text[pos] == '[') {
            size_t end_bracket = pos + 1;
            while (end_bracket < len && text[end_bracket] != ']' && text[end_bracket] != '\n') {
                end_bracket++;
            }
            if (end_bracket < len && text[end_bracket] == ']') {
                size_t tag_len = end_bracket - pos + 1;
                char tag[32];
                if (tag_len < sizeof(tag)) {
                    strncpy(tag, text + pos, tag_len);
                    tag[tag_len] = '\0';

                    int is_open = (tag[1] != '/');
                    const char *tag_name = is_open ? tag + 1 : tag + 2;

                    int is_known = 0;
                    if (strncmp(tag_name, "b]", 2) == 0) {
                        append_run_with_formatting(out, text + seg_start, pos - seg_start, b, i_tag, u, s, code);
                        b = is_open; is_known = 1;
                    } else if (strncmp(tag_name, "i]", 2) == 0) {
                        append_run_with_formatting(out, text + seg_start, pos - seg_start, b, i_tag, u, s, code);
                        i_tag = is_open; is_known = 1;
                    } else if (strncmp(tag_name, "u]", 2) == 0) {
                        append_run_with_formatting(out, text + seg_start, pos - seg_start, b, i_tag, u, s, code);
                        u = is_open; is_known = 1;
                    } else if (strncmp(tag_name, "s]", 2) == 0) {
                        append_run_with_formatting(out, text + seg_start, pos - seg_start, b, i_tag, u, s, code);
                        s = is_open; is_known = 1;
                    } else if (strncmp(tag_name, "code]", 5) == 0) {
                        append_run_with_formatting(out, text + seg_start, pos - seg_start, b, i_tag, u, s, code);
                        code = is_open; is_known = 1;
                    }

                    if (is_known) {
                        pos = end_bracket + 1;
                        seg_start = pos;
                        continue;
                    }
                }
            }
        }
        pos++;
    }

    if (seg_start < len) {
        append_run_with_formatting(out, text + seg_start, len - seg_start, b, i_tag, u, s, code);
    }
}

static void emit_drawing_xml(d_buf_t *out, const char *rel_id, int doc_pr_id, const char *alt) {
    char buf[1024];
    snprintf(buf, sizeof(buf),
        "<w:r><w:drawing><wp:inline distT=\"0\" distB=\"0\" distL=\"0\" distR=\"0\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/wordprocessingDrawing\">\n"
        "  <wp:extent cx=\"5486400\" cy=\"3657600\"/>\n"
        "  <wp:docPr id=\"%d\" name=\"Picture %d\" descr=\"%s\"/>\n"
        "  <a:graphic xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\">\n"
        "    <a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">\n"
        "      <pic:pic xmlns:pic=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">\n"
        "        <pic:nvPicPr><pic:cNvPr id=\"%d\" name=\"Picture %d\"/><pic:cNvPicPr/></pic:nvPicPr>\n"
        "        <pic:blipFill>\n"
        "          <a:blip r:embed=\"%s\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"/>\n"
        "          <a:stretch><a:fillRect/></a:stretch>\n"
        "        </pic:blipFill>\n"
        "        <pic:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"5486400\" cy=\"3657600\"/></a:xfrm>\n"
        "        <a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></pic:spPr>\n"
        "      </pic:pic>\n"
        "    </a:graphicData>\n"
        "  </a:graphic>\n"
        "</wp:inline></w:drawing></w:r>",
        doc_pr_id, doc_pr_id, alt ? alt : "image", doc_pr_id, doc_pr_id, rel_id);
    dbuf_append(out, buf);
}

unsigned char *wrt_to_docx(const char *wrt_text, size_t *out_len) {
    if (!wrt_text) wrt_text = "";

    char *md_converted = NULL;
    if (wrt_has_markdown(wrt_text)) {
        md_converted = wrt_markdown_to_wrt(wrt_text);
        if (md_converted) wrt_text = md_converted;
    }

    docx_image_t images[MAX_DOCX_IMAGES];
    int image_count = 0;

    d_buf_t doc_xml;
    dbuf_init(&doc_xml);
    dbuf_append(&doc_xml,
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">\n"
        "<w:body>\n");

    const char *p = wrt_text;
    int in_table = 0;
    int in_list = 0;

    while (*p) {
        const char *line_start = p;
        while (*p && *p != '\n') p++;
        size_t line_len = p - line_start;
        if (*p == '\n') p++;

        // Trim leading and trailing whitespace
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

        // Check for Image tag: [img src="data:image/png;base64,..." alt="..."]
        if (strncmp(line, "[img ", 5) == 0) {
            char *b64_start = strstr(line, ";base64,");
            char alt_val[256] = "image";
            char *alt_ptr = strstr(line, "alt=\"");
            if (alt_ptr) {
                alt_ptr += 5;
                char *alt_end = strchr(alt_ptr, '"');
                if (alt_end) {
                    size_t alen = alt_end - alt_ptr;
                    if (alen >= sizeof(alt_val)) alen = sizeof(alt_val) - 1;
                    strncpy(alt_val, alt_ptr, alen);
                    alt_val[alen] = '\0';
                }
            }

            int handled_image = 0;
            if (b64_start && image_count < MAX_DOCX_IMAGES) {
                b64_start += 8;
                char *b64_end = strchr(b64_start, '"');
                if (b64_end) {
                    *b64_end = '\0';
                    size_t raw_len = 0;
                    unsigned char *img_data = base64_decode(b64_start, &raw_len);
                    if (img_data) {
                        int idx = image_count++;
                        snprintf(images[idx].r_id, sizeof(images[idx].r_id), "rIdImg%d", idx + 1);
                        snprintf(images[idx].filename, sizeof(images[idx].filename), "image%d.png", idx + 1);
                        images[idx].bytes = img_data;
                        images[idx].size = raw_len;
                        snprintf(images[idx].alt, sizeof(images[idx].alt), "%s", alt_val);

                        dbuf_append(&doc_xml, "<w:p>");
                        emit_drawing_xml(&doc_xml, images[idx].r_id, idx + 10, images[idx].alt);
                        dbuf_append(&doc_xml, "</w:p>\n");
                        handled_image = 1;
                    }
                }
            }

            if (!handled_image) {
                // Fallback placeholder
                dbuf_append(&doc_xml, "<w:p><w:r><w:t>[Image: ");
                dbuf_append_xml_escaped(&doc_xml, alt_val, strlen(alt_val));
                dbuf_append(&doc_xml, "]</w:t></w:r></w:p>\n");
            }
        } else if (strcmp(line, "[table]") == 0) {
            in_table = 1;
            dbuf_append(&doc_xml,
                "<w:tbl>\n"
                "  <w:tblPr>\n"
                "    <w:tblBorders>\n"
                "      <w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n"
                "      <w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n"
                "      <w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n"
                "      <w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n"
                "      <w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n"
                "      <w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n"
                "    </w:tblBorders>\n"
                "  </w:tblPr>\n");
        } else if (strcmp(line, "[/table]") == 0) {
            in_table = 0;
            dbuf_append(&doc_xml, "</w:tbl>\n");
        } else if (in_table && line[0] == '|') {
            dbuf_append(&doc_xml, "  <w:tr>\n");
            char *row_copy = strdup(line);
            char *cell = strtok(row_copy + 1, "|");
            while (cell) {
                while (*cell && isspace((unsigned char)*cell)) cell++;
                size_t clen = strlen(cell);
                while (clen > 0 && isspace((unsigned char)cell[clen - 1])) clen--;
                cell[clen] = '\0';

                dbuf_append(&doc_xml, "    <w:tc><w:p>");
                parse_and_emit_inline_runs(&doc_xml, cell);
                dbuf_append(&doc_xml, "</w:p></w:tc>\n");
                cell = strtok(NULL, "|");
            }
            free(row_copy);
            dbuf_append(&doc_xml, "  </w:tr>\n");
        } else if (strcmp(line, "[list]") == 0) {
            in_list = 1;
        } else if (strcmp(line, "[/list]") == 0) {
            in_list = 0;
        } else if (in_list && line[0] == '*' && line[1] == ' ') {
            dbuf_append(&doc_xml, "<w:p><w:pPr><w:pStyle w:val=\"ListBullet\"/></w:pPr>");
            parse_and_emit_inline_runs(&doc_xml, line + 2);
            dbuf_append(&doc_xml, "</w:p>\n");
        } else if (strncmp(line, "[h1]", 4) == 0) {
            char *end_tag = strstr(line + 4, "[/h1]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&doc_xml, "<w:p><w:pPr><w:pStyle w:val=\"Heading1\"/></w:pPr>");
            parse_and_emit_inline_runs(&doc_xml, line + 4);
            dbuf_append(&doc_xml, "</w:p>\n");
        } else if (strncmp(line, "[h2]", 4) == 0) {
            char *end_tag = strstr(line + 4, "[/h2]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&doc_xml, "<w:p><w:pPr><w:pStyle w:val=\"Heading2\"/></w:pPr>");
            parse_and_emit_inline_runs(&doc_xml, line + 4);
            dbuf_append(&doc_xml, "</w:p>\n");
        } else if (strncmp(line, "[h3]", 4) == 0) {
            char *end_tag = strstr(line + 4, "[/h3]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&doc_xml, "<w:p><w:pPr><w:pStyle w:val=\"Heading3\"/></w:pPr>");
            parse_and_emit_inline_runs(&doc_xml, line + 4);
            dbuf_append(&doc_xml, "</w:p>\n");
        } else if (strncmp(line, "[quote]", 7) == 0) {
            char *end_tag = strstr(line + 7, "[/quote]");
            if (end_tag) *end_tag = '\0';
            dbuf_append(&doc_xml, "<w:p><w:pPr><w:pStyle w:val=\"Quote\"/></w:pPr>");
            parse_and_emit_inline_runs(&doc_xml, line + 7);
            dbuf_append(&doc_xml, "</w:p>\n");
        } else {
            // Regular Paragraph
            dbuf_append(&doc_xml, "<w:p>");
            parse_and_emit_inline_runs(&doc_xml, line);
            dbuf_append(&doc_xml, "</w:p>\n");
        }
        free(line);
    }

    dbuf_append(&doc_xml, "<w:sectPr/></w:body></w:document>\n");

    // Generate word/_rels/document.xml.rels
    d_buf_t doc_rels;
    dbuf_init(&doc_rels);
    dbuf_append(&doc_rels,
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
        "  <Relationship Id=\"rIdStyles\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>\n");

    for (int i = 0; i < image_count; i++) {
        char rel_entry[512];
        snprintf(rel_entry, sizeof(rel_entry),
            "  <Relationship Id=\"%.31s\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"media/%.63s\"/>\n",
            images[i].r_id, images[i].filename);
        dbuf_append(&doc_rels, rel_entry);
    }
    dbuf_append(&doc_rels, "</Relationships>\n");

    // Package into ZIP in memory using temp file or zip buffer
    char tmp_zip_path[64] = "/tmp/aladdin_wrt_XXXXXX.docx";
    int fd = mkstemps(tmp_zip_path, 5);
    if (fd >= 0) close(fd);

    int err = 0;
    zip_t *za = zip_open(tmp_zip_path, ZIP_CREATE | ZIP_TRUNCATE, &err);
    if (!za) {
        if (md_converted) free(md_converted);
        free(doc_xml.data);
        free(doc_rels.data);
        for (int i = 0; i < image_count; i++) free(images[i].bytes);
        *out_len = 0;
        return NULL;
    }

    // Add [Content_Types].xml
    zip_source_t *s_ct = zip_source_buffer(za, CONTENT_TYPES_XML, strlen(CONTENT_TYPES_XML), 0);
    zip_file_add(za, "[Content_Types].xml", s_ct, ZIP_FL_OVERWRITE);

    // Add _rels/.rels
    zip_source_t *s_root_rels = zip_source_buffer(za, ROOT_RELS_XML, strlen(ROOT_RELS_XML), 0);
    zip_file_add(za, "_rels/.rels", s_root_rels, ZIP_FL_OVERWRITE);

    // Add word/styles.xml
    zip_source_t *s_styles = zip_source_buffer(za, STYLES_XML, strlen(STYLES_XML), 0);
    zip_file_add(za, "word/styles.xml", s_styles, ZIP_FL_OVERWRITE);

    // Add word/_rels/document.xml.rels
    zip_source_t *s_doc_rels = zip_source_buffer(za, doc_rels.data, doc_rels.len, 0);
    zip_file_add(za, "word/_rels/document.xml.rels", s_doc_rels, ZIP_FL_OVERWRITE);

    // Add word/document.xml
    zip_source_t *s_doc = zip_source_buffer(za, doc_xml.data, doc_xml.len, 0);
    zip_file_add(za, "word/document.xml", s_doc, ZIP_FL_OVERWRITE);

    // Add images to word/media/
    for (int i = 0; i < image_count; i++) {
        char zip_entry[128];
        snprintf(zip_entry, sizeof(zip_entry), "word/media/%s", images[i].filename);
        zip_source_t *s_img = zip_source_buffer(za, images[i].bytes, images[i].size, 0);
        zip_file_add(za, zip_entry, s_img, ZIP_FL_OVERWRITE);
    }

    zip_close(za);

    free(doc_xml.data);
    free(doc_rels.data);
    for (int i = 0; i < image_count; i++) free(images[i].bytes);

    // Read back temporary docx file into memory buffer
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
 * DOCX -> WRT CONVERSION
 * ============================================================ */

typedef struct {
    char id[32];
    char target[256];
} rel_item_t;

char *docx_to_wrt(const unsigned char *docx_data, size_t docx_len) {
    if (!docx_data || docx_len == 0) return strdup("");

    zip_error_t zerr;
    zip_error_init(&zerr);
    zip_source_t *src = zip_source_buffer_create(docx_data, docx_len, 0, &zerr);
    if (!src) return strdup("");

    zip_t *za = zip_open_from_source(src, ZIP_RDONLY, &zerr);
    if (!za) {
        zip_source_free(src);
        return strdup("");
    }

    // 1. Read word/_rels/document.xml.rels to resolve image relationships
    rel_item_t rels[MAX_DOCX_IMAGES];
    int rel_count = 0;

    zip_file_t *z_rels = zip_fopen(za, "word/_rels/document.xml.rels", 0);
    if (z_rels) {
        zip_stat_t st_rels;
        zip_stat(za, "word/_rels/document.xml.rels", 0, &st_rels);
        char *rels_data = (char *)malloc(st_rels.size + 1);
        zip_fread(z_rels, rels_data, st_rels.size);
        rels_data[st_rels.size] = '\0';
        zip_fclose(z_rels);

        const char *rp = rels_data;
        while ((rp = strstr(rp, "<Relationship ")) != NULL && rel_count < MAX_DOCX_IMAGES) {
            const char *id_ptr = strstr(rp, "Id=\"");
            const char *target_ptr = strstr(rp, "Target=\"");
            if (id_ptr && target_ptr) {
                id_ptr += 4;
                target_ptr += 8;
                char *id_end = strchr(id_ptr, '"');
                char *target_end = strchr(target_ptr, '"');
                if (id_end && target_end) {
                    size_t id_len = id_end - id_ptr;
                    size_t t_len = target_end - target_ptr;
                    if (id_len < sizeof(rels[rel_count].id) && t_len < sizeof(rels[rel_count].target)) {
                        strncpy(rels[rel_count].id, id_ptr, id_len);
                        rels[rel_count].id[id_len] = '\0';
                        strncpy(rels[rel_count].target, target_ptr, t_len);
                        rels[rel_count].target[t_len] = '\0';
                        rel_count++;
                    }
                }
            }
            rp += 14;
        }
        free(rels_data);
    }

    // 2. Read word/document.xml
    zip_file_t *z_doc = zip_fopen(za, "word/document.xml", 0);
    if (!z_doc) {
        zip_close(za);
        return strdup("");
    }

    zip_stat_t st_doc;
    zip_stat(za, "word/document.xml", 0, &st_doc);
    char *doc_xml = (char *)malloc(st_doc.size + 1);
    zip_fread(z_doc, doc_xml, st_doc.size);
    doc_xml[st_doc.size] = '\0';
    zip_fclose(z_doc);

    d_buf_t out;
    dbuf_init(&out);

    // Scan for paragraphs <w:p> and tables <w:tbl>
    const char *p = doc_xml;
    while (*p) {
        const char *next_p = strstr(p, "<w:p");
        const char *next_tbl = strstr(p, "<w:tbl");

        if (!next_p && !next_tbl) break;

        // Process table first if it appears earlier
        if (next_tbl && (!next_p || next_tbl < next_p)) {
            const char *tbl_end = strstr(next_tbl, "</w:tbl>");
            if (!tbl_end) { p = next_tbl + 6; continue; }

            dbuf_append(&out, "[table]\n");

            const char *tr_scan = next_tbl;
            while ((tr_scan = strstr(tr_scan, "<w:tr")) != NULL && tr_scan < tbl_end) {
                const char *tr_end = strstr(tr_scan, "</w:tr>");
                if (!tr_end || tr_end > tbl_end) break;

                dbuf_append(&out, "|");
                const char *tc_scan = tr_scan;
                while ((tc_scan = strstr(tc_scan, "<w:tc")) != NULL && tc_scan < tr_end) {
                    const char *tc_end = strstr(tc_scan, "</w:tc>");
                    if (!tc_end || tc_end > tr_end) break;

                    dbuf_append(&out, " ");
                    // Extract text inside this cell
                    const char *t_scan = tc_scan;
                    while ((t_scan = strstr(t_scan, "<w:t")) != NULL && t_scan < tc_end) {
                        const char *t_val = strchr(t_scan, '>');
                        if (t_val && t_val < tc_end) {
                            t_val++;
                            const char *t_end = strstr(t_val, "</w:t>");
                            if (t_end && t_end <= tc_end) {
                                unescape_xml_into(&out, t_val, t_end - t_val);
                            }
                        }
                        t_scan += 4;
                    }
                    dbuf_append(&out, " |");
                    tc_scan = tc_end + 7;
                }
                dbuf_append(&out, "\n");
                tr_scan = tr_end + 7;
            }

            dbuf_append(&out, "[/table]\n\n");
            p = tbl_end + 8;
            continue;
        }

        // Process paragraph <w:p>
        const char *p_end = strstr(next_p, "</w:p>");
        if (!p_end) { p = next_p + 4; continue; }

        // Determine paragraph style
        int heading_level = 0;
        int is_quote = 0;
        int is_list = 0;

        const char *style_ptr = strstr(next_p, "<w:pStyle ");
        if (style_ptr && style_ptr < p_end) {
            const char *val_ptr = strstr(style_ptr, "w:val=\"");
            if (val_ptr && val_ptr < p_end) {
                val_ptr += 7;
                char *vend = strchr(val_ptr, '"');
                if (vend && vend < p_end) {
                    char st_name[64];
                    size_t st_len = vend - val_ptr;
                    if (st_len >= sizeof(st_name)) st_len = sizeof(st_name) - 1;
                    strncpy(st_name, val_ptr, st_len);
                    st_name[st_len] = '\0';
                    for (char *c = st_name; *c; c++) *c = tolower((unsigned char)*c);

                    if (strstr(st_name, "heading 1") || strstr(st_name, "heading1") || strstr(st_name, "title")) {
                        heading_level = 1;
                    } else if (strstr(st_name, "heading 2") || strstr(st_name, "heading2")) {
                        heading_level = 2;
                    } else if (strstr(st_name, "heading 3") || strstr(st_name, "heading3") || strstr(st_name, "heading")) {
                        heading_level = 3;
                    } else if (strstr(st_name, "quote") || strstr(st_name, "block")) {
                        is_quote = 1;
                    } else if (strstr(st_name, "list")) {
                        is_list = 1;
                    }
                }
            }
        }

        d_buf_t para_buf;
        dbuf_init(&para_buf);

        d_buf_t images_buf;
        dbuf_init(&images_buf);

        // Scan runs <w:r> inside this paragraph
        const char *r_scan = next_p;
        while ((r_scan = strstr(r_scan, "<w:r")) != NULL && r_scan < p_end) {
            const char *r_end = strstr(r_scan, "</w:r>");
            if (!r_end || r_end > p_end) break;

            // Check drawing/image
            const char *drawing_ptr = strstr(r_scan, "<w:drawing");
            if (drawing_ptr && drawing_ptr < r_end) {
                const char *blip_ptr = strstr(drawing_ptr, "r:embed=\"");
                if (blip_ptr && blip_ptr < r_end) {
                    blip_ptr += 9;
                    char *embed_end = strchr(blip_ptr, '"');
                    if (embed_end && embed_end < r_end) {
                        char embed_id[32];
                        size_t eid_len = embed_end - blip_ptr;
                        if (eid_len < sizeof(embed_id)) {
                            strncpy(embed_id, blip_ptr, eid_len);
                            embed_id[eid_len] = '\0';

                            // Find target in rels
                            const char *img_target = NULL;
                            for (int k = 0; k < rel_count; k++) {
                                if (strcmp(rels[k].id, embed_id) == 0) {
                                    img_target = rels[k].target;
                                    break;
                                }
                            }

                            if (img_target) {
                                char zip_entry[512];
                                if (strncmp(img_target, "word/", 5) == 0) {
                                    strncpy(zip_entry, img_target, sizeof(zip_entry) - 1);
                                } else if (img_target[0] == '/') {
                                    snprintf(zip_entry, sizeof(zip_entry), "word%s", img_target);
                                } else {
                                    snprintf(zip_entry, sizeof(zip_entry), "word/%s", img_target);
                                }
                                zip_entry[sizeof(zip_entry) - 1] = '\0';

                                zip_file_t *zf_img = zip_fopen(za, zip_entry, 0);
                                if (zf_img) {
                                    zip_stat_t st_img;
                                    zip_stat(za, zip_entry, 0, &st_img);
                                    unsigned char *ibuf = (unsigned char *)malloc(st_img.size);
                                    zip_fread(zf_img, ibuf, st_img.size);
                                    zip_fclose(zf_img);

                                    char *b64 = base64_encode(ibuf, st_img.size);
                                    free(ibuf);

                                    const char *mime = "image/png";
                                    if (strstr(zip_entry, ".jpeg") || strstr(zip_entry, ".jpg")) mime = "image/jpeg";
                                    else if (strstr(zip_entry, ".gif")) mime = "image/gif";
                                    else if (strstr(zip_entry, ".bmp")) mime = "image/bmp";

                                    dbuf_append(&images_buf, "[img src=\"data:");
                                    dbuf_append(&images_buf, mime);
                                    dbuf_append(&images_buf, ";base64,");
                                    dbuf_append(&images_buf, b64);
                                    dbuf_append(&images_buf, "\" alt=\"image\"]\n");
                                    free(b64);
                                }
                            }
                        }
                    }
                }
            }

            // Run properties
            int is_bold = 0, is_italic = 0, is_underline = 0, is_strike = 0, is_code = 0;
            const char *rpr = strstr(r_scan, "<w:rPr>");
            if (rpr && rpr < r_end) {
                const char *rpr_end = strstr(rpr, "</w:rPr>");
                if (rpr_end && rpr_end < r_end) {
                    if (strstr(rpr, "<w:b/>") && strstr(rpr, "<w:b/>") < rpr_end) is_bold = 1;
                    if (strstr(rpr, "<w:i/>") && strstr(rpr, "<w:i/>") < rpr_end) is_italic = 1;
                    if (strstr(rpr, "<w:u ") && strstr(rpr, "<w:u ") < rpr_end) is_underline = 1;
                    if (strstr(rpr, "<w:strike") && strstr(rpr, "<w:strike") < rpr_end) is_strike = 1;
                    if (strstr(rpr, "Courier") || strstr(rpr, "Consolas") || strstr(rpr, "monospace") || strstr(rpr, "w:val=\"Code\"")) is_code = 1;
                }
            }

            // Text in <w:t>
            const char *t_scan = r_scan;
            while ((t_scan = strstr(t_scan, "<w:t")) != NULL && t_scan < r_end) {
                const char *t_val = strchr(t_scan, '>');
                if (t_val && t_val < r_end) {
                    t_val++;
                    const char *t_end = strstr(t_val, "</w:t>");
                    if (t_end && t_end <= r_end) {
                        if (is_bold) dbuf_append(&para_buf, "[b]");
                        if (is_italic) dbuf_append(&para_buf, "[i]");
                        if (is_underline) dbuf_append(&para_buf, "[u]");
                        if (is_strike) dbuf_append(&para_buf, "[s]");
                        if (is_code) dbuf_append(&para_buf, "[code]");

                        unescape_xml_into(&para_buf, t_val, t_end - t_val);

                        if (is_code) dbuf_append(&para_buf, "[/code]");
                        if (is_strike) dbuf_append(&para_buf, "[/s]");
                        if (is_underline) dbuf_append(&para_buf, "[/u]");
                        if (is_italic) dbuf_append(&para_buf, "[/i]");
                        if (is_bold) dbuf_append(&para_buf, "[/b]");
                    }
                }
                t_scan += 4;
            }

            r_scan = r_end + 6;
        }

        // Emit paragraph
        if (images_buf.len > 0) {
            dbuf_append(&out, images_buf.data);
        }

        if (para_buf.len > 0) {
            if (heading_level > 0) {
                char htag[8];
                snprintf(htag, sizeof(htag), "h%d", heading_level);
                dbuf_append(&out, "["); dbuf_append(&out, htag); dbuf_append(&out, "]");
                dbuf_append(&out, para_buf.data);
                dbuf_append(&out, "[/"); dbuf_append(&out, htag); dbuf_append(&out, "]\n\n");
            } else if (is_quote) {
                dbuf_append(&out, "[quote]");
                dbuf_append(&out, para_buf.data);
                dbuf_append(&out, "[/quote]\n\n");
            } else if (is_list) {
                dbuf_append(&out, "* ");
                dbuf_append(&out, para_buf.data);
                dbuf_append(&out, "\n");
            } else {
                dbuf_append(&out, para_buf.data);
                dbuf_append(&out, "\n\n");
            }
        }

        free(para_buf.data);
        free(images_buf.data);

        p = p_end + 6;
    }

    free(doc_xml);
    zip_close(za);

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
 * FILE-BASED CLI HELPERS
 * ============================================================ */

int docx_to_wrt_file(const char *docx_path, const char *wrt_path) {
    FILE *f = fopen(docx_path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    unsigned char *buf = (unsigned char *)malloc(fsize);
    if (fread(buf, 1, fsize, f) != (size_t)fsize) {
        free(buf); fclose(f); return -1;
    }
    fclose(f);

    char *wrt = docx_to_wrt(buf, (size_t)fsize);
    free(buf);

    if (!wrt) return -1;

    FILE *out = fopen(wrt_path, "w");
    if (!out) { free(wrt); return -1; }
    fputs(wrt, out);
    fclose(out);
    free(wrt);
    return 0;
}

int wrt_to_docx_file(const char *wrt_path, const char *docx_path) {
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

    size_t out_len = 0;
    unsigned char *docx_bytes = wrt_to_docx(buf, &out_len);
    free(buf);

    if (!docx_bytes || out_len == 0) return -1;

    FILE *out = fopen(docx_path, "wb");
    if (!out) { free(docx_bytes); return -1; }
    fwrite(docx_bytes, 1, out_len, out);
    fclose(out);
    free(docx_bytes);
    return 0;
}
