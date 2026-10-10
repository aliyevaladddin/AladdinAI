# NOTICE: This file is protected under RCF-PL
CC = gcc
CFLAGS = -O2 -Wall -Wextra -std=c11 -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -D_GNU_SOURCE

SRCS = wrt_engine.c wrt_docx.c wrt_markdown.c wrt_odt.c wrt_pptx.c wrt_check.c wrt_daemon.c wrt_files.c wrt_html.c wrt_json.c wrt_tags.c wrt_util.c
HDRS = wrt_engine.h wrt_internal.h wrt_docx.h wrt_markdown.h wrt_odt.h wrt_pptx.h

LIB_SRCS = wrt_docx.c wrt_markdown.c wrt_odt.c wrt_pptx.c wrt_check.c wrt_daemon.c wrt_files.c wrt_html.c wrt_json.c wrt_tags.c wrt_util.c

TARGETS = wrt-engine wrt-validate

all: $(TARGETS)

wrt-engine: $(SRCS) $(HDRS)
	$(CC) $(CFLAGS) $(SRCS) -o wrt-engine -lzip -lz

wrt-validate: wrt_validate.c
	$(CC) $(CFLAGS) wrt_validate.c -o wrt-validate

test_wrt: test_wrt.c $(LIB_SRCS) $(HDRS)
	$(CC) $(CFLAGS) test_wrt.c $(LIB_SRCS) -o test_wrt -lzip -lz

test_standalone: test_standalone.c
	$(CC) $(CFLAGS) test_standalone.c -o test_standalone

test: test_wrt test_standalone
	./test_wrt
	./test_standalone

clean:
	rm -f $(TARGETS) test_wrt test_standalone *.o

.PHONY: all clean test