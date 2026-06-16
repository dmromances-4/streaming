import type { LiveCountry } from "../api/types";

interface LiveCountryFilterProps {
  countries: LiveCountry[];
  selected: string;
  onSelect: (code: string) => void;
}

export function LiveCountryFilter({
  countries,
  selected,
  onSelect,
}: LiveCountryFilterProps) {
  return (
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
        Todos
      </button>
      {countries.map((c) => (
        <button
          key={c.code}
          type="button"
          onClick={() => onSelect(c.code)}
          className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition ${
            selected === c.code
              ? "bg-stream-accent text-white"
              : "bg-stream-elevated text-white/80 hover:bg-stream-border"
          }`}
        >
          {c.name}
          <span className="ml-1.5 text-xs opacity-70">{c.count}</span>
        </button>
      ))}
    </div>
  );
}
