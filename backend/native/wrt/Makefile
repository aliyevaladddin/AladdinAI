# NOTICE: This file is protected under RCF-PL
CC = gcc
CFLAGS = -O2 -Wall -Wextra -std=c11 -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -D_GNU_SOURCE

TARGETS = wrt-engine wrt-edit wrt-validate

all: $(TARGETS)

wrt-engine: wrt_engine.c wrt_engine.h wrt_docx.c wrt_docx.h wrt_markdown.c wrt_markdown.h wrt_odt.c wrt_odt.h wrt_pptx.c wrt_pptx.h
	$(CC) $(CFLAGS) wrt_engine.c wrt_docx.c wrt_markdown.c wrt_odt.c wrt_pptx.c -o wrt-engine -lzip -lz

wrt-edit: wrt-edit.c wrt_editor.c wrt_editor.h
	$(CC) $(CFLAGS) wrt-edit.c wrt_editor.c -o wrt-edit

wrt-validate: wrt-validate.c
	$(CC) $(CFLAGS) wrt-validate.c -o wrt-validate

clean:
	rm -f $(TARGETS) *.o

.PHONY: all clean
