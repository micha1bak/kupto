# --- ETAP 1: Instalacja zależności ---
FROM node:22-alpine AS deps
# Alpine wymaga libc6-compat dla niektórych natywnych modułów
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Kopiujemy pliki blokady, aby wykorzystać cache Dockera
COPY package.json pnpm-lock.yaml* ./
# Włączamy pnpm i instalujemy zależności
RUN corepack enable pnpm && pnpm i --frozen-lockfile

# --- ETAP 2: Budowanie aplikacji ---
FROM node:22-alpine AS builder
WORKDIR /app
# Kopiujemy node_modules z poprzedniego etapu
COPY --from=deps /app/node_modules ./node_modules
# Kopiujemy resztę kodu źródłowego
COPY . .

# Budujemy wersję produkcyjną
RUN corepack enable pnpm && pnpm run build

# --- ETAP 3: Finalny obraz (Runner) ---
FROM node:22-alpine AS runner
WORKDIR /app

# Ważne dla bezpieczeństwa: nie uruchamiamy jako root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

ENV NODE_ENV=production
# Wyłączamy zbieranie telemetrii Next.js w kontenerze
ENV NEXT_TELEMETRY_DISABLED=1

# Kopiujemy tylko to, co niezbędne do działania (standalone)
COPY --from=builder /app/public ./public
# Standalone zawiera minimalny serwer node i skopiowane node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000

# Serwer Next.js standalone uruchamia się przez server.js
CMD ["node", "server.js"]
