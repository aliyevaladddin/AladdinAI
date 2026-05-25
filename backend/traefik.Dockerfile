FROM traefik:v3.1

# OrbStack requires Docker API >= 1.40.
# The Go Docker SDK reads DOCKER_API_VERSION at runtime;
# baking it into the image ensures it's always set even if
# docker-compose env injection is skipped.
ENV DOCKER_API_VERSION=1.44
