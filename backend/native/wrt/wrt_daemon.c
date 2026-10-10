// NOTICE: This file is protected under RCF-PL
/*
 * AladdinAI — Native C WRT Document Engine
 * Unix domain socket daemon
 */

#include "wrt_internal.h"
#include "wrt_engine.h"

#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
#include <poll.h>
#include <signal.h>

/* ============================================================
 * UNIX DOMAIN SOCKET DAEMON
 * ============================================================ */

static volatile int g_daemon_running = 1;

static void daemon_sig_handler(int sig) {
    (void)sig;
    g_daemon_running = 0;
}

static void handle_daemon_request(int client_fd, const char *req) {
    char *action = extract_json_string(req, "action");
    char *content = extract_json_string(req, "content");
    char *path = extract_json_string(req, "path");
    const char *doc = content ? content : "";

    str_buf_t resp;
    buf_init(&resp);

    if (action && strcmp(action, "validate") == 0) {
        wrt_report_t rep;
        wrt_validate(doc, &rep);
        char *json = wrt_report_to_json(&rep);
        buf_append(&resp, "{\"type\":\"validate_result\",\"data\":");
        buf_append(&resp, json);
        buf_append(&resp, "}\n");
        free(json);
    } else if (action && strcmp(action, "fix") == 0) {
        char *fixed = wrt_fix(doc);
        buf_append(&resp, "{\"type\":\"fix_result\",\"content\":\"");
        buf_append_json_escaped(&resp, fixed);
        buf_append(&resp, "\"}\n");
        free(fixed);
    } else if (action && strcmp(action, "to-html") == 0) {
        char *html = wrt_to_html(doc);
        buf_append(&resp, "{\"type\":\"to_html_result\",\"html\":\"");
        buf_append_json_escaped(&resp, html);
        buf_append(&resp, "\"}\n");
        free(html);
    } else if (action && strcmp(action, "to-editable-html") == 0) {
        char *html = wrt_to_editable_html(doc);
        buf_append(&resp, "{\"type\":\"to_editable_html_result\",\"html\":\"");
        buf_append_json_escaped(&resp, html);
        buf_append(&resp, "\"}\n");
        free(html);
    } else if (action && strcmp(action, "from-editable-html") == 0) {
        char *wrt = wrt_from_editable_html(doc);
        buf_append(&resp, "{\"type\":\"from_editable_html_result\",\"content\":\"");
        buf_append_json_escaped(&resp, wrt);
        buf_append(&resp, "\"}\n");
        free(wrt);
    } else if (action && strcmp(action, "stats") == 0) {
        wrt_report_t rep;
        wrt_validate(doc, &rep);
        char num[32];
        buf_append(&resp, "{\"type\":\"stats_result\",\"lines\":");
        snprintf(num, sizeof(num), "%d", rep.line_count); buf_append(&resp, num);
        buf_append(&resp, ",\"words\":");
        snprintf(num, sizeof(num), "%d", rep.word_count); buf_append(&resp, num);
        buf_append(&resp, ",\"chars\":");
        snprintf(num, sizeof(num), "%d", rep.char_count); buf_append(&resp, num);
        buf_append(&resp, ",\"tags\":");
        snprintf(num, sizeof(num), "%d", rep.tag_count); buf_append(&resp, num);
        buf_append(&resp, ",\"valid\":");
        buf_append(&resp, rep.valid ? "true" : "false");
        buf_append(&resp, "}\n");
    } else if (action && strcmp(action, "list_files") == 0) {
        char *json = wrt_list_files_json(path);
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "read_file") == 0) {
        char *json = wrt_read_file_json(path);
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "save_file") == 0) {
        char *json = wrt_save_file_json(path, doc);
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "recent_files") == 0) {
        char *json = wrt_get_recent_files_json();
        buf_append(&resp, json);
        free(json);
    } else if (action && strcmp(action, "docx_to_wrt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing path parameter for docx_to_wrt\"}\n");
        } else {
            FILE *f = fopen(path, "rb");
            if (!f) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Cannot open docx file\"}\n");
            } else {
                fseek(f, 0, SEEK_END);
                long sz = ftell(f);
                fseek(f, 0, SEEK_SET);
                unsigned char *data = (unsigned char *)malloc(sz);
                if (fread(data, 1, sz, f) != (size_t)sz) {
                    free(data); fclose(f);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed reading docx file\"}\n");
                } else {
                    fclose(f);
                    char *wrt = docx_to_wrt(data, sz);
                    free(data);
                    if (!wrt) {
                        buf_append(&resp, "{\"type\":\"error\",\"message\":\"docx conversion failed\"}\n");
                    } else {
                        buf_append(&resp, "{\"type\":\"docx_to_wrt_result\",\"content\":\"");
                        buf_append_json_escaped(&resp, wrt);
                        buf_append(&resp, "\"}\n");
                        free(wrt);
                    }
                }
            }
        }
    } else if (action && strcmp(action, "wrt_to_docx") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing output path parameter for wrt_to_docx\"}\n");
        } else {
            size_t out_len = 0;
            unsigned char *docx_bytes = wrt_to_docx(doc, &out_len);
            if (!docx_bytes || out_len == 0) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed converting wrt to docx\"}\n");
            } else {
                FILE *f = fopen(path, "wb");
                if (!f) {
                    free(docx_bytes);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed opening output docx file\"}\n");
                } else {
                    fwrite(docx_bytes, 1, out_len, f);
                    fclose(f);
                    free(docx_bytes);
                    char num[32];
                    snprintf(num, sizeof(num), "%zu", out_len);
                    buf_append(&resp, "{\"type\":\"wrt_to_docx_result\",\"bytes\":");
                    buf_append(&resp, num);
                    buf_append(&resp, ",\"path\":\"");
                    buf_append_json_escaped(&resp, path);
                    buf_append(&resp, "\"}\n");
                }
            }
        }
    } else if (action && strcmp(action, "md_to_wrt") == 0) {
        char *wrt = wrt_markdown_to_wrt(doc);
        buf_append(&resp, "{\"type\":\"md_to_wrt_result\",\"content\":\"");
        buf_append_json_escaped(&resp, wrt ? wrt : "");
        buf_append(&resp, "\"}\n");
        free(wrt);
    } else if (action && strcmp(action, "wrt_to_md") == 0) {
        char *md = wrt_to_markdown(doc);
        buf_append(&resp, "{\"type\":\"wrt_to_md_result\",\"content\":\"");
        buf_append_json_escaped(&resp, md ? md : "");
        buf_append(&resp, "\"}\n");
        free(md);
    } else if (action && strcmp(action, "odt_to_wrt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing path parameter for odt_to_wrt\"}\n");
        } else {
            FILE *f = fopen(path, "rb");
            if (!f) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Cannot open odt file\"}\n");
            } else {
                fseek(f, 0, SEEK_END);
                long sz = ftell(f);
                fseek(f, 0, SEEK_SET);
                unsigned char *data = (unsigned char *)malloc(sz);
                if (fread(data, 1, sz, f) != (size_t)sz) {
                    free(data); fclose(f);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed reading odt file\"}\n");
                } else {
                    fclose(f);
                    char *wrt = odt_to_wrt(data, sz);
                    free(data);
                    if (!wrt) {
                        buf_append(&resp, "{\"type\":\"error\",\"message\":\"odt conversion failed\"}\n");
                    } else {
                        buf_append(&resp, "{\"type\":\"odt_to_wrt_result\",\"content\":\"");
                        buf_append_json_escaped(&resp, wrt);
                        buf_append(&resp, "\"}\n");
                        free(wrt);
                    }
                }
            }
        }
    } else if (action && strcmp(action, "wrt_to_odt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing output path parameter for wrt_to_odt\"}\n");
        } else {
            size_t out_len = 0;
            unsigned char *odt_bytes = wrt_to_odt(doc, &out_len);
            if (!odt_bytes || out_len == 0) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed converting wrt to odt\"}\n");
            } else {
                FILE *f = fopen(path, "wb");
                if (!f) {
                    free(odt_bytes);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed opening output odt file\"}\n");
                } else {
                    fwrite(odt_bytes, 1, out_len, f);
                    fclose(f);
                    free(odt_bytes);
                    char num[32];
                    snprintf(num, sizeof(num), "%zu", out_len);
                    buf_append(&resp, "{\"type\":\"wrt_to_odt_result\",\"bytes\":");
                    buf_append(&resp, num);
                    buf_append(&resp, ",\"path\":\"");
                    buf_append_json_escaped(&resp, path);
                    buf_append(&resp, "\"}\n");
                }
            }
        }
    } else if (action && strcmp(action, "pptx_to_wrt") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing path parameter for pptx_to_wrt\"}\n");
        } else {
            FILE *f = fopen(path, "rb");
            if (!f) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Cannot open pptx file\"}\n");
            } else {
                fseek(f, 0, SEEK_END);
                long sz = ftell(f);
                fseek(f, 0, SEEK_SET);
                unsigned char *data = (unsigned char *)malloc(sz);
                if (fread(data, 1, sz, f) != (size_t)sz) {
                    free(data); fclose(f);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed reading pptx file\"}\n");
                } else {
                    fclose(f);
                    char *wrt = pptx_to_wrt(data, sz);
                    free(data);
                    if (!wrt) {
                        buf_append(&resp, "{\"type\":\"error\",\"message\":\"pptx conversion failed\"}\n");
                    } else {
                        buf_append(&resp, "{\"type\":\"pptx_to_wrt_result\",\"content\":\"");
                        buf_append_json_escaped(&resp, wrt);
                        buf_append(&resp, "\"}\n");
                        free(wrt);
                    }
                }
            }
        }
    } else if (action && strcmp(action, "wrt_to_pptx") == 0) {
        if (!path || strlen(path) == 0) {
            buf_append(&resp, "{\"type\":\"error\",\"message\":\"Missing output path parameter for wrt_to_pptx\"}\n");
        } else {
            size_t out_len = 0;
            unsigned char *pptx_bytes = wrt_to_pptx(doc, &out_len);
            if (!pptx_bytes || out_len == 0) {
                buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed converting wrt to pptx\"}\n");
            } else {
                FILE *f = fopen(path, "wb");
                if (!f) {
                    free(pptx_bytes);
                    buf_append(&resp, "{\"type\":\"error\",\"message\":\"Failed opening output pptx file\"}\n");
                } else {
                    fwrite(pptx_bytes, 1, out_len, f);
                    fclose(f);
                    free(pptx_bytes);
                    char num[32];
                    snprintf(num, sizeof(num), "%zu", out_len);
                    buf_append(&resp, "{\"type\":\"wrt_to_pptx_result\",\"bytes\":");
                    buf_append(&resp, num);
                    buf_append(&resp, ",\"path\":\"");
                    buf_append_json_escaped(&resp, path);
                    buf_append(&resp, "\"}\n");
                }
            }
        }
    } else if (action && strcmp(action, "ping") == 0) {
        buf_append(&resp, "{\"type\":\"pong\",\"version\":\"" WRT_ENGINE_VERSION "\"}\n");
    } else {
        buf_append(&resp, "{\"type\":\"error\",\"message\":\"Unknown or missing action\"}\n");
    }

    if (resp.len > 0) {
        ssize_t written = 0;
        while (written < (ssize_t)resp.len) {
            ssize_t n = write(client_fd, resp.data + written, resp.len - written);
            if (n <= 0) break;
            written += n;
        }
    }

    free(action);
    free(content);
    free(path);
    free(resp.data);
}

