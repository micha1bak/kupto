import { apiFetch } from "./client";

export interface SseEvent {
  event: string;
  data: unknown;
}

/** Parser strumienia SSE odporny na zdarzenia podzielone między fragmenty sieciowe. */
export function createSseParser(onEvent: (event: SseEvent) => void) {
  let buffer = "";
  return (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, "\n");
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length) onEvent({ event, data: JSON.parse(data.join("\n")) });
    }
  };
}

export interface ChatHandlers {
  onDelta: (text: string) => void;
  onListChanged: () => void;
  onError: (message: string) => void;
}

/** Wysyła wiadomość do asystenta i przekazuje kolejne zdarzenia odpowiedzi. */
export async function streamChat(content: string, handlers: ChatHandlers): Promise<void> {
  const response = await apiFetch("/api/chat/messages", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader();
  const parse = createSseParser(({ event, data }) => {
    const payload = data as { text?: string; message?: string };
    if (event === "delta") handlers.onDelta(payload.text ?? "");
    else if (event === "list_changed") handlers.onListChanged();
    else if (event === "error") handlers.onError(payload.message ?? "Błąd asystenta.");
  });
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parse(value);
  }
}
