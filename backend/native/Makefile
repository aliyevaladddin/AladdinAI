# NOTICE: This file is protected under RCF-PL
CC = gcc
CFLAGS = -O2 -Wall -Wextra -std=c11 -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE
LDFLAGS = -lutil

TARGETS = aladdin-term aladdin-grep aladdin-log-stream

all: $(TARGETS)

aladdin-term: aladdin_term.c aladdin_term.h
	$(CC) $(CFLAGS) aladdin_term.c -o aladdin-term $(LDFLAGS)

aladdin-grep: aladdin_grep.c
	$(CC) $(CFLAGS) aladdin_grep.c -o aladdin-grep

aladdin-log-stream: aladdin_log_stream.c
	$(CC) $(CFLAGS) aladdin_log_stream.c -o aladdin-log-stream

clean:
	rm -f $(TARGETS) *.o

.PHONY: all clean
