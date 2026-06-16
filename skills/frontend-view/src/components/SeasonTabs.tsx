import type { SeasonSummary } from "../api/types";

interface SeasonTabsProps {
  seasons: SeasonSummary[];
  active: number;
  onChange: (season: number) => void;
}

export function SeasonTabs({ seasons, active, onChange }: SeasonTabsProps) {
  if (!seasons.length) return null;

  return (
    <div className="scrollbar-hide flex gap-2 overflow-x-auto border-b border-stream-border pb-1">
      {seasons.map((s) => (
        <button
          key={s.season_number}
          type="button"
          onClick={() => onChange(s.season_number)}
          className={`shrink-0 rounded-t px-4 py-2 text-sm font-semibold transition ${
            active === s.season_number
              ? "border-b-2 border-stream-accent text-white"
              : "text-stream-muted hover:text-white"
          }`}
        >
          Temporada {s.season_number}
          <span className="ml-1 text-xs font-normal text-stream-muted">
            ({s.ready_count}/{s.episode_count})
          </span>
        </button>
      ))}
    </div>
  );
}
