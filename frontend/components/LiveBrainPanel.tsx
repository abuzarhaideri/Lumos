"use client";

import { Dispatch, SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { SsePayload } from "@/lib/types";

interface LiveBrainPanelProps {
  sessionId: string;
  active: boolean;
}

interface LogEntry {
  id: string;
  type: "architect" | "content" | "student" | "pass" | "fail" | "info";
  message: string;
}

type AgentStatus = "idle" | "active" | "done";

export default function LiveBrainPanel({ sessionId, active }: LiveBrainPanelProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<"idle" | "connecting" | "open" | "closed">("idle");
  const [iteration, setIteration] = useState(0);
  const [agents, setAgents] = useState<Record<"architect" | "content" | "student", AgentStatus>>(
    {
      architect: "idle",
      content: "idle",
      student: "idle"
    }
  );
  const logRef = useRef<HTMLDivElement>(null);

  const resolvedStreamUrl = useMemo(() => {
    const base = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
    return `${base}/api/sessions/${sessionId}/stream`;
  }, [sessionId]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    if (!active || !sessionId) {
      setStatus("idle");
      return;
    }
    setStatus("connecting");
    setLogs([]);
    setIteration(0);
    setAgents({ architect: "idle", content: "idle", student: "idle" });

    const source = new EventSource(resolvedStreamUrl);

    source.onopen = () => setStatus("open");
    source.onerror = () => {
      setStatus("closed");
      source.close();
    };
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as SsePayload;
        if (payload.type === "done") {
          setStatus("closed");
          source.close();
          return;
        }
        if (payload.type !== "log" || !payload.message) {
          return;
        }
        const message = payload.message;
        setLogs((prev) => [
          ...prev,
          { id: crypto.randomUUID(), type: classifyLog(message), message }
        ]);
        hydrateAgentState(message, setAgents, setIteration);
      } catch {
        setLogs((prev) => [
          ...prev,
          { id: crypto.randomUUID(), type: "info", message: String(event.data) }
        ]);
      }
    };

    return () => source.close();
  }, [active, resolvedStreamUrl, sessionId]);

  return (
    <section className="flex h-[calc(100vh-10rem)] min-h-[560px] flex-col overflow-hidden rounded-2xl border border-stone-300 bg-stone-50 shadow-sm">
      <header className="flex items-center gap-2 border-b border-stone-200 px-4 py-4">
        <span className="h-2 w-2 rounded-full bg-stone-700" />
        <h2 className="text-sm font-semibold text-stone-800">Live Brain</h2>
        <p className="ml-auto text-xs text-stone-500">status: {status}</p>
      </header>

      <div ref={logRef} className="flex-1 space-y-2 overflow-y-auto p-4">
        {logs.length === 0 ? (
          <p className="text-sm text-stone-500">
            {active ? "Waiting for agents to publish logs..." : "Start a run to stream logs."}
          </p>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
                className={`rounded-xl border px-3 py-2 text-xs ${logColors[log.type]}`}
              >
                {log.message}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-stone-200 p-3">
        {(["architect", "content", "student"] as const).map((name) => (
          <div
            key={name}
            className={`rounded-lg border p-2 text-center text-xs ${agentCardClass[agents[name]]}`}
          >
            <p className="text-lg leading-none">{agentIcons[name]}</p>
            <p className="mt-1 capitalize text-stone-600">{name}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 border-t border-stone-200 px-3 py-2 text-xs text-stone-500">
        <span>feedback loop</span>
        <div className="flex gap-1">
          {[1, 2, 3].map((n) => (
            <span
              key={n}
              className={`h-2 w-2 rounded-full border ${
                n < iteration
                  ? "border-stone-700 bg-stone-700"
                  : n === iteration
                    ? "animate-pulse border-stone-500 bg-stone-500"
                    : "border-stone-300"
              }`}
            />
          ))}
        </div>
        <span className="ml-auto">max 3</span>
      </div>
    </section>
  );
}

function classifyLog(message: string): LogEntry["type"] {
  if (message.includes("Architect")) return "architect";
  if (message.includes("Content")) return "content";
  if (message.includes("Student")) return "student";
  if (message.includes("PASSED")) return "pass";
  if (message.includes("Failed") || message.includes("Error")) return "fail";
  return "info";
}

function hydrateAgentState(
  message: string,
  setAgents: Dispatch<SetStateAction<Record<"architect" | "content" | "student", AgentStatus>>>,
  setIteration: Dispatch<SetStateAction<number>>
) {
  if (message.includes("Architect Agent")) {
    setAgents((prev) => ({
      ...prev,
      architect: message.includes("Created") ? "done" : "active"
    }));
  } else if (message.includes("Content Agent")) {
    setAgents((prev) => ({
      ...prev,
      architect: "done",
      content: message.includes("written") ? "done" : "active"
    }));
  } else if (message.includes("Student Agent")) {
    setAgents((prev) => ({
      ...prev,
      content: "done",
      student: message.includes("PASSED") ? "done" : "active"
    }));
    const match = message.match(/attempt (\d+)/i);
    if (match) setIteration(Number(match[1]));
  }
}

const logColors: Record<LogEntry["type"], string> = {
  architect: "border-stone-300 bg-white text-stone-700",
  content: "border-stone-300 bg-white text-stone-700",
  student: "border-stone-300 bg-white text-stone-700",
  pass: "border-emerald-200 bg-emerald-50 text-emerald-700",
  fail: "border-red-200 bg-red-50 text-red-700",
  info: "border-stone-300 bg-stone-100 text-stone-600"
};

const agentCardClass: Record<AgentStatus, string> = {
  idle: "border-stone-300 bg-white",
  active: "border-stone-400 bg-stone-100",
  done: "border-emerald-300 bg-emerald-50"
};

const agentIcons = {
  architect: "🏗️",
  content: "✍️",
  student: "🎓"
};