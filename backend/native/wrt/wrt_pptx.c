// NOTICE: This file is protected under RCF-PL 
/*
 * AladdinAI — Native C PPTX <-> WRT Converter
 * Ultra-fast bidirectional PowerPoint .pptx <-> .wrt converter using libzip
 */

#include "wrt_pptx.h"
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
 * STATIC PPTX OPENXML ASSETS
 * ============================================================ */

static const char ROOT_RELS_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
    "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/>\n"
    "</Relationships>\n";

static const char SLIDE_LAYOUT_RELS[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
    "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"../slideMasters/slideMaster1.xml\"/>\n"
    "</Relationships>\n";

static const char SLIDE_LAYOUT_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<p:sldLayout xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
    "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
    "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" type=\"blank\">\n"
    "  <p:cSld name=\"Blank\">\n"
    "    <p:spTree>\n"
    "      <p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>\n"
    "      <p:grpSpPr/>\n"
    "    </p:spTree>\n"
    "  </p:cSld>\n"
    "</p:sldLayout>\n";

static const char SLIDE_MASTER_RELS[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
    "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>\n"
    "</Relationships>\n";

static const char SLIDE_MASTER_XML[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<p:sldMaster xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
    "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
    "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">\n"
    "  <p:cSld>\n"
    "    <p:spTree>\n"
    "      <p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>\n"
    "      <p:grpSpPr/>\n"
    "    </p:spTree>\n"
    "  </p:cSld>\n"
    "  <p:sldLayoutIdLst>\n"
    "    <p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/>\n"
    "  </p:sldLayoutIdLst>\n"
    "</p:sldMaster>\n";

/* ============================================================
 * INLINE WRT TAG EMITTER FOR PPTX DRAWINGML
 * ============================================================ */

static void parse_and_emit_pptx_runs(d_buf_t *out, const char *text, int default_sz, int is_default_bold) {
    if (!text) return;
    const char *p = text;

    while (*p) {
        int is_bold = is_default_bold;
        int is_italic = 0;
        int is_underline = 0;
        int is_strike = 0;
        const char *span_content = NULL;
        size_t span_len = 0;

        if (*p == '[') {
            if (strncmp(p, "[b]", 3) == 0) {
                const char *close = strstr(p + 3, "[/b]");
                if (close) {
                    is_bold = 1;
                    span_content = p + 3;
                    span_len = close - (p + 3);
                    p = close + 4;
                }
            } else if (strncmp(p, "[i]", 3) == 0) {
                const char *close = strstr(p + 3, "[/i]");
                if (close) {
                    is_italic = 1;
                    span_content = p + 3;
                    span_len = close - (p + 3);
                    p = close + 4;
                }
            } else if (strncmp(p, "[u]", 3) == 0) {
                const char *close = strstr(p + 3, "[/u]");
                if (close) {
                    is_underline = 1;
                    span_content = p + 3;
                    span_len = close - (p + 3);
                    p = close + 4;
                }
            } else if (strncmp(p, "[s]", 3) == 0) {
                const char *close = strstr(p + 3, "[/s]");
                if (close) {
                    is_strike = 1;
                    span_content = p + 3;
                    span_len = close - (p + 3);
                    p = close + 4;
                }
            } else if (strncmp(p, "[code]", 6) == 0) {
                const char *close = strstr(p + 6, "[/code]");
                if (close) {
                    span_content = p + 6;
                    span_len = close - (p + 6);
                    p = close + 7;
                }
            }
        }

        if (span_content) {
            char rpr[256];
            snprintf(rpr, sizeof(rpr), "<a:r><a:rPr lang=\"en-US\" sz=\"%d\"%s%s%s%s/><a:t>",
                     default_sz,
                     is_bold ? " b=\"1\"" : "",
                     is_italic ? " i=\"1\"" : "",
                     is_underline ? " u=\"sng\"" : "",
                     is_strike ? " strike=\"sngStrike\"" : "");
            dbuf_append(out, rpr);
            dbuf_append_xml_escaped(out, span_content, span_len);
            dbuf_append(out, "</a:t></a:r>");
            continue;
        }

        const char *next_tag = strchr(p, '[');
        size_t chunk_len = next_tag ? (size_t)(next_tag - p) : strlen(p);
        if (chunk_len > 0) {
            char rpr[128];
            snprintf(rpr, sizeof(rpr), "<a:r><a:rPr lang=\"en-US\" sz=\"%d\"%s/><a:t>",
                     default_sz, is_default_bold ? " b=\"1\"" : "");
            dbuf_append(out, rpr);
            dbuf_append_xml_escaped(out, p, chunk_len);
            dbuf_append(out, "</a:t></a:r>");
            p += chunk_len;
        } else if (*p == '[') {
            char rpr[128];
            snprintf(rpr, sizeof(rpr), "<a:r><a:rPr lang=\"en-US\" sz=\"%d\"/><a:t>[</a:t></a:r>", default_sz);
            dbuf_append(out, rpr);
            p++;
        }
    }
}

/* ============================================================
 * WRT -> PPTX CONVERTER
 * ============================================================ */

#define MAX_PPTX_SLIDES 100

typedef struct {
    char *title;
    d_buf_t body_lines;
    d_buf_t table_xml;
    int has_table;
} pptx_slide_data_t;

unsigned char *wrt_to_pptx(const char *wrt_text, size_t *out_len) {
    if (!wrt_text) wrt_text = "";

    char *md_converted = NULL;
    if (wrt_has_markdown(wrt_text)) {
        md_converted = wrt_markdown_to_wrt(wrt_text);
        if (md_converted) wrt_text = md_converted;
    }

    pptx_slide_data_t slides[MAX_PPTX_SLIDES];
    int slide_count = 0;
    memset(slides, 0, sizeof(slides));

    // Parse WRT into slide blocks
    const char *p = wrt_text;
    int current_slide = -1;
    int in_table = 0;

    // Check if wrt_text has any [slide ...] tags
    int has_slide_tags = (strstr(wrt_text, "[slide") != NULL);
    if (!has_slide_tags) {
        // Wrap entire content into slide 0
        current_slide = 0;
        slide_count = 1;
        dbuf_init(&slides[0].body_lines);
        dbuf_init(&slides[0].table_xml);
    }

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

        if (strncmp(line, "[slide", 6) == 0) {
            if (slide_count < MAX_PPTX_SLIDES) {
                current_slide = slide_count++;
                dbuf_init(&slides[current_slide].body_lines);
                dbuf_init(&slides[current_slide].table_xml);
            }
            free(line);
            continue;
        } else if (strcmp(line, "[/slide]") == 0) {
            current_slide = -1;
            free(line);
            continue;
        }

        if (current_slide < 0) {
            // Content before first slide tag: open slide 0
            if (slide_count < MAX_PPTX_SLIDES) {
                current_slide = slide_count++;
                dbuf_init(&slides[current_slide].body_lines);
                dbuf_init(&slides[current_slide].table_xml);
            } else {
                free(line);
                continue;
            }
        }

        // Within current slide
        pptx_slide_data_t *s = &slides[current_slide];

        if (strncmp(line, "[h1]", 4) == 0 || strncmp(line, "[h2]", 4) == 0) {
            char *tag_end = strstr(line + 4, "[/");
            if (tag_end) *tag_end = '\0';
            if (!s->title) {
                s->title = strdup(line + 4);
            } else {
                // Secondary title becomes bold paragraph
                dbuf_append(&s->body_lines, "<a:p>");
                parse_and_emit_pptx_runs(&s->body_lines, line + 4, 2400, 1);
                dbuf_append(&s->body_lines, "</a:p>\n");
            }
        } else if (strcmp(line, "[table]") == 0) {
            in_table = 1;
            s->has_table = 1;
        } else if (strcmp(line, "[/table]") == 0) {
            in_table = 0;
        } else if (in_table && line[0] == '|') {
            dbuf_append(&s->table_xml, "            <a:tr h=\"370840\">\n");
            char *row_copy = strdup(line);
            char *cell = strtok(row_copy + 1, "|");
            while (cell) {
                while (*cell && isspace((unsigned char)*cell)) cell++;
                size_t clen = strlen(cell);
                while (clen > 0 && isspace((unsigned char)cell[clen - 1])) clen--;
                cell[clen] = '\0';

                dbuf_append(&s->table_xml, "              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p>");
                parse_and_emit_pptx_runs(&s->table_xml, cell, 1400, 0);
                dbuf_append(&s->table_xml, "</a:p></a:txBody></a:tc>\n");
                cell = strtok(NULL, "|");
            }
            free(row_copy);
            dbuf_append(&s->table_xml, "            </a:tr>\n");
        } else {
            // Body paragraph
            dbuf_append(&s->body_lines, "<a:p>");
            if (line[0] == '*' && line[1] == ' ') {
                parse_and_emit_pptx_runs(&s->body_lines, line + 2, 1800, 0);
            } else {
                parse_and_emit_pptx_runs(&s->body_lines, line, 1800, 0);
            }
            dbuf_append(&s->body_lines, "</a:p>\n");
        }

        free(line);
    }

    if (slide_count == 0) {
        // At least one blank slide
        slide_count = 1;
        slides[0].title = strdup("Presentation");
        dbuf_init(&slides[0].body_lines);
        dbuf_init(&slides[0].table_xml);
    }

    // Generate OpenXML package
    char tmp_zip_path[64];
    snprintf(tmp_zip_path, sizeof(tmp_zip_path), "/tmp/wrt_pptx_%d_%u.pptx", getpid(), (unsigned)rand());

    int zip_err = 0;
    zip_t *za = zip_open(tmp_zip_path, ZIP_CREATE | ZIP_TRUNCATE, &zip_err);
    if (!za) {
        for (int i = 0; i < slide_count; i++) {
            if (slides[i].title) free(slides[i].title);
            if (slides[i].body_lines.data) free(slides[i].body_lines.data);
            if (slides[i].table_xml.data) free(slides[i].table_xml.data);
        }
        if (md_converted) free(md_converted);
        *out_len = 0;
        return NULL;
    }

    // 1. [Content_Types].xml
    d_buf_t ct;
    dbuf_init(&ct);
    dbuf_append(&ct,
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n"
        "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n"
        "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n"
        "  <Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>\n"
        "  <Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>\n"
        "  <Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>\n");
    for (int i = 1; i <= slide_count; i++) {
        char s_ov[256];
        snprintf(s_ov, sizeof(s_ov), "  <Override PartName=\"/ppt/slides/slide%d.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>\n", i);
        dbuf_append(&ct, s_ov);
    }
    dbuf_append(&ct, "</Types>\n");
    zip_file_add(za, "[Content_Types].xml", zip_source_buffer(za, ct.data, ct.len, 0), ZIP_FL_OVERWRITE);

    // 2. _rels/.rels
    zip_file_add(za, "_rels/.rels", zip_source_buffer(za, ROOT_RELS_XML, strlen(ROOT_RELS_XML), 0), ZIP_FL_OVERWRITE);

    // 3. ppt/slideLayouts and slideMasters
    zip_file_add(za, "ppt/slideLayouts/slideLayout1.xml", zip_source_buffer(za, SLIDE_LAYOUT_XML, strlen(SLIDE_LAYOUT_XML), 0), ZIP_FL_OVERWRITE);
    zip_file_add(za, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", zip_source_buffer(za, SLIDE_LAYOUT_RELS, strlen(SLIDE_LAYOUT_RELS), 0), ZIP_FL_OVERWRITE);
    zip_file_add(za, "ppt/slideMasters/slideMaster1.xml", zip_source_buffer(za, SLIDE_MASTER_XML, strlen(SLIDE_MASTER_XML), 0), ZIP_FL_OVERWRITE);
    zip_file_add(za, "ppt/slideMasters/_rels/slideMaster1.xml.rels", zip_source_buffer(za, SLIDE_MASTER_RELS, strlen(SLIDE_MASTER_RELS), 0), ZIP_FL_OVERWRITE);

    // 4. ppt/presentation.xml and ppt/_rels/presentation.xml.rels
    d_buf_t pres;
    d_buf_t pres_rels;
    dbuf_init(&pres);
    dbuf_init(&pres_rels);

    dbuf_append(&pres,
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">\n"
        "  <p:sldMasterIdLst>\n"
        "    <p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/>\n"
        "  </p:sldMasterIdLst>\n"
        "  <p:sldIdLst>\n");

    dbuf_append(&pres_rels,
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
        "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"slideMasters/slideMaster1.xml\"/>\n");

    for (int i = 1; i <= slide_count; i++) {
        char sld_entry[128];
        snprintf(sld_entry, sizeof(sld_entry), "    <p:sldId id=\"%d\" r:id=\"rId%d\"/>\n", 255 + i, i + 1);
        dbuf_append(&pres, sld_entry);

        char rel_entry[256];
        snprintf(rel_entry, sizeof(rel_entry), "  <Relationship Id=\"rId%d\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide%d.xml\"/>\n", i + 1, i);
        dbuf_append(&pres_rels, rel_entry);
    }

    dbuf_append(&pres,
        "  </p:sldIdLst>\n"
        "  <p:sldSz cx=\"9144000\" cy=\"6858000\" type=\"screen4x3\"/>\n"
        "  <p:notesSz cx=\"6858000\" cy=\"9144000\"/>\n"
        "</p:presentation>\n");
    dbuf_append(&pres_rels, "</Relationships>\n");

    zip_file_add(za, "ppt/presentation.xml", zip_source_buffer(za, pres.data, pres.len, 0), ZIP_FL_OVERWRITE);
    zip_file_add(za, "ppt/_rels/presentation.xml.rels", zip_source_buffer(za, pres_rels.data, pres_rels.len, 0), ZIP_FL_OVERWRITE);

    // 5. Each slide: ppt/slides/slide%d.xml and rels
    for (int i = 0; i < slide_count; i++) {
        d_buf_t sld;
        dbuf_init(&sld);
        dbuf_append(&sld,
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
            "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
            "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">\n"
            "  <p:cSld>\n"
            "    <p:spTree>\n"
            "      <p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>\n"
            "      <p:grpSpPr/>\n");

        // Title box
        const char *title_text = slides[i].title ? slides[i].title : "Slide";
        dbuf_append(&sld,
            "      <p:sp>\n"
            "        <p:nvSpPr><p:cNvPr id=\"2\" name=\"Title\"/><p:cNvSpPr><a:spLocks noGrp=\"1\"/></p:cNvSpPr><p:nvPr><p:ph type=\"title\"/></p:nvPr></p:nvSpPr>\n"
            "        <p:spPr><a:xfrm><a:off x=\"457200\" y=\"457200\"/><a:ext cx=\"8229600\" cy=\"1143000\"/></a:xfrm></p:spPr>\n"
            "        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang=\"en-US\" sz=\"3600\" b=\"1\"/><a:t>");
        dbuf_append_xml_escaped(&sld, title_text, strlen(title_text));
        dbuf_append(&sld, "</a:t></a:r></a:p></p:txBody>\n      </p:sp>\n");

        // Content box
        if (slides[i].body_lines.len > 0) {
            dbuf_append(&sld,
                "      <p:sp>\n"
                "        <p:nvSpPr><p:cNvPr id=\"3\" name=\"Content\"/><p:cNvSpPr><a:spLocks noGrp=\"1\"/></p:cNvSpPr><p:nvPr><p:ph type=\"body\"/></p:nvPr></p:nvSpPr>\n"
                "        <p:spPr><a:xfrm><a:off x=\"457200\" y=\"1828800\"/><a:ext cx=\"8229600\" cy=\"4572000\"/></a:xfrm></p:spPr>\n"
                "        <p:txBody><a:bodyPr/><a:lstStyle/>\n");
            dbuf_append(&sld, slides[i].body_lines.data);
            dbuf_append(&sld, "        </p:txBody>\n      </p:sp>\n");
        }

        // Table shape if present
        if (slides[i].has_table && slides[i].table_xml.len > 0) {
            dbuf_append(&sld,
                "      <p:graphicFrame>\n"
                "        <p:nvGraphicFramePr><p:cNvPr id=\"4\" name=\"Table\"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp=\"1\"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>\n"
                "        <p:spPr><a:xfrm><a:off x=\"457200\" y=\"2000000\"/><a:ext cx=\"8229600\" cy=\"3500000\"/></a:xfrm></p:spPr>\n"
                "        <a:graphic>\n"
                "          <a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/table\">\n"
                "            <a:tbl>\n"
                "              <a:tblPr/>\n");
            dbuf_append(&sld, slides[i].table_xml.data);
            dbuf_append(&sld,
                "            </a:tbl>\n"
                "          </a:graphicData>\n"
                "        </a:graphic>\n"
                "      </p:graphicFrame>\n");
        }

        dbuf_append(&sld,
            "    </p:spTree>\n"
            "  </p:cSld>\n"
            "</p:sld>\n");

        char sld_path[64], sld_rel_path[64];
        snprintf(sld_path, sizeof(sld_path), "ppt/slides/slide%d.xml", i + 1);
        snprintf(sld_rel_path, sizeof(sld_rel_path), "ppt/slides/_rels/slide%d.xml.rels", i + 1);

        zip_file_add(za, sld_path, zip_source_buffer(za, sld.data, sld.len, 0), ZIP_FL_OVERWRITE);

        static const char SLIDE_RELS[] =
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
            "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>\n"
            "</Relationships>\n";
        zip_file_add(za, sld_rel_path, zip_source_buffer(za, SLIDE_RELS, strlen(SLIDE_RELS), 0), ZIP_FL_OVERWRITE);
    }

    zip_close(za);

    // Clean up temporary slide buffers
    for (int i = 0; i < slide_count; i++) {
        if (slides[i].title) free(slides[i].title);
        if (slides[i].body_lines.data) free(slides[i].body_lines.data);
        if (slides[i].table_xml.data) free(slides[i].table_xml.data);
    }
    free(ct.data);
    free(pres.data);
    free(pres_rels.data);

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
 * PPTX -> WRT PARSER
 * ============================================================ */

static void parse_pptx_runs(d_buf_t *out, const char *p_start, const char *p_end) {
    const char *scan = p_start;
    while ((scan = strstr(scan, "<a:r>")) != NULL && scan < p_end) {
        const char *r_end = strstr(scan, "</a:r>");
        if (!r_end || r_end > p_end) break;

        int is_bold = 0, is_italic = 0, is_underline = 0, is_strike = 0;
        const char *rpr = strstr(scan, "<a:rPr");
        if (rpr && rpr < r_end) {
            const char *rpr_close = strchr(rpr, '>');
            if (rpr_close && rpr_close <= r_end) {
                if (strstr(rpr, "b=\"1\"") && strstr(rpr, "b=\"1\"") < rpr_close) is_bold = 1;
                if (strstr(rpr, "i=\"1\"") && strstr(rpr, "i=\"1\"") < rpr_close) is_italic = 1;
                if (strstr(rpr, "u=\"sng\"") && strstr(rpr, "u=\"sng\"") < rpr_close) is_underline = 1;
                if (strstr(rpr, "strike=\"sngStrike\"") && strstr(rpr, "strike=\"sngStrike\"") < rpr_close) is_strike = 1;
            }
        }

        const char *t_tag = strstr(scan, "<a:t>");
        if (t_tag && t_tag < r_end) {
            const char *t_end = strstr(t_tag + 5, "</a:t>");
            if (t_end && t_end <= r_end) {
                if (is_bold) dbuf_append(out, "[b]");
                if (is_italic) dbuf_append(out, "[i]");
                if (is_underline) dbuf_append(out, "[u]");
                if (is_strike) dbuf_append(out, "[s]");

                dbuf_append_len(out, t_tag + 5, t_end - (t_tag + 5));

                if (is_strike) dbuf_append(out, "[/s]");
                if (is_underline) dbuf_append(out, "[/u]");
                if (is_italic) dbuf_append(out, "[/i]");
                if (is_bold) dbuf_append(out, "[/b]");
            }
        }

        scan = r_end + 6;
    }
}

char *pptx_to_wrt(const unsigned char *pptx_data, size_t pptx_len) {
    if (!pptx_data || pptx_len == 0) return strdup("");

    zip_error_t zerr;
    zip_error_init(&zerr);
    zip_source_t *src = zip_source_buffer_create(pptx_data, pptx_len, 0, &zerr);
    if (!src) return strdup("");

    zip_t *za = zip_open_from_source(src, ZIP_RDONLY, &zerr);
    if (!za) {
        zip_source_free(src);
        return strdup("");
    }

    d_buf_t out;
    dbuf_init(&out);

    // Scan slides in numerical order: slide1.xml, slide2.xml, ...
    int slide_num = 1;
    while (slide_num <= MAX_PPTX_SLIDES) {
        char sld_name[64];
        snprintf(sld_name, sizeof(sld_name), "ppt/slides/slide%d.xml", slide_num);

        zip_file_t *zf = zip_fopen(za, sld_name, 0);
        if (!zf) {
            if (slide_num == 1) {
                // If slide1 doesn't exist, stop
                break;
            }
            // Check if there are other slides or if we reached the end
            int found_more = 0;
            for (int k = slide_num + 1; k <= slide_num + 5; k++) {
                char test_name[64];
                snprintf(test_name, sizeof(test_name), "ppt/slides/slide%d.xml", k);
                zip_stat_t st;
                if (zip_stat(za, test_name, 0, &st) == 0) {
                    found_more = 1;
                    break;
                }
            }
            if (!found_more) break;
            slide_num++;
            continue;
        }

        d_buf_t sld_buf;
        dbuf_init(&sld_buf);
        char buf[4096];
        zip_int64_t nread = 0;
        while ((nread = zip_fread(zf, buf, sizeof(buf))) > 0) {
            dbuf_append_len(&sld_buf, buf, nread);
        }
        zip_fclose(zf);

        char slide_hdr[32];
        snprintf(slide_hdr, sizeof(slide_hdr), "[slide %d]\n", slide_num);
        dbuf_append(&out, slide_hdr);

        // Scan shapes in the slide
        const char *scan = sld_buf.data;
        while (scan && *scan) {
            // Find next shape or table
            const char *sp_start = strstr(scan, "<p:sp>");
            const char *tbl_start = strstr(scan, "<a:tbl>");

            if (!sp_start && !tbl_start) break;

            if (tbl_start && (!sp_start || tbl_start < sp_start)) {
                // Process Table
                const char *tbl_end = strstr(tbl_start, "</a:tbl>");
                if (tbl_end) {
                    dbuf_append(&out, "[table]\n");
                    const char *tr_scan = tbl_start;
                    while ((tr_scan = strstr(tr_scan, "<a:tr")) != NULL && tr_scan < tbl_end) {
                        const char *tr_end = strstr(tr_scan, "</a:tr>");
                        if (!tr_end || tr_end > tbl_end) break;

                        dbuf_append(&out, "|");
                        const char *tc_scan = tr_scan;
                        while ((tc_scan = strstr(tc_scan, "<a:tc")) != NULL && tc_scan < tr_end) {
                            const char *tc_end = strstr(tc_scan, "</a:tc>");
                            if (!tc_end || tc_end > tr_end) break;

                            dbuf_append(&out, " ");
                            parse_pptx_runs(&out, tc_scan, tc_end);
                            dbuf_append(&out, " |");
                            tc_scan = tc_end + 7;
                        }
                        dbuf_append(&out, "\n");
                        tr_scan = tr_end + 7;
                    }
                    dbuf_append(&out, "[/table]\n\n");
                    scan = tbl_end + 8;
                    continue;
                }
            }

            if (sp_start) {
                const char *sp_end = strstr(sp_start, "</p:sp>");
                if (!sp_end) break;

                int is_title = 0;
                if (strstr(sp_start, "type=\"title\"") && strstr(sp_start, "type=\"title\"") < sp_end) is_title = 1;
                if (strstr(sp_start, "type=\"ctrTitle\"") && strstr(sp_start, "type=\"ctrTitle\"") < sp_end) is_title = 1;

                // Process paragraphs in shape
                const char *p_scan = sp_start;
                while ((p_scan = strstr(p_scan, "<a:p>")) != NULL && p_scan < sp_end) {
                    const char *p_end = strstr(p_scan, "</a:p>");
                    if (!p_end || p_end > sp_end) break;

                    d_buf_t para;
                    dbuf_init(&para);
                    parse_pptx_runs(&para, p_scan, p_end);

                    char *ptxt = para.data;
                    while (*ptxt && isspace((unsigned char)*ptxt)) ptxt++;
                    size_t plen = strlen(ptxt);
                    while (plen > 0 && isspace((unsigned char)ptxt[plen - 1])) plen--;
                    ptxt[plen] = '\0';

                    if (plen > 0) {
                        if (is_title) {
                            if (strncmp(ptxt, "[b]", 3) == 0 && plen >= 7 && strcmp(ptxt + plen - 4, "[/b]") == 0) {
                                ptxt += 3;
                                plen -= 7;
                                ptxt[plen] = '\0';
                            }
                            dbuf_append(&out, "[h1]");
                            dbuf_append(&out, ptxt);
                            dbuf_append(&out, "[/h1]\n\n");
                        } else {
                            dbuf_append(&out, ptxt);
                            dbuf_append(&out, "\n\n");
                        }
                    }
                    free(para.data);
                    p_scan = p_end + 6;
                }

                scan = sp_end + 7;
            }
        }

        dbuf_append(&out, "[/slide]\n\n");
        free(sld_buf.data);
        slide_num++;
    }

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
 * FILE HELPERS
 * ============================================================ */

int pptx_to_wrt_file(const char *pptx_path, const char *wrt_path) {
    FILE *f = fopen(pptx_path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    unsigned char *data = (unsigned char *)malloc(fsize > 0 ? fsize : 1);
    if (fsize > 0) fread(data, 1, fsize, f);
    fclose(f);

    char *wrt = pptx_to_wrt(data, fsize);
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

int wrt_to_pptx_file(const char *wrt_path, const char *pptx_path) {
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
    unsigned char *pptx_bytes = wrt_to_pptx(data, &out_len);
    free(data);
    if (!pptx_bytes) return -1;

    FILE *out = fopen(pptx_path, "wb");
    if (!out) {
        free(pptx_bytes);
        return -1;
    }
    fwrite(pptx_bytes, 1, out_len, out);
    fclose(out);
    free(pptx_bytes);
    return 0;
}
