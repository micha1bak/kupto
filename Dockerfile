# ==========================================
# ETAP 1: Budowanie aplikacji (Builder)
# ==========================================
FROM node:22-alpine AS builder
WORKDIR /usr/src/app

# Kopiujemy pakiety
COPY package*.json ./

# NOWE: Kopiujemy schemat Prismy przed instalacją i generowaniem
COPY prisma ./prisma/

# Instalujemy zależności
RUN npm ci --legacy-peer-deps

# NOWE: Generujemy klienta Prismy, aby kod TypeScript miał do niego dostęp i mógł się skompilować
RUN npx prisma generate

# Kopiujemy resztę kodu i kompilujemy
COPY . .
RUN npm run build


# ==========================================
# ETAP 2: Środowisko produkcyjne (Production)
# ==========================================
FROM node:20-alpine AS production
ENV NODE_ENV=production
WORKDIR /usr/src/app

COPY package*.json ./

# NOWE: Ponownie kopiujemy schemat, bo wygenerowanie klienta wymaga pliku schema.prisma
COPY prisma ./prisma/

# Instalujemy tylko paczki produkcyjne
RUN npm ci --omit=dev --legacy-peer-deps

# NOWE: Generujemy klienta produkcyjnego pod środowisko Alpine Linux
RUN npx prisma generate

# Kopiujemy skompilowany kod z pierwszego etapu
COPY --from=builder /usr/src/app/build ./build
COPY --from=builder /usr/src/app/src/public  ./src/public

EXPOSE 3000
CMD ["node", "build/index.js"]
