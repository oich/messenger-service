# Stage 1: Build
FROM node:20.18-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

# Build args AFTER npm ci so changing HUB_URL doesn't re-download packages
ARG VITE_HUB_URL=""
ARG VITE_API_TARGET=""
ENV VITE_HUB_URL=${VITE_HUB_URL}
ENV VITE_API_TARGET=${VITE_API_TARGET}

COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
