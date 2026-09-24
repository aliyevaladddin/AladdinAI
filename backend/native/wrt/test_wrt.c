#include "wrt_engine.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

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

void test_validate_valid() {
    printf("\n=== test_validate_valid ===\n");
    const char *content = "[h1]Architecture Document[/h1]\n[quote]Deterministic computing[/quote]\n[b]bold text[/b]";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.valid == 1, "Valid document should pass validation");
    TEST_ASSERT(rep.tag_count == 6, "Should count 6 tags (3 open + 3 close)");
    TEST_ASSERT(rep.issue_count == 0, "Should have no issues");
}

void test_validate_invalid_unclosed() {
    printf("\n=== test_validate_invalid_unclosed ===\n");
    const char *content = "[h1]Architecture[/h1]\n[b]unclosed bold tag";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.valid == 0, "Unclosed tag should fail validation");
    TEST_ASSERT(rep.issue_count > 0, "Should have at least one issue");
    TEST_ASSERT_STR_EQ(rep.issues[0].tag, "b", "Issue should be about 'b' tag");
}

void test_validate_empty_tag() {
    printf("\n=== test_validate_empty_tag ===\n");
    const char *content = "[] is empty";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.valid == 0, "Empty tag should fail validation");
    TEST_ASSERT(rep.issue_count > 0, "Should have issue for empty tag");
}

void test_validate_unknown_tag() {
    printf("\n=== test_validate_unknown_tag ===\n");
    const char *content = "[unknown]text[/unknown]";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.valid == 0, "Unknown tag should fail validation");
    TEST_ASSERT(rep.issue_count > 0, "Should have issue for unknown tag");
    TEST_ASSERT_STR_EQ(rep.issues[0].tag, "unknown", "Issue should mention unknown tag");
}

void test_validate_mismatched_tags() {
    printf("\n=== test_validate_mismatched_tags ===\n");
    const char *content = "[b]bold [/i]text";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.valid == 0, "Mismatched tags should fail validation");
    TEST_ASSERT(rep.issue_count > 0, "Should have issue for mismatched tags");
}

void test_fix_unclosed() {
    printf("\n=== test_fix_unclosed ===\n");
    const char *content = "[b]unclosed bold";
    char *fixed = wrt_fix(content);
    TEST_ASSERT(fixed != NULL, "Fix should return non-NULL");
    TEST_ASSERT(strstr(fixed, "[/b]") != NULL, "Fixed content should have closing [/b]");
    free(fixed);
}

void test_fix_empty_tag() {
    printf("\n=== test_fix_empty_tag ===\n");
    const char *content = "text [] more";
    char *fixed = wrt_fix(content);
    TEST_ASSERT(fixed != NULL, "Fix should return non-NULL");
    TEST_ASSERT(strstr(fixed, "[]") == NULL, "Fixed content should not have empty tags");
    free(fixed);
}

void test_to_html_basic() {
    printf("\n=== test_to_html_basic ===\n");
    const char *content = "[h1]Title[/h1]\n[quote]Quote test[/quote]";
    char *html = wrt_to_html(content);
    TEST_ASSERT(html != NULL, "HTML conversion should return non-NULL");
    TEST_ASSERT(strstr(html, "<h1 class=\"wrt-heading\">Title</h1>") != NULL, "Should convert h1");
    TEST_ASSERT(strstr(html, "wrt-quote") != NULL, "Should convert quote");
    free(html);
}

void test_to_html_inline_tags() {
    printf("\n=== test_to_html_inline_tags ===\n");
    const char *content = "[b]bold[/b] [i]italic[/i] [u]underline[/u] [s]strike[/s] [code]code[/code]";
    char *html = wrt_to_html(content);
    TEST_ASSERT(strstr(html, "<strong>") != NULL, "Should convert [b] to <strong>");
    TEST_ASSERT(strstr(html, "</strong>") != NULL, "Should close <strong>");
    TEST_ASSERT(strstr(html, "<em>") != NULL, "Should convert [i] to <em>");
    TEST_ASSERT(strstr(html, "<u>") != NULL, "Should convert [u] to <u>");
    TEST_ASSERT(strstr(html, "<s>") != NULL, "Should convert [s] to <s>");
    TEST_ASSERT(strstr(html, "<code") != NULL, "Should convert [code] to <code>");
    free(html);
}

void test_to_html_table() {
    printf("\n=== test_to_html_table ===\n");
    const char *content = "[table]\n| Col 1 | Col 2 |\n|---|---|\n| A | B |\n[/table]";
    char *html = wrt_to_html(content);
    TEST_ASSERT(strstr(html, "<table") != NULL, "Should convert table");
    TEST_ASSERT(strstr(html, "<th") != NULL, "Should have header cells");
    TEST_ASSERT(strstr(html, "<td") != NULL, "Should have data cells");
    free(html);
}

void test_to_html_list() {
    printf("\n=== test_to_html_list ===\n");
    const char *content = "[list]\n- Item 1\n- Item 2\n[/list]";
    char *html = wrt_to_html(content);
    TEST_ASSERT(strstr(html, "<ul") != NULL, "Should convert list to ul");
    TEST_ASSERT(strstr(html, "<li>") != NULL, "Should have list items");
    free(html);
}

void test_to_editable_html() {
    printf("\n=== test_to_editable_html ===\n");
    const char *content = "[h1]Title[/h1]\n<p>Paragraph[/p]";
    char *html = wrt_to_editable_html(content);
    TEST_ASSERT(html != NULL, "Editable HTML should return non-NULL");
    TEST_ASSERT(strstr(html, "wrt-editable") != NULL, "Should have wrt-editable wrapper");
    TEST_ASSERT(strstr(html, "<h1 class=\"wrt-heading\">") != NULL, "Should have heading");
    TEST_ASSERT(strstr(html, "</div>") != NULL, "Should close wrapper div");
    free(html);
}

void test_from_editable_html() {
    printf("\n=== test_from_editable_html ===\n");
    const char *html = "<div class=\"wrt-editable\"><h1>Title</h1><p>Para <strong>bold</strong></p></div>";
    char *wrt = wrt_from_editable_html(html);
    TEST_ASSERT(wrt != NULL, "From editable HTML should return non-NULL");
    TEST_ASSERT(strstr(wrt, "[h1]Title[/h1]") != NULL, "Should convert h1");
    TEST_ASSERT(strstr(wrt, "[b]bold[/b]") != NULL, "Should convert strong to [b]");
    free(wrt);
}

void test_from_editable_html_entities() {
    printf("\n=== test_from_editable_html_entities ===\n");
    const char *html = "<div class=\"wrt-editable\"><p>A &amp; B &lt; C</p></div>";
    char *wrt = wrt_from_editable_html(html);
    TEST_ASSERT(strstr(wrt, "A & B < C") != NULL, "Should decode HTML entities");
    free(wrt);
}

void test_stats() {
    printf("\n=== test_stats ===\n");
    const char *content = "One two three four\nFive six";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.word_count == 6, "Should count 6 words");
    TEST_ASSERT(rep.line_count >= 2, "Should count at least 2 lines");
}

void test_report_to_json() {
    printf("\n=== test_report_to_json ===\n");
    wrt_report_t rep = {0};
    rep.valid = 1;
    rep.word_count = 10;
    rep.char_count = 50;
    rep.line_count = 3;
    rep.tag_count = 4;
    rep.issue_count = 0;
    char *json = wrt_report_to_json(&rep);
    TEST_ASSERT(json != NULL, "JSON should be generated");
    TEST_ASSERT(strstr(json, "\"valid\":true") != NULL, "JSON should have valid=true");
    TEST_ASSERT(strstr(json, "\"word_count\":10") != NULL, "JSON should have word_count");
    free(json);
}

void test_wrt_to_json_escaping() {
    printf("\n=== test_wrt_to_json_escaping ===\n");
    wrt_report_t rep = {0};
    rep.valid = 0;
    rep.issue_count = 1;
    rep.issues[0].line = 1;
    rep.issues[0].col = 5;
    strcpy(rep.issues[0].tag, "test");
    strcpy(rep.issues[0].message, "Has \"quotes\" and \\backslash");
    rep.issues[0].severity = 1;
    char *json = wrt_report_to_json(&rep);
    TEST_ASSERT(strstr(json, "\\\"quotes\\\"") != NULL, "Should escape quotes in JSON");
    TEST_ASSERT(strstr(json, "\\\\backslash") != NULL, "Should escape backslash in JSON");
    free(json);
}

void test_empty_input() {
    printf("\n=== test_empty_input ===\n");
    wrt_report_t rep;
    wrt_validate("", &rep);
    TEST_ASSERT(rep.valid == 1, "Empty input should be valid");
    TEST_ASSERT(rep.word_count == 0, "Empty input should have 0 words");
    TEST_ASSERT(rep.char_count == 0, "Empty input should have 0 chars");

    char *fixed = wrt_fix("");
    TEST_ASSERT(strcmp(fixed, "") == 0, "Fix empty should return empty");
    free(fixed);

    char *html = wrt_to_html("");
    TEST_ASSERT(html != NULL, "HTML of empty should not be NULL");
    free(html);
}

void test_unicode_content() {
    printf("\n=== test_unicode_content ===\n");
    const char *content = "[h1]Привет мир[/h1]\n[quote]中文内容[/quote]";
    wrt_report_t rep;
    wrt_validate(content, &rep);
    TEST_ASSERT(rep.valid == 1, "Unicode content should be valid");

    char *html = wrt_to_html(content);
    TEST_ASSERT(strstr(html, "Привет") != NULL, "Should preserve Cyrillic");
    TEST_ASSERT(strstr(html, "中文") != NULL, "Should preserve Chinese");
    free(html);
}

int main() {
    printf("Running WRT Engine C Tests\n");
    printf("==========================\n");

    test_validate_valid();
    test_validate_invalid_unclosed();
    test_validate_empty_tag();
    test_validate_unknown_tag();
    test_validate_mismatched_tags();
    test_fix_unclosed();
    test_fix_empty_tag();
    test_to_html_basic();
    test_to_html_inline_tags();
    test_to_html_table();
    test_to_html_list();
    test_to_editable_html();
    test_from_editable_html();
    test_from_editable_html_entities();
    test_stats();
    test_report_to_json();
    test_wrt_to_json_escaping();
    test_empty_input();
    test_unicode_content();

    printf("\n==========================\n");
    printf("Tests run:   %d\n", tests_run);
    printf("Tests passed: %d\n", tests_passed);
    printf("Tests failed: %d\n", tests_failed);

    return tests_failed == 0 ? 0 : 1;
}