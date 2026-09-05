// NOTICE: This file is protected under RCF-PL
/*
 * WRT Editor — lightweight document editing mode for aladdin_term
 *
 * A simple line-based editor for .wrt files (AladdinAI's tagged-text format).
 * Supports basic editing + quick tag insertion shortcuts.
 *
 * Usage: wrt-edit <filename>
 *
 * Key bindings:
 *   Ctrl+B  — insert [b]bold[/b]
 *   Ctrl+I  — insert [i]italic[/i]
 *   Ctrl+U  — insert [u]underline[/u]
 *   Ctrl+K  — insert [code]code[/code]
 *   Ctrl+S  — save file
 *   Ctrl+Q  — quit (prompt if modified)
 *   Arrow keys — navigate
 *   Home/End — line start/end
 *   Backspace — delete char
 */

#include "wrt_editor.h"
#include <errno.h>

static struct termios orig_termios;

/* Restore terminal to original state */
static void disable_raw_mode(void) {
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
}

/* Enable raw mode for character-by-character input */
static void enable_raw_mode(void) {
    tcgetattr(STDIN_FILENO, &orig_termios);
    atexit(disable_raw_mode);

    struct termios raw = orig_termios;
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 1;

    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
}

/* Get terminal window size */
void wrt_get_window_size(int *rows, int *cols) {
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == -1 || ws.ws_col == 0) {
        *rows = 24;
        *cols = 80;
    } else {
        *rows = ws.ws_row;
        *cols = ws.ws_col;
    }
}

/* Initialize editor state */
static wrt_editor_t *wrt_editor_new(const char *filename) {
    wrt_editor_t *ed = calloc(1, sizeof(wrt_editor_t));
    if (!ed) return NULL;

    ed->filename = strdup(filename);
    ed->capacity = WRT_INITIAL_CAPACITY;
    ed->lines = calloc(ed->capacity, sizeof(char *));
    ed->num_lines = 0;
    ed->cursor_x = 0;
    ed->cursor_y = 0;
    ed->offset_y = 0;
    ed->modified = 0;

    wrt_get_window_size(&ed->screen_rows, &ed->screen_cols);
    ed->screen_rows -= 2; // Reserve for status bar

    return ed;
}

/* Free editor state */
void wrt_editor_free(wrt_editor_t *ed) {
    if (!ed) return;

    for (int i = 0; i < ed->num_lines; i++) {
        free(ed->lines[i]);
    }
    free(ed->lines);
    free(ed->filename);
    free(ed);
}

/* Ensure capacity for more lines */
static void wrt_ensure_capacity(wrt_editor_t *ed) {
    if (ed->num_lines >= ed->capacity) {
        ed->capacity *= 2;
        if (ed->capacity > WRT_MAX_LINES) {
            ed->capacity = WRT_MAX_LINES;
        }
        ed->lines = realloc(ed->lines, ed->capacity * sizeof(char *));
    }
}

/* Load file into editor */
int wrt_editor_load(wrt_editor_t *ed, const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) {
        // New file — start with empty line
        wrt_ensure_capacity(ed);
        ed->lines[0] = strdup("");
        ed->num_lines = 1;
        return 0;
    }

    char *line = NULL;
    size_t linecap = 0;
    ssize_t linelen;

    while ((linelen = getline(&line, &linecap, f)) != -1) {
        // Remove trailing newline
        while (linelen > 0 && (line[linelen - 1] == '\n' || line[linelen - 1] == '\r')) {
            line[--linelen] = '\0';
        }

        wrt_ensure_capacity(ed);
        ed->lines[ed->num_lines++] = strdup(line);
    }

    free(line);
    fclose(f);

    // Ensure at least one line
    if (ed->num_lines == 0) {
        wrt_ensure_capacity(ed);
        ed->lines[0] = strdup("");
        ed->num_lines = 1;
    }

    return 0;
}

/* Save editor contents to file */
int wrt_editor_save(wrt_editor_t *ed) {
    FILE *f = fopen(ed->filename, "w");
    if (!f) {
        return -1;
    }

    for (int i = 0; i < ed->num_lines; i++) {
        fprintf(f, "%s\n", ed->lines[i]);
    }

    fclose(f);
    ed->modified = 0;
    return 0;
}

