// NOTICE: This file is protected under RCF-PL
/*
 * wrt-validate — WRT file validator and fixer
 *
 * Validates .wrt files for:
 * - Unclosed tags
 * - Mismatched opening/closing tags
 * - Empty tags []
 * - Invalid tag names
 *
 * Usage: wrt-validate <file.wrt> [--fix]
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

typedef struct {
    char tag[32];
    int line;
    int col;
} TagStack;

typedef struct {
    char *message;
    int line;
    int col;
    int severity; // 0=error, 1=warning
} ValidationError;

static ValidationError *errors = NULL;
static int num_errors = 0;
static int errors_capacity = 0;

static TagStack *tag_stack = NULL;
static int stack_size = 0;
static int stack_capacity = 0;

void add_error(const char *msg, int line, int col, int severity) {
    if (num_errors >= errors_capacity) {
        errors_capacity = errors_capacity == 0 ? 10 : errors_capacity * 2;
        errors = realloc(errors, errors_capacity * sizeof(ValidationError));
    }

    errors[num_errors].message = strdup(msg);
    errors[num_errors].line = line;
    errors[num_errors].col = col;
    errors[num_errors].severity = severity;
    num_errors++;
}

void push_tag(const char *tag, int line, int col) {
    if (stack_size >= stack_capacity) {
        stack_capacity = stack_capacity == 0 ? 10 : stack_capacity * 2;
        tag_stack = realloc(tag_stack, stack_capacity * sizeof(TagStack));
    }

    strncpy(tag_stack[stack_size].tag, tag, 31);
    tag_stack[stack_size].tag[31] = '\0';
    tag_stack[stack_size].line = line;
    tag_stack[stack_size].col = col;
    stack_size++;
}

TagStack* pop_tag() {
    if (stack_size == 0) return NULL;
    stack_size--;
    return &tag_stack[stack_size];
}

int is_valid_tag(const char *tag) {
    const char *valid_tags[] = {
        "b", "i", "u", "s", "code", "h1", "h2", "h3",
        "quote", "list", "table", "img", NULL
    };

    for (int i = 0; valid_tags[i] != NULL; i++) {
        if (strcmp(tag, valid_tags[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

void validate_file(const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) {
        fprintf(stderr, "Error: Cannot open file %s\n", filename);
        return;
    }

    char *line = NULL;
    size_t linecap = 0;
    int line_num = 0;

    while (getline(&line, &linecap, f) != -1) {
        line_num++;

        for (int i = 0; line[i]; i++) {
            // Check for empty tags []
            if (line[i] == '[' && line[i+1] == ']') {
                char msg[128];
                snprintf(msg, sizeof(msg), "Empty tag []");
                add_error(msg, line_num, i + 1, 1);
                i++; // Skip ]
                continue;
            }

            // Check for opening tag [tag]
            if (line[i] == '[' && line[i+1] != '/') {
                int tag_start = i + 1;
                int tag_end = tag_start;

                // Find closing ]
                while (line[tag_end] && line[tag_end] != ']') {
                    tag_end++;
                }

                if (line[tag_end] == ']') {
                    char tag[32];
                    int tag_len = tag_end - tag_start;
                    if (tag_len >= 32) tag_len = 31;

                    strncpy(tag, line + tag_start, tag_len);
                    tag[tag_len] = '\0';

                    // Skip attributes (for img tags)
                    char *space = strchr(tag, ' ');
                    if (space) *space = '\0';

                    if (tag[0] == '\0') {
                        add_error("Empty tag name", line_num, i + 1, 0);
                    } else if (!is_valid_tag(tag)) {
                        char msg[128];
                        snprintf(msg, sizeof(msg), "Unknown tag: [%s]", tag);
                        add_error(msg, line_num, i + 1, 1);
                    } else if (strcmp(tag, "img") != 0 && strcmp(tag, "list") != 0 && strcmp(tag, "table") != 0) {
                        // Only track tags that need closing
                        push_tag(tag, line_num, i + 1);
                    }

                    i = tag_end;
                }
            }
            // Check for closing tag [/tag]
            else if (line[i] == '[' && line[i+1] == '/') {
                int tag_start = i + 2;
                int tag_end = tag_start;

                // Find closing ]
                while (line[tag_end] && line[tag_end] != ']') {
                    tag_end++;
                }

                if (line[tag_end] == ']') {
                    char tag[32];
                    int tag_len = tag_end - tag_start;
                    if (tag_len >= 32) tag_len = 31;

                    strncpy(tag, line + tag_start, tag_len);
                    tag[tag_len] = '\0';

                    TagStack *open_tag = pop_tag();
                    if (!open_tag) {
                        char msg[128];
                        snprintf(msg, sizeof(msg), "Closing tag [/%s] without opening tag", tag);
                        add_error(msg, line_num, i + 1, 0);
                    } else if (strcmp(open_tag->tag, tag) != 0) {
                        char msg[128];
                        snprintf(msg, sizeof(msg), "Mismatched tags: [%s] at line %d, [/%s] here",
                                 open_tag->tag, open_tag->line, tag);
                        add_error(msg, line_num, i + 1, 0);
                    }

                    i = tag_end;
                }
            }
        }
    }

    // Check for unclosed tags
    while (stack_size > 0) {
        TagStack *open_tag = pop_tag();
        char msg[128];
        snprintf(msg, sizeof(msg), "Unclosed tag [%s]", open_tag->tag);
        add_error(msg, open_tag->line, open_tag->col, 0);
    }

    free(line);
    fclose(f);
}

void print_errors() {
    if (num_errors == 0) {
        printf("✓ No errors found\n");
        return;
    }

    printf("Found %d issue%s:\n\n", num_errors, num_errors == 1 ? "" : "s");

    for (int i = 0; i < num_errors; i++) {
        const char *prefix = errors[i].severity == 0 ? "ERROR" : "WARNING";
        printf("  %s (line %d, col %d): %s\n",
               prefix, errors[i].line, errors[i].col, errors[i].message);
    }
}

void cleanup() {
    for (int i = 0; i < num_errors; i++) {
        free(errors[i].message);
    }
    free(errors);
    free(tag_stack);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <file.wrt> [--fix]\n", argv[0]);
        fprintf(stderr, "\nValidates .wrt files for tag errors.\n");
        fprintf(stderr, "  --fix  Attempt to automatically fix errors (not implemented yet)\n");
        return 1;
    }

    const char *filename = argv[1];
    int fix_mode = (argc > 2 && strcmp(argv[2], "--fix") == 0);

    if (fix_mode) {
        fprintf(stderr, "Note: --fix mode not implemented yet\n");
    }

    validate_file(filename);
    print_errors();
    cleanup();

    return num_errors > 0 ? 1 : 0;
}
