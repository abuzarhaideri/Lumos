"use client";

interface ChatHeaderProps {
  modelName: string;
  online: boolean;
  darkMode: boolean;
  onToggleTheme: () => void;
}

export default function ChatHeader({ modelName, online, darkMode, onToggleTheme }: ChatHeaderProps) {
  return (
    <header
      className={`sticky top-0 z-10 rounded-t-2xl border-b px-6 py-4 backdrop-blur ${
        darkMode ? "border-zinc-800 bg-zinc-900/80" : "border-stone-200/80 bg-white/75"
      }`}
    >
      <div className="mx-auto flex max-w-3xl items-center gap-3">
        <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.7)]" />
        <div>
          <p className={`text-sm font-semibold ${darkMode ? "text-zinc-100" : "text-stone-800"}`}>
            {modelName}
          </p>
          <p className={`text-xs ${darkMode ? "text-zinc-400" : "text-stone-500"}`}>
            {online ? "Connected" : "Offline"}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={onToggleTheme}
            className={`rounded-xl border px-3 py-1.5 text-xs transition ${
              darkMode
                ? "border-zinc-700 bg-zinc-800 text-zinc-100 hover:bg-zinc-700"
                : "border-stone-300 bg-white text-stone-800 hover:bg-stone-100"
            }`}
          >
            {darkMode ? "Light" : "Dark"}
          </button>
          <button
            className={`rounded-xl border p-2 text-xs transition ${
              darkMode
                ? "border-zinc-700 bg-zinc-800 hover:bg-zinc-700"
                : "border-stone-300 bg-white hover:bg-stone-100"
            }`}
          >
            ⚙️
          </button>
        </div>
      </div>
    </header>
  );
}
