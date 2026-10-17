# Build context is the repo root (see docker-compose.yml): the web build imports ../standards.
FROM node:24-alpine AS build
RUN corepack enable
WORKDIR /repo/web
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
COPY standards/ /repo/standards/
RUN pnpm build
RUN pnpm prune --prod

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOST=0.0.0.0 API_INTERNAL_URL=http://api:4000
COPY --from=build /repo/web/build ./build
COPY --from=build /repo/web/node_modules ./node_modules
COPY --from=build /repo/web/package.json ./
EXPOSE 3000
USER node
CMD ["node", "build"]
