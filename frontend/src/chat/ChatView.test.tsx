import { fireEvent, screen, waitFor } from "@testing-library/react";
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

const greeting = { id: 1, role: "assistant", content: "Witaj!", created_at: "" };

/** Historia jak na serwerze: przed wysłaniem tylko powitanie, potem także nowa wymiana. */
function historyRoute(after: object[]) {
  let calls = 0;
  return () => jsonResponse(calls++ === 0 ? [greeting] : [greeting, ...after]);
}

test("shows history and streams assistant reply incrementally", async () => {
  const fetch = mockFetch({
    "GET /api/chat/messages": historyRoute([
      { id: 2, role: "user", content: "kup chleb", created_at: "" },
      { id: 3, role: "assistant", content: "Dodałem chleb.", created_at: "" },
    ]),
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

test("exchange is shown once after history refresh and after returning to the tab", async () => {
  const fetch = mockFetch({
    "GET /api/chat/messages": historyRoute([
      { id: 2, role: "user", content: "kup mleko", created_at: "" },
      { id: 3, role: "assistant", content: "Dodałem mleko.", created_at: "" },
    ]),
    "GET /api/list": { id: 1, groups: [] },
    "POST /api/chat/messages": () =>
      sseResponse(['event: delta\ndata: {"text": "Dodałem mleko."}\n\nevent: done\ndata: {}\n\n']),
  });
  renderWithProviders(<ChatView />);
  await screen.findByText("Witaj!");

  await sendMessage("kup mleko");
  await vi.waitFor(() =>
    expect(fetch.mock.calls.filter(([url, init]) => url === "/api/chat/messages" && !init?.method)).toHaveLength(2),
  );
  fireEvent.focus(window);
  window.dispatchEvent(new Event("visibilitychange"));

  await vi.waitFor(() => expect(screen.getAllByText("Dodałem mleko.")).toHaveLength(1));
  expect(screen.getAllByText("kup mleko")).toHaveLength(1);
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

test("pasted recipe longer than 2000 characters is sent", async () => {
  const recipe = `Naleśniki\n${"Składniki: mąka, mleko, jajka. ".repeat(150)}`.trim();
  const fetch = mockFetch({
    "GET /api/chat/messages": [],
    "GET /api/list": { id: 1, groups: [] },
    "POST /api/chat/messages": () =>
      sseResponse(['event: delta\ndata: {"text": "Czego brakuje?"}\n\nevent: done\ndata: {}\n\n']),
  });
  renderWithProviders(<ChatView />);
  await screen.findByText(/wkleić przepis/);

  await userEvent.click(screen.getByLabelText("Wiadomość"));
  await userEvent.paste(recipe);
  await userEvent.click(screen.getByRole("button", { name: "Wyślij" }));

  await waitFor(() =>
    expect(fetch.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true),
  );
  const post = fetch.mock.calls.find(([, init]) => init?.method === "POST")!;
  expect(JSON.parse(post[1]!.body as string)).toEqual({ content: recipe });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("too long message is blocked locally", async () => {
  const fetch = mockFetch({ "GET /api/chat/messages": [] });
  renderWithProviders(<ChatView />);
  await screen.findByText(/Napisz, czego potrzebujesz/);

  const textarea = screen.getByLabelText("Wiadomość");
  await userEvent.click(textarea);
  await userEvent.paste("x".repeat(8001));
  await userEvent.click(screen.getByRole("button", { name: "Wyślij" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("najwyżej 8000 znaków");
  expect(fetch.mock.calls.every(([, init]) => init?.method !== "POST")).toBe(true);
});
