#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* Standalone inline implementation for testing conversion logic */
typedef struct {
    char *data;
    size_t len;
    size_t cap;
} str_buf_t;

static void buf_init(str_buf_t *b) {
    b->cap = 4096;
    b->data = malloc(b->cap);
    b->data[0] = '\0';
    b->len = 0;
}

static void buf_append_len(str_buf_t *b, const char *s, size_t n) {
    if (b->len + n + 1 >= b->cap) {
        while (b->len + n + 1 >= b->cap) b->cap *= 2;
        b->data = realloc(b->data, b->cap);
    }
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = '\0';
}

static void buf_append(str_buf_t *b, const char *s) { buf_append_len(b, s, strlen(s)); }
static void buf_append_c(str_buf_t *b, char c) { char s[2] = {c, '\0'}; buf_append_len(b, s, 1); }

char *wrt_from_editable_html(const char *html) {
    if (!html || !html[0]) return strdup("");

    str_buf_t b;
    buf_init(&b);
    const char *p = html;
    int in_list = 0;
    int in_table = 0;
    int in_tr = 0;
    int in_td = 0;
    int in_blockquote = 0;
    int first_text = 1;

    while (*p) {
        if (*p == '\n' || *p == '\r') { p++; continue; }

        /* Skip wrapper div */
        if (strncmp(p, "<div", 4) == 0) {
            const char *end = strchr(p, '>');
            if (end) p = end + 1;
            else { p++; continue; }
            continue;
        }
        if (strncmp(p, "</div>", 6) == 0) { p += 6; continue; }

        /* <p> tags */
        if (strncmp(p, "<p", 2) == 0 && (p[2] == '>' || p[2] == ' ')) {
            p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            if (!first_text && b.len > 0 && b.data[b.len - 1] != '\n')
                buf_append_c(&b, '\n');
            continue;
        }
        if (strncmp(p, "</p>", 4) == 0) {
            p += 4;
            if (b.len > 0 && b.data[b.len - 1] != '\n')
                buf_append_c(&b, '\n');
            first_text = 0;
            continue;
        }

        /* <br> or <br/> */
        if (strncmp(p, "<br", 3) == 0) {
            p += 3;
            if (*p == ' ' || *p == '/') {
                while (*p && *p != '>') p++;
            }
            if (*p == '>') p++;
            buf_append_c(&b, '\n');
            continue;
        }

        /* <strong> or <b> */
        if (strncmp(p, "<strong", 7) == 0 || (strncmp(p, "<b", 2) == 0 && (p[2] == '>' || p[2] == ' '))) {
            if (strncmp(p, "<strong", 7) == 0) p += 7;
            else p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[b]");
            continue;
        }
        if (strncmp(p, "</strong>", 9) == 0) { p += 9; buf_append(&b, "[/b]"); continue; }
        if (strncmp(p, "</b>", 4) == 0) { p += 4; buf_append(&b, "[/b]"); continue; }

        /* <em> or <i> */
        if (strncmp(p, "<em", 3) == 0 || (strncmp(p, "<i", 2) == 0 && (p[2] == '>' || p[2] == ' '))) {
            if (strncmp(p, "<em", 3) == 0) p += 3;
            else p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[i]");
            continue;
        }
        if (strncmp(p, "</em>", 5) == 0) { p += 5; buf_append(&b, "[/i]"); continue; }
        if (strncmp(p, "</i>", 4) == 0) { p += 4; buf_append(&b, "[/i]"); continue; }

        /* <u> */
        if (strncmp(p, "<u", 2) == 0 && (p[2] == '>' || p[2] == ' ')) {
            p += 2;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[u]");
            continue;
        }
        if (strncmp(p, "</u>", 4) == 0) { p += 4; buf_append(&b, "[/u]"); continue; }

        /* <s> */
        if (strncmp(p, "<s>", 3) == 0) { p += 3; buf_append(&b, "[s]"); continue; }
        if (strncmp(p, "</s>", 4) == 0) { p += 4; buf_append(&b, "[/s]"); continue; }

        /* <code> */
        if (strncmp(p, "<code", 5) == 0 && (p[5] == '>' || p[5] == ' ')) {
            p += 5;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "[code]");
            continue;
        }
        if (strncmp(p, "</code>", 7) == 0) { p += 7; buf_append(&b, "[/code]"); continue; }

        /* <blockquote> */
        if (strncmp(p, "<blockquote", 11) == 0) {
            p += 11;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            in_blockquote = 1;
            buf_append(&b, "[quote]");
            continue;
        }
        if (strncmp(p, "</blockquote>", 13) == 0) {
            p += 13;
            in_blockquote = 0;
            buf_append(&b, "[/quote]");
            if (b.len > 0 && b.data[b.len - 1] != '\n')
                buf_append_c(&b, '\n');
            continue;
        }

        /* <h1>, <h2>, <h3> */
        if (strncmp(p, "<h1", 3) == 0 || strncmp(p, "<h2", 3) == 0 || strncmp(p, "<h3", 3) == 0) {
            char htag = p[2];
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            char htag_close[6];
            snprintf(htag_close, sizeof(htag_close), "</h%c>", htag);
            /* Collect heading content */
            str_buf_t hcontent;
            buf_init(&hcontent);
            while (*p && strncmp(p, htag_close, strlen(htag_close)) != 0) {
                if (*p == '<') {
                    p++;
                    while (*p && *p != '>') p++;
                    if (*p == '>') p++;
                    continue;
                }
                buf_append_c(&hcontent, *p);
                p++;
            }
            if (*p) p += strlen(htag_close);
            buf_append(&b, "[h");
            buf_append_c(&b, htag);
            buf_append(&b, "]");
            buf_append(&b, hcontent.data);
            buf_append(&b, "[/h");
            buf_append_c(&b, htag);
            buf_append(&b, "]");
            if (b.len > 0 && b.data[b.len - 1] != '\n')
                buf_append_c(&b, '\n');
            free(hcontent.data);
            continue;
        }

        /* <ul> */
        if (strncmp(p, "<ul", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            in_list = 1;
            buf_append(&b, "[list]\n");
            continue;
        }
        if (strncmp(p, "</ul>", 5) == 0) {
            p += 5;
            in_list = 0;
            buf_append(&b, "[/list]\n");
            continue;
        }

        /* <li> */
        if (strncmp(p, "<li", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            buf_append(&b, "- ");
            continue;
        }
        if (strncmp(p, "</li>", 5) == 0) {
            p += 5;
            buf_append_c(&b, '\n');
            continue;
        }

        /* <table> */
        if (strncmp(p, "<table", 6) == 0) {
            p += 6;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            in_table = 1;
            buf_append(&b, "[table]\n");
            continue;
        }
        if (strncmp(p, "</table>", 8) == 0) {
            p += 8;
            in_table = 0;
            buf_append(&b, "[/table]\n");
            continue;
        }

        /* <tr> */
        if (strncmp(p, "<tr", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            in_tr = 1;
            continue;
        }
        if (strncmp(p, "</tr>", 5) == 0) {
            p += 5;
            in_tr = 0;
            buf_append(&b, "|\n");
            continue;
        }

        /* <th> and <td> */
        if (strncmp(p, "<th", 3) == 0 || strncmp(p, "<td", 3) == 0) {
            p += 3;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            in_td = 1;
            buf_append(&b, "| ");
            continue;
        }
        if (strncmp(p, "</th>", 5) == 0 || strncmp(p, "</td>", 5) == 0) {
            p += 5;
            in_td = 0;
            buf_append(&b, " ");
            continue;
        }

        /* Skip remaining tags */
        if (*p == '<') {
            p++;
            while (*p && *p != '>') p++;
            if (*p == '>') p++;
            continue;
        }

        /* HTML entities */
        if (*p == '&') {
            if (strncmp(p, "&amp;", 5) == 0) { buf_append_c(&b, '&'); p += 5; }
            else if (strncmp(p, "&lt;", 4) == 0) { buf_append_c(&b, '<'); p += 4; }
            else if (strncmp(p, "&gt;", 4) == 0) { buf_append_c(&b, '>'); p += 4; }
            else if (strncmp(p, "&quot;", 6) == 0) { buf_append_c(&b, '"'); p += 6; }
            else if (strncmp(p, "&#39;", 5) == 0) { buf_append_c(&b, '\''); p += 5; }
            else {
                const char *semi = p;
                int i = 0;
                while (semi[i] && semi[i] != ';' && semi[i] != '<' && semi[i] != ' ' && i < 10) i++;
                if (semi[i] == ';') { buf_append_len(&b, p, i + 1); p += i + 1; }
                else { buf_append_c(&b, '&'); p++; }
            }
            continue;
        }

        /* Regular text */
        const char *text_start = p;
        while (*p && *p != '<' && *p != '&') p++;
        if (p > text_start) buf_append_len(&b, text_start, p - text_start);
        first_text = 0;
    }
    if (b.len > 0 && b.data[b.len - 1] != '\n') buf_append_c(&b, '\n');
    return b.data;
}

/* Test counters */
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST_ASSERT(cond, msg) \
    do { \
        tests_run++; \
        if (cond) { \
            tests_passed++; \
            printf("  PASS: %s\n", msg); \
        } else { \
            tests_failed++; \
            printf("  FAIL: %s\n", msg); \
        } \
    } while (0)

#define TEST_ASSERT_STR_EQ(actual, expected, msg) \
    do { \
        tests_run++; \
        if (strcmp(actual, expected) == 0) { \
            tests_passed++; \
            printf("  PASS: %s\n", msg); \
        } else { \
            tests_failed++; \
            printf("  FAIL: %s\n", msg); \
            printf("    Expected: [%s]\n", expected); \
            printf("    Actual:   [%s]\n", actual); \
        } \
    } while (0)

void test_basic_conversion() {
    printf("\n=== test_basic_conversion ===\n");
    const char *html = "<div class=\"wrt-editable\"><p>Hello</p><p>World</p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(result != NULL, "Result should not be NULL");
    TEST_ASSERT(strstr(result, "Hello") != NULL, "Should contain 'Hello'");
    TEST_ASSERT(strstr(result, "World") != NULL, "Should contain 'World'");
    free(result);
}

void test_strong_to_bold() {
    printf("\n=== test_strong_to_bold ===\n");
    const char *html = "<div class=\"wrt-editable\"><p><strong>bold</strong></p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[b]bold[/b]") != NULL, "Should convert <strong> to [b][/b]");
    free(result);
}

