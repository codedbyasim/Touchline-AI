import { useEffect, useState } from "react";
import type { Player } from "./api";

interface Props {
  minute: number;
  players: Player[];
  spotlight: string;
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export default function Pitch({ minute, players, spotlight }: Props) {
  const [t, setT] = useState(1);

  useEffect(() => {
    let frame = 0;
    const start = performance.now();
    const duration = 1500;
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      setT(1 - Math.pow(1 - p, 3));
      if (p < 1) frame = requestAnimationFrame(step);
    };
    setT(0);
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [minute]);

  return (
    <svg viewBox="0 0 120 80" className="h-full w-full" role="img" aria-label="Pitch">
      <defs>
        <pattern id="mow" width="10" height="80" patternUnits="userSpaceOnUse">
          <rect width="10" height="80" fill="#0c3b28" />
          <rect width="5" height="80" fill="#0e4430" />
        </pattern>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="0.6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="120" height="80" fill="url(#mow)" />
      <rect x="0" y="0" width="40" height="80" fill="rgba(255,51,85,0.05)" />
      <rect x="80" y="0" width="40" height="80" fill="rgba(61,139,253,0.05)" />
      <rect
        x="54"
        y="32"
        width="28"
        height="24"
        fill={minute === 54 ? "rgba(232,197,71,0.16)" : "rgba(232,197,71,0.05)"}
        stroke="rgba(232,197,71,0.7)"
        strokeDasharray="1.2 0.8"
        strokeWidth="0.25"
      />
      {minute === 67 && <rect x="0" y="0" width="36" height="20" fill="rgba(255,90,106,0.16)" />}
      <g fill="none" stroke="rgba(236,253,245,0.78)" strokeWidth="0.28">
        <rect x="1" y="1" width="118" height="78" />
        <line x1="60" y1="1" x2="60" y2="79" />
        <circle cx="60" cy="40" r="9.15" />
        <circle cx="60" cy="40" r="0.4" fill="rgba(236,253,245,0.78)" />
        <rect x="1" y="19.84" width="16.5" height="40.32" />
        <rect x="102.5" y="19.84" width="16.5" height="40.32" />
        <rect x="1" y="30.84" width="5.5" height="18.32" />
        <rect x="113.5" y="30.84" width="5.5" height="18.32" />
        <rect x="0" y="36" width="1.2" height="8" fill="rgba(236,253,245,0.78)" />
        <rect x="118.8" y="36" width="1.2" height="8" fill="rgba(236,253,245,0.78)" />
      </g>
      {players.map((player) => {
        const shift = player.shift_m ?? 0;
        const ghost = shift >= 15;
        const x = lerp(player.baseline_xy[0], player.active_xy[0], ghost ? t : 1);
        const y = lerp(player.baseline_xy[1], player.active_xy[1], ghost ? t : 1);
        const fill = player.team_id === "NLR" ? "#ff3355" : "#3d8bfd";
        const hot = spotlight === player.player_id;
        return (
          <g key={player.player_id} filter={hot ? "url(#glow)" : undefined}>
            {ghost && (
              <g>
                <line
                  x1={player.baseline_xy[0]}
                  y1={player.baseline_xy[1]}
                  x2={x}
                  y2={y}
                  stroke={fill}
                  strokeWidth="0.35"
                  strokeDasharray="0.8 0.6"
                  opacity="0.85"
                />
                <circle
                  cx={player.baseline_xy[0]}
                  cy={player.baseline_xy[1]}
                  r="2.05"
                  fill="none"
                  stroke={fill}
                  strokeWidth="0.35"
                  strokeDasharray="0.7 0.55"
                  opacity="0.8"
                />
              </g>
            )}
            {hot && <circle cx={x} cy={y} r="3.3" fill="none" stroke="#e8c547" strokeWidth="0.45" />}
            <circle cx={x} cy={y} r="2.05" fill={fill} stroke="#f8fafc" strokeWidth="0.22" />
            <text
              x={x}
              y={y + 0.7}
              textAnchor="middle"
              fontSize="2.1"
              fontFamily="Oswald, sans-serif"
              fill="#ffffff"
            >
              {player.shirt_number}
            </text>
            <title>{`${player.player_name} #${player.shirt_number}`}</title>
          </g>
        );
      })}
    </svg>
  );
}
