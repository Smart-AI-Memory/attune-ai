import { METRICS } from '@/lib/features';

interface TestsBadgeProps {
  tests?: string;
  coverage?: number;
}

// Defaults come from lib/features METRICS — the README badge's
// CI-guarded round floor and the enforced coverage floor. Never
// hard-code a raw collected-test count here; it goes stale.
export default function TestsBadge({
  tests = METRICS.testsFloor,
  coverage = METRICS.coverageFloorPct,
}: TestsBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-[#10B981] text-white">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
      <span>
        {tests} tests | {coverage}% coverage
      </span>
    </span>
  );
}
