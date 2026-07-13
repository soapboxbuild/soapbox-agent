# Playwright base image ships Chromium + all system deps (needed for export_report_pdf).
FROM mcr.microsoft.com/playwright:v1.48.0-jammy AS builder
WORKDIR /build
COPY package*.json ./
RUN npm install
COPY src ./src
COPY tsconfig.json ./
RUN npm run build
RUN npm prune --production

FROM mcr.microsoft.com/playwright:v1.48.0-jammy
WORKDIR /app
ENV NODE_ENV=production
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY --from=builder /build/node_modules ./node_modules
COPY --from=builder /build/dist ./dist
EXPOSE 3000
CMD ["node", "dist/index.js"]
