# ==============================================================================
# Base / Development Stage: Pinned Node 22 Alpine
# ==============================================================================
FROM node:22-alpine AS development

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json* ./

RUN npm install

# Copy application source
COPY . .

EXPOSE 5173

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:5173/upi/ || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ==============================================================================
# Builder Stage: Compile React + Vite assets with /upi/ base
# ==============================================================================
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Build assets with base path /upi/ and API URL /upi-api
ENV VITE_BASE_PATH=/upi/ \
    VITE_API_BASE_URL=/upi-api

RUN npm run build

# ==============================================================================
# Production Stage: Pinned Nginx 1.27 Alpine Static Server
# ==============================================================================
FROM nginx:1.27-alpine AS production

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built frontend assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
