// NOTICE: This file is protected under RCF-PL
#ifndef ALADDIN_TERM_H
#define ALADDIN_TERM_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pty.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <sys/epoll.h>
#include <sys/wait.h>

#define ALADDIN_TERM_VERSION "2.2.2"
#define DEFAULT_SOCKET_PATH "/tmp/aladdin_term.sock"
#define BUFFER_SIZE 16384
#define MAX_EVENTS 16

/* Function prototypes */
size_t json_escape_pty_data(const char *src, size_t src_len, char *dst, size_t dst_max);
void parse_and_process_payload(int pty_master, const char *payload);

#endif /* ALADDIN_TERM_H */
