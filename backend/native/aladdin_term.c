// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI Native C PTY Daemon — aladdin_term.c
 * Ultra-fast Unix Domain Socket PTY server for AladdinAI.
 */

#include "aladdin_term.h"

static const char *g_socket_path = NULL;

static void cleanup_and_exit(int sig) {
    (void)sig;
    if (g_socket_path) {
        unlink(g_socket_path);
    }
    exit(0);
}

size_t json_escape_pty_data(const char *src, size_t src_len, char *dst, size_t dst_max) {
    static const char hex[] = "0123456789abcdef";
    size_t d = 0;
    
    d += snprintf(dst + d, dst_max - d, "{\"type\":\"data\",\"data\":\"");

    for (size_t s = 0; s < src_len && d < dst_max - 30; s++) {
        unsigned char c = (unsigned char)src[s];
        if (c == '"') {
            dst[d++] = '\\';
            dst[d++] = '"';
        } else if (c == '\\') {
            dst[d++] = '\\';
            dst[d++] = '\\';
        } else if (c == '\n') {
            dst[d++] = '\\';
            dst[d++] = 'n';
        } else if (c == '\r') {
            dst[d++] = '\\';
            dst[d++] = 'r';
        } else if (c == '\t') {
            dst[d++] = '\\';
            dst[d++] = 't';
        } else if (c == '\b') {
            dst[d++] = '\\';
            dst[d++] = 'b';
        } else if (c < 0x20) {
            dst[d++] = '\\';
            dst[d++] = 'u';
            dst[d++] = '0';
            dst[d++] = '0';
            dst[d++] = hex[(c >> 4) & 0x0F];
            dst[d++] = hex[c & 0x0F];
        } else {
            dst[d++] = c;
        }
    }

    d += snprintf(dst + d, dst_max - d, "\"}\n");
    return d;
}

void parse_and_process_payload(int pty_master, const char *payload) {
    // Check if JSON resize message: {"type":"resize","cols":80,"rows":24}
    const char *type_pos = strstr(payload, "\"type\":\"resize\"");
    if (!type_pos) type_pos = strstr(payload, "\"type\": \"resize\"");

    if (type_pos) {
        int cols = 80, rows = 24;
        const char *c_pos = strstr(payload, "\"cols\":");
        if (!c_pos) c_pos = strstr(payload, "\"cols\": ");
        const char *r_pos = strstr(payload, "\"rows\":");
        if (!r_pos) r_pos = strstr(payload, "\"rows\": ");

        if (c_pos) cols = atoi(c_pos + (c_pos[7] == ' ' ? 8 : 7));
        if (r_pos) rows = atoi(r_pos + (r_pos[7] == ' ' ? 8 : 7));

        if (cols > 0 && rows > 0) {
            struct winsize ws;
            ws.ws_col = (unsigned short)cols;
            ws.ws_row = (unsigned short)rows;
            ws.ws_xpixel = 0;
            ws.ws_ypixel = 0;
            ioctl(pty_master, TIOCSWINSZ, &ws);
        }
        return;
    }

    // Check if JSON data message: {"type":"data","data":"..."}
    const char *data_pos = strstr(payload, "\"type\":\"data\"");
    if (!data_pos) data_pos = strstr(payload, "\"type\": \"data\"");

    if (data_pos) {
        const char *val_pos = strstr(payload, "\"data\":");
        if (val_pos) {
            val_pos = strchr(val_pos, '"');
            if (val_pos) {
                val_pos++; // skip starting quote
                const char *end_pos = strrchr(val_pos, '"');
                if (end_pos && end_pos > val_pos) {
                    // Process unescaping of \\n, \\r, \\", \\\\ etc.
                    char *unencoded = malloc(end_pos - val_pos + 1);
                    if (unencoded) {
                        size_t uidx = 0;
                        for (const char *p = val_pos; p < end_pos; p++) {
                            if (*p == '\\' && p + 1 < end_pos) {
                                p++;
                                if (*p == 'n') unencoded[uidx++] = '\n';
                                else if (*p == 'r') unencoded[uidx++] = '\r';
                                else if (*p == 't') unencoded[uidx++] = '\t';
                                else if (*p == 'b') unencoded[uidx++] = '\b';
                                else unencoded[uidx++] = *p;
                            } else {
                                unencoded[uidx++] = *p;
                            }
                        }
                        write(pty_master, unencoded, uidx);
                        free(unencoded);
                        return;
                    }
                }
            }
        }
    }

    // Raw fallback
    write(pty_master, payload, strlen(payload));
}

