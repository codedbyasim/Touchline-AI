export type Lang = "en" | "es" | "ar";
export type Persona = "CASUAL_FAN" | "TACTICO_ANALYST" | "BROADCAST_STUDIO";
export type Club = "NLR" | "MCB";

export interface Chrome {
  product: string;
  kicker: string;
  struggling: string;
  ask: string;
  askPlaceholder: string;
  spotlight: string;
  allPlayers: string;
  favorite: string;
  autoEvent: string;
  recap: string;
  copy: string;
  copied: string;
  json: string;
  verified: string;
  cci: string;
  agents: string;
  play: string;
  pause: string;
  live: string;
  close: string;
  why: string;
  handoffs: string;
  epistemic: string;
  updating: string;
  cache: string;
  fallback: string;
  liveModel: string;
  quiet: string;
  between: string;
  fullTime: string;
  method: string;
  pass: string;
  shot: string;
  sprint: string;
  turning: string;
  xg: string;
  peak: string;
  shifts: string;
  personas: Record<Persona, string>;
  rhythm: Record<string, string>;
  clubs: Record<Club, string>;
}

export const chrome: Record<Lang, Chrome> = {
  en: {
    product: "Touchline",
    kicker: "Synthetic match desk",
    struggling: "Why are we struggling?",
    ask: "Ask",
    askPlaceholder: "Ask about this phase…",
    spotlight: "Spotlight",
    allPlayers: "All players",
    favorite: "Our club",
    autoEvent: "Auto-event",
    recap: "3 turning points",
    copy: "Copy JSON",
    copied: "Copied",
    json: "Overlay JSON",
    verified: "Verified",
    cci: "Control vs chaos",
    agents: "Agent trace",
    play: "Play",
    pause: "Pause",
    live: "Live",
    close: "Close",
    why: "Why it matters",
    handoffs: "Handoffs",
    epistemic: "What the stream cannot prove",
    updating: "Updating",
    cache: "Precomputed cache",
    fallback: "Deterministic fallback",
    liveModel: "Semantic Kernel",
    quiet: "Quiet phase",
    between: "Tracking this phase. A bookmark opens the full four-agent briefing.",
    fullTime: "Full time",
    method: "Detected from unlabeled 25 fps frames. The ball had to leave a player, from under 1.5 m to beyond 2.0 m, with acceleration above 8 m/s².",
    pass: "Pass",
    shot: "Shot",
    sprint: "Sprint",
    turning: "Three turning points",
    xg: "Expected goals",
    peak: "Peak pass difficulty",
    shifts: "Tactical shifts",
    personas: {
      CASUAL_FAN: "Casual fan",
      TACTICO_ANALYST: "Tactico analyst",
      BROADCAST_STUDIO: "Broadcast studio",
    },
    rhythm: {
      HIGH_POSITIONAL_CONTROL: "High positional control",
      BALANCED_COMPETITIVE_RHYTHM: "Balanced rhythm",
      END_TO_END_TRANSITION_CHAOS: "End-to-end chaos",
    },
    clubs: { NLR: "North London Red", MCB: "Manchester Blue" },
  },
  es: {
    product: "Touchline",
    kicker: "Mesa de partido sintético",
    struggling: "¿Por qué sufrimos?",
    ask: "Preguntar",
    askPlaceholder: "Pregunta sobre esta fase…",
    spotlight: "Foco",
    allPlayers: "Todos",
    favorite: "Nuestro club",
    autoEvent: "Auto-evento",
    recap: "3 giros",
    copy: "Copiar JSON",
    copied: "Copiado",
    json: "JSON del rótulo",
    verified: "Verificado",
    cci: "Control frente a caos",
    agents: "Traza de agentes",
    play: "Reproducir",
    pause: "Pausa",
    live: "Directo",
    close: "Cerrar",
    why: "Por qué importa",
    handoffs: "Entregas",
    epistemic: "Lo que el flujo no puede probar",
    updating: "Actualizando",
    cache: "Caché precalculada",
    fallback: "Respaldo determinista",
    liveModel: "Semantic Kernel",
    quiet: "Fase tranquila",
    between: "Siguiendo esta fase. Un marcador abre el informe de los cuatro agentes.",
    fullTime: "Final",
    method: "Detectado en fotogramas de 25 fps sin etiquetas. El balón sale de un jugador, de menos de 1.5 m a más de 2.0 m, con aceleración superior a 8 m/s².",
    pass: "Pase",
    shot: "Tiro",
    sprint: "Sprint",
    turning: "Tres giros del partido",
    xg: "Goles esperados",
    peak: "Dificultad máxima",
    shifts: "Cambios tácticos",
    personas: {
      CASUAL_FAN: "Afición",
      TACTICO_ANALYST: "Analista táctico",
      BROADCAST_STUDIO: "Estudio",
    },
    rhythm: {
      HIGH_POSITIONAL_CONTROL: "Control posicional alto",
      BALANCED_COMPETITIVE_RHYTHM: "Ritmo equilibrado",
      END_TO_END_TRANSITION_CHAOS: "Caos de transiciones",
    },
    clubs: { NLR: "Rojo del Norte de Londres", MCB: "Azul de Mánchester" },
  },
  ar: {
    product: "Touchline",
    kicker: "منصة مباراة اصطناعية",
    struggling: "لماذا نعاني؟",
    ask: "اسأل",
    askPlaceholder: "اسأل عن هذه المرحلة…",
    spotlight: "تسليط",
    allPlayers: "كل اللاعبين",
    favorite: "نادينا",
    autoEvent: "اكتشاف الأحداث",
    recap: "٣ منعطفات",
    copy: "نسخ JSON",
    copied: "تم النسخ",
    json: "JSON الشريط",
    verified: "موثّق",
    cci: "السيطرة مقابل الفوضى",
    agents: "أثر الوكلاء",
    play: "تشغيل",
    pause: "إيقاف",
    live: "مباشر",
    close: "إغلاق",
    why: "لماذا يهم",
    handoffs: "التسليم",
    epistemic: "ما لا يستطيع التدفق إثباته",
    updating: "جارٍ التحديث",
    cache: "ذاكرة محسوبة مسبقاً",
    fallback: "احتياطي حتمي",
    liveModel: "Semantic Kernel",
    quiet: "مرحلة هادئة",
    between: "نتتبع هذه المرحلة. العلامة تفتح إحاطة الوكلاء الأربعة.",
    fullTime: "نهاية المباراة",
    method: "اكتُشف من إطارات 25 إطاراً في الثانية بلا تسميات. تغادر الكرة اللاعب من أقل من 1.5 م إلى أكثر من 2.0 م بتسارع أعلى من 8 م/ث².",
    pass: "تمريرة",
    shot: "تسديدة",
    sprint: "انطلاقة",
    turning: "ثلاثة منعطفات",
    xg: "الأهداف المتوقعة",
    peak: "ذروة صعوبة التمرير",
    shifts: "التحولات التكتيكية",
    personas: {
      CASUAL_FAN: "مشجع",
      TACTICO_ANALYST: "محلل تكتيكي",
      BROADCAST_STUDIO: "الاستوديو",
    },
    rhythm: {
      HIGH_POSITIONAL_CONTROL: "سيطرة موضعية عالية",
      BALANCED_COMPETITIVE_RHYTHM: "إيقاع متوازن",
      END_TO_END_TRANSITION_CHAOS: "فوضى من مرمانا إلى مرماهم",
    },
    clubs: { NLR: "أحمر شمال لندن", MCB: "أزرق مانشستر" },
  },
};

export const SPOTLIGHTS = [
  { id: "NLR_07", name: "B. Saka-Style", shirt: 7 },
  { id: "MCB_02", name: "K. Walker-Peters", shirt: 2 },
  { id: "NLR_08", name: "M. Odegaard-Style", shirt: 8 },
  { id: "MCB_09", name: "E. Haaland-Style", shirt: 9 },
] as const;

export const BOOKMARKS = [22, 54, 67, 82, 90] as const;
