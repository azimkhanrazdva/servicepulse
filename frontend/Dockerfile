FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM build AS public-build
RUN npx vite build --mode public --outDir public-dist
FROM nginx:1.28-alpine AS public
COPY public-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=public-build /app/public-dist /usr/share/nginx/html
FROM nginx:1.28-alpine AS management
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
