import { Link } from "react-router-dom";
import type { CatalogItem } from "../api/types";

interface TitleCardProps {
  item: CatalogItem;
  className?: string;
}

export function TitleCard({ item, className = "w-[140px] md:w-[160px]" }: TitleCardProps) {
  return (
    <Link
      to={`/title/${item.id}`}
      className={`group relative block shrink-0 snap-start ${className}`}
    >
      <div className="aspect-[2/3] overflow-hidden rounded-md bg-stream-elevated shadow-lg transition duration-300 group-hover:scale-105 group-hover:ring-2 group-hover:ring-white/30">
        {item.poster_url ? (
          <img
            src={item.poster_url}
            alt={item.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center p-3 text-center text-xs text-stream-muted">
            {item.title}
          </div>
        )}
        <div className="absolute inset-0 flex items-end bg-gradient-to-t from-black/80 via-transparent to-transparent p-3 opacity-0 transition group-hover:opacity-100">
          <span className="text-sm font-semibold leading-tight">{item.title}</span>
        </div>
      </div>
      {item.pipeline_status === "ready" && (
        <span className="absolute right-2 top-2 rounded bg-emerald-500/90 px-1.5 py-0.5 text-[10px] font-bold uppercase text-black">
          Listo
        </span>
      )}
      {item.tags.includes("cocteleria") && (
        <span className="absolute left-2 top-2 rounded bg-amber-500/90 px-1.5 py-0.5 text-[10px] font-bold uppercase text-black">
          Cóctel
        </span>
      )}
    </Link>
  );
}
