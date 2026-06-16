import { Link } from "react-router-dom";
import type { CatalogItem } from "../api/types";
import { TitleCard } from "./TitleCard";

interface ContentRowProps {
  title: string;
  items: CatalogItem[];
  browseLink?: string;
}

export function ContentRow({ title, items, browseLink }: ContentRowProps) {
  if (!items.length) return null;

  return (
    <section className="mb-8">
      <div className="mb-3 flex items-center justify-between px-4 md:px-10">
        <h2 className="text-lg font-bold md:text-xl">{title}</h2>
        {browseLink && (
          <Link
            to={browseLink}
            className="text-sm text-stream-muted transition hover:text-white"
          >
            Ver todo
          </Link>
        )}
      </div>
      <div className="scrollbar-hide flex gap-3 overflow-x-auto px-4 pb-2 snap-x snap-mandatory md:px-10">
        {items.map((item) => (
          <TitleCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}
