# NOTICE: This file is protected under RCF-PL
CC = gcc
# _GNU_SOURCE: struct ucred / SO_PEERCRED for the socket peer check in aladdin_term.c
CFLAGS = -O2 -Wall -Wextra -std=c11 -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -D_GNU_SOURCE
LDFLAGS = -lutil

TARGETS = aladdin-term aladdin-grep aladdin-log-stream wrt-edit wrt-validate

all: $(TARGETS)

aladdin-term: aladdin_term.c aladdin_term.h
	$(CC) $(CFLAGS) aladdin_term.c -o aladdin-term $(LDFLAGS)

wrt-edit: wrt-edit.c wrt_editor.c wrt_editor.h
	$(CC) $(CFLAGS) wrt-edit.c wrt_editor.c -o wrt-edit

wrt-validate: wrt-validate.c
	$(CC) $(CFLAGS) wrt-validate.c -o wrt-validate

aladdin-grep: aladdin_grep.c
	$(CC) $(CFLAGS) aladdin_grep.c -o aladdin-grep

aladdin-log-stream: aladdin_log_stream.c
	$(CC) $(CFLAGS) aladdin_log_stream.c -o aladdin-log-stream

clean:
	rm -f $(TARGETS) *.o

.PHONY: all clean