int wrt_engine_daemon(const char *socket_path) {
    if (!socket_path) socket_path = DEFAULT_WRT_SOCKET_PATH;

    signal(SIGINT, daemon_sig_handler);
    signal(SIGTERM, daemon_sig_handler);
    signal(SIGPIPE, SIG_IGN);

    unlink(socket_path);

    int server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("unix socket failed");
        return 1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socket_path, sizeof(addr.sun_path) - 1);

    mode_t old_mask = umask(0177);
    int bind_res = bind(server_fd, (struct sockaddr *)&addr, sizeof(addr));
    umask(old_mask);

    if (bind_res < 0) {
        perror("unix bind failed");
        close(server_fd);
        return 1;
    }

    // Secure socket permissions: only owner can read/write, set BEFORE listen()
    if (chmod(socket_path, 0600) < 0) {
        perror("unix chmod failed");
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 32) < 0) {
        perror("unix listen failed");
        close(server_fd);
        return 1;
    }

    printf("[Aladdin WRT Engine Daemon] Listening on Unix Socket: %s\n", socket_path);
    fflush(stdout);

    while (g_daemon_running) {
        struct pollfd pfd;
        pfd.fd = server_fd;
        pfd.events = POLLIN;
        int ret = poll(&pfd, 1, 1000);
        if (ret <= 0) continue;

        int client_fd = accept(server_fd, NULL, NULL);
        if (client_fd < 0) continue;

        str_buf_t in;
        buf_init(&in);
        char chunk[4096];
        ssize_t n;
        while ((n = read(client_fd, chunk, sizeof(chunk))) > 0) {
            buf_append_len(&in, chunk, (size_t)n);
            if (strchr(chunk, '\n')) break;
        }

        if (in.len > 0) {
            handle_daemon_request(client_fd, in.data);
        }

        free(in.data);
        close(client_fd);
    }

    close(server_fd);
    unlink(socket_path);
    return 0;
}