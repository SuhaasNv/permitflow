# Build the static bundle, then serve it with nginx. One image for every environment: the API URL is
# injected at container start (docker/entrypoint.sh), not at build time.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
RUN apk add --no-cache curl
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker/security-headers.conf.template /etc/nginx/templates/security-headers.conf.template
RUN mkdir -p /etc/nginx/snippets
COPY docker/entrypoint.sh /entrypoint.sh
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
