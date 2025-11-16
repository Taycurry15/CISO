# Multi-stage build for ComplianceFlow Landing Page
# This Dockerfile creates an optimized nginx container serving the static site

# Stage 1: Build (if you add build steps later)
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files (create these if you add dependencies)
# COPY package*.json ./
# RUN npm ci --only=production

# Copy source files
COPY . .

# Build steps (if needed)
# RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# Install security updates
RUN apk update && \
    apk upgrade && \
    apk add --no-cache ca-certificates && \
    rm -rf /var/cache/apk/*

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/complianceflow.conf

# Copy static files
COPY --from=builder /app /usr/share/nginx/html

# Create non-root user for nginx
RUN addgroup -g 101 -S nginx && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Switch to non-root user
USER nginx

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/index.html || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
