import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { captureInstallPrompt } from "./pwa/install";
import { registerServiceWorker } from "./pwa/register";
import "./index.css";

// Zanim cokolwiek się zamontuje: `beforeinstallprompt` może przyjść jeszcze na ekranie logowania.
captureInstallPrompt();

// SW tylko w buildzie produkcyjnym — w `vite dev` przeszkadzałby w HMR.
if (import.meta.env.PROD) {
  window.addEventListener("load", () => {
    registerServiceWorker().catch((error) => console.warn("Rejestracja service workera:", error));
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
