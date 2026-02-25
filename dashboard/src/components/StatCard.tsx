import { useId } from "react";

interface StatCardProps {
  label: string;
  value: string;
  subtitle: string;
  color: string;
  trend: number[];
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const gradientId = useId();
  if (data.length < 2) return null;

  const h = 50;
  const w = 100;
  const pad = 2;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const coords = data.map((v, i) => ({
    x: pad + (i / (data.length - 1)) * (w - pad * 2),
    y: pad + (1 - (v - min) / range) * (h - pad * 2),
  }));

  const linePoints = coords.map((c) => `${c.x},${c.y}`).join(" ");

  const areaPoints = [
    `${coords[0].x},${h}`,
    ...coords.map((c) => `${c.x},${c.y}`),
    `${coords[coords.length - 1].x},${h}`,
  ].join(" ");

  return (
    <svg width={w} height={h} className="sparkline">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.4" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#${gradientId})`} points={areaPoints} />
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={linePoints}
      />
    </svg>
  );
}

export default function StatCard({ label, value, subtitle, color, trend }: StatCardProps) {
  return (
    <div
      className="stat-card"
      style={{
        background: `linear-gradient(135deg, ${color}12 0%, ${color}06 50%, #141c2e 100%)`,
        borderColor: `${color}25`,
      }}
    >
      <div className="stat-label">{label}</div>
      <div className="stat-body">
        <div>
          <div className="stat-value" style={{ color }}>{value}</div>
          <div className="stat-subtitle">{subtitle}</div>
        </div>
        <Sparkline data={trend} color={color} />
      </div>
    </div>
  );
}