/* Render editor screen */
void wrt_editor_render(wrt_editor_t *ed) {
    char buf[65536];
    int len = 0;

    // Clear screen and move cursor to home
    len += snprintf(buf + len, sizeof(buf) - len, CLEAR_SCREEN);
    len += snprintf(buf + len, sizeof(buf) - len, CURSOR_HOME);
    len += snprintf(buf + len, sizeof(buf) - len, CURSOR_HIDE);

    // Render visible lines
    for (int y = 0; y < ed->screen_rows; y++) {
        int file_row = y + ed->offset_y;

        if (file_row >= ed->num_lines) {
            len += snprintf(buf + len, sizeof(buf) - len, COLOR_DIM "~" COLOR_RESET);
        } else {
            // Highlight .wrt tags for visibility
            char *line = ed->lines[file_row];
            for (int i = 0; line[i]; i++) {
                if (line[i] == '[' && (i == 0 || line[i-1] != '\\')) {
                    // Start of tag
                    int j = i + 1;
                    while (line[j] && line[j] != ']') j++;
                    if (line[j] == ']') {
                        // Complete tag found
                        len += snprintf(buf + len, sizeof(buf) - len, COLOR_CYAN);
                        for (int k = i; k <= j; k++) {
                            buf[len++] = line[k];
                        }
                        len += snprintf(buf + len, sizeof(buf) - len, COLOR_RESET);
                        i = j;
                        continue;
                    }
                }
                buf[len++] = line[i];
            }
        }

        len += snprintf(buf + len, sizeof(buf) - len, "\r\n");
    }

    // Status bar
    len += snprintf(buf + len, sizeof(buf) - len, COLOR_BOLD COLOR_BLUE);
    char status[256];
    snprintf(status, sizeof(status), " %s %s | Line %d/%d Col %d | ^S:Save ^Q:Quit ^B:Bold ^I:Italic ^U:Underline ^K:Code ^H:Heading ",
             ed->filename, ed->modified ? "[+]" : "",
             ed->cursor_y + 1, ed->num_lines, ed->cursor_x + 1);

    int padding = ed->screen_cols - strlen(status);
    len += snprintf(buf + len, sizeof(buf) - len, "%s", status);
    for (int i = 0; i < padding; i++) {
        buf[len++] = ' ';
    }
    len += snprintf(buf + len, sizeof(buf) - len, COLOR_RESET "\r\n");

    // Message bar
    len += snprintf(buf + len, sizeof(buf) - len, COLOR_GREEN "WRT Editor - Lightweight document editing" COLOR_RESET);

    // Position cursor
    int screen_y = ed->cursor_y - ed->offset_y;
    len += snprintf(buf + len, sizeof(buf) - len, "\033[%d;%dH", screen_y + 1, ed->cursor_x + 1);
    len += snprintf(buf + len, sizeof(buf) - len, CURSOR_SHOW);

    write(STDOUT_FILENO, buf, len);
}

/* Insert character at cursor */
void wrt_editor_insert_char(wrt_editor_t *ed, int c) {
    if (ed->cursor_y >= ed->num_lines) {
        return;
    }

    char *line = ed->lines[ed->cursor_y];
    int len = strlen(line);

    if (len >= WRT_MAX_LINE_LENGTH - 1) {
        return; // Line too long
    }

    char *new_line = malloc(len + 2);
    memcpy(new_line, line, ed->cursor_x);
    new_line[ed->cursor_x] = c;
    memcpy(new_line + ed->cursor_x + 1, line + ed->cursor_x, len - ed->cursor_x);
    new_line[len + 1] = '\0';

    free(ed->lines[ed->cursor_y]);
    ed->lines[ed->cursor_y] = new_line;
    ed->cursor_x++;
    ed->modified = 1;
}

/* Delete character at cursor */
void wrt_editor_delete_char(wrt_editor_t *ed) {
    if (ed->cursor_y >= ed->num_lines) {
        return;
    }

    if (ed->cursor_x == 0 && ed->cursor_y == 0) {
        return; // Nothing to delete
    }

    char *line = ed->lines[ed->cursor_y];
    int len = strlen(line);

    if (ed->cursor_x > 0) {
        // Delete character before cursor
        char *new_line = malloc(len);
        memcpy(new_line, line, ed->cursor_x - 1);
        memcpy(new_line + ed->cursor_x - 1, line + ed->cursor_x, len - ed->cursor_x);
        new_line[len - 1] = '\0';

        free(ed->lines[ed->cursor_y]);
        ed->lines[ed->cursor_y] = new_line;
        ed->cursor_x--;
        ed->modified = 1;
    } else {
        // Join with previous line
        if (ed->cursor_y > 0) {
            char *prev_line = ed->lines[ed->cursor_y - 1];
            int prev_len = strlen(prev_line);

            char *new_line = malloc(prev_len + len + 1);
            strcpy(new_line, prev_line);
            strcat(new_line, line);

            free(ed->lines[ed->cursor_y - 1]);
            free(ed->lines[ed->cursor_y]);
            ed->lines[ed->cursor_y - 1] = new_line;

            // Shift lines up
            for (int i = ed->cursor_y; i < ed->num_lines - 1; i++) {
                ed->lines[i] = ed->lines[i + 1];
            }
            ed->num_lines--;
            ed->cursor_y--;
            ed->cursor_x = prev_len;
            ed->modified = 1;
        }
    }
}