int main(int argc, char *argv[]) {
    const char *socket_path = DEFAULT_SOCKET_PATH;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--socket") == 0 && i + 1 < argc) {
            socket_path = argv[++i];
        }
    }

    signal(SIGCHLD, SIG_IGN);
    signal(SIGINT, cleanup_and_exit);
    signal(SIGTERM, cleanup_and_exit);

    g_socket_path = socket_path;
    unlink(socket_path);

    int server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("unix socket failed");
        exit(EXIT_FAILURE);
    }

    struct sockaddr_un un_addr;
    memset(&un_addr, 0, sizeof(un_addr));
    un_addr.sun_family = AF_UNIX;
    strncpy(un_addr.sun_path, socket_path, sizeof(un_addr.sun_path) - 1);

    if (bind(server_fd, (struct sockaddr *)&un_addr, sizeof(un_addr)) < 0) {
        perror("unix bind failed");
        exit(EXIT_FAILURE);
    }
    chmod(socket_path, 0777);

    if (listen(server_fd, 5) < 0) {
        perror("unix listen failed");
        exit(EXIT_FAILURE);
    }
    printf("[Aladdin-Term C Daemon] Listening on Unix Socket: %s\n", socket_path);

    while (1) {
        int client_fd = accept(server_fd, NULL, NULL);
        if (client_fd < 0) continue;

        // Spawn PTY for client
        int pty_master;
        pid_t pid = forkpty(&pty_master, NULL, NULL, NULL);
        if (pid < 0) {
            perror("forkpty failed");
            close(client_fd);
            continue;
        }

        if (pid == 0) {
            // Child process: launch bash
            setenv("TERM", "xterm-256color", 1);
            char *args[] = {"/bin/bash", NULL};
            execvp(args[0], args);
            exit(EXIT_FAILURE);
        }

        // Parent process: relay line-buffered JSON between Unix socket and PTY master
        int epoll_fd = epoll_create1(0);
        struct epoll_event ev, events[MAX_EVENTS];

        ev.events = EPOLLIN;
        ev.data.fd = client_fd;
        epoll_ctl(epoll_fd, EPOLL_CTL_ADD, client_fd, &ev);

        ev.events = EPOLLIN;
        ev.data.fd = pty_master;
        epoll_ctl(epoll_fd, EPOLL_CTL_ADD, pty_master, &ev);

        char in_buf[BUFFER_SIZE];
        size_t in_len = 0;
        int running = 1;

        while (running) {
            int nfds = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
            for (int i = 0; i < nfds; i++) {
                int fd = events[i].data.fd;

                if (fd == pty_master) {
                    // Read PTY output -> write JSON line to Unix socket
                    char pty_buf[4096];
                    ssize_t n = read(pty_master, pty_buf, sizeof(pty_buf));
                    if (n <= 0) {
                        running = 0;
                        break;
                    }
                    char json_buf[16384];
                    size_t jlen = json_escape_pty_data(pty_buf, (size_t)n, json_buf, sizeof(json_buf));
                    write(client_fd, json_buf, jlen);
                } else if (fd == client_fd) {
                    // Read Unix socket input line-by-line
                    ssize_t n = read(client_fd, in_buf + in_len, sizeof(in_buf) - in_len - 1);
                    if (n <= 0) {
                        running = 0;
                        break;
                    }
                    in_len += n;
                    in_buf[in_len] = '\0';

                    char *line_start = in_buf;
                    char *newline_pos;

                    while ((newline_pos = strchr(line_start, '\n')) != NULL) {
                        *newline_pos = '\0';
                        if (strlen(line_start) > 0) {
                            parse_and_process_payload(pty_master, line_start);
                        }
                        line_start = newline_pos + 1;
                    }

                    // Move leftover partial line to beginning of buffer
                    size_t remaining = in_buf + in_len - line_start;
                    if (remaining > 0) {
                        memmove(in_buf, line_start, remaining);
                    }
                    in_len = remaining;
                }
            }
        }

        close(epoll_fd);
        close(pty_master);
        close(client_fd);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, 0);
    }

    close(server_fd);
    unlink(socket_path);
    return 0;
}
