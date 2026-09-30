FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install && npm install-scripts approve esbuild
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm","run","dev"]
