"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Send, ChevronDown, ChevronUp, X } from "lucide-react";
import { getSimulation, getIDIMessages, sendIDIMessage, endIDISession } from "@/lib/api";
import Spinner from "@/components/ui/Spinner";

export default function IDIChatPage() {
  const { projectId, simulationId } = useParams<{ projectId: string; simulationId: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [input, setInput] = useState("");
  const [showScript, setShowScript] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { data: simulation } = useQuery({
    queryKey: ["simulation", simulationId],
    queryFn: () => getSimulation(projectId, simulationId),
  });

  const { data: messages = [], isLoading: loadingMessages } = useQuery({
    queryKey: ["idi-messages", simulationId],
    queryFn: () => getIDIMessages(projectId, simulationId),
    enabled: !!simulation,
  });

  const send = useMutation({
    mutationFn: (content: string) => sendIDIMessage(projectId, simulationId, content),
    onMutate: async (content: string) => {
      await qc.cancelQueries({ queryKey: ["idi-messages", simulationId] });
      const previous = qc.getQueryData(["idi-messages", simulationId]);
      qc.setQueryData(["idi-messages", simulationId], (old: typeof messages) => [
        ...(old ?? []),
        {
          id: `optimistic-${Date.now()}`,
          simulation_id: simulationId,
          persona_id: null,
          role: "user" as const,
          content,
          created_at: new Date().toISOString(),
        },
      ]);
      return { previous };
    },
    onError: (_err, _content, context) => {
      qc.setQueryData(["idi-messages", simulationId], context?.previous);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["idi-messages", simulationId] });
    },
  });

  const end = useMutation({
    mutationFn: () => endIDISession(projectId, simulationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation", simulationId] });
      router.push(`/projects/${projectId}/simulations/${simulationId}`);
    },
  });

  // Redirect if session is no longer active
  useEffect(() => {
    if (simulation && simulation.status !== "active") {
      router.push(`/projects/${projectId}/simulations/${simulationId}`);
    }
  }, [simulation?.status]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const content = input.trim();
    if (!content || send.isPending) return;
    setInput("");
    send.mutate(content);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-100 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/projects/${projectId}`)}
            className="text-zinc-400 hover:text-zinc-700 transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-medium">
              P
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-900">Manual Interview</p>
              <p className="text-xs text-zinc-400">
                {simulation
                  ? `${messages.filter(m => m.role === "user").length} questions asked`
                  : "Loading…"}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {simulation?.idi_script_text && (
            <button
              onClick={() => setShowScript(v => !v)}
              className="flex items-center gap-1.5 text-xs text-zinc-500 border border-zinc-200 rounded-lg px-3 py-1.5 hover:border-zinc-300 transition-colors"
            >
              Script {showScript ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
          <button
            onClick={() => setConfirmEnd(true)}
            className="flex items-center gap-1.5 text-xs text-red-600 border border-red-200 rounded-lg px-3 py-1.5 hover:bg-red-50 transition-colors"
          >
            End Interview
          </button>
        </div>
      </div>

      {/* Script panel */}
      {showScript && simulation?.idi_script_text && (
        <div className="shrink-0 border-b border-zinc-100 bg-zinc-50 px-5 py-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-zinc-600 uppercase tracking-wide">Interview Script</p>
            <button onClick={() => setShowScript(false)} className="text-zinc-400 hover:text-zinc-600">
              <X size={14} />
            </button>
          </div>
          <pre className="text-xs text-zinc-600 whitespace-pre-wrap font-sans leading-relaxed max-h-40 overflow-y-auto">
            {simulation.idi_script_text}
          </pre>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {loadingMessages && (
          <div className="flex justify-center py-10">
            <Spinner className="h-6 w-6 border-zinc-200 border-t-zinc-600" />
          </div>
        )}

        {!loadingMessages && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-10">
            <p className="text-sm text-zinc-500 mb-1">Start the interview</p>
            <p className="text-xs text-zinc-400">Ask your first question below.</p>
          </div>
        )}

        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} gap-2.5`}
          >
            {msg.role === "persona" && (
              <div className="w-7 h-7 rounded-full bg-zinc-200 text-zinc-600 flex items-center justify-center text-xs font-medium shrink-0 mt-1">
                P
              </div>
            )}
            <div
              className={`max-w-[72%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-500 text-white rounded-tr-sm"
                  : "bg-zinc-100 text-zinc-800 rounded-tl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {send.isPending && (
          <div className="flex justify-start gap-2.5">
            <div className="w-7 h-7 rounded-full bg-zinc-200 text-zinc-600 flex items-center justify-center text-xs font-medium shrink-0 mt-1">
              P
            </div>
            <div className="bg-zinc-100 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-zinc-100 px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={send.isPending}
            className="flex-1 resize-none rounded-xl border border-zinc-200 px-3.5 py-2.5 text-sm text-zinc-800 placeholder:text-zinc-400 focus:outline-none focus:ring-1 focus:ring-indigo-500/20 max-h-32 overflow-y-auto disabled:opacity-50"
            style={{ minHeight: "42px" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || send.isPending}
            className="w-10 h-10 rounded-xl bg-indigo-500 text-white flex items-center justify-center hover:bg-indigo-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-xs text-zinc-400 mt-1.5 ml-0.5">Enter to send · Shift+Enter for new line</p>
      </div>

      {/* End interview confirm dialog */}
      {confirmEnd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6">
            <h3 className="text-base font-semibold text-zinc-900 mb-2">End the interview?</h3>
            <p className="text-sm text-zinc-500 mb-5">
              This will close the session and generate your research report.
              {messages.filter(m => m.role === "user").length < 3 && (
                <span className="block mt-2 text-amber-600">You've only asked {messages.filter(m => m.role === "user").length} question{messages.filter(m => m.role === "user").length !== 1 ? "s" : ""} — consider asking more for a richer report.</span>
              )}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmEnd(false)}
                className="flex-1 py-2.5 text-sm font-medium text-zinc-700 border border-zinc-200 rounded-xl hover:bg-zinc-50 transition-colors"
              >
                Keep going
              </button>
              <button
                onClick={() => { setConfirmEnd(false); end.mutate(); }}
                disabled={end.isPending}
                className="flex-1 py-2.5 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {end.isPending ? "Ending…" : "End & Generate Report"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
