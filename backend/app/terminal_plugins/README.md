# Terminal Plugins (Manifests)

This directory contains YAML manifests for AladdinAI's web terminal and remote development environments.

These manifests define the container image, configuration, port, command arguments, and dynamic routing templates for different terminal and IDE providers.

## Available Plugins

### 🖥️ `ttyd.yaml`
A lightweight, fast, single-binary terminal that runs a shell directly inside the container. It uses the `tsl0922/ttyd:1.7.4` Docker image and serves a `bash` terminal over HTTP/WebSocket on port `7681`.

### 💻 `code-server.yaml`
Runs a full, browser-based VS Code environment (`code-server`) inside the user's isolated workspace container. This allows developers to edit code, run tests, and use terminal panels directly from their web browser.

### 🌐 `wetty.yaml`
An SSH terminal emulator over HTTP/WebSocket. It enables SSH tunneling and proxying, letting users securely connect to remote VMs or hosts from the browser.

## Manifest Structure

Every manifest YAML file must include the following properties:
* **`type`**: The unique identifier for the provider type (e.g., `ttyd`, `code-server`).
* **`name` & `description`**: Human-readable labels displayed in the AladdinAI UI dashboard.
* **`image`**: The official or custom Docker image to run (e.g., `tsl0922/ttyd:1.7.4`).
* **`internal_port`**: The port the application inside the container listens to. Traefik routes traffic to this port.
* **`command`**: The entrypoint and arguments array to run inside the container (e.g., `["ttyd", "--writable", "bash"]`).
* **`healthcheck`**: A Docker healthcheck definition used to monitor container readiness before opening user routing.
* **`url_template`**: The dynamic path template evaluated when generating access tokens and redirect URLs (e.g., `"{scheme}://{host}/p/{provider_id}/?token={token}"`).
