import { addDays, mondayOf, shortDate, toDay, weekdayName, weekLabel } from "./dates";

test("daty lokalne bez przesunięcia przez UTC", () => {
  expect(toDay(new Date(2026, 9, 27, 0, 5))).toBe("2026-10-27");
  expect(toDay(new Date(2026, 9, 27, 23, 55))).toBe("2026-10-27");
});

test("przesuwanie dni przez koniec miesiąca, roku i zmianę czasu", () => {
  expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
  expect(addDays("2026-12-28", 7)).toBe("2027-01-04");
  expect(addDays("2026-10-26", -7)).toBe("2026-10-19");
  // 25 października 2026 kończy się czas letni w Polsce.
  expect(addDays("2026-10-24", 2)).toBe("2026-10-26");
  expect(addDays("2026-03-28", 2)).toBe("2026-03-30");
});

test("poniedziałek tygodnia", () => {
  expect(mondayOf("2026-10-26")).toBe("2026-10-26");
  expect(mondayOf("2026-10-27")).toBe("2026-10-26");
  expect(mondayOf("2026-11-01")).toBe("2026-10-26");
});

test("opisy dni i tygodni po polsku", () => {
  expect(weekdayName("2026-10-27")).toBe("wtorek");
  expect(weekdayName("2026-11-01")).toBe("niedziela");
  expect(shortDate("2026-10-27")).toBe("27 paź");
  expect(weekLabel("2026-10-26")).toBe("26 paź – 1 lis");
});
