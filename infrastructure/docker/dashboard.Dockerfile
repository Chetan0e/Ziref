FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

COPY package.json pnpm-workspace.yaml ./
COPY apps/dashboard/package.json ./apps/dashboard/
COPY packages/types/package.json ./packages/types/

RUN pnpm install

COPY . .

RUN pnpm --filter dashboard build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
RUN npm install -g pnpm

COPY --from=builder /app ./

EXPOSE 3000

CMD ["pnpm", "--filter", "dashboard", "start"]
