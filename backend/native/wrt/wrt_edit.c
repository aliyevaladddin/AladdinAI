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
        fprintf(stderr, "\nWRT Editor — lightweight document editor for AladdinAI\n");
        fprintf(stderr, "Hotkeys:\n");
        fprintf(stderr, "  Ctrl+B  — [b]bold[/b]\n");
        fprintf(stderr, "  Ctrl+I  — [i]italic[/i]\n");
        fprintf(stderr, "  Ctrl+U  — [u]underline[/u]\n");
        fprintf(stderr, "  Ctrl+K  — [code]code[/code]\n");
        fprintf(stderr, "  Ctrl+S  — save\n");
        fprintf(stderr, "  Ctrl+Q  — quit\n");
        return 1;
    }

    return wrt_editor_run(argv[1]);
}
