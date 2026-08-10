# syntax=docker/dockerfile:1.7
FROM node:24.18.0-alpine AS dependencies
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

FROM dependencies AS development
COPY frontend/ .
EXPOSE 4200
CMD ["npm", "start", "--", "--proxy-config", "proxy.conf.json"]

FROM dependencies AS build
COPY frontend/ .
RUN npm run build

FROM nginx:1.29.1-alpine AS production
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/base-frontend/browser /usr/share/nginx/html
EXPOSE 80
