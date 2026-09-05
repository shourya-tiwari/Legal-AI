export interface Block {
  id: string | number;
  text: string;
  type?: string;
  page?: number;
}

export function ClauseList({
  blocks,
  selectedId,
  onSelect,
}: {
  blocks: Block[];
  selectedId: string | number | null;
  onSelect: (id: string | number) => void;
}) {
  if (blocks.length === 0) {
    return <p className="text-sm text-zinc-500">No clauses extracted.</p>;
  }

  return (
    <ul className="flex flex-col gap-1" role="listbox" aria-label="Extracted clauses">
      {blocks.map((block) => {
        const active = String(block.id) === String(selectedId);
        return (
          <li key={block.id}>
            <button
              type="button"
              role="option"
              aria-selected={active}
              onClick={() => onSelect(block.id)}
              className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                active
                  ? "border-indigo-400/50 bg-indigo-500/10 text-indigo-200"
                  : "border-white/10 bg-white/[0.02] text-zinc-300 hover:bg-white/[0.06]"
              }`}
            >
              {block.type && (
                <span className="mr-2 rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-zinc-400">
                  {block.type}
                </span>
              )}
              <span className="line-clamp-2">{block.text}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
