// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI Fast Native Grep Engine — aladdin_grep.c
 * Uses mmap() and fast strstr for microsecond project searching.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <dirent.h>

static int g_match_count = 0;
static const int MAX_MATCHES = 50;

static void search_file(const char *filepath, const char *query) {
    if (g_match_count >= MAX_MATCHES) return;

    int fd = open(filepath, O_RDONLY);
    if (fd < 0) return;

    struct stat st;
    if (fstat(fd, &st) < 0 || st.st_size == 0 || st.st_size > 10 * 1024 * 1024) {
        close(fd);
        return; // Skip empty files or files larger than 10MB
    }

    char *mapped = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    if (mapped == MAP_FAILED) return;

    size_t qlen = strlen(query);
    const char *ptr = mapped;
    const char *end = mapped + st.st_size;
    int line_no = 1;
    const char *line_start = mapped;

    while (ptr < end && g_match_count < MAX_MATCHES) {
        if (*ptr == '\n') {
            size_t line_len = ptr - line_start;
            if (line_len >= qlen && memmem(line_start, line_len, query, qlen) != NULL) {
                printf("{\"file\":\"%s\",\"line\":%d,\"content\":\"", filepath, line_no);
                for (size_t i = 0; i < line_len && i < 256; i++) {
                    char c = line_start[i];
                    if (c == '"') printf("\\\"");
                    else if (c == '\\') printf("\\\\");
                    else if (c == '\r' || c == '\t') printf(" ");
                    else if ((unsigned char)c >= 0x20) putchar(c);
                }
                printf("\"}\n");
                fflush(stdout);
                g_match_count++;
            }
            line_no++;
            line_start = ptr + 1;
        }
        ptr++;
    }

    munmap(mapped, st.st_size);
}

static void search_directory(const char *dirpath, const char *query) {
    if (g_match_count >= MAX_MATCHES) return;

    DIR *dir = opendir(dirpath);
    if (!dir) return;

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL && g_match_count < MAX_MATCHES) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
        if (strcmp(entry->d_name, ".git") == 0 || strcmp(entry->d_name, "node_modules") == 0 ||
            strcmp(entry->d_name, ".next") == 0 || strcmp(entry->d_name, ".venv") == 0) continue;

        char path[1024];
        snprintf(path, sizeof(path), "%s/%s", dirpath, entry->d_name);

        struct stat st;
        if (stat(path, &st) == 0) {
            if (S_ISDIR(st.st_mode)) {
                search_directory(path, query);
            } else if (S_ISREG(st.st_mode)) {
                search_file(path, query);
            }
        }
    }
    closedir(dir);
}

int main(int argc, char *argv[]) {
    const char *dirpath = ".";
    const char *query = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--path") == 0 && i + 1 < argc) {
            dirpath = argv[++i];
        } else if (strcmp(argv[i], "--query") == 0 && i + 1 < argc) {
            query = argv[++i];
        }
    }

    if (!query || strlen(query) == 0) {
        fprintf(stderr, "Usage: aladdin-grep --path <dir> --query <text>\n");
        return 1;
    }

    search_directory(dirpath, query);
    return 0;
}
