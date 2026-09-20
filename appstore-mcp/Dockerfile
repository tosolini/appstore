FROM node:22-alpine

WORKDIR /app

RUN npm init -y \
 && npm install zod

COPY server.js .

RUN chown -R node:node /app

USER node

EXPOSE 3000
CMD ["node", "server.js"]


