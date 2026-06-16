export function CardSkeleton() {
  return (
    <div className="aspect-[2/3] w-[140px] shrink-0 animate-pulse rounded-md bg-stream-elevated md:w-[160px]" />
  );
}

export function RowSkeleton() {
  return (
    <div className="space-y-3 px-4 md:px-10">
      <div className="h-6 w-48 animate-pulse rounded bg-stream-elevated" />
      <div className="flex gap-3 overflow-hidden">
        {Array.from({ length: 8 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

export function HeroSkeleton() {
  return (
    <div className="h-[55vh] min-h-[360px] animate-pulse bg-stream-elevated md:h-[70vh]" />
  );
}

export function LiveGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className="flex flex-col items-center gap-3 rounded-xl border border-stream-border bg-stream-surface p-4 animate-pulse"
        >
          <div className="h-12 w-12 rounded-lg bg-stream-elevated" />
          <div className="h-4 w-20 rounded bg-stream-elevated" />
        </div>
      ))}
    </div>
  );
}

export function EpisodeSkeleton() {
  return (
    <div className="flex gap-4 rounded-lg bg-stream-surface/60 p-4 animate-pulse">
      <div className="h-12 w-12 rounded bg-stream-elevated" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-1/3 rounded bg-stream-elevated" />
        <div className="h-3 w-full rounded bg-stream-elevated" />
      </div>
    </div>
  );
}
