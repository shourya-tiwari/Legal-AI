"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  GitCompareArrows,
  Plus,
  Trash2,
  Save,
  Palette,
  Keyboard,
  Database,
} from "lucide-react";
import { getOrgSettings, updateOrgSettings } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useDocuments } from "@/lib/stores/documents";
import { useChat } from "@/lib/stores/chat";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Kbd } from "@/components/ui/kbd";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { titleCase } from "@/lib/format";

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        title="Settings"
        description="Negotiation playbook, appearance, keyboard shortcuts, and local data."
      />
      <PageBody className="max-w-3xl">
        <Tabs defaultValue="negotiation">
          <TabsList>
            <TabsTrigger value="negotiation">
              <GitCompareArrows /> Playbook
            </TabsTrigger>
            <TabsTrigger value="appearance">
              <Palette /> Appearance
            </TabsTrigger>
            <TabsTrigger value="shortcuts">
              <Keyboard /> Shortcuts
            </TabsTrigger>
            <TabsTrigger value="data">
              <Database /> Local data
            </TabsTrigger>
          </TabsList>

          <TabsContent value="negotiation">
            <NegotiationPrefs />
          </TabsContent>
          <TabsContent value="appearance">
            <Appearance />
          </TabsContent>
          <TabsContent value="shortcuts">
            <Shortcuts />
          </TabsContent>
          <TabsContent value="data">
            <LocalData />
          </TabsContent>
        </Tabs>
      </PageBody>
    </>
  );
}

function NegotiationPrefs() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: qk.orgSettings,
    queryFn: getOrgSettings,
    retry: false,
  });
  const [clauseType, setClauseType] = React.useState("");
  const [language, setLanguage] = React.useState("");
  const [rationale, setRationale] = React.useState("");

  const prefs = (q.data?.negotiation_preferences ?? {}) as Record<
    string,
    { preferred_language: string; rationale?: string }
  >;

  const save = useMutation({
    mutationFn: (patch: Parameters<typeof updateOrgSettings>[0]) =>
      updateOrgSettings(patch),
    onSuccess: () => {
      toast.success("Playbook updated");
      qc.invalidateQueries({ queryKey: qk.orgSettings });
    },
    onError: (e) =>
      toast.error("Save failed", {
        description: String(e).includes("admin")
          ? "Requires an admin role."
          : String(e),
      }),
  });

  if (q.isLoading) return <Skeleton className="h-64 w-full" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Negotiation playbook</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="text-sm text-muted-foreground">
          Preferred language per clause type. The Negotiation agent flags{" "}
          <em>any</em> deviation (not a similarity threshold) and produces a
          redline — every suggestion stays pending review.
        </p>

        {Object.keys(prefs).length > 0 && (
          <ul className="space-y-3">
            {Object.entries(prefs).map(([type, p]) => (
              <li
                key={type}
                className="rounded-lg border border-border bg-surface p-3"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="primary">{titleCase(type)}</Badge>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => {
                      const next = { ...prefs };
                      delete next[type];
                      // send full replacement via merge of a cleared key is not
                      // supported; write an empty string to neutralise it
                      save.mutate({
                        negotiation_preferences: {
                          [type]: { preferred_language: "", rationale: "" },
                        },
                      });
                    }}
                    aria-label="Remove"
                  >
                    <Trash2 />
                  </Button>
                </div>
                <p className="mt-2 text-sm">{p.preferred_language}</p>
                {p.rationale && (
                  <p className="mt-1 text-xs text-subtle-foreground">
                    {p.rationale}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}

        <div className="space-y-3 rounded-lg border border-dashed border-border p-4">
          <p className="flex items-center gap-1.5 text-sm font-medium">
            <Plus className="size-4" /> Add a preference
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="ct">Clause type</Label>
            <Input
              id="ct"
              value={clauseType}
              onChange={(e) => setClauseType(e.target.value)}
              placeholder="e.g. governing_law, indemnification, termination"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pl">Preferred language</Label>
            <Textarea
              id="pl"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              rows={3}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ra">Rationale (optional)</Label>
            <Input
              id="ra"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
            />
          </div>
          <Button
            onClick={() => {
              save.mutate({
                negotiation_preferences: {
                  [clauseType.trim()]: {
                    preferred_language: language.trim(),
                    rationale: rationale.trim(),
                  },
                },
              });
              setClauseType("");
              setLanguage("");
              setRationale("");
            }}
            loading={save.isPending}
            disabled={!clauseType.trim() || !language.trim()}
          >
            <Save /> Add to playbook
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Appearance() {
  const { theme, setTheme } = useTheme();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5">
          <Label>Theme</Label>
          <div className="flex gap-2">
            {(["light", "dark", "system"] as const).map((t) => (
              <Button
                key={t}
                variant={theme === t ? "primary" : "outline"}
                size="sm"
                onClick={() => setTheme(t)}
                className="capitalize"
              >
                {t}
              </Button>
            ))}
          </div>
          <p className="text-xs text-subtle-foreground">
            The interface is designed dark-first; the light theme is fully
            supported. Motion respects{" "}
            <code>prefers-reduced-motion</code>.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

const SHORTCUTS: [string, string][] = [
  ["⌘ K  /  Ctrl K", "Open the command palette"],
  ["⌘ U", "Upload a document (from the palette)"],
  ["Enter", "Send a message / question"],
  ["Shift + Enter", "New line in a message"],
  ["Esc", "Close a dialog or the palette"],
];

function Shortcuts() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Keyboard shortcuts</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y divide-border">
          {SHORTCUTS.map(([keys, desc]) => (
            <li
              key={desc}
              className="flex items-center justify-between py-2.5 text-sm"
            >
              <span className="text-muted-foreground">{desc}</span>
              <Kbd className="h-6 px-2">{keys}</Kbd>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function LocalData() {
  const docs = useDocuments((s) => s.docs);
  const clearDocs = useDocuments((s) => s.clear);
  const conversations = useChat((s) => s.conversations);
  const clearChat = useChat((s) => s.clearAll);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Local data</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Because the backend has no document-list or conversation-history
          endpoint, your library and chats live in this browser&rsquo;s
          <code> localStorage</code>. Clearing them does not touch the backend.
        </p>
        <div className="flex items-center justify-between rounded-lg border border-border p-3">
          <div>
            <p className="text-sm font-medium">Document library</p>
            <p className="text-xs text-muted-foreground">
              {docs.length} document{docs.length === 1 ? "" : "s"}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              clearDocs();
              toast.success("Library cleared");
            }}
            disabled={docs.length === 0}
          >
            <Trash2 /> Clear
          </Button>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-border p-3">
          <div>
            <p className="text-sm font-medium">Assistant conversations</p>
            <p className="text-xs text-muted-foreground">
              {conversations.length} conversation
              {conversations.length === 1 ? "" : "s"}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              clearChat();
              toast.success("Conversations cleared");
            }}
            disabled={conversations.length === 0}
          >
            <Trash2 /> Clear
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
