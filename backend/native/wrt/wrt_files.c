// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Native file operations
 */

#include "wrt_internal.h"
#include "wrt_engine.h"
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <dirent.h>
#include <time.h>
#include <errno.h>

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
        target_dir = ".";
    }

    char resolved[PATH_MAX];
    if (realpath(target_dir, resolved) == NULL) {
        strncpy(resolved, target_dir, sizeof(resolved) - 1);
        resolved[sizeof(resolved) - 1] = '\0';
    }

    // Open directory via file descriptor to prevent TOCTOU symlink swap
    int dir_fd = open(resolved, O_DIRECTORY | O_RDONLY | O_NOFOLLOW);
    if (dir_fd < 0) {
        str_buf_t err;
        buf_init(&err);
        buf_append(&err, "{\"type\":\"list_files_result\",\"success\":false,\"error\":\"Cannot open directory\",\"path\":\"");
        buf_append_json_escaped(&err, resolved);
        buf_append(&err, "\",\"files\":[]}\n");
        return err.data;
    }

    DIR *dir = fdopendir(dir_fd);
    if (!dir) {
        close(dir_fd);
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

    int fd = open(file_path, O_RDONLY | O_NOFOLLOW);
    if (fd < 0) {
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"Cannot open file\"}\n");
        return b.data;
    }

    struct stat st;
    if (fstat(fd, &st) != 0) {
        close(fd);
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"Cannot stat file\"}\n");
        return b.data;
    }

    if (S_ISDIR(st.st_mode)) {
        close(fd);
        buf_append(&b, "{\"type\":\"read_file_result\",\"success\":false,\"error\":\"Path is a directory\"}\n");
        return b.data;
    }

    FILE *fp = fdopen(fd, "rb");
    if (!fp) {
        close(fd);
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

    // Use open with O_NOFOLLOW to prevent symlink attacks, O_EXCL to prevent overwrite
    int fd = open(file_path, O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW, 0644);
    if (fd < 0) {
        buf_append(&b, "{\"type\":\"save_file_result\",\"success\":false,\"error\":\"Cannot open file for writing: ");
        buf_append_json_escaped(&b, file_path);
        buf_append(&b, "\"}\n");
        return b.data;
    }

    size_t len = content ? strlen(content) : 0;
    if (len > 0) {
        ssize_t written = write(fd, content, len);
        if ((size_t)written != len) {
            close(fd);
            buf_append(&b, "{\"type\":\"save_file_result\",\"success\":false,\"error\":\"Write failed\"}\n");
            return b.data;
        }
    }
    close(fd);

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