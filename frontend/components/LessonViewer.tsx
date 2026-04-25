"use client";

import { LessonContent } from "@/lib/types";
import { motion } from "framer-motion";

interface LessonViewerProps {
  lesson: LessonContent | null;
  loading: boolean;
}

export default function LessonViewer({ lesson, loading }: LessonViewerProps) {
  return (
    <section className="flex h-[calc(100vh-10rem)] min-h-[560px] flex-col overflow-hidden rounded-2xl border border-stone-300 bg-white shadow-sm">
      <header className="border-b border-stone-200 px-5 py-4">
        <h2 className="text-sm font-semibold text-stone-800">Lumos Tutor</h2>
        <p className="text-xs text-stone-500">A calm, conversational lesson flow</p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        <ChatBubble
          role="assistant"
          text={
            loading
              ? "Generating your curriculum from the uploaded document..."
              : "I built your first lesson. Read it and check the quiz below."
          }
        />

        {!lesson && !loading ? (
          <ChatBubble
            role="assistant"
            text="Upload a PDF/MD/TXT file to start. Your personalized curriculum appears here."
          />
        ) : null}

        {lesson?.sections.map((section, index) => (
          <motion.article
            key={`${section.title}-${index}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: index * 0.04 }}
            className="ml-6 rounded-2xl border border-stone-200 bg-stone-50 p-4"
          >
            <p className="mb-2 text-xs uppercase tracking-wide text-stone-500">{section.type}</p>
            <h3 className="mb-2 text-sm font-semibold text-stone-800">{section.title}</h3>
            {section.body ? <p className="text-sm leading-7 text-stone-700">{section.body}</p> : null}
            {section.type === "code" && section.snippet ? (
              <pre className="mt-3 overflow-x-auto rounded-xl border border-stone-200 bg-stone-100 p-3 text-xs text-stone-800">
                <code>{section.snippet}</code>
              </pre>
            ) : null}
          </motion.article>
        ))}

        {lesson ? (
          <motion.section
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="ml-6 rounded-2xl border border-stone-200 bg-white p-4"
          >
            <h3 className="text-sm font-semibold text-stone-800">Quiz Checkpoint</h3>
            <p className="mb-3 mt-1 text-xs text-stone-500">
              Pass threshold: {(lesson.quiz.pass_threshold * 100).toFixed(0)}%
            </p>
            <ol className="space-y-3">
              {lesson.quiz.questions.map((question) => (
                <li key={question.id} className="text-sm text-stone-800">
                  <p className="font-medium">{question.stem}</p>
                  {question.options?.length ? (
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-stone-600">
                      {question.options.map((option, idx) => (
                        <li key={`${question.id}-${idx}`}>{option}</li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ol>
          </motion.section>
        ) : null}
      </div>
    </section>
  );
}

function ChatBubble({ role, text }: { role: "assistant" | "user"; text: string }) {
  const assistant = role === "assistant";
  return (
    <div className={`flex ${assistant ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[84%] rounded-2xl px-4 py-3 text-sm leading-6 ${
          assistant
            ? "border border-stone-200 bg-stone-50 text-stone-800"
            : "bg-stone-900 text-stone-100"
        }`}
      >
        {text}
      </div>
    </div>
  );
}
