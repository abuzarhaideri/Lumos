"use client";

import { AnimatePresence, motion } from "framer-motion";

export interface ChatThread {
  id: string;
  title: string;
  createdAt: number;
}

interface SidebarProps {
  collapsed: boolean;
  chats: ChatThread[];
  activeChatId: string;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  authMode: "login" | "signup";
  isLoggedIn: boolean;
  userName: string;
  onAuthModeToggle: () => void;
  onSubmitAuth: (formData: FormData) => void;
  onLogout: () => void;
  darkMode: boolean;
}

export default function Sidebar(props: SidebarProps) {
  const {
    collapsed,
    chats,
    activeChatId,
    onToggle,
    onNewChat,
    onSelectChat,
    authMode,
    isLoggedIn,
    userName,
    onAuthModeToggle,
    onSubmitAuth,
    onLogout,
    darkMode
  } = props;

  return (
    <motion.aside
      animate={{ width: collapsed ? 80 : 292 }}
      transition={{ duration: 0.25, ease: "easeInOut" }}
      className={`hidden h-full overflow-hidden rounded-2xl border shadow-[0_10px_30px_rgba(10,10,20,0.06)] backdrop-blur md:flex md:flex-col ${
        darkMode ? "border-zinc-800 bg-zinc-900/75 text-zinc-100" : "border-stone-300/80 bg-white/55 text-stone-900"
      }`}
    >
      <div className="flex items-center justify-between px-3 py-3">
          <button
            onClick={onToggle}
            className={`rounded-xl p-2 transition ${
              darkMode
                ? "text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
                : "text-stone-600 hover:bg-stone-100 hover:text-stone-900"
            }`}
          >
          {collapsed ? "»" : "«"}
        </button>
        {!collapsed ? <span className="text-sm font-semibold">Lumos AI</span> : null}
        {!collapsed ? (
            <button
              onClick={onNewChat}
              className={`rounded-xl border px-2.5 py-1 text-xs transition hover:-translate-y-px ${
                darkMode
                  ? "border-zinc-700 bg-zinc-800 hover:bg-zinc-700"
                  : "border-stone-300 bg-white hover:bg-stone-50"
              }`}
            >
            + New
          </button>
        ) : null}
      </div>

      <AnimatePresence>
        {!collapsed ? (
          <motion.div
            key="expanded"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="flex min-h-0 flex-1 flex-col px-3 pb-3"
          >
            <div
              className={`mb-3 rounded-2xl border p-3 ${
                darkMode ? "border-zinc-800 bg-zinc-900/80" : "border-stone-200 bg-white/80"
              }`}
            >
              {!isLoggedIn ? (
                <form
                  className="space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    onSubmitAuth(new FormData(e.currentTarget));
                  }}
                >
                  <p className={`text-xs font-medium ${darkMode ? "text-zinc-400" : "text-stone-600"}`}>{authMode.toUpperCase()}</p>
                  <input name="name" placeholder="Name" className={`w-full rounded-xl border px-3 py-2 text-sm outline-none ring-blue-300/50 transition focus:ring-2 ${darkMode ? "border-zinc-700 bg-zinc-800 text-zinc-100" : "border-stone-300 bg-white text-stone-900"}`} required />
                  <input name="email" type="email" placeholder="Email" className={`w-full rounded-xl border px-3 py-2 text-sm outline-none ring-blue-300/50 transition focus:ring-2 ${darkMode ? "border-zinc-700 bg-zinc-800 text-zinc-100" : "border-stone-300 bg-white text-stone-900"}`} required />
                  <input name="password" type="password" placeholder="Password" className={`w-full rounded-xl border px-3 py-2 text-sm outline-none ring-blue-300/50 transition focus:ring-2 ${darkMode ? "border-zinc-700 bg-zinc-800 text-zinc-100" : "border-stone-300 bg-white text-stone-900"}`} required />
                  <button className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-2 text-sm text-white shadow-sm transition hover:brightness-110">
                    {authMode === "login" ? "Log in" : "Sign up"}
                  </button>
                  <button type="button" onClick={onAuthModeToggle} className={`text-xs underline ${darkMode ? "text-zinc-400" : "text-stone-600"}`}>
                    {authMode === "login" ? "Need account? Sign up" : "Already have account? Log in"}
                  </button>
                </form>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Hi, {userName}</p>
                  <button onClick={onLogout} className={`rounded-lg border px-2 py-1 text-xs transition ${darkMode ? "border-zinc-700 hover:bg-zinc-800" : "border-stone-300 hover:bg-stone-100"}`}>
                    Log out
                  </button>
                </div>
              )}
            </div>

            <p className={`mb-2 px-1 text-xs ${darkMode ? "text-zinc-500" : "text-stone-500"}`}>Previous chats</p>
            <div className="min-h-0 space-y-1 overflow-y-auto pr-1">
              {chats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  className={`w-full rounded-xl px-3 py-2 text-left text-sm transition ${
                    chat.id === activeChatId
                      ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm"
                      : darkMode
                        ? "bg-zinc-900 text-zinc-200 hover:bg-zinc-800"
                        : "bg-white text-stone-700 hover:bg-stone-100"
                  }`}
                >
                  <p className="truncate">{chat.title}</p>
                </button>
              ))}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.aside>
  );
}
