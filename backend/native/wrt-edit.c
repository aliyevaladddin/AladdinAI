// NOTICE: This file is protected under RCF-PL
/*
 * wrt-edit — standalone CLI wrapper for WRT editor
 *
 * Compiles into a separate executable for editing .wrt documents
 * Usage: wrt-edit <filename>*/

#include "wrt_editor.h"
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <filename.wrt>\n", argv[0]);
        fprintf(stderr, "\nWRT Editor — легкий редактор документов для AladdinAI\n");
        fprintf(stderr, "Горячие клавиши:\n");
        fprintf(stderr, "  Ctrl+B  — [b]жирный[/b]\n");
        fprintf(stderr, "  Ctrl+I  — [i]курсив[/i]\n");
        fprintf(stderr, "  Ctrl+U  — [u]подчёркнутый[/u]\n");
        fprintf(stderr, "  Ctrl+K  — [code]код[/code]\n");
        fprintf(stderr, "  Ctrl+S  — сохранить\n");
        fprintf(stderr, "  Ctrl+Q  — выйти\n");
        return 1;
    }

    return wrt_editor_run(argv[1]);
}
