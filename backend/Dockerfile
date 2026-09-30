FROM node:24-alpine
WORKDIR /app
COPY package.json package-lock.json ./
COPY backend/package.json ./backend/package.json
COPY frontend/package.json ./frontend/package.json
RUN npm ci --workspace backend --include-workspace-root
COPY backend/tsconfig.json ./backend/tsconfig.json
COPY backend/src ./backend/src
COPY database/migrations ./database/migrations
RUN npm --workspace backend run build
EXPOSE 3000
CMD ["npm","--workspace","backend","start"]
