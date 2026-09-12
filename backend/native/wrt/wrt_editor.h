// NOTICE: This file is protected under RCF-PL
#ifndef WRT_EDITOR_H
#define WRT_EDITOR_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <ctype.h>

#define WRT_MAX_LINE_LENGTH 4096
#define WRT_MAX_LINES 10000
#define WRT_INITIAL_CAPACITY 1000

/* ANSI escape sequences */
#define CLEAR_SCREEN "\033[2J"
#define CURSOR_HOME "\033[H"
#define CURSOR_HIDE "\033[?25l"
#define CURSOR_SHOW "\033[?25h"
#define COLOR_RESET "\033[0m"
#define COLOR_BOLD "\033[1m"
#define COLOR_DIM "\033[2m"
#define COLOR_CYAN "\033[36m"
#define COLOR_GREEN "\033[32m"
#define COLOR_YELLOW "\033[33m"
#define COLOR_BLUE "\033[34m"

/* Editor state */
typedef struct {
    char **lines;
    int num_lines;
    int capacity;
    int cursor_x;
    int cursor_y;
    int offset_y;
    int screen_rows;
    int screen_cols;
    char *filename;
    int modified;
} wrt_editor_t;

/* Function prototypes */
int wrt_editor_run(const char *filename);
void wrt_editor_free(wrt_editor_t *ed);
int wrt_editor_load(wrt_editor_t *ed, const char *filename);
int wrt_editor_save(wrt_editor_t *ed);
void wrt_editor_render(wrt_editor_t *ed);
void wrt_editor_insert_char(wrt_editor_t *ed, int c);
void wrt_editor_delete_char(wrt_editor_t *ed);
void wrt_editor_insert_tag(wrt_editor_t *ed, const char *tag);
void wrt_editor_move_cursor(wrt_editor_t *ed, int dx, int dy);
void wrt_editor_process_key(wrt_editor_t *ed, int key);
void wrt_get_window_size(int *rows, int *cols);

#endif /* WRT_EDITOR_H */