void test_em_to_italic() {
    printf("\n=== test_em_to_italic ===\n");
    const char *html = "<div class=\"wrt-editable\"><p><em>italic</em></p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[i]italic[/i]") != NULL, "Should convert <em> to [i][/i]");
    free(result);
}

void test_underline() {
    printf("\n=== test_underline ===\n");
    const char *html = "<div class=\"wrt-editable\"><p><u>underline</u></p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[u]underline[/u]") != NULL, "Should convert <u> to [u][/u]");
    free(result);
}

void test_strikethrough() {
    printf("\n=== test_strikethrough ===\n");
    const char *html = "<div class=\"wrt-editable\"><p><s>strike</s></p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[s]strike[/s]") != NULL, "Should convert <s> to [s][/s]");
    free(result);
}

void test_code() {
    printf("\n=== test_code ===\n");
    const char *html = "<div class=\"wrt-editable\"><p><code>code</code></p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[code]code[/code]") != NULL, "Should convert <code> to [code][/code]");
    free(result);
}

void test_headings() {
    printf("\n=== test_headings ===\n");
    const char *html = "<div class=\"wrt-editable\"><h1>Title</h1><h2>Sub</h2><h3>Subsub</h3></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[h1]Title[/h1]") != NULL, "Should convert h1");
    TEST_ASSERT(strstr(result, "[h2]Sub[/h2]") != NULL, "Should convert h2");
    TEST_ASSERT(strstr(result, "[h3]Subsub[/h3]") != NULL, "Should convert h3");
    free(result);
}