/* Insert newline at cursor */
static void wrt_insert_newline(wrt_editor_t *ed) {
    if (ed->num_lines >= WRT_MAX_LINES) {
        return;
    }

    char *line = ed->lines[ed->cursor_y];

    // Split current line
    char *new_line1 = malloc(ed->cursor_x + 1);
    memcpy(new_line1, line, ed->cursor_x);
    new_line1[ed->cursor_x] = '\0';

    char *new_line2 = strdup(line + ed->cursor_x);

    free(ed->lines[ed->cursor_y]);
    ed->lines[ed->cursor_y] = new_line1;

    // Shift lines down
    wrt_ensure_capacity(ed);
    for (int i = ed->num_lines; i > ed->cursor_y + 1; i--) {
        ed->lines[i] = ed->lines[i - 1];
    }

    ed->lines[ed->cursor_y + 1] = new_line2;
    ed->num_lines++;
    ed->cursor_y++;
    ed->cursor_x = 0;
    ed->modified = 1;
}

/* Insert .wrt tag at cursor */
void wrt_editor_insert_tag(wrt_editor_t *ed, const char *tag) {
    // Insert opening tag
    for (const char *p = tag; *p; p++) {
        wrt_editor_insert_char(ed, *p);
    }

    // Save position for cursor
    int saved_x = ed->cursor_x;

    // Insert closing tag
    char closing[64];
    snprintf(closing, sizeof(closing), "[/%s", tag + 1); // Skip opening [
    for (const char *p = closing; *p; p++) {
        wrt_editor_insert_char(ed, *p);
    }

    // Move cursor between tags
    ed->cursor_x = saved_x;
}

/* Move cursor */
void wrt_editor_move_cursor(wrt_editor_t *ed, int dx, int dy) {
    if (dy != 0) {
        ed->cursor_y += dy;
        if (ed->cursor_y < 0) ed->cursor_y = 0;
        if (ed->cursor_y >= ed->num_lines) ed->cursor_y = ed->num_lines - 1;

        // Clamp cursor_x to line length
        int len = strlen(ed->lines[ed->cursor_y]);
        if (ed->cursor_x > len) ed->cursor_x = len;
    }

    if (dx != 0) {
        ed->cursor_x += dx;
        if (ed->cursor_x < 0) ed->cursor_x = 0;

        int len = strlen(ed->lines[ed->cursor_y]);
        if (ed->cursor_x > len) ed->cursor_x = len;
    }

    // Adjust viewport
    if (ed->cursor_y < ed->offset_y) {
        ed->offset_y = ed->cursor_y;
    }
    if (ed->cursor_y >= ed->offset_y + ed->screen_rows) {
        ed->offset_y = ed->cursor_y - ed->screen_rows + 1;
    }
}

/* Read a key (including escape sequences) */
static int wrt_read_key(void) {
    int nread;
    char c;

    while ((nread = read(STDIN_FILENO, &c, 1)) != 1) {
        if (nread == -1 && errno != EAGAIN) return -1;
    }

    if (c == '\033') {
        char seq[3];

        if (read(STDIN_FILENO, &seq[0], 1) != 1) return '\033';
        if (read(STDIN_FILENO, &seq[1], 1) != 1) return '\033';

        if (seq[0] == '[') {
            switch (seq[1]) {
                case 'A': return 1000; // Up arrow
                case 'B': return 1001; // Down arrow
                case 'C': return 1002; // Right arrow
                case 'D': return 1003; // Left arrow
                case 'H': return 1004; // Home
                case 'F': return 1005; // End
            }
        }

        return '\033';
    }

    return c;
}

