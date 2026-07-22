// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI Fast Native Log Stream Filter — aladdin_log_stream.c
 * High-speed native log filtering and pattern detection.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define MAX_LINE_LEN 4096

static void process_log_line(const char *line, const char *filter) {
    if (filter && strlen(filter) > 0) {
        if (strstr(line, filter) == NULL) {
            return; // Skip non-matching lines
        }
    }

    // Determine log level heuristic
    const char *level = "INFO";
    if (strstr(line, "ERROR") || strstr(line, "Error") || strstr(line, "ERR") || strstr(line, "FAIL")) {
        level = "ERROR";
    } else if (strstr(line, "WARN") || strstr(line, "Warning")) {
        level = "WARN";
    } else if (strstr(line, "DEBUG")) {
        level = "DEBUG";
    }

    // Output structured JSON line
    printf("{\"level\":\"%s\",\"message\":\"", level);
    for (const char *p = line; *p != '\0'; p++) {
        if (*p == '"') printf("\\\"");
        else if (*p == '\\') printf("\\\\");
        else if (*p == '\n' || *p == '\r') continue;
        else if ((unsigned char)*p >= 0x20) putchar(*p);
    }
    printf("\"}\n");
    fflush(stdout);
}

int main(int argc, char *argv[]) {
    const char *file_path = NULL;
    const char *filter = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--file") == 0 && i + 1 < argc) {
            file_path = argv[++i];
        } else if (strcmp(argv[i], "--filter") == 0 && i + 1 < argc) {
            filter = argv[++i];
        }
    }

    FILE *fp = stdin;
    if (file_path) {
        fp = fopen(file_path, "r");
        if (!fp) {
            fprintf(stderr, "Failed to open log file: %s\n", file_path);
            return 1;
        }
    }

    char line_buf[MAX_LINE_LEN];
    while (fgets(line_buf, sizeof(line_buf), fp)) {
        process_log_line(line_buf, filter);
    }

    if (file_path && fp) {
        fclose(fp);
    }
    return 0;
}
