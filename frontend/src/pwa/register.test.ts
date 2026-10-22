import { describe, expect, it, vi } from "vitest";
import { registerServiceWorker } from "./register";

function setup({ controlled = true } = {}) {
  const swTarget = new EventTarget();
  const registration = { update: vi.fn().mockResolvedValue(undefined) };
  const serviceWorker = Object.assign(swTarget, {
    controller: controlled ? {} : null,
    register: vi.fn().mockResolvedValue(registration),
  }) as unknown as ServiceWorkerContainer;
  const docTarget = new EventTarget();
  const doc = Object.assign(docTarget, { visibilityState: "visible" as DocumentVisibilityState });
  const reload = vi.fn();
  const setVisibility = (state: DocumentVisibilityState) => {
    doc.visibilityState = state;
    doc.dispatchEvent(new Event("visibilitychange"));
  };
  const controllerChange = () => swTarget.dispatchEvent(new Event("controllerchange"));
  return { serviceWorker, document: doc, doc, reload, registration, setVisibility, controllerChange };
}

describe("registerServiceWorker", () => {
  it("nic nie robi bez obsługi service workerów", async () => {
    const reload = vi.fn();
    await expect(
      registerServiceWorker({ serviceWorker: undefined, document, reload }),
    ).resolves.toBeUndefined();
  });

  it("rejestruje /sw.js dla całej aplikacji z pominięciem cache HTTP", async () => {
    const t = setup();
    await registerServiceWorker(t);
    expect(t.serviceWorker.register).toHaveBeenCalledWith("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });
  });

  it("sprawdza aktualizację przy powrocie na pierwszy plan", async () => {
    const t = setup();
    await registerServiceWorker(t);
    t.setVisibility("hidden");
    expect(t.registration.update).not.toHaveBeenCalled();
    t.setVisibility("visible");
    expect(t.registration.update).toHaveBeenCalledTimes(1);
  });

  it("nie przeładowuje przy pierwszej instalacji", async () => {
    const t = setup({ controlled: false });
    await registerServiceWorker(t);
    t.controllerChange();
    t.setVisibility("hidden");
    expect(t.reload).not.toHaveBeenCalled();
  });

  it("po aktualizacji przeładowuje dopiero przy przejściu w tło", async () => {
    const t = setup();
    await registerServiceWorker(t);
    t.controllerChange();
    expect(t.reload).not.toHaveBeenCalled();
    t.setVisibility("hidden");
    expect(t.reload).toHaveBeenCalledTimes(1);
    t.setVisibility("visible");
    t.setVisibility("hidden");
    expect(t.reload).toHaveBeenCalledTimes(1);
  });

  it("po aktualizacji w tle przeładowuje od razu", async () => {
    const t = setup();
    await registerServiceWorker(t);
    t.doc.visibilityState = "hidden";
    t.controllerChange();
    expect(t.reload).toHaveBeenCalledTimes(1);
  });
});
