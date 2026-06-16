interface LiveChannelSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function LiveChannelSearch({ value, onChange }: LiveChannelSearchProps) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Buscar canal o país…"
      className="w-full rounded-lg border border-stream-border bg-stream-surface px-4 py-2.5 text-sm outline-none focus:border-stream-accent md:max-w-sm"
    />
  );
}
