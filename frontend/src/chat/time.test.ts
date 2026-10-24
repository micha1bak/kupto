import { formatMessageTime } from "./time";

describe("godzina wiadomości czatu", () => {
  const now = new Date(2026, 9, 24, 20, 0);

  it("dzisiejsza wiadomość — sama godzina", () => {
    expect(formatMessageTime(new Date(2026, 9, 24, 8, 5).toISOString(), now)).toBe("08:05");
  });

  it("starsza wiadomość — z datą", () => {
    expect(formatMessageTime(new Date(2026, 9, 3, 18, 30).toISOString(), now)).toBe("3.10, 18:30");
  });

  it("brak lub zła data — bez godziny", () => {
    expect(formatMessageTime("", now)).toBeNull();
    expect(formatMessageTime("nie-data", now)).toBeNull();
  });
});
