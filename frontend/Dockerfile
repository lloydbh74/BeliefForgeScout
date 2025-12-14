# Use official nginx image for better security
FROM nginx:1.24-alpine

# Create non-root user (check if group exists first)
RUN addgroup -g 1001 -S nginx || true && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true

# Install security updates
RUN apk update && \
    apk add --no-cache \
    ca-certificates && \
    rm -rf /var/cache/apk/*

# Copy frontend files with proper permissions
COPY --chown=nginx:nginx . /usr/share/nginx/html/
COPY --chown=nginx:nginx nginx.conf /etc/nginx/nginx.conf

# Create necessary directories
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run/nginx && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run/nginx

# Switch to non-root user (nginx already exists in base image)
# Keep as root for nginx to work properly, but ensure files are owned by nginx
# USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]