import { Copy, Pause, Play, Radio } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  analyze,
  cachedInsight,
  diagnose,
  fetchAuto,
  fetchRecap,
  fetchTelemetry,
  overlayDocument,
  positionsFor,
  quietView,
  type Ask,
  type AutoEvent,
  type Insight,
  type Player,
  type Recap,
} from "./api";
import Pitch from "./Pitch";
import { BOOKMARKS, chrome, SPOTLIGHTS, type Club, type Lang, type Persona } from "./i18n";

const EMPTY_ASK: Ask = {
  minute: 54,
  persona: "CASUAL_FAN",
  language: "en",
  favorite_club: "NLR",
  spotlight_player_id: "",
};

function clock(minute: number) {
  return `${String(minute).padStart(2, "0")}:00`;
}

function modeLabel(insight: Insight, text: (typeof chrome)["en"]) {
  if (insight.mode === "semantic_kernel" && insight.served_from === "api") return text.liveModel;
  if (insight.served_from === "precomputed_cache") return text.cache;
  return text.fallback;
}

export default function App() {
  const [minute, setMinute] = useState(54);
  const [persona, setPersona] = useState<Persona>("CASUAL_FAN");
  const [language, setLanguage] = useState<Lang>("en");
  const [club, setClub] = useState<Club>("NLR");
  const [spotlight, setSpotlight] = useState("");
  const [question, setQuestion] = useState("");
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<1 | 10>(1);
  const [busy, setBusy] = useState(false);
  const [insight, setInsight] = useState<Insight>(() => cachedInsight(EMPTY_ASK) ?? quietView(54, EMPTY_ASK));
  const [struggle, setStruggle] = useState<Insight | null>(null);
  const [jsonOpen, setJsonOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [autoOpen, setAutoOpen] = useState(false);
  const [autoClip, setAutoClip] = useState<AutoEvent | null>(null);
  const [recapOpen, setRecapOpen] = useState(false);
  const [recap, setRecap] = useState<Recap | null>(null);
  const token = useRef(0);
  const minuteRef = useRef(minute);
  minuteRef.current = minute;
  const prefs = useRef({ persona, language, club, spotlight });
  prefs.current = { persona, language, club, spotlight };
  const text = chrome[language];
  const shown = struggle ?? insight;
  const players = positionsFor(minute, shown);
  const overlay = useMemo(() => overlayDocument(shown, players), [shown, players]);

  async function load(ask: Ask, opts?: { struggle?: boolean; question?: string }) {
    const seq = ++token.current;
    setBusy(true);
    const cached = opts?.struggle ? null : cachedInsight(ask);
    if (cached && seq === token.current) {
      setInsight(cached);
      setStruggle(null);
    }
    const live = opts?.struggle ? await diagnose(ask) : await analyze({ ...ask, custom_question: opts?.question });
    if (seq !== token.current) return;
    if (opts?.struggle) setStruggle(live);
    else {
      setStruggle(null);
      setInsight(live);
    }
    setBusy(false);
  }

  useEffect(() => {
    if (playing) return;
    const ask: Ask = { minute, persona, language, favorite_club: club, spotlight_player_id: spotlight };
    if (BOOKMARKS.includes(minute as (typeof BOOKMARKS)[number])) {
      void load(ask);
    } else {
      const seq = ++token.current;
      setStruggle(null);
      void fetchTelemetry(minute).then((frame) => {
        if (seq !== token.current || !frame) return;
        setInsight(quietView(minute, ask));
        setBusy(false);
      });
    }
    // load identity changes with the desk controls, not with play.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minute, persona, language, club, spotlight, playing]);

  useEffect(() => {
    if (!playing) return;
    let source: EventSource | null = null;
    let local: number | null = null;
    let stopped = false;
    let sawMessage = false;
    const applyMinute = (next: number) => {
      setMinute(next);
      const ask: Ask = {
        minute: next,
        persona: prefs.current.persona,
        language: prefs.current.language,
        favorite_club: prefs.current.club,
        spotlight_player_id: prefs.current.spotlight,
      };
      if (BOOKMARKS.includes(next as (typeof BOOKMARKS)[number])) void load(ask);
      else setInsight(quietView(next, ask));
      if (next >= 90) setPlaying(false);
    };
    const startLocal = () => {
      local = window.setInterval(() => {
        if (stopped) return;
        const next = Math.min(90, minuteRef.current + 1);
        minuteRef.current = next;
        applyMinute(next);
      }, speed === 10 ? 100 : 1000);
    };
    try {
      source = new EventSource(`/api/live/stream?start_minute=${minute}&speed=${speed}`);
      source.onmessage = (event) => {
        if (stopped) return;
        sawMessage = true;
        const data = JSON.parse(event.data) as { current_minute: number };
        applyMinute(data.current_minute);
      };
      source.addEventListener("end", () => {
        source?.close();
        setPlaying(false);
      });
      source.onerror = () => {
        source?.close();
        if (!stopped && !sawMessage) startLocal();
      };
    } catch {
      startLocal();
    }
    return () => {
      stopped = true;
      source?.close();
      if (local) window.clearInterval(local);
    };
    // Restart only when the user hits play or changes speed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed]);

  useEffect(() => {
    if (minute !== 90) {
      setRecapOpen(false);
      return;
    }
    const ask: Ask = { minute, persona, language, favorite_club: club, spotlight_player_id: spotlight };
    void fetchRecap(ask).then((payload) => {
      setRecap(payload);
      setRecapOpen(true);
    });
  }, [minute, persona, language, club, spotlight]);

  async function onStruggle() {
    const ask: Ask = { minute, persona, language, favorite_club: club, spotlight_player_id: spotlight };
    await load(ask, { struggle: true });
  }

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    const ask: Ask = { minute, persona, language, favorite_club: club, spotlight_player_id: spotlight };
    await load(ask, { question: question });
  }

  async function onAuto() {
    setAutoClip(await fetchAuto(minute));
    setAutoOpen(true);
  }

  async function onCopy() {
    const textBody = JSON.stringify(overlay, null, 2);
    try {
      await navigator.clipboard.writeText(textBody);
    } catch {
      setJsonOpen(true);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  const dir = language === "ar" ? "rtl" : "ltr";

  return (
    <div className="desk-grid flex h-full min-h-0 flex-col text-slate-100" dir={dir} lang={language}>
      <header className="panel z-10 mx-3 mt-3 shrink-0 rounded-2xl px-4 py-3">
        <div className="flex flex-wrap items-center gap-4">
          <div className="min-w-[140px]">
            <div className="font-display text-2xl uppercase tracking-[0.18em]">{text.product}</div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{text.kicker}</div>
          </div>
          <div className="flex items-center gap-3 rounded-xl bg-black/40 px-3 py-2" dir="ltr" data-testid="scoreboard">
            <TeamMark code="NLR" name={chrome.en.clubs.NLR} score={shown.scoreline?.NLR ?? 0} tone="nlr" />
            <div className="font-display text-3xl tabular-nums text-slate-200">–</div>
            <TeamMark code="MCB" name={chrome.en.clubs.MCB} score={shown.scoreline?.MCB ?? 0} tone="mcb" />
          </div>
          <div className="text-center" dir="ltr">
            <div className="font-display text-3xl tabular-nums leading-none" data-testid="clock">
              {minute >= 90 ? text.fullTime : clock(minute)}
            </div>
            <div className="mt-1 flex items-center justify-center gap-1 text-[10px] uppercase tracking-[0.18em] text-rose-300">
              <Radio size={12} className={playing ? "animate-pulse" : ""} />
              {text.live}
            </div>
          </div>
          <div className="flex flex-wrap gap-1" dir="ltr">
            {BOOKMARKS.map((mark) => (
              <button
                key={mark}
                data-testid={`bookmark-${mark}`}
                className={`rounded-full px-3 py-1 text-sm font-semibold ${
                  minute === mark ? "bg-white text-ink" : "bg-white/5 text-slate-200 hover:bg-white/10"
                }`}
                onClick={() => {
                  setPlaying(false);
                  setMinute(mark);
                }}
              >
                {mark}'
              </button>
            ))}
          </div>
          <div className="ms-auto flex items-center gap-2">
            <div className="flex rounded-full bg-black/40 p-1" dir="ltr">
              {(["en", "es", "ar"] as Lang[]).map((code) => (
                <button
                  key={code}
                  data-testid={`lang-${code}`}
                  className={`rounded-full px-2.5 py-1 text-xs font-bold uppercase ${
                    language === code ? "bg-white text-ink" : "text-slate-300"
                  }`}
                  onClick={() => setLanguage(code)}
                >
                  {code}
                </button>
              ))}
            </div>
            <button data-testid="auto-event" className="rounded-full bg-mcb/20 px-3 py-1.5 text-sm font-semibold text-sky-100" onClick={() => void onAuto()}>
              {text.autoEvent}
            </button>
            <button data-testid="recap-button" className="rounded-full bg-white/10 px-3 py-1.5 text-sm" onClick={() => setMinute(90)}>
              {text.recap}
            </button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3" dir="ltr">
          <div className="flex gap-2" data-testid="agent-trace">
            {(shown.agent_trace?.length ? shown.agent_trace : ghostTrace()).map((agent, index) => (
              <div
                key={agent.agent_id}
                className={`agent-node live min-w-[148px] rounded-xl border border-verified/40 bg-black/30 px-2.5 py-1.5 ${
                  agent.status === "recovered" ? "border-amber-300/50" : ""
                }`}
                style={{ animationDelay: `${index * 0.12}s` }}
              >
                <div className="text-[10px] uppercase tracking-[0.16em] text-slate-400">{agent.stage}</div>
                <div className="truncate text-xs font-semibold">{agent.name}</div>
                <div className="font-display text-sm tabular-nums text-verified">{Number(agent.latency_ms).toFixed(2)} ms</div>
              </div>
            ))}
          </div>
          <div className="ms-auto flex min-w-[280px] flex-1 items-center gap-2">
            <button
              data-testid="play"
              className="grid h-9 w-9 place-items-center rounded-full bg-white text-ink"
              onClick={() => setPlaying((value) => !value)}
              aria-label={playing ? text.pause : text.play}
            >
              {playing ? <Pause size={16} /> : <Play size={16} className="ms-0.5" />}
            </button>
            <input
              data-testid="scrubber"
              className="flex-1 accent-sky-400"
              type="range"
              min={1}
              max={90}
              value={minute}
              onChange={(event) => {
                setPlaying(false);
                setMinute(Number(event.target.value));
              }}
            />
            <button className={`rounded-full px-2 py-1 text-xs ${speed === 1 ? "bg-white text-ink" : "bg-white/10"}`} onClick={() => setSpeed(1)}>
              1x
            </button>
            <button data-testid="speed-10" className={`rounded-full px-2 py-1 text-xs ${speed === 10 ? "bg-white text-ink" : "bg-white/10"}`} onClick={() => setSpeed(10)}>
              10x
            </button>
          </div>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-[300px_minmax(0,1fr)_340px]">
        <aside className="panel flex min-h-0 flex-col gap-3 overflow-auto rounded-2xl p-3">
          <div className="grid grid-cols-1 gap-1">
            {(Object.keys(text.personas) as Persona[]).map((item) => (
              <button
                key={item}
                data-testid={`persona-${item}`}
                className={`rounded-xl px-3 py-2 text-start text-sm ${
                  persona === item ? "bg-white text-ink" : "bg-white/5 hover:bg-white/10"
                }`}
                onClick={() => setPersona(item)}
              >
                {text.personas[item]}
              </button>
            ))}
          </div>
          <label className="text-[11px] uppercase tracking-[0.16em] text-slate-400">
            {text.spotlight}
            <select
              data-testid="spotlight"
              className="mt-1 w-full rounded-xl bg-black/40 px-3 py-2 text-sm text-slate-100"
              value={spotlight}
              onChange={(event) => setSpotlight(event.target.value)}
            >
              <option value="">{text.allPlayers}</option>
              {SPOTLIGHTS.map((player) => (
                <option key={player.id} value={player.id}>
                  #{player.shirt} {player.name}
                </option>
              ))}
            </select>
          </label>
          <div>
            <div className="mb-1 text-[11px] uppercase tracking-[0.16em] text-slate-400">{text.favorite}</div>
            <div className="grid grid-cols-2 gap-1">
              {(["NLR", "MCB"] as Club[]).map((item) => (
                <button
                  key={item}
                  data-testid={`club-${item}`}
                  className={`rounded-xl px-2 py-2 text-sm font-semibold ${
                    club === item ? (item === "NLR" ? "bg-nlr text-white" : "bg-mcb text-white") : "bg-white/5"
                  }`}
                  onClick={() => setClub(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <button data-testid="struggle" className="rounded-xl bg-nlr/90 px-3 py-3 text-sm font-semibold" onClick={() => void onStruggle()}>
            {text.struggling}
          </button>
          <form onSubmit={(event) => void onAsk(event)} className="flex gap-1">
            <input
              data-testid="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={text.askPlaceholder}
              className="w-full rounded-xl bg-black/40 px-3 py-2 text-sm outline-none ring-sky-400/40 focus:ring"
            />
            <button className="rounded-xl bg-white/10 px-3 text-sm" type="submit">
              {text.ask}
            </button>
          </form>
          <Gauge value={shown.control_vs_chaos_index || 0} label={text.cci} caption={text.rhythm[shown.rhythm_state] || shown.rhythm_state || "—"} />
        </aside>

        <section className="relative min-h-[320px] overflow-hidden rounded-2xl border border-white/10 bg-[#07261b]" dir="ltr" data-testid="pitch-wrap">
          <div className="absolute left-3 top-3 z-10 flex gap-2 text-[11px] uppercase tracking-[0.14em]">
            <span className="rounded-full bg-nlr px-2 py-1">NLR</span>
            <span className="rounded-full bg-mcb px-2 py-1">MCB</span>
          </div>
          <Pitch minute={minute} players={players as Player[]} spotlight={spotlight} />
          <div className="lower-third absolute inset-x-0 bottom-0 z-10 px-4 py-3" data-testid="lower-third">
            <div className="flex items-end justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.2em] text-amber-200">{modeLabel(shown, text)}</div>
                <div className="truncate font-display text-2xl uppercase leading-none" data-testid="headline">
                  {shown.headline || text.quiet}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(shown.badges || []).slice(0, 3).map((badge) => (
                    <span key={badge.label} data-testid="badge" className="rounded-full bg-verified/15 px-2 py-0.5 text-xs font-semibold text-verified">
                      {badge.label}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex shrink-0 gap-1">
                <button className="rounded-full bg-white/10 px-3 py-1 text-xs" onClick={() => setJsonOpen((open) => !open)}>
                  {text.json}
                </button>
                <button data-testid="copy-json" className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-semibold text-ink" onClick={() => void onCopy()}>
                  <Copy size={12} />
                  {copied ? text.copied : text.copy}
                </button>
              </div>
            </div>
            {jsonOpen && (
              <pre data-testid="overlay-json" className="mt-2 max-h-40 overflow-auto rounded-lg bg-black/70 p-2 text-[10px] leading-relaxed text-slate-200">
                {JSON.stringify(overlay, null, 2)}
              </pre>
            )}
          </div>
        </section>

        <aside className="panel flex min-h-0 flex-col gap-3 overflow-auto rounded-2xl p-4" data-testid="story">
          <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.16em] text-slate-400">
            <span>{busy ? text.updating : modeLabel(shown, text)}</span>
            <span>{shown.intent === "diagnose" || struggle ? text.struggling : text.personas[persona]}</span>
          </div>
          <h1 className="font-display text-3xl uppercase leading-[0.95]">{shown.headline || text.quiet}</h1>
          <p className="text-[15px] leading-relaxed text-slate-100" data-testid="narrative">
            {shown.narrative_body || text.between}
          </p>
          {shown.why_it_matters && (
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">{text.why}</div>
              <p className="mt-1 text-sm text-slate-300">{shown.why_it_matters}</p>
            </div>
          )}
          <div className="flex flex-col gap-1">
            {(shown.badges || []).map((badge) => (
              <div key={badge.label} className="rounded-lg border border-verified/30 bg-verified/10 px-2 py-1 text-sm text-verified">
                {text.verified} · {badge.label}
              </div>
            ))}
          </div>
          {shown.epistemic_note && (
            <div className="rounded-xl border border-amber-300/30 bg-amber-300/10 p-3 text-sm text-amber-100" data-testid="epistemic">
              <div className="text-[11px] uppercase tracking-[0.16em]">{text.epistemic}</div>
              {shown.epistemic_note}
            </div>
          )}
          {!!shown.handoffs?.length && (
            <details className="text-xs text-slate-400">
              <summary className="cursor-pointer uppercase tracking-[0.14em]">{text.handoffs}</summary>
              <ul className="mt-2 space-y-1">
                {shown.handoffs.map((hop) => (
                  <li key={hop}>{hop}</li>
                ))}
              </ul>
            </details>
          )}
        </aside>
      </div>

      {autoOpen && autoClip && (
        <Modal title={text.autoEvent} onClose={() => setAutoOpen(false)} closeLabel={text.close} testid="auto-modal">
          <p className="text-sm text-slate-300">{text.method}</p>
          <div className="mt-3 grid gap-2">
            {autoClip.events.map((event, index) => (
              <article key={index} className="rounded-xl bg-white/5 p-3">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-400">{String(event.event_type)}</div>
                <div className="font-display text-xl uppercase">
                  {eventLabel(String(event.event_type), text)} · #{String(event.shirt_number ?? "")} {String(event.player_name ?? "")}
                </div>
                <div className="mt-1 text-sm text-slate-200">{eventMetrics(event)}</div>
              </article>
            ))}
          </div>
        </Modal>
      )}

      {recapOpen && recap && (
        <Modal title={text.turning} onClose={() => setRecapOpen(false)} closeLabel={text.close} testid="recap-modal">
          <div className="mb-3 flex flex-wrap gap-2 text-sm">
            <span className="rounded-full bg-verified/15 px-3 py-1 text-verified" data-testid="recap-xg">
              {text.xg}: NLR {recap.xg.NLR.toFixed(2)} – MCB {recap.xg.MCB.toFixed(2)}
            </span>
            <span className="rounded-full bg-white/10 px-3 py-1">
              {text.peak}: {recap.peak_pdr.toFixed(1)}
            </span>
            <span className="rounded-full bg-white/10 px-3 py-1">
              {text.shifts}: {recap.tactical_shifts}
            </span>
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            {recap.turning_points.map((card) => (
              <article key={card.minute} className="rounded-xl bg-white/5 p-3">
                <div className="font-display text-2xl">{card.minute}'</div>
                <div className="text-sm font-semibold">{card.headline}</div>
                <p className="mt-1 text-xs leading-relaxed text-slate-300">{card.narrative_body}</p>
              </article>
            ))}
          </div>
        </Modal>
      )}
    </div>
  );
}

function ghostTrace() {
  return [
    { agent_id: "agent_1", name: "Telemetry Engine", role: "", stage: "interpret", latency_ms: 0, status: "ghost" },
    { agent_id: "agent_2", name: "Causal Analyst", role: "", stage: "explain", latency_ms: 0, status: "ghost" },
    { agent_id: "agent_3", name: "Broadcast Personalizer", role: "", stage: "personalize", latency_ms: 0, status: "ghost" },
    { agent_id: "agent_4", name: "Grounding Auditor", role: "", stage: "render", latency_ms: 0, status: "ghost" },
  ];
}

function TeamMark({ code, name, score, tone }: { code: string; name: string; score: number; tone: "nlr" | "mcb" }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`grid h-9 w-9 place-items-center rounded-md font-display text-sm ${tone === "nlr" ? "bg-nlr" : "bg-mcb"}`}>{code}</div>
      <div>
        <div className="max-w-[120px] truncate text-[10px] uppercase tracking-[0.14em] text-slate-400">{name}</div>
        <div className="font-display text-3xl leading-none tabular-nums">{score}</div>
      </div>
    </div>
  );
}

function Gauge({ value, label, caption }: { value: number; label: string; caption: string }) {
  const v = Math.max(0, Math.min(100, value || 0));
  const color = v < 35 ? "#3ddc84" : v <= 65 ? "#e8c547" : "#ff5a6a";
  const angle = -90 + (v / 100) * 180;
  return (
    <div data-testid="cci" className="mt-auto rounded-2xl bg-black/30 p-3">
      <svg viewBox="0 0 120 78" className="mx-auto h-24 w-full">
        <path d="M12 66 A 48 48 0 0 1 108 66" fill="none" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" pathLength={100} />
        <path d="M12 66 A 48 48 0 0 1 108 66" fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" pathLength={100} strokeDasharray={`${v} 100`} />
        <line x1="60" y1="66" x2="60" y2="30" stroke={color} strokeWidth="2" transform={`rotate(${angle} 60 66)`} />
        <circle cx="60" cy="66" r="3" fill={color} />
        <text x="60" y="58" textAnchor="middle" fill="#f8fafc" fontSize="14" fontFamily="Oswald, sans-serif">
          {v.toFixed(1)}
        </text>
      </svg>
      <div className="text-center text-[10px] uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <div className="text-center text-sm">{caption}</div>
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
  closeLabel,
  testid,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  closeLabel: string;
  testid: string;
}) {
  return (
    <div className="modal-backdrop fixed inset-0 z-30 grid place-items-center p-6" data-testid={testid}>
      <div className="panel max-h-[80vh] w-full max-w-4xl overflow-auto rounded-2xl p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-3xl uppercase">{title}</h2>
          <button className="rounded-full bg-white/10 px-3 py-1 text-sm" onClick={onClose}>
            {closeLabel}
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function eventLabel(kind: string, text: (typeof chrome)["en"]) {
  if (kind === "pass") return text.pass;
  if (kind === "shot") return text.shot;
  if (kind === "sprint") return text.sprint;
  return kind;
}

function eventMetrics(event: Record<string, unknown>) {
  const pass = event.pass_metrics as { distance_m?: number; pass_difficulty_rating?: number; defenders_bypassed?: number; accurate?: boolean } | null;
  if (pass) {
    return `${pass.distance_m} m · PDR ${pass.pass_difficulty_rating} · ${pass.defenders_bypassed} bypassed · ${event.ball_speed_kmh} km/h · ${pass.accurate ? "accurate" : "incomplete"}`;
  }
  if (event.shot_speed_kmh) return `${event.shot_speed_kmh} km/h`;
  if (event.player_speed_kmh) return `${event.player_speed_kmh} km/h`;
  return "";
}
