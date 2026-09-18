# bun builds, node serves. The runtime image carries the Nitro output and
# node_modules the server needs, not the toolchain that produced them.
FROM oven/bun:1-debian AS build

WORKDIR /app

COPY package.json bun.lock bunfig.toml ./
RUN bun install --frozen-lockfile

COPY . .

# The Vite/TanStack config defaults Nitro to a Cloudflare target. This deploys as
# a container, so build the plain Node server instead.
ENV NITRO_PRESET=node-server
RUN bun run build

FROM node:24-bookworm-slim AS runtime

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

COPY --from=build /app/.output ./.output

USER node

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
    CMD node -e "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["node", ".output/server/index.mjs"]
