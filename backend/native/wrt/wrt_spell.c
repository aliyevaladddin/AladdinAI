// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Spell checking integration using SymSpell C99
 */

#include "wrt_internal.h"
#include "wrt_engine.h"
#include "symspell.h"

static symspell_dict_t *g_symspell_dict = NULL;
static int g_symspell_attempted_init = 0;

void wrt_spellcheck_init(const char *dict_path) {
    if (g_symspell_dict) return;
    g_symspell_attempted_init = 1;

    g_symspell_dict = symspell_create(2, 7);
    if (!g_symspell_dict) {
        fprintf(stderr, "[wrt_spellcheck] Failed to create symspell dictionary\n");
        return;
    }

    const char *paths[] = {
        dict_path ? dict_path : "/workspaces/AladdinAI/backend/native/wrt/dict/dictionary.txt",
        "backend/native/wrt/dict/dictionary.txt",
        "wrt/dict/dictionary.txt",
        "dict/dictionary.txt",
        "/workspaces/AladdinAI/backend/native/wrt/dict/dictionary.txt",
        NULL
    };

    for (int i = 0; paths[i] != NULL; i++) {
        FILE *f = fopen(paths[i], "r");
        if (f) {
            fclose(f);
            if (symspell_load_dictionary(g_symspell_dict, paths[i], 0, 1)) {
                size_t words = 0, entries = 0;
                symspell_get_stats(g_symspell_dict, &words, &entries);
                printf("[wrt_spellcheck] Loaded dictionary from %s (%zu words, %zu entries)\n",
                       paths[i], words, entries);
                return;
            }
        }
    }

    fprintf(stderr, "[wrt_spellcheck] Warning: No dictionary file found for SymSpell\n");
}

void wrt_spellcheck_cleanup(void) {
    if (g_symspell_dict) {
        symspell_destroy(g_symspell_dict);
        g_symspell_dict = NULL;
    }
}

char *wrt_spellcheck_json(const char *text) {
    if (!g_symspell_attempted_init) {
        wrt_spellcheck_init(NULL);
    }

    str_buf_t b;
    buf_init(&b);
    buf_append(&b, "{\"type\":\"spellcheck_result\",\"issues\":[");

    if (!g_symspell_dict || !text || !*text) {
        buf_append(&b, "]}\n");
        return b.data;
    }

    int line = 1;
    int col = 1;
    size_t i = 0;
    size_t len = strlen(text);
    int first_issue = 1;

    while (i < len) {
        char c = text[i];

        if (c == '\n') {
            line++;
            col = 1;
            i++;
            continue;
        }

        // Skip WRT tags like [b], [/b], [h1], [img ...], [link url="..."]
        if (c == '[') {
            size_t j = i + 1;
            while (j < len && text[j] != ']' && text[j] != '\n') j++;
            if (j < len && text[j] == ']') {
                col += (int)(j - i + 1);
                i = j + 1;
                continue;
            }
        }

        // Extract word tokens: English / ASCII alphabetic words (length >= 2)
        if (isalpha((unsigned char)c)) {
            size_t word_start = i;
            int word_start_col = col;

            while (i < len && isalpha((unsigned char)text[i])) {
                i++;
                col++;
            }

            size_t word_len = i - word_start;
            if (word_len >= 2 && word_len < 64) {
                char word[64];
                memcpy(word, text + word_start, word_len);
                word[word_len] = '\0';

                // Lowercase for lookup
                char lower_word[64];
                for (size_t k = 0; k < word_len; k++) {
                    lower_word[k] = (char)tolower((unsigned char)word[k]);
                }
                lower_word[word_len] = '\0';

                symspell_suggestion_t suggs[8];
                int count = symspell_lookup(g_symspell_dict, lower_word, 2, suggs, 8);

                // If distance == 0 is present, word is correctly spelled!
                int is_correct = 0;
                for (int s = 0; s < count; s++) {
                    if (suggs[s].distance == 0) {
                        is_correct = 1;
                        break;
                    }
                }

                if (!is_correct && count > 0) {
                    if (!first_issue) buf_append_c(&b, ',');
                    first_issue = 0;

                    char num[32];
                    buf_append(&b, "{\"line\":");
                    snprintf(num, sizeof(num), "%d", line); buf_append(&b, num);
                    buf_append(&b, ",\"col\":");
                    snprintf(num, sizeof(num), "%d", word_start_col); buf_append(&b, num);
                    buf_append(&b, ",\"len\":");
                    snprintf(num, sizeof(num), "%d", (int)word_len); buf_append(&b, num);
                    buf_append(&b, ",\"word\":\"");
                    buf_append_json_escaped(&b, word);
                    buf_append(&b, "\",\"suggestions\":[");

                    int first_sugg = 1;
                    for (int s = 0; s < count; s++) {
                        if (suggs[s].distance == 0) continue;
                        if (!first_sugg) buf_append_c(&b, ',');
                        first_sugg = 0;

                        // Preserve capitalization if original word began with upper
                        char cand[128];
                        strncpy(cand, suggs[s].term, sizeof(cand) - 1);
                        cand[sizeof(cand) - 1] = '\0';
                        if (isupper((unsigned char)word[0])) {
                            cand[0] = (char)toupper((unsigned char)cand[0]);
                        }

                        buf_append(&b, "\"");
                        buf_append_json_escaped(&b, cand);
                        buf_append(&b, "\"");
                    }
                    buf_append(&b, "]}");
                }
            }
            continue;
        }

        i++;
        col++;
    }

    buf_append(&b, "]}\n");
    return b.data;
}
