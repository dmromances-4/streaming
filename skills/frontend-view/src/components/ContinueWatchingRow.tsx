import { Link } from "react-router-dom";
import { useContinueWatching } from "../hooks/useContinueWatching";

export function ContinueWatchingRow() {
  const { items, loading } = useContinueWatching();

  if (loading) return null;
  if (!items.length) return null;

  return (
    <section className="mb-8">
      <h2 className="mb-3 px-4 text-lg font-bold md:px-10 md:text-xl">
        Continuar viendo
      </h2>
      <div className="scrollbar-hide flex gap-3 overflow-x-auto px-4 pb-2 md:px-10">
        {items.map((item) => (
          <Link
            key={item.id}
            to={item.href}
            className="group relative w-[140px] shrink-0 md:w-[160px]"
          >
            <div className="aspect-[2/3] overflow-hidden rounded-md bg-stream-elevated">
              {item.poster_url ? (
                <img
                  src={item.poster_url}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center p-2 text-center text-xs text-stream-muted">
                  {item.title}
                </div>
              )}
              {item.progressPercent > 0 && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
                  <div
                    className="h-full bg-stream-accent"
                    style={{ width: `${item.progressPercent}%` }}
                  />
                </div>
              )}
            </div>
            <p className="mt-2 line-clamp-2 text-xs font-medium">{item.title}</p>
            {item.progressPercent > 0 && (
              <p className="text-[10px] text-stream-muted">
                {item.progressPercent}% visto
              </p>
            )}
          </Link>
        ))}
      </div>
    </section>
  );
}
