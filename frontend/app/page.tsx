"use client";

import { useEffect, useMemo, useState } from "react";
import ChatComposer from "@/components/chat/ChatComposer";
import ChatHeader from "@/components/chat/ChatHeader";
import MessageList, { ChatMessage } from "@/components/chat/MessageList";
import Sidebar from "@/components/chat/Sidebar";

interface ChatThread {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
}

export default function HomePage() {
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userName, setUserName] = useState("Guest");
  const [activeChatId, setActiveChatId] = useState("chat-1");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [backendHealthy, setBackendHealthy] = useState(true);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);
  // IMPORTANT: Keep initial state SSR-deterministic to avoid hydration mismatch.
  const [chats, setChats] = useState<ChatThread[]>(() => [
    {
      id: "chat-1",
      title: "New chat",
      createdAt: 0,
      messages: [
        {
          role: "assistant",
          content: "Hey! I am Lumos. Tell me what you want to learn today.",
          createdAt: 0
        }
      ]
    }
  ]);

  const backendBase = useMemo(() => process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000", []);
  const activeChat = chats.find((chat) => chat.id === activeChatId) ?? chats[0];

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("lumos-theme");
    if (savedTheme === "dark" || savedTheme === "light") {
      setDarkMode(savedTheme === "dark");
      return;
    }
    setDarkMode(window.matchMedia("(prefers-color-scheme: dark)").matches);
  }, []);

  useEffect(() => {
    const restoreAuth = async () => {
      const savedToken = window.localStorage.getItem("lumos-token");
      if (!savedToken) {
        setAuthLoading(false);
        return;
      }
      try {
        const res = await fetch(`${backendBase}/api/auth/me`, {
          headers: { Authorization: `Bearer ${savedToken}` }
        });
        if (!res.ok) throw new Error("Expired session");
        const data = (await res.json()) as { user: { name: string; email: string } };
        setIsLoggedIn(true);
        setUserName(data.user.name);
        setToken(savedToken);
      } catch {
        window.localStorage.removeItem("lumos-token");
      } finally {
        setAuthLoading(false);
      }
    };
    void restoreAuth();
  }, [backendBase]);

  useEffect(() => {
    // After mount, replace placeholder timestamps with real client time.
    setChats((prev) => {
      const first = prev[0];
      if (!first || first.createdAt !== 0) return prev;
      const now = Date.now();
      return [
        {
          ...first,
          createdAt: now,
          messages: first.messages.map((m, i) => ({ ...m, createdAt: now + i }))
        },
        ...prev.slice(1)
      ];
    });
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    window.localStorage.setItem("lumos-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const createNewChat = () => {
    const id = `chat-${Date.now()}`;
    const newChat: ChatThread = {
      id,
      title: "New chat",
      createdAt: Date.now(),
      messages: [
        { role: "assistant", content: "New chat started. Ask me anything.", createdAt: Date.now() }
      ]
    };
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(id);
  };

  const sendPresetPrompt = (prompt: string) => {
    setInput(prompt);
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !activeChat) return;

    const userMessage: ChatMessage = { role: "user", content: text, createdAt: Date.now() };
    const updatedMessages = [...activeChat.messages, userMessage];
    const maybeTitle = activeChat.messages.length <= 1 ? text.slice(0, 36) : activeChat.title;

    setInput("");
    setSending(true);
    setError("");
    if (!isLoggedIn || !token) {
      setSending(false);
      setError("Please login first to chat with AI.");
      return;
    }
    const startedAt = performance.now();
    setChats((prev) =>
      prev.map((chat) =>
        chat.id === activeChat.id
          ? { ...chat, title: maybeTitle || "New chat", messages: updatedMessages }
          : chat
      )
    );

    try {
      const res = await fetch(`${backendBase}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ messages: updatedMessages })
      });
      if (!res.ok) throw new Error("AI reply failed.");
      const data = (await res.json()) as { reply: string };
      setBackendHealthy(true);
      setLastLatencyMs(Math.round(performance.now() - startedAt));

      setChats((prev) =>
        prev.map((chat) =>
          chat.id === activeChat.id
            ? {
                ...chat,
                messages: [
                  ...updatedMessages,
                  { role: "assistant", content: data.reply, createdAt: Date.now() }
                ]
              }
            : chat
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setBackendHealthy(false);
      setLastLatencyMs(Math.round(performance.now() - startedAt));
      setChats((prev) =>
        prev.map((chat) =>
          chat.id === activeChat.id
            ? {
                ...chat,
                messages: [
                  ...updatedMessages,
                  {
                    role: "assistant",
                    content: "Backend response nahi mila. Backend run karo and /api/chat check karo.",
                    createdAt: Date.now()
                  }
                ]
              }
            : chat
        )
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <main>
      <div
        className={`h-screen overflow-hidden p-3 transition-colors ${
          darkMode
            ? "bg-gradient-to-br from-[#0F0F0F] via-zinc-900 to-indigo-950/50 text-zinc-100"
            : "bg-gradient-to-br from-stone-100 via-stone-100 to-indigo-100/40 text-stone-900"
        }`}
      >
        <div className="mx-auto grid h-full max-w-[1500px] grid-cols-1 gap-3 md:grid-cols-[auto_1fr]">
          <Sidebar
            collapsed={sidebarCollapsed}
            chats={chats.map(({ id, title, createdAt }) => ({ id, title, createdAt }))}
            activeChatId={activeChatId}
            onToggle={() => setSidebarCollapsed((v) => !v)}
            onNewChat={createNewChat}
            onSelectChat={setActiveChatId}
            authMode={authMode}
            isLoggedIn={isLoggedIn}
            userName={userName}
            onAuthModeToggle={() => setAuthMode((m) => (m === "login" ? "signup" : "login"))}
            onSubmitAuth={async (formData) => {
              setError("");
              const payload = {
                name: String(formData.get("name") ?? "").trim(),
                email: String(formData.get("email") ?? "").trim(),
                password: String(formData.get("password") ?? "")
              };
              try {
                const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/signup";
                const res = await fetch(`${backendBase}${endpoint}`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok) {
                  throw new Error(data?.detail || "Authentication failed");
                }
                setIsLoggedIn(true);
                setUserName(data.user.name || payload.name || "User");
                setToken(data.access_token);
                window.localStorage.setItem("lumos-token", data.access_token);
              } catch (err) {
                setIsLoggedIn(false);
                setToken("");
                setError(err instanceof Error ? err.message : "Authentication failed");
              }
            }}
            onLogout={() => {
              setIsLoggedIn(false);
              setToken("");
              window.localStorage.removeItem("lumos-token");
            }}
            darkMode={darkMode}
          />

          <section
            className={`flex h-full min-w-0 flex-col overflow-hidden rounded-2xl border shadow-[0_16px_48px_rgba(16,18,40,0.08)] backdrop-blur ${
              darkMode ? "border-zinc-800 bg-zinc-900/70" : "border-stone-300/80 bg-white/70"
            }`}
          >
            <div
              className={`grid grid-cols-2 gap-2 border-b px-4 py-3 text-xs sm:grid-cols-5 ${
                darkMode ? "border-zinc-800 bg-zinc-900/70" : "border-stone-200 bg-stone-50/80"
              }`}
            >
              {[
                "Clear user + pain",
                "10-second clarity",
                "Zero instruction use",
                "Technical execution",
                "Demo quality"
              ].map((item) => (
                <div
                  key={item}
                  className={`rounded-lg border px-2 py-1 text-center ${
                    darkMode
                      ? "border-zinc-700 bg-zinc-800/70 text-zinc-200"
                      : "border-stone-200 bg-white text-stone-700"
                  }`}
                >
                  {item}
                </div>
              ))}
            </div>

            <ChatHeader
              modelName="Lumos Tutor • Claude Sonnet"
              online={backendHealthy}
              darkMode={darkMode}
              onToggleTheme={() => setDarkMode((v) => !v)}
            />

            <div
              className={`border-b px-5 py-3 ${
                darkMode ? "border-zinc-800 bg-zinc-900/40" : "border-stone-200 bg-white/80"
              }`}
            >
              <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2">
                <p className={`text-xs ${darkMode ? "text-zinc-300" : "text-stone-600"}`}>
                  Lumos turns dry technical docs into structured lessons and quizzes with AI feedback loops.
                </p>
                <span
                  className={`ml-auto rounded-md px-2 py-1 text-[11px] ${
                    backendHealthy
                      ? darkMode
                        ? "bg-emerald-900/40 text-emerald-300"
                        : "bg-emerald-100 text-emerald-700"
                      : darkMode
                        ? "bg-red-900/40 text-red-300"
                        : "bg-red-100 text-red-700"
                  }`}
                >
                  {backendHealthy ? "API Healthy" : "API Error"}
                </span>
                {lastLatencyMs !== null ? (
                  <span
                    className={`rounded-md px-2 py-1 text-[11px] ${
                      darkMode ? "bg-zinc-800 text-zinc-300" : "bg-stone-100 text-stone-700"
                    }`}
                  >
                    {lastLatencyMs} ms
                  </span>
                ) : null}
              </div>
              <div className="mx-auto mt-2 flex max-w-3xl flex-wrap gap-2">
                {[
                  "Explain transformers for a 10th class student",
                  "Generate a 3-lesson plan from this topic: FastAPI",
                  "Quiz me on Python async with 5 MCQs"
                ].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => sendPresetPrompt(prompt)}
                    className={`rounded-full border px-3 py-1 text-xs transition ${
                      darkMode
                        ? "border-zinc-700 bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
                        : "border-stone-300 bg-white text-stone-700 hover:bg-stone-100"
                    }`}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-0 min-h-0 flex-1 overflow-y-auto overscroll-contain scroll-smooth">
              <MessageList messages={activeChat?.messages ?? []} typing={sending} darkMode={darkMode} />
            </div>

            <div className="px-4 pb-2">
              {authLoading ? (
                <p className="mx-auto max-w-3xl text-xs text-stone-500 dark:text-zinc-400">
                  Restoring session...
                </p>
              ) : null}
              {error ? <p className="mx-auto max-w-3xl text-xs text-red-600">{error}</p> : null}
            </div>

            <ChatComposer
              value={input}
              onChange={setInput}
              onSend={sendMessage}
              sending={sending}
              darkMode={darkMode}
            />
          </section>
        </div>
      </div>
    </main>
  );
}
