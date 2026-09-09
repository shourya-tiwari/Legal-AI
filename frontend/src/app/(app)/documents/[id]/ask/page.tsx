"use client";

import * as React from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { Send, Sparkles, User, ArrowUpRight } from "lucide-react";
import { askDocument, type AskResponse } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { FaithfulnessBadge } from "@/components/shared/faithfulness-badge";
import { CopyButton } from "@/components/shared/copy-button";

const SUGGESTED = [
  "How can this agreement be terminated?",
  "What are my payment obligations and deadlines?",
  "Is there an indemnification clause, and how broad is it?",
  "What happens if I breach the contract?",
  "Which jurisdiction's law governs this contract?",
];

interface Turn {
  q: string;
  a?: AskResponse;
  error?: string;
}

export default function AskPage() {
  const { id, document } = useWorkspace();
  const [input, setInput] = React.useState("");
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: (question: string) => askDocument(id, question),
    onMutate: (question) => {
      setTurns((t) => [...t, { q: question }]);
      setInput("");
    },
    onSuccess: (a) =>
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x))),
    onError: (e) =>
      setTurns((t) =>
        t.map((x, i) =>
          i === t.length - 1 ? { ...x, error: String(e) } : x,
        ),
      ),
  });

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const submit = () => {
    const q = input.trim();
    if (q && !ask.isPending) ask.mutate(q);
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      {turns.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="Ask this contract anything"
          description="Answers are grounded in the document text and checked by an NLI entailment head — unsupported claims are surfaced."
          action={
            <div className="mt-2 flex flex-wrap justify-center gap-2">
              {SUGGESTED.slice(0, 3).map((s) => (
                <Button
                  key={s}
                  variant="secondary"
                  size="sm"
                  onClick={() => ask.mutate(s)}
                >
                  {s}
                </Button>
              ))}
            </div>
          }
        />
      ) : (
        <div className="space-y-5">
          {turns.map((turn, i) => (
            <div key={i} className="space-y-3">
              <div className="flex justify-end">
                <div className="flex max-w-[85%] items-start gap-2.5">
                  <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                    {turn.q}
                  </div>
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    <User className="size-3.5" />
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary-muted text-primary">
                  <Sparkles className="size-3.5" />
                </div>
                <Card className="flex-1">
                  <CardContent className="space-y-2.5 pt-5">
                    {turn.error ? (
                      <p className="text-sm text-danger">{turn.error}</p>
                    ) : turn.a ? (
                      <>
                        <p className="whitespace-pre-wrap text-sm">
                          {turn.a.answer}
                        </p>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <FaithfulnessBadge
                            ok={turn.a.faithful}
                            method={turn.a.faithfulness_method}
                            unsupportedCount={
                              (turn.a.unsupported_claims ?? []).length
                            }
                          />
                          <CopyButton value={turn.a.answer} />
                        </div>
                        {(turn.a.unsupported_claims ?? []).length > 0 && (
                          <div className="rounded-lg border border-warning/30 bg-warning/10 p-2.5 text-xs text-muted-foreground">
                            <p className="mb-1 font-medium text-warning">
                              Not fully supported by the text:
                            </p>
                            {(turn.a.unsupported_claims ?? []).map((c, j) => (
                              <p key={j}>• {c}</p>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Spinner /> Reading the contract…
                      </span>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      <div className="sticky bottom-0 -mx-4 border-t border-border bg-background/90 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-xl sm:border">
        <div className="flex items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={`Ask about ${document.data?.filename ?? "this contract"}…`}
            rows={1}
            className="max-h-32 min-h-9 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
          />
          <Button
            size="icon"
            onClick={submit}
            disabled={!input.trim() || ask.isPending}
            aria-label="Send"
          >
            <Send />
          </Button>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <div className="flex gap-1.5 overflow-x-auto">
            {SUGGESTED.map((s) => (
              <button
                key={s}
                onClick={() => ask.mutate(s)}
                disabled={ask.isPending}
                className="shrink-0 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
          <Button variant="ghost" size="sm" asChild className="shrink-0">
            <Link href="/assistant">
              Full assistant <ArrowUpRight />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
