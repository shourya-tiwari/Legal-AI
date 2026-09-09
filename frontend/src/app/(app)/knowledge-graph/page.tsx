"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Search, Network, GitCompareArrows, Clock } from "lucide-react";
import { queryKgTerm, queryKgConflicts } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ListSkeleton } from "@/components/shared/loaders";

export default function KnowledgeGraphPage() {
  const [term, setTerm] = React.useState("");
  const [submitted, setSubmitted] = React.useState("");
  const [asOf, setAsOf] = React.useState("");

  const usage = useQuery({
    queryKey: qk.kgQuery(submitted, asOf || undefined),
    queryFn: () => queryKgTerm(submitted, asOf || undefined),
    enabled: !!submitted,
  });
  const conflicts = useQuery({
    queryKey: qk.kgConflicts(submitted),
    queryFn: () => queryKgConflicts(submitted),
    enabled: !!submitted,
  });

  const clauses = (usage.data?.clauses ?? []) as Record<string, unknown>[];
  const conflictRows = (conflicts.data?.conflicts ?? []) as Record<
    string,
    unknown
  >[];

  return (
    <>
      <PageHeader
        title="Knowledge Graph"
        description="Portfolio-wide term explorer. Search a defined term to see every clause across every ingested document that uses it — including documents where the term was automatically linked as the same underlying entity."
      />
      <PageBody className="space-y-6">
        <Card>
          <CardContent className="pt-5">
            <form
              className="flex flex-col gap-3 sm:flex-row sm:items-end"
              onSubmit={(e) => {
                e.preventDefault();
                setSubmitted(term.trim());
              }}
            >
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="term">Defined term</Label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle-foreground" />
                  <Input
                    id="term"
                    value={term}
                    onChange={(e) => setTerm(e.target.value)}
                    placeholder='e.g. "Tenant", "the Company", "Confidential Information"'
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="asof" className="flex items-center gap-1.5">
                  <Clock className="size-3.5" /> As of
                </Label>
                <Input
                  id="asof"
                  type="date"
                  value={asOf}
                  onChange={(e) => setAsOf(e.target.value)}
                  className="w-40"
                />
              </div>
              <Button type="submit" disabled={!term.trim()}>
                Search
              </Button>
            </form>
          </CardContent>
        </Card>

        {!submitted ? (
          <EmptyState
            icon={Network}
            title="Search a term"
            description="The graph is populated by ingesting documents from the workspace. Bitemporal versioning lets you query it as of any point in time."
          />
        ) : (
          <Tabs defaultValue="usage">
            <TabsList>
              <TabsTrigger value="usage">
                <Network /> Usage ({clauses.length})
              </TabsTrigger>
              <TabsTrigger value="conflicts">
                <GitCompareArrows /> Conflicts ({conflictRows.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="usage">
              {usage.isLoading ? (
                <ListSkeleton />
              ) : usage.isError ? (
                <ErrorState
                  error={usage.error}
                  title="Query failed — is the knowledge graph online?"
                  onRetry={() => usage.refetch()}
                />
              ) : clauses.length === 0 ? (
                <EmptyState
                  icon={Search}
                  title={`No clauses use "${submitted}"`}
                  description={
                    asOf
                      ? `Nothing as of ${asOf}. Try clearing the date, or ingest more documents.`
                      : "Either the term isn't defined anywhere, or no documents have been ingested."
                  }
                />
              ) : (
                <div className="space-y-3">
                  {clauses.map((c, i) => (
                    <Card key={i}>
                      <CardContent className="pt-4">
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <Badge variant="primary">{submitted}</Badge>
                          {typeof c.document_id !== "undefined" && (
                            <Link
                              href={`/documents/${c.document_id}`}
                              className="text-xs text-primary hover:underline"
                            >
                              doc {String(c.document_id)}
                            </Link>
                          )}
                          {typeof c.clause_id !== "undefined" && (
                            <span className="font-mono text-xs text-subtle-foreground">
                              clause {String(c.clause_id)}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {String(
                            c.content ?? c.text ?? c.clause_text ?? "—",
                          )}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="conflicts">
              {conflicts.isLoading ? (
                <ListSkeleton />
              ) : conflicts.isError ? (
                <ErrorState
                  error={conflicts.error}
                  onRetry={() => conflicts.refetch()}
                />
              ) : conflictRows.length === 0 ? (
                <EmptyState
                  icon={GitCompareArrows}
                  title="No candidate conflicts"
                  description={`No document pairs use "${submitted}" as both an obligation and a prohibition. Candidate conflicts are for review, not confirmed — actor/action aren't resolved.`}
                />
              ) : (
                <div className="space-y-3">
                  {conflictRows.map((c, i) => (
                    <Card
                      key={i}
                      className="border-danger/30 bg-danger/[0.04]"
                    >
                      <CardHeader>
                        <CardTitle className="text-danger">
                          Candidate conflict on “{submitted}”
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="grid gap-3 text-sm md:grid-cols-2">
                        <div>
                          <Badge variant="danger">obligation</Badge>
                          <p className="mt-1 text-muted-foreground">
                            {String(
                              c.obligation_clause ??
                                c.obligation ??
                                c.obligation_text ??
                                "—",
                            )}
                          </p>
                        </div>
                        <div>
                          <Badge variant="warning">prohibition</Badge>
                          <p className="mt-1 text-muted-foreground">
                            {String(
                              c.prohibition_clause ??
                                c.prohibition ??
                                c.prohibition_text ??
                                "—",
                            )}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}
      </PageBody>
    </>
  );
}
