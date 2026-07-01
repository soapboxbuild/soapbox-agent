# Build context must be the repo root (not template-mcp/).
# In Railway: Root Directory = (empty), Dockerfile Path = template-mcp/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /build
COPY template-mcp/package*.json ./
RUN npm ci
COPY template-mcp/src ./src
COPY template-mcp/tsconfig.json ./
RUN npm run build
RUN npm prune --production

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /build/node_modules ./node_modules
COPY --from=builder /build/dist ./dist
COPY templates ./templates
EXPOSE 3000
CMD ["node", "dist/index.js"]