void test_blockquote() {
    printf("\n=== test_blockquote ===\n");
    const char *html = "<div class=\"wrt-editable\"><blockquote>Quote text</blockquote></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[quote]Quote text[/quote]") != NULL, "Should convert blockquote");
    free(result);
}

void test_unordered_list() {
    printf("\n=== test_unordered_list ===\n");
    const char *html = "<div class=\"wrt-editable\"><ul><li>Item 1</li><li>Item 2</li></ul></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[list]") != NULL, "Should have [list] tag");
    TEST_ASSERT(strstr(result, "- Item 1") != NULL, "Should have list items");
    TEST_ASSERT(strstr(result, "[/list]") != NULL, "Should close list");
    free(result);
}

void test_table() {
    printf("\n=== test_table ===\n");
    const char *html = "<div class=\"wrt-editable\"><table><tr><th>H1</th><th>H2</th></tr><tr><td>A</td><td>B</td></tr></table></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[table]") != NULL, "Should have [table] tag");
    TEST_ASSERT(strstr(result, "| H1 ") != NULL, "Should have header row");
    TEST_ASSERT(strstr(result, "| A ") != NULL, "Should have data row");
    TEST_ASSERT(strstr(result, "[/table]") != NULL, "Should close table");
    free(result);
}

void test_br() {
    printf("\n=== test_br ===\n");
    const char *html = "<div class=\"wrt-editable\"><p>Line1<br>Line2</p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "Line1\n") != NULL, "Should have newline after Line1");
    TEST_ASSERT(strstr(result, "Line2") != NULL, "Should have Line2");
    free(result);
}

