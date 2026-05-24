FROM node:20-alpine

WORKDIR /app

# Skip electron postinstall — not needed for web dev server
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .

CMD ["npm", "run", "dev"]
