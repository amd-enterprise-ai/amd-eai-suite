# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# ---- Dependencies ----
FROM node:22-alpine AS dependencies
WORKDIR /app
RUN corepack enable
COPY package*.json pnpm-lock.yaml .env.local.dummy .npmrc ./
RUN mv .env.local.dummy .env.local
RUN pnpm install --frozen-lockfile

# ---- Build ----
FROM dependencies AS build
ARG GITHUB_SHA_SHORT
COPY . .
RUN export NEXT_PUBLIC_BUILD_VERSION="$(date +"%y%m%d")-$GITHUB_SHA_SHORT"; \
    echo "Creating build $NEXT_PUBLIC_BUILD_VERSION"; \
    pnpm build

# ---- Production ----
FROM node:22-alpine AS production
WORKDIR /app
RUN corepack enable && corepack prepare pnpm --activate
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/package*.json ./
COPY --from=build /app/pnpm-lock.yaml ./
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/next-i18next.config.js ./next-i18next.config.js
COPY --from=build /app/public ./public
RUN chown -R node:node /app

# Expose the port the app will run on
EXPOSE 8000

# Start the application
CMD [ "pnpm", "start"]
