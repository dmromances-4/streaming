interface LiveRegionFilterProps {
  regions: string[];
  selected: string;
  onSelect: (region: string) => void;
}

export function LiveRegionFilter({
  regions,
  selected,
  onSelect,
}: LiveRegionFilterProps) {
  if (regions.length === 0) return null;

  return (
    <div className="mb-6">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stream-muted">
        Comunidades autónomas
      </p>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
        <button
          type="button"
          onClick={() => onSelect("")}
          className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition ${
            selected === ""
              ? "bg-stream-accent text-white"
              : "bg-stream-elevated text-white/80 hover:bg-stream-border"
          }`}
        >
          Todas
        </button>
        <button
          type="button"
          onClick={() => onSelect("__nacional__")}
          className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition ${
            selected === "__nacional__"
              ? "bg-stream-accent text-white"
              : "bg-stream-elevated text-white/80 hover:bg-stream-border"
          }`}
        >
          Nacional RTVE
        </button>
        <button
          type="button"
          onClick={() => onSelect("__autonomic__")}
          className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition ${
            selected === "__autonomic__"
              ? "bg-stream-accent text-white"
              : "bg-stream-elevated text-white/80 hover:bg-stream-border"
          }`}
        >
          Autonómicas
        </button>
        {regions.map((region) => (
          <button
            key={region}
            type="button"
            onClick={() => onSelect(region)}
            className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition ${
              selected === region
                ? "bg-stream-accent text-white"
                : "bg-stream-elevated text-white/80 hover:bg-stream-border"
            }`}
          >
            {region}
          </button>
        ))}
      </div>
    </div>
  );
}