/* Check if cursor is after an opening tag and auto-close it */
static void wrt_auto_close_tag(wrt_editor_t *ed) {
    if (ed->cursor_y >= ed->num_lines || ed->cursor_x == 0) {
        return;
    }

    char *line = ed->lines[ed->cursor_y];
    int len = strlen(line);

    // Look backwards from cursor to find opening tag
    int tag_start = -1;
    for (int i = ed->cursor_x - 1; i >= 0; i--) {
        if (line[i] == ']') {
            // Check if this is an opening tag (no / after [)
            int bracket_pos = i - 1;
            while (bracket_pos >= 0 && line[bracket_pos] != '[') {
                bracket_pos--;
            }
            if (bracket_pos >= 0 && bracket_pos + 1 < i && line[bracket_pos + 1] != '/') {
                tag_start = bracket_pos;
                break;
            }
        } else if (line[i] == '[') {
            tag_start = i;
            break;
        }
    }

    if (tag_start == -1) {
        return;
    }

    // Extract tag name
    char tag_name[32];
    int tag_idx = 0;
    for (int i = tag_start + 1; i < ed->cursor_x && i < len && tag_idx < 31; i++) {
        if (line[i] == ']') {
            break;
        }
        tag_name[tag_idx++] = line[i];
    }
    tag_name[tag_idx] = '\0';

    // Check if it's a valid tag
    const char *valid_tags[] = {"b", "i", "u", "s", "code", "h1", "h2", "h3", "quote", NULL};
    int is_valid = 0;
    for (int i = 0; valid_tags[i] != NULL; i++) {
        if (strcmp(tag_name, valid_tags[i]) == 0) {
            is_valid = 1;
            break;
        }
    }

    if (!is_valid) {
        return;
    }

    // Insert closing tag
    char closing[64];
    snprintf(closing, sizeof(closing), "[/%s]", tag_name);

    for (const char *p = closing; *p; p++) {
        wrt_editor_insert_char(ed, *p);
    }

    // Move cursor back between tags
    int closing_len = strlen(closing);
    ed->cursor_x -= closing_len;
}

/* Process key press */
void wrt_editor_process_key(wrt_editor_t *ed, int key) {
    switch (key) {
        case 1000: // Up
            wrt_editor_move_cursor(ed, 0, -1);
            break;
        case 1001: // Down
            wrt_editor_move_cursor(ed, 0, 1);
            break;
        case 1002: // Right
            wrt_editor_move_cursor(ed, 1, 0);
            break;
        case 1003: // Left
            wrt_editor_move_cursor(ed, -1, 0);
            break;
        case 1004: // Home
            ed->cursor_x = 0;
            break;
        case 1005: // End
            ed->cursor_x = strlen(ed->lines[ed->cursor_y]);
            break;
        case 127: // Backspace
        case 8:   // Ctrl+H (also backspace on some terminals)
            wrt_editor_delete_char(ed);
            break;
        case '\r': // Enter
        case '\n':
            wrt_insert_newline(ed);
            break;
        case 2: // Ctrl+B — bold
            wrt_editor_insert_tag(ed, "[b]");
            break;
        case 9: // Ctrl+I (Tab, but we use it for italic)
            wrt_editor_insert_tag(ed, "[i]");
            break;
        case 21: // Ctrl+U — underline
            wrt_editor_insert_tag(ed, "[u]");
            break;
        case 11: // Ctrl+K — code
            wrt_editor_insert_tag(ed, "[code]");
            break;
        case ']': // Auto-close tag on ]
            wrt_editor_insert_char(ed, key);
            wrt_auto_close_tag(ed);
            break;
        default:
            if (key >= 32 && key < 127) {
                wrt_editor_insert_char(ed, key);
            }
            break;
    }
}

/* Main editor loop */
int wrt_editor_run(const char *filename) {
    wrt_editor_t *ed = wrt_editor_new(filename);
    if (!ed) {
        fprintf(stderr, "Failed to initialize editor\n");
        return 1;
    }

    if (wrt_editor_load(ed, filename) < 0) {
        fprintf(stderr, "Failed to load file: %s\n", filename);
        wrt_editor_free(ed);
        return 1;
    }

    enable_raw_mode();

    int quit = 0;
    while (!quit) {
        wrt_editor_render(ed);

        int key = wrt_read_key();

        if (key == 19) { // Ctrl+S — save
            if (wrt_editor_save(ed) == 0) {
                // Show brief save message
                write(STDOUT_FILENO, "\r\nSaved.\r\n", 10);
                usleep(500000); // 0.5s
            } else {
                write(STDOUT_FILENO, "\r\nSave failed!\r\n", 17);
                usleep(1000000); // 1s
            }
        } else if (key == 17) { // Ctrl+Q — quit
            if (ed->modified) {
                write(STDOUT_FILENO, "\r\nUnsaved changes. Save first? (y/n/c): ", 41);
                int c = wrt_read_key();
                if (c == 'y' || c == 'Y') {
                    if (wrt_editor_save(ed) == 0) {
                        quit = 1;
                    }
                } else if (c == 'n' || c == 'N') {
                    quit = 1;
                } // else cancel (c or any other key)
            } else {
                quit = 1;
            }
        } else {
            wrt_editor_process_key(ed, key);
        }
    }

    disable_raw_mode();
    wrt_editor_free(ed);

    printf("Editor closed.\n");
    return 0;
}
