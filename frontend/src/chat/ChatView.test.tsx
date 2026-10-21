import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatView } from "./ChatView";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

async function sendMessage(text: string) {
  await userEvent.type(screen.getByLabelText("Wiadomość"), text);
  await userEvent.click(screen.getByRole("button", { name: "Wyślij" }));
}

test("shows history and streams assistant reply incrementally", async () => {
  const fetch = mockFetch({
    "GET /api/chat/messages": [{ id: 1, role: "assistant", content: "Witaj!", created_at: "" }],
    "GET /api/list": { id: 1, groups: [] },
    "POST /api/chat/messages": () =>
      sseResponse([
        'event: delta\ndata: {"text": "Dodałem "}\n\n',
        'event: list_changed\ndata: {}\n\nevent: delta\ndata: {"te',
        'xt": "chleb."}\n\nevent: done\ndata: {}\n\n',
      ]),
  });
  const { queryClient } = renderWithProviders(<ChatView />);
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");

  expect(await screen.findByText("Witaj!")).toBeInTheDocument();
  await sendMessage("kup chleb");

  expect(await screen.findByText("Dodałem chleb.")).toBeInTheDocument();
  expect(screen.getByText("kup chleb")).toBeInTheDocument();
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["list"] });
  const post = fetch.mock.calls.find(([, init]) => init?.method === "POST")!;
  expect(JSON.parse(post[1]!.body as string)).toEqual({ content: "kup chleb" });
});

test("shows rate limit message", async () => {
  mockFetch({
    "GET /api/chat/messages": [],
    "GET /api/list": { id: 1, groups: [] },
    "POST /api/chat/messages": () =>
      jsonResponse({ detail: "Przekroczono limit 30 wiadomości na godzinę." }, 429),
  });
  renderWithProviders(<ChatView />);

  await sendMessage("hej");

  expect(await screen.findByRole("alert")).toHaveTextContent("Przekroczono limit");
});

test("shows assistant error event", async () => {
  mockFetch({
    "GET /api/chat/messages": [],
    "GET /api/list": { id: 1, groups: [] },
    "POST /api/chat/messages": () =>
      sseResponse([
        'event: error\ndata: {"message": "Asystent jest chwilowo niedostępny."}\n\nevent: done\ndata: {}\n\n',
      ]),
  });
  renderWithProviders(<ChatView />);

  await sendMessage("hej");

  expect(await screen.findByRole("alert")).toHaveTextContent("chwilowo niedostępny");
});

test("too long message is blocked locally", async () => {
  const fetch = mockFetch({ "GET /api/chat/messages": [] });
  renderWithProviders(<ChatView />);
  await screen.findByText(/Napisz, czego potrzebujesz/);

  const textarea = screen.getByLabelText("Wiadomość");
  await userEvent.click(textarea);
  await userEvent.paste("x".repeat(2001));
  await userEvent.click(screen.getByRole("button", { name: "Wyślij" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("najwyżej 2000 znaków");
  expect(fetch.mock.calls.every(([, init]) => init?.method !== "POST")).toBe(true);
});

test("clears history", async () => {
  const fetch = mockFetch({
    "GET /api/chat/messages": [{ id: 1, role: "user", content: "stara wiadomość", created_at: "" }],
    "DELETE /api/chat/messages": () => jsonResponse(null, 204),
  });
  renderWithProviders(<ChatView />);

  await userEvent.click(await screen.findByRole("button", { name: "Wyczyść historię" }));

  await vi.waitFor(() => expect(screen.queryByText("stara wiadomość")).not.toBeInTheDocument());
  expect(fetch).toHaveBeenCalledWith("/api/chat/messages", expect.objectContaining({ method: "DELETE" }));
});
