"use client";

import * as React from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import {
  Plus,
  Send,
  Sparkles,
  User,
  Trash2,
  Pencil,
  Download,
  Search,
  MessageSquare,
  FileText,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { askDocument } from "@/lib/api";
import { useChat, type ChatMessage } from "@/lib/stores/chat";
import { useDocuments } from "@/lib/stores/documents";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Markdown } from "@/components/shared/markdown";
import { CopyButton } from "@/components/shared/copy-button";
import { FaithfulnessBadge } from "@/components/shared/faithfulness-badge";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const rid = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

export default function AssistantPage() {
  const {
    conversations,
    activeId,
    create,
    setActive,
    remove,
    rename,
    addMessage,
    updateMessage,
    setDocument,
  } = useChat();
  const docs = useDocuments((s) => s.docs);

  const [input, setInput] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [sidebarOpen, setSidebarOpen] = React.useState(true);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  const active = conversations.find((c) => c.id === activeId) ?? null;

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active?.messages.length]);

  const ask = useMutation({
    mutationFn: ({ docId, question }: { docId: number; question: string }) =>
      askDocument(docId, question),
  });

  const send = async () => {
    const question = input.trim();
    if (!question || !active || active.documentId == null || ask.isPending)
      return;
    setInput("");
    const userMsg: ChatMessage = {
      id: rid(),
      role: "user",
      content: question,
      createdAt: new Date().toISOString(),
    };
    const assistantMsg: ChatMessage = {
      id: rid(),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
    };
    addMessage(active.id, userMsg);
    addMessage(active.id, assistantMsg);
    try {
      const res = await ask.mutateAsync({
        docId: active.documentId,
        question,
      });
      updateMessage(active.id, assistantMsg.id, {
        content: res.answer,
        faithful: res.faithful,
        faithfulnessMethod: res.faithfulness_method,
        unsupportedClaims: res.unsupported_claims ?? [],
      });
    } catch (e) {
      updateMessage(active.id, assistantMsg.id, { error: String(e) });
    }
  };

  const exportConversation = () => {
    if (!active) return;
    const md =
      `# ${active.title}\n\n` +
      `Document: ${active.documentName ?? "—"}\n\n` +
      active.messages
        .map(
          (m) =>
            `**${m.role === "user" ? "You" : "Assistant"}:**\n\n${
              m.content || m.error || ""
            }`,
        )
        .join("\n\n---\n\n");
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement("a");
    a.href = url;
    a.download = `${active.title.slice(0, 40)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filtered = conversations.filter(
    (c) =>
      !search ||
      c.title.toLowerCase().includes(search.toLowerCase()) ||
      c.messages.some((m) =>
        m.content.toLowerCase().includes(search.toLowerCase()),
      ),
  );

  return (
    <div className="flex h-[calc(100dvh-3.5rem)]">
      {/* Conversation list */}
      <aside
        className={cn(
          "flex shrink-0 flex-col border-r border-border bg-surface transition-[width]",
          sidebarOpen ? "w-72" : "w-0 overflow-hidden",
        )}
      >
        <div className="flex items-center gap-2 border-b border-border p-3">
          <Button
            size="sm"
            className="flex-1"
            onClick={() => create(docs[0]?.id ?? null, docs[0]?.filename ?? null)}
          >
            <Plus /> New chat
          </Button>
        </div>
        <div className="border-b border-border p-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-subtle-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats…"
              className="h-8 pl-8 text-xs"
            />
          </div>
        </div>
        <div className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-subtle-foreground">
              {conversations.length === 0 ? "No conversations yet" : "No matches"}
            </p>
          ) : (
            filtered.map((c) => (
              <button
                key={c.id}
                onClick={() => setActive(c.id)}
                className={cn(
                  "group flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                  c.id === activeId
                    ? "bg-primary-muted text-primary"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                <MessageSquare className="size-3.5 shrink-0" />
                <span className="flex-1 truncate">{c.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    remove(c.id);
                  }}
                  className="opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
                  aria-label="Delete conversation"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Thread */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center gap-2 border-b border-border px-4">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="Toggle conversation list"
          >
            {sidebarOpen ? <PanelLeftClose /> : <PanelLeftOpen />}
          </Button>
          {active && (
            <>
              <button
                className="truncate text-sm font-medium hover:text-primary"
                onClick={() => {
                  const t = window.prompt("Rename conversation", active.title);
                  if (t?.trim()) rename(active.id, t.trim());
                }}
              >
                {active.title}
                <Pencil className="ml-1.5 inline size-3 text-subtle-foreground" />
              </button>
              <div className="ml-auto flex items-center gap-1.5">
                <Select
                  value={active.documentId?.toString() ?? ""}
                  onValueChange={(v) => {
                    const d = docs.find((x) => x.id === Number(v));
                    setDocument(active.id, Number(v), d?.filename ?? null);
                  }}
                >
                  <SelectTrigger className="h-8 w-48 text-xs">
                    <SelectValue placeholder="Select a document…" />
                  </SelectTrigger>
                  <SelectContent>
                    {docs.map((d) => (
                      <SelectItem key={d.id} value={d.id.toString()}>
                        {d.filename}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={exportConversation}
                  aria-label="Export"
                >
                  <Download />
                </Button>
              </div>
            </>
          )}
        </header>

        {!active ? (
          <div className="flex flex-1 items-center justify-center p-6">
            {docs.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="Upload a contract first"
                description="The assistant answers questions grounded in a specific document."
                action={
                  <Button asChild>
                    <Link href="/documents/upload">Upload a document</Link>
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={Sparkles}
                title="Start a conversation"
                description="Ask grounded questions about any contract in your library."
                action={
                  <Button
                    onClick={() =>
                      create(docs[0].id, docs[0].filename)
                    }
                  >
                    <Plus /> New chat
                  </Button>
                }
              />
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="mx-auto max-w-3xl space-y-6 p-4 sm:p-6">
                {active.documentId == null && (
                  <EmptyState
                    icon={FileText}
                    title="Pick a document"
                    description="Select which contract to ground answers in, using the selector above."
                  />
                )}
                {active.messages.length === 0 && active.documentId != null && (
                  <div className="flex flex-wrap gap-2 pt-4">
                    {[
                      "Summarise the key risks in this contract",
                      "What are the termination conditions?",
                      "Explain the indemnification clause",
                      "What deadlines do I need to track?",
                    ].map((s) => (
                      <button
                        key={s}
                        onClick={() => {
                          setInput(s);
                        }}
                        className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
                {active.messages.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      "flex gap-3",
                      m.role === "user" && "flex-row-reverse",
                    )}
                  >
                    <div
                      className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-full",
                        m.role === "user"
                          ? "bg-muted text-muted-foreground"
                          : "bg-primary-muted text-primary",
                      )}
                    >
                      {m.role === "user" ? (
                        <User className="size-3.5" />
                      ) : (
                        <Sparkles className="size-3.5" />
                      )}
                    </div>
                    <div
                      className={cn(
                        "min-w-0 max-w-[85%]",
                        m.role === "user" && "flex flex-col items-end",
                      )}
                    >
                      {m.role === "user" ? (
                        <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                          {m.content}
                        </div>
                      ) : m.error ? (
                        <p className="rounded-2xl rounded-tl-sm border border-danger/30 bg-danger/10 px-4 py-2.5 text-sm text-danger">
                          {m.error}
                        </p>
                      ) : m.content ? (
                        <div className="space-y-2">
                          <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3">
                            <Markdown>{m.content}</Markdown>
                          </div>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {m.faithful != null && (
                              <FaithfulnessBadge
                                ok={m.faithful}
                                method={m.faithfulnessMethod}
                                unsupportedCount={m.unsupportedClaims?.length ?? 0}
                              />
                            )}
                            <CopyButton value={m.content} />
                          </div>
                          {(m.unsupportedClaims?.length ?? 0) > 0 && (
                            <div className="rounded-lg border border-warning/30 bg-warning/10 p-2.5 text-xs text-muted-foreground">
                              <p className="mb-1 font-medium text-warning">
                                Not fully grounded in the text:
                              </p>
                              {m.unsupportedClaims!.map((c, i) => (
                                <p key={i}>• {c}</p>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-2.5 text-sm text-muted-foreground">
                          <Spinner /> Reading {active.documentName}…
                        </span>
                      )}
                      {m.role === "assistant" && (
                        <p className="mt-1 text-[10px] text-subtle-foreground">
                          {relativeTime(m.createdAt)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
            </div>

            <div className="border-t border-border p-3 sm:p-4">
              <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-border bg-surface p-2">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  placeholder={
                    active.documentId == null
                      ? "Select a document first…"
                      : `Ask about ${active.documentName}…`
                  }
                  disabled={active.documentId == null}
                  rows={1}
                  className="max-h-40 min-h-8 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
                />
                <Button
                  size="icon"
                  onClick={send}
                  disabled={
                    !input.trim() ||
                    ask.isPending ||
                    active.documentId == null
                  }
                  aria-label="Send"
                >
                  <Send />
                </Button>
              </div>
              <p className="mx-auto mt-1.5 max-w-3xl text-center text-[10px] text-subtle-foreground">
                Answers are grounded in the selected document and
                entailment-checked. Conversations are stored only in this
                browser.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
