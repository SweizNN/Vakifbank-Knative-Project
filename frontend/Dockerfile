# ── Stage 1: Static Build ────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="VakıfBank DevOps Team" \
      service="frontend" \
      version="1.0.0"

# Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Statik dosyalar
COPY index.html  /usr/share/nginx/html/index.html
COPY style.css   /usr/share/nginx/html/style.css
COPY app.js      /usr/share/nginx/html/app.js

# Nginx varsayılan config'i kaldır
RUN rm -f /etc/nginx/conf.d/default.conf.bak

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
