import { useEffect, useState } from "react";
import { Clock } from "lucide-react";

function formatMs(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface PipelineTimerProps {
  /** When the current step started (Date.now()). */
  startedAt: number;
  /** Estimated duration for this step in seconds. */
  estimatedSeconds: number;
  /** Current step label (e.g. "Plan"). */
  stepLabel: string;
}

export default function PipelineTimer({
  startedAt,
  estimatedSeconds,
  stepLabel,
}: PipelineTimerProps) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const elapsedMs = now - startedAt;
  const estimatedMs = estimatedSeconds * 1000;
  const remainingMs = estimatedMs - elapsedMs;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-4 rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-3 font-mono text-sm">
      <span className="flex items-center gap-2 text-gray-400">
        <Clock className="h-4 w-4" />
        {stepLabel}
      </span>
      <span className="text-gray-600">Polling for result…</span>
      <span className="text-gray-500">
        Elapsed: <span className="text-gray-300">{formatMs(elapsedMs)}</span>
      </span>
      <span className="text-gray-500">
        Est.: <span className="text-gray-400">{formatMs(estimatedMs)}</span>
      </span>
      <span className="text-gray-500">
        {remainingMs > 0 ? (
          <>
            Remaining:{" "}
            <span className="font-semibold text-accent-cyan">
              {formatMs(remainingMs)}
            </span>
          </>
        ) : (
          <span className="text-amber-400/90">
            Over estimate ({formatMs(elapsedMs)})
          </span>
        )}
      </span>
    </div>
  );
}
