import type { Config } from 'jest';
import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  // Ścieżka do aplikacji Next.js
  dir: './',
});

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node', // Logowanie testujemy w środowisku Node (Server Actions)
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
};

export default createJestConfig(config);
