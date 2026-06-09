import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Send, Bot, User as UserIcon, Sparkles } from "lucide-react";

interface Msg {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

const SUGGESTIONS = [
  "Generate attendance summary for this month",
  "Check PM POSHAN stock status",
  "Verify audit readiness",
  "Show attendance anomalies",
];

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.chat.history().then((rows) => {
      setMessages(rows.map((r) => ({ role: r.role, content: r.content, agent: r.agent })));
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: message }]);
    setLoading(true);
    try {
      const res = await api.chat.send(message);
      setMessages((m) => [...m, { role: "assistant", content: res.reply, agent: res.agent }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}`, agent: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b bg-white px-8 py-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h1 className="text-xl font-semibold">Ask ShikshaSetu AI</h1>
        </div>
        <p className="text-sm text-muted-foreground">Powered by Gemini · routed through Supervisor + specialist agents</p>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto text-center py-12">
            <Bot className="h-12 w-12 mx-auto text-primary mb-3" />
            <h2 className="text-lg font-medium">How can I help you today?</h2>
            <p className="text-sm text-muted-foreground mb-6">Ask about attendance, PM POSHAN, audit, or anything administrative.</p>
            <div className="grid gap-2 max-w-md mx-auto">
              {SUGGESTIONS.map((s) => (
                <Button key={s} variant="outline" className="justify-start text-left h-auto py-3" onClick={() => send(s)}>
                  {s}
                </Button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            {m.role === "assistant" && (
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Bot className="h-4 w-4 text-primary" />
              </div>
            )}
            <Card className={`max-w-2xl p-4 ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-white"}`}>
              {m.role === "assistant" && m.agent && (
                <Badge variant="outline" className="mb-2 text-xs">{m.agent}</Badge>
              )}
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</div>
            </Card>
            {m.role === "user" && (
              <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                <UserIcon className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-primary animate-pulse" />
            </div>
            <Card className="p-4 bg-white"><div className="text-sm text-muted-foreground">Thinking…</div></Card>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t bg-white px-8 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex gap-2 max-w-3xl mx-auto"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about attendance, PM POSHAN, audit…"
            disabled={loading}
          />
          <Button type="submit" disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
