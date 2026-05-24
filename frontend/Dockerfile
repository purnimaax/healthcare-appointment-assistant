# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Install deps (cache-friendly)
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# Build
COPY . .
# Allow the API base to be baked in at build time
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- Runtime stage ---
FROM nginx:alpine

# Static assets
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config: SPA fallback + /api proxy to the backend service
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
