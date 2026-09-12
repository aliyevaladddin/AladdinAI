// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * High-performance, lightweight engine for .wrt documents
 */

#ifndef WRT_ENGINE_H
#define WRT_ENGINE_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdint.h>

#define WRT_ENGINE_VERSION "1.1.0"
#define WRT_MAX_TAG_LEN    32
#define WRT_MAX_ISSUES     128
#define WRT_MAX_STACK      256

typedef struct {
    int line;
    int col;
    char tag[WRT_MAX_TAG_LEN];
    char message[256];
    int severity; /* 0 = error, 1 = warning */
} wrt_issue_t;

typedef struct {
    int valid;
    int issue_count;
    wrt_issue_t issues[WRT_MAX_ISSUES];
    int word_count;
    int char_count;
    int line_count;
    int tag_count;
} wrt_report_t;

#define DEFAULT_WRT_SOCKET_PATH "/tmp/aladdin_wrt.sock"

/* Core Document Engine API */
void wrt_validate(const char *text, wrt_report_t *out);
char *wrt_fix(const char *text);
char *wrt_to_html(const char *text);
char *wrt_report_to_json(const wrt_report_t *rep);

/* Native File Operations API */
char *wrt_list_files_json(const char *dir_path);
char *wrt_read_file_json(const char *file_path);
char *wrt_save_file_json(const char *file_path, const char *content);
char *wrt_get_recent_files_json(void);
void  wrt_record_recent_file(const char *file_path);

int  wrt_engine_daemon(const char *socket_path);

/* DOCX <-> WRT Conversion API */
#include "wrt_docx.h"

/* Markdown <-> WRT Conversion API */
#include "wrt_markdown.h"

/* ODT <-> WRT Conversion API */
#include "wrt_odt.h"

/* PPTX <-> WRT Conversion API */
#include "wrt_pptx.h"

#endif /* WRT_ENGINE_H */
