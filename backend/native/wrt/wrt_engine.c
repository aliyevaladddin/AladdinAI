// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * CLI entry point
 */

#include "wrt_internal.h"
#include "wrt_engine.h"

/* ============================================================
 * CLI ENTRY POINT
 * ============================================================ */

#ifndef WRT_ENGINE_NO_MAIN

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
        fprintf(stderr, "Usage: %s <validate|fix|to-html|to-editable-html|from-editable-html|stats> [file|-]\n", argv[0]);
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
        const char *dir = (argc >= 3) ? argv[2] : ".";
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
    } else if (strcmp(cmd, "to-editable-html") == 0) {
        char *html = wrt_to_editable_html(text);
        fputs(html, stdout);
        free(html);
        free(text);
        return 0;
    } else if (strcmp(cmd, "from-editable-html") == 0) {
        /* text already contains the HTML read from stdin/file */
        char *wrt = wrt_from_editable_html(text);
        fputs(wrt, stdout);
        free(wrt);
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

#endif /* WRT_ENGINE_NO_MAIN */