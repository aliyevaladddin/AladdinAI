// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Comprehensive Security & Edge Case Tests for Native WRT Engine
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "wrt_internal.h"
#include "wrt_engine.h"

#define TEST_PASS(name) printf("  PASS: %s\n", name)
#define TEST_FAIL(name, reason) do { \
    printf("  FAIL: %s (%s)\n", name, reason); \
    exit(1); \
} while(0)

/* 1. Empty document and whitespace tests */
void test_empty_and_whitespace(void) {
    printf("\n=== test_empty_and_whitespace ===\n");
    char *res1 = wrt_spellcheck_json("");
    assert(res1 != NULL);
    assert(strstr(res1, "\"issues\":[]") != NULL);
    free(res1);
    TEST_PASS("Empty string returns empty issues");

    char *res2 = wrt_spellcheck_json("    \n\n\t\t   \n");
    assert(res2 != NULL);
    assert(strstr(res2, "\"issues\":[]") != NULL);
    free(res2);
    TEST_PASS("Whitespace-only returns empty issues");
}

/* 2. Very long word (10,000+ chars) */
void test_very_long_word(void) {
    printf("\n=== test_very_long_word ===\n");
    size_t size = 15000;
    char *huge = malloc(size + 1);
    memset(huge, 'a', size);
    huge[size] = '\0';

    char *res = wrt_spellcheck_json(huge);
    assert(res != NULL);
    // Huge word exceeds max word token limit (64 chars) and must safely be skipped without crash
    assert(strstr(res, "spellcheck_result") != NULL);
    free(res);
    free(huge);
    TEST_PASS("15,000 char word handled safely without buffer overflow");
}

/* 3. Document with thousands of typos in a row */
void test_thousand_typos(void) {
    printf("\n=== test_thousand_typos ===\n");
    str_buf_t b;
    buf_init(&b);
    for (int i = 0; i < 2000; i++) {
        buf_append(&b, "helo ");
    }
    char *res = wrt_spellcheck_json(b.data);
    assert(res != NULL);
    assert(strstr(res, "spellcheck_result") != NULL);
    assert(strstr(res, "\"word\":\"helo\"") != NULL);
    free(res);
    free(b.data);
    TEST_PASS("2000 consecutive typos processed and dynamically resized in JSON buffer");
}

/* 4. Invalid UTF-8 bytes and boundary conditions */
void test_invalid_utf8_and_boundaries(void) {
    printf("\n=== test_invalid_utf8_and_boundaries ===\n");
    // Trailing \xc2 without \xa0
    const char invalid1[] = "Hello \xc2";
    char *html1 = wrt_to_editable_html(invalid1);
    assert(html1 != NULL);
    free(html1);

    char *wrt1 = wrt_from_editable_html("<p>Hello \xc2</p>");
    assert(wrt1 != NULL);
    free(wrt1);
    TEST_PASS("Trailing 0xC2 byte does not cause out-of-bounds read");

    // \xc2 followed by something other than \xa0
    const char invalid2[] = "<p>Test \xc2\x20 more</p>";
    char *wrt2 = wrt_from_editable_html(invalid2);
    assert(wrt2 != NULL);
    free(wrt2);
    TEST_PASS("0xC2 followed by non-0xA0 handled safely");
}

/* 5. Cyrillic and Azerbaijani UTF-8 column alignment */
void test_utf8_column_alignment(void) {
    printf("\n=== test_utf8_column_alignment ===\n");
    // "Привет helo" -> Привет is 6 characters (12 bytes in UTF-8).
    // In Monaco, "Привет " has 7 UTF-16 units. The word "helo" starts at column 8.
    const char text[] = "Привет helo";
    char *res = wrt_spellcheck_json(text);
    assert(res != NULL);
    assert(strstr(res, "\"col\":8") != NULL);
    free(res);
    TEST_PASS("Cyrillic multi-byte characters correctly count as single columns for Monaco (col=8)");
}

/* 6. Tag validation regression */
void test_tag_validation_regression(void) {
    printf("\n=== test_tag_validation_regression ===\n");
    // Valid prose with bracketed URLs and numbers
    wrt_report_t rep1;
    wrt_validate("Citation [1] and [https://example.com] are allowed", &rep1);
    assert(rep1.valid == 1);
    TEST_PASS("Bracketed citations and URLs do not trigger false tag errors");

    // Invalid: unclosed real tag [b]
    wrt_report_t rep2;
    wrt_validate("Unclosed [b]bold text", &rep2);
    assert(rep2.valid == 0);
    assert(rep2.issue_count > 0);
    assert(strcmp(rep2.issues[0].tag, "b") == 0);
    TEST_PASS("Unclosed real WRT tag [b] is strictly caught as error");

    // Invalid: mismatched tags
    wrt_report_t rep3;
    wrt_validate("[b]bold[/i]", &rep3);
    assert(rep3.valid == 0);
    TEST_PASS("Mismatched real WRT tags [b][/i] strictly caught as error");
}

int main(void) {
    printf("Running AladdinAI WRT Engine Security & Edge Case Suite\n");
    printf("========================================================\n");
    wrt_spellcheck_init(NULL);

    test_empty_and_whitespace();
    test_very_long_word();
    test_thousand_typos();
    test_invalid_utf8_and_boundaries();
    test_utf8_column_alignment();
    test_tag_validation_regression();

    printf("\nAll Security & Edge Case tests passed successfully!\n");
    wrt_spellcheck_cleanup();
    return 0;
}
