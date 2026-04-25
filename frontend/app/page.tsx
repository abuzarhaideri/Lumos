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
  const [error, setError] = useState("");
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

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !activeChat) return;

    const userMessage: ChatMessage = { role: "user", content: text, createdAt: Date.now() };
    const updatedMessages = [...activeChat.messages, userMessage];
    const maybeTitle = activeChat.messages.length <= 1 ? text.slice(0, 36) : activeChat.title;

    setInput("");
    setSending(true);
    setError("");
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: updatedMessages })
      });
      if (!res.ok) throw new Error("AI reply failed.");
      const data = (await res.json()) as { reply: string };

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
            onSubmitAuth={(formData) => {
              const name = String(formData.get("name") ?? "User").trim();
              setUserName(name || "User");
              setIsLoggedIn(true);
            }}
            onLogout={() => setIsLoggedIn(false)}
            darkMode={darkMode}
          />

          <section
            className={`flex h-full min-w-0 flex-col rounded-2xl border shadow-[0_16px_48px_rgba(16,18,40,0.08)] backdrop-blur ${
              darkMode ? "border-zinc-800 bg-zinc-900/70" : "border-stone-300/80 bg-white/70"
            }`}
          >
            <ChatHeader
              modelName="Lumos Tutor • Claude Sonnet"
              online={true}
              darkMode={darkMode}
              onToggleTheme={() => setDarkMode((v) => !v)}
            />

            <div className="min-h-0 flex-1 overflow-y-auto scroll-smooth">
              <MessageList messages={activeChat?.messages ?? []} typing={sending} darkMode={darkMode} />
            </div>

            <div className="px-4 pb-2">
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
