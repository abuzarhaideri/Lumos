"use client";
import * as React from "react";

interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onFileUpload: (file: File) => void;
  sending: boolean;
  darkMode: boolean;
}

export default function ChatComposer({
  value,
  onChange,
  onSend,
  onFileUpload,
  sending,
  darkMode
}: ChatComposerProps) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  return (
    <div
      className={`sticky bottom-0 border-t px-4 py-4 backdrop-blur sm:px-6 ${
        darkMode ? "border-zinc-800 bg-zinc-900/85" : "border-stone-200/90 bg-white/80"
      }`}
    >
      <div className="mx-auto max-w-3xl">
        <div
          className={`flex items-end gap-2 rounded-2xl border p-2 shadow-[0_10px_24px_rgba(20,20,30,0.08)] ${
            darkMode ? "border-zinc-700 bg-zinc-800" : "border-stone-300 bg-white"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.txt,.md"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                onFileUpload(e.target.files[0]);
                e.target.value = ""; // reset
              }
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className={`rounded-xl p-2 transition ${
              darkMode
                ? "text-zinc-400 hover:bg-zinc-700 hover:text-zinc-100"
                : "text-stone-500 hover:bg-stone-100 hover:text-stone-800"
            }`}
          >
            📎
          </button>
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Ask Lumos anything..."
            rows={2}
            className={`max-h-40 min-h-12 flex-1 resize-y bg-transparent px-2 py-1 text-sm leading-6 outline-none ${
              darkMode ? "text-zinc-100 placeholder:text-zinc-500" : "text-stone-900 placeholder:text-stone-400"
            }`}
          />
          <button
            className={`rounded-xl p-2 transition ${
              darkMode
                ? "text-zinc-400 hover:bg-zinc-700 hover:text-zinc-100"
                : "text-stone-500 hover:bg-stone-100 hover:text-stone-800"
            }`}
          >
            🎙️
          </button>
          <button
            onClick={onSend}
            disabled={sending}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition duration-200 hover:brightness-110 disabled:opacity-50"
          >
            {sending ? "..." : "➤"}
          </button>
        </div>
      </div>
    </div>
  );
}
