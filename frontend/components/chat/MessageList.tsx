"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  createdAt: number;
}

interface MessageListProps {
  messages: ChatMessage[];
  typing: boolean;
  darkMode: boolean;
}

export default function MessageList({ messages, typing, darkMode }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to latest message (smooth).
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, typing]);

  return (
    <div className="mx-auto w-full max-w-3xl space-y-3 px-4 py-5 sm:px-6">
      <AnimatePresence initial={false}>
        {messages.map((message, idx) => {
          const previous = messages[idx - 1];
          const grouped = previous?.role === message.role;
          return (
            <motion.div
              key={`${message.role}-${idx}-${message.createdAt}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
              className={`flex ${message.role === "assistant" ? "justify-start" : "justify-end"} ${
                grouped ? "mt-1" : "mt-4"
              }`}
            >
              <div
                className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm ${
                  message.role === "assistant"
                    ? darkMode
                      ? "border border-zinc-700 bg-zinc-800 text-zinc-100"
                      : "border border-stone-200 bg-white text-stone-800"
                    : "bg-gradient-to-br from-blue-600 to-indigo-600 text-white"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                {!grouped ? (
                  <p
                    className={`mt-2 text-[11px] ${
                      message.role === "assistant"
                        ? darkMode
                          ? "text-zinc-400"
                          : "text-stone-400"
                        : "text-blue-100/90"
                    }`}
                  >
                    {formatTimeStable(message.createdAt)}
                  </p>
                ) : null}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>

      {typing ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
          <div
            className={`rounded-2xl border px-4 py-3 shadow-sm ${
              darkMode ? "border-zinc-700 bg-zinc-800" : "border-stone-200 bg-white"
            }`}
          >
            <div className="flex items-center gap-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-stone-400 [animation-delay:-0.2s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-stone-400 [animation-delay:-0.1s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-stone-400" />
            </div>
          </div>
        </motion.div>
      ) : null}
      <div ref={endRef} />
    </div>
  );
}

function formatTimeStable(epochMs: number) {
  if (!epochMs) return "";
  // Stable across SSR/CSR: UTC HH:MM (no locale, no AM/PM).
  return new Date(epochMs).toISOString().slice(11, 16);
}