void test_html_entities() {
    printf("\n=== test_html_entities ===\n");
    const char *html = "<div class=\"wrt-editable\"><p>A &amp; B &lt; C &gt; D</p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "A & B < C > D") != NULL, "Should decode entities");
    free(result);
}

void test_with_attributes() {
    printf("\n=== test_with_attributes ===\n");
    const char *html = "<div class=\"wrt-editable\"><p class=\"intro\" id=\"p1\">Text</p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "Text") != NULL, "Should extract text even with attributes");
    free(result);
}

void test_empty_input() {
    printf("\n=== test_empty_input ===\n");
    const char *html = "";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(result != NULL, "Result should not be NULL");
    TEST_ASSERT(strcmp(result, "") == 0, "Empty input should give empty output");
    free(result);
}

void test_nested_tags() {
    printf("\n=== test_nested_tags ===\n");
    const char *html = "<div class=\"wrt-editable\"><p><strong>Bold <em>and italic</em></strong></p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "[b]Bold ") != NULL, "Should have bold open");
    TEST_ASSERT(strstr(result, "[i]and italic[/i]") != NULL, "Should have italic");
    TEST_ASSERT(strstr(result, "[/b]") != NULL, "Should have bold close");
    free(result);
}

void test_multiline_paragraphs() {
    printf("\n=== test_multiline_paragraphs ===\n");
    const char *html = "<div class=\"wrt-editable\"><p>First</p><p>Second</p><p>Third</p></div>";
    char *result = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(result, "First\n") != NULL, "Should have newline after First");
    TEST_ASSERT(strstr(result, "Second\n") != NULL, "Should have newline after Second");
    TEST_ASSERT(strstr(result, "Third\n") != NULL, "Should have newline after Third");
    free(result);
}

int main() {
    printf("Running WRT Standalone C Tests\n");
    printf("==============================\n");

    test_basic_conversion();
    test_strong_to_bold();
    test_em_to_italic();
    test_underline();
    test_strikethrough();
    test_code();
    test_headings();
    test_blockquote();
    test_unordered_list();
    test_table();
    test_br();
    test_html_entities();
    test_with_attributes();
    test_empty_input();
    test_nested_tags();
    test_multiline_paragraphs();

    printf("\n==============================\n");
    printf("Tests run:   %d\n", tests_run);
    printf("Tests passed: %d\n", tests_passed);
    printf("Tests failed: %d\n", tests_failed);

    return tests_failed == 0 ? 0 : 1;
}
