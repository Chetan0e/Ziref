FROM node:20-alpine

# Install build dependencies, git, bash, pnpm, yarn, bun
RUN apk add --no-cache bash git python3 make g++ curl ca-certificates && \
    corepack enable && \
    npm install -g pnpm yarn

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash && \
    mv /root/.bun/bin/bun /usr/local/bin/bun || true

# Create unprivileged build user
RUN addgroup -g 1001 buildgroup && \
    adduser -u 1001 -G buildgroup -s /bin/bash -D builduser

# Create workspace directory with write permissions for builduser
RUN mkdir -p /app && chown -R builduser:buildgroup /app

WORKDIR /app
USER builduser

# Default shell
SHELL ["/bin/bash", "-c"]
