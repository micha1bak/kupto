import { createSseParser, type SseEvent } from "./sse";

test("parses events split across chunks, including mid-event and mid-character splits", () => {
  const events: SseEvent[] = [];
  const parse = createSseParser((e) => events.push(e));

  parse('event: delta\ndata: {"text": "Dod');
  parse('ałem"}\n\nevent: list_');
  parse("changed\ndata: {}\n");
  parse("\nevent: done\r\ndata: {}\r\n\r\n");

  expect(events).toEqual([
    { event: "delta", data: { text: "Dodałem" } },
    { event: "list_changed", data: {} },
    { event: "done", data: {} },
  ]);
});

test("keeps incomplete event in buffer until boundary arrives", () => {
  const events: SseEvent[] = [];
  const parse = createSseParser((e) => events.push(e));

  parse('event: delta\ndata: {"text": "a"}');
  expect(events).toEqual([]);

  parse("\n\n");
  expect(events).toHaveLength(1);
});
