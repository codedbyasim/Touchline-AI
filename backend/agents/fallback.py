"""Deterministic copy for every moment, persona, and language.

Used when AIML_API_KEY is empty, the model times out, or Agent 4 rejects
ungrounded prose. Every digit is formatted from the telemetry payload.
"""

from __future__ import annotations

PERSONAS = ("CASUAL_FAN", "TACTICO_ANALYST", "BROADCAST_STUDIO")
LANGUAGES = ("en", "es", "ar")
CLUBS = ("NLR", "MCB")
PRESSURED = {22: "MCB", 54: "NLR", 67: "NLR", 82: "MCB"}

TEAM_NAME = {
    "en": {"NLR": "North London Red", "MCB": "Manchester Blue"},
    "es": {"NLR": "Rojo del Norte de Londres", "MCB": "Azul de Mánchester"},
    "ar": {"NLR": "أحمر شمال لندن", "MCB": "أزرق مانشستر"},
}

VOICE = {
    "en": {
        "pressure": "We are under it, and our shape is the story.",
        "control": "We are the side turning the screw.",
        "neutral": "From our seats the whole match is readable.",
    },
    "es": {
        "pressure": "Lo estamos sufriendo y nuestra forma es la historia.",
        "control": "Somos quienes aprietan el partido.",
        "neutral": "Desde nuestra grada se lee el partido entero.",
    },
    "ar": {
        "pressure": "نحن تحت الضغط وشكلنا هو القصة.",
        "control": "نحن الطرف الذي يشدد الخناق.",
        "neutral": "من مقاعدنا تُقرأ المباراة كاملة.",
    },
}

# headline, body, why. Placeholders come from facts().
STORIES: dict[int, dict[str, dict[str, tuple[str, str, str]]]] = {
    22: {
        "en": {
            "CASUAL_FAN": (
                "The high press steals the ball and the goal",
                "North London Red hunt every loose touch. Manchester Blue give it away {turnovers} times and the shot leaves at {shot} km/h. The goal is a stolen one, not a long attack.",
                "A high block that wins the ball in the danger area is worth a goal on its own.",
            ),
            "TACTICO_ANALYST": (
                "PPDA {ppda} turns the press into a trap",
                "NLR PPDA is {ppda} with {turnovers} turnovers in the window. The line-break rates {pdr} and the shot is {shot} km/h. CCI {cci} marks end-to-end chaos rather than a settled attack.",
                "The rest-defence never resets because the ball is won too high.",
            ),
            "BROADCAST_STUDIO": (
                "Stay with the press — the finish is a rocket",
                "Red shirts are in the faces of blue shirts. Call the turnover, then the shot at {shot} km/h. Pass difficulty on the assist is {pdr}. This goal is won, not built.",
                "Cue the press graphic before the replay of the finish.",
            ),
        },
        "es": {
            "CASUAL_FAN": (
                "La presión alta roba el balón y llega el gol",
                "El Rojo del Norte de Londres caza cada toque. El Azul de Mánchester pierde la pelota {turnovers} veces y el tiro sale a {shot} km/h. El gol es robado, no tejido.",
                "Un bloque alto que recupera en zona de peligro vale un gol por sí solo.",
            ),
            "TACTICO_ANALYST": (
                "PPDA {ppda}: la presión se vuelve trampa",
                "El PPDA del NLR es {ppda} con {turnovers} pérdidas. El pase rompe líneas con {pdr} y el tiro va a {shot} km/h. El CCI {cci} describe caos de transiciones, no un ataque sentado.",
                "La defensa no se reordena porque el balón se gana demasiado arriba.",
            ),
            "BROADCAST_STUDIO": (
                "Quédate en la presión: el remate es un misil",
                "Camisetas rojas encima de las azules. Canta la pérdida y el tiro a {shot} km/h. La dificultad del pase es {pdr}. Este gol se gana, no se construye.",
                "Saca el gráfico de presión antes de la repetición.",
            ),
        },
        "ar": {
            "CASUAL_FAN": (
                "الضغط العالي يسرق الكرة ويصنع الهدف",
                "أحمر شمال لندن يطارد كل لمسة. أزرق مانشستر يفقد الكرة {turnovers} مرات والتسديدة تنطلق بسرعة {shot} كم/س. الهدف مسروق لا مبني.",
                "الكتلة العالية التي تستعيد الكرة في منطقة الخطر تساوي هدفاً وحدها.",
            ),
            "TACTICO_ANALYST": (
                "PPDA {ppda} يحوّل الضغط إلى فخ",
                "PPDA لأحمر الشمال {ppda} مع {turnovers} فقدان. صعوبة التمريرة {pdr} وسرعة التسديدة {shot} كم/س. مؤشر CCI {cci} يعني فوضى انتقالات لا هجوماً مستقراً.",
                "الارتكاز لا يعود لأن الكرة تُستعاد عالياً جداً.",
            ),
            "BROADCAST_STUDIO": (
                "ابق مع الضغط فالتسديدة صاروخ",
                "القمصان الحمراء في وجوه الزرقاء. أعلن الفقدان ثم التسديدة بسرعة {shot} كم/س. صعوبة التمريرة {pdr}. هذا هدف مُنتزع.",
                "أخرج رسم الضغط قبل إعادة التسديدة.",
            ),
        },
    },
    54: {
        "en": {
            "CASUAL_FAN": (
                "A full-back steps inside and the middle opens",
                "Manchester Blue hold {poss_mcb} percent of the ball and walk a full-back {shift} metres inside. North London Red stand off. The quiet is the danger, not a frantic spell.",
                "When a full-back leaves the touchline, the centre belongs to the team with the ball.",
            ),
            "TACTICO_ANALYST": (
                "Full-back inversion creates a Zone 14 overload",
                "The shift is {shift} m inside with a 3v2 in zone 14. NLR PPDA moves from {ppda_base} to {ppda}. Central xT rises {lift} percent to {xt}. Line-break PDR is {pdr}. CCI {cci} is high positional control.",
                "The overload is structural: more bodies between the lines, less pressure on the ball.",
            ),
            "BROADCAST_STUDIO": (
                "Draw the arrow — number two has stepped in",
                "Number 2 is {shift} metres inside and blue shirts own the pocket. Tell viewers the game went calm on purpose. The killer pass rates {pdr} with the ball at {ball} km/h.",
                "Hold the freeze-frame on the full-back's two positions.",
            ),
        },
        "es": {
            "CASUAL_FAN": (
                "Un lateral entra por dentro y se abre el medio",
                "El Azul de Mánchester tiene el {poss_mcb} por ciento del balón y mete un lateral {shift} metros hacia dentro. El Rojo se queda atrás. El silencio es el peligro.",
                "Cuando el lateral abandona la cal, el centro es de quien tiene el balón.",
            ),
            "TACTICO_ANALYST": (
                "La inversión del lateral crea superioridad en zona 14",
                "El desplazamiento es de {shift} m hacia dentro con un 3v2 en la zona 14. El PPDA del NLR pasa de {ppda_base} a {ppda}. La xT central sube un {lift} por ciento hasta {xt}. El PDR es {pdr}. CCI {cci}: control posicional alto.",
                "La superioridad es estructural: más gente entre líneas y menos presión.",
            ),
            "BROADCAST_STUDIO": (
                "Dibuja la flecha: el dos ha entrado",
                "El número 2 está {shift} metros por dentro y las azules mandan en el bolsillo. Di que la calma es deliberada. El pase clave vale {pdr} y el balón va a {ball} km/h.",
                "Congela los dos puntos del lateral.",
            ),
        },
        "ar": {
            "CASUAL_FAN": (
                "الظهير يدخل للداخل وينفتح الوسط",
                "أزرق مانشستر يملك {poss_mcb} في المئة من الكرة ويُدخل ظهيراً {shift} متراً إلى الداخل. الأحمر يتراجع. الهدوء هو الخطر.",
                "حين يغادر الظهير الخط، يصبح الوسط لمن معه الكرة.",
            ),
            "TACTICO_ANALYST": (
                "انقلاب الظهير يصنع زيادة في المنطقة 14",
                "الإزاحة {shift} م للداخل مع 3v2 في المنطقة 14. PPDA للأحمر من {ppda_base} إلى {ppda}. xT المركزية ترتفع {lift} بالمئة إلى {xt}. صعوبة التمريرة {pdr}. CCI {cci} سيطرة موضعية عالية.",
                "الزيادة بنيوية: أجسام أكثر بين الخطوط وضغط أقل على الكرة.",
            ),
            "BROADCAST_STUDIO": (
                "ارسم السهم: الرقم 2 دخل للداخل",
                "الرقم 2 على بعد {shift} متراً داخل الملعب والأزرق يملك الجيب. قل إن الهدوء مقصود. التمريرة القاتلة صعوبتها {pdr} والكرة بسرعة {ball} كم/س.",
                "ثبّت صورة موقعي الظهير.",
            ),
        },
    },
    67: {
        "en": {
            "CASUAL_FAN": (
                "The card kills the press and the game opens",
                "After the yellow card the left side stops running. Flank pressure drops {drop} percent and final-third entries are {entries}. Manchester Blue play through a side that has sat down. The score is level and the match feels loose.",
                "A booking on the press leader turns a plan into a retreat.",
            ),
            "TACTICO_ANALYST": (
                "Low block after the card is a pressing collapse",
                "Left-flank pressures fall {drop} percent. Final-third entries in the window: {entries}. CCI {cci} is end-to-end chaos and NLR PPDA rises to {ppda}. The block is no longer a choice.",
                "Rest offence disappears, so Manchester Blue receive facing play.",
            ),
            "BROADCAST_STUDIO": (
                "Left side gone — chaos after the booking",
                "The card took the press with it, down {drop} percent. Red shirts have {entries} final-third entries. Chaos index {cci}. This is the hangover of the equaliser.",
                "Split the screen: the booking, then the open left channel.",
            ),
        },
        "es": {
            "CASUAL_FAN": (
                "La tarjeta apaga la presión y el partido se abre",
                "Tras la amarilla el costado izquierdo deja de correr. La presión baja un {drop} por ciento y las entradas al último tercio son {entries}. El Azul juega a través de un bloque sentado.",
                "Una tarjeta al líder de la presión convierte el plan en retirada.",
            ),
            "TACTICO_ANALYST": (
                "El bloque bajo tras la tarjeta es un colapso",
                "Las presiones del costado caen un {drop} por ciento. Entradas al último tercio: {entries}. El CCI {cci} es caos de transiciones y el PPDA del NLR sube a {ppda}. El bloque ya no es una elección.",
                "Desaparece el ataque posicional y el Azul recibe de cara.",
            ),
            "BROADCAST_STUDIO": (
                "Se fue la izquierda: caos tras la amarilla",
                "La tarjeta se llevó la presión, un {drop} por ciento menos. El Rojo tiene {entries} entradas al último tercio. Índice de caos {cci}. Es la resaca del empate.",
                "Pantalla partida: la tarjeta y luego el carril abierto.",
            ),
        },
        "ar": {
            "CASUAL_FAN": (
                "البطاقة تُسكت الضغط وتنفتح المباراة",
                "بعد الإنذار يتوقف الطرف الأيسر عن الركض. ضغط الجناح ينخفض {drop} بالمئة ودخول الثلث الأخير {entries}. الأزرق يلعب عبر خصم جلس في الخلف.",
                "إنذار قائد الضغط يحوّل الخطة إلى تراجع.",
            ),
            "TACTICO_ANALYST": (
                "الكتلة المنخفضة بعد البطاقة انهيار ضغط",
                "ضغط الطرف ينخفض {drop} بالمئة. دخول الثلث الأخير: {entries}. CCI {cci} فوضى انتقالات وPPDA للأحمر يرتفع إلى {ppda}. التكتل لم يعد خياراً.",
                "يختفي الهجوم البنائي فيستلم الأزرق وهو مواجه للمرمى.",
            ),
            "BROADCAST_STUDIO": (
                "الطرف الأيسر انتهى: فوضى بعد البطاقة",
                "البطاقة أخذت الضغط معها بانخفاض {drop} بالمئة. الأحمر لديه {entries} دخول للثلث الأخير. مؤشر الفوضى {cci}. هذه آثار هدف التعادل.",
                "اقسم الشاشة: البطاقة ثم الممر المفتوح.",
            ),
        },
    },
    82: {
        "en": {
            "CASUAL_FAN": (
                "Fresh legs against a tired full-back win it",
                "The substitute hits {sprint} km/h while a tired full-back is stuck at {tired} km/h. The pass through the line is the hardest of the night at {pdr} and it becomes the winner.",
                "Pace is a tactic. The new winger attacks the player who can no longer cover the ground.",
            ),
            "TACTICO_ANALYST": (
                "Substitution pace mismatch breaks the rest-defence",
                "Peak sprint {sprint} km/h against the full-back at {tired} km/h. Threshold is {threshold}. Number 8's line-break is PDR {pdr} with ball speed {ball} km/h. This is a mismatch, not a deflection.",
                "The rest-defence is late because the recovery run is no longer fast enough.",
            ),
            "BROADCAST_STUDIO": (
                "Fresh legs, heavy legs, that is the winner",
                "Number 19 hits {sprint}. The ball fizzes at {ball} km/h and the pass rates {pdr}. Put the tired full-back in the same frame. That contrast is the goal.",
                "Call the sprint number before the finish hits the net.",
            ),
        },
        "es": {
            "CASUAL_FAN": (
                "Piernas frescas contra un lateral cansado",
                "El cambio llega a {sprint} km/h y el lateral cansado se queda en {tired} km/h. El pase que rompe la línea es el más difícil de la noche, {pdr}, y se vuelve el gol de la victoria.",
                "El ritmo es una táctica. El extremo nuevo ataca a quien ya no cubre el espacio.",
            ),
            "TACTICO_ANALYST": (
                "El desajuste de ritmo tras el cambio rompe la defensa",
                "Pico de {sprint} km/h frente al lateral a {tired} km/h. El umbral es {threshold}. El pase del 8 vale PDR {pdr} con balón a {ball} km/h. Es un desajuste, no un rechace.",
                "La cobertura llega tarde porque la carrera de recuperación ya no alcanza.",
            ),
            "BROADCAST_STUDIO": (
                "Pierna fresca contra pierna pesada: el gol",
                "El 19 llega a {sprint}. El balón viaja a {ball} km/h y el pase vale {pdr}. Mete al lateral cansado en el mismo plano. Ese contraste es el gol.",
                "Canta la velocidad antes de que el balón entre.",
            ),
        },
        "ar": {
            "CASUAL_FAN": (
                "ساق جديدة أمام ظهير متعب تحسم المباراة",
                "البديل يصل إلى {sprint} كم/س والظهير المتعب عالق عند {tired} كم/س. التمريرة التي تكسر الخط هي الأصعب الليلة بصعوبة {pdr} وتصبح هدف الفوز.",
                "الإيقاع تكتيك. الجناح الجديد يهاجم من لم يعد يغطي المسافة.",
            ),
            "TACTICO_ANALYST": (
                "تفاوت السرعة بعد التبديل يكسر الارتكاز",
                "ذروة {sprint} كم/س مقابل الظهير عند {tired} كم/س. العتبة {threshold}. تمريرة الرقم 8 صعوبتها {pdr} وسرعة الكرة {ball} كم/س. هذا تفاوت لا ارتداد.",
                "التغطية تتأخر لأن ركضة العودة لم تعد سريعة بما يكفي.",
            ),
            "BROADCAST_STUDIO": (
                "ساق جديدة وساق ثقيلة: هذا هو الهدف",
                "الرقم 19 يصل إلى {sprint}. الكرة بسرعة {ball} كم/س وصعوبة التمريرة {pdr}. ضع الظهير المتعب في الإطار نفسه. هذا التباين هو الهدف.",
                "انطق رقم السرعة قبل أن تدخل الكرة.",
            ),
        },
    },
    90: {
        "en": {
            "CASUAL_FAN": (
                "Three pictures explain a two-one full time",
                "Full time {nlr}-{mcb}. A press, a full-back stepping inside, and a substitute sprint decide it. Expected goals finish {xg_nlr} to {xg_mcb}.",
                "The scoreboard hides the four shapes the match actually passed through.",
            ),
            "TACTICO_ANALYST": (
                "xG, peak difficulty, and four tactical shifts",
                "xG finishes NLR {xg_nlr} to MCB {xg_mcb}. Peak pass difficulty is {peak}. The engine logged {shifts} distinct tactical shifts across the ninety minutes.",
                "The recap is the press, the inversion, and the pace mismatch.",
            ),
            "BROADCAST_STUDIO": (
                "Wrap on three pictures and the expected goals",
                "Close on the press, the step-in, and the sprint. xG {xg_nlr} to {xg_mcb}. Peak difficulty {peak}. {shifts} shifts, one scoreline: {nlr} to {mcb}.",
                "Leave the three freeze-frames up under the final score.",
            ),
        },
        "es": {
            "CASUAL_FAN": (
                "Tres fotos explican un dos a uno",
                "Final {nlr}-{mcb}. Una presión, un lateral que entra y un sprint del cambio lo deciden. Los goles esperados cierran {xg_nlr} a {xg_mcb}.",
                "El marcador esconde las cuatro formas que tuvo el partido.",
            ),
            "TACTICO_ANALYST": (
                "xG, dificultad máxima y cuatro cambios tácticos",
                "La xG cierra NLR {xg_nlr} frente a MCB {xg_mcb}. La dificultad máxima del pase es {peak}. El motor registró {shifts} cambios tácticos distintos.",
                "El resumen es la presión, la inversión y el desajuste de ritmo.",
            ),
            "BROADCAST_STUDIO": (
                "Cierre con tres fotos y los goles esperados",
                "Cierra con la presión, la entrada del lateral y el sprint. xG {xg_nlr} a {xg_mcb}. Dificultad máxima {peak}. {shifts} cambios y un marcador: {nlr} a {mcb}.",
                "Deja las tres fotos bajo el resultado final.",
            ),
        },
        "ar": {
            "CASUAL_FAN": (
                "ثلاث صور تفسر نهاية اثنين لواحد",
                "نهاية {nlr}-{mcb}. ضغط، وظهير يدخل للداخل، وانطلاقة بديل تحسمها. الأهداف المتوقعة تنتهي {xg_nlr} مقابل {xg_mcb}.",
                "لوحة النتيجة تخفي الأشكال الأربعة التي مرت بها المباراة.",
            ),
            "TACTICO_ANALYST": (
                "xG والذروة وأربعة تحولات تكتيكية",
                "xG تنتهي NLR {xg_nlr} مقابل MCB {xg_mcb}. ذروة صعوبة التمرير {peak}. المحرك سجّل {shifts} تحولات تكتيكية مختلفة.",
                "الخلاصة هي الضغط والانقلاب وتفاوت الإيقاع.",
            ),
            "BROADCAST_STUDIO": (
                "الختام على ثلاث صور والأهداف المتوقعة",
                "اختم بالضغط ودخول الظهير والانطلاقة. xG {xg_nlr} مقابل {xg_mcb}. الذروة {peak}. {shifts} تحولات ونتيجة {nlr} لـ {mcb}.",
                "اترك اللقطات الثلاث تحت النتيجة النهائية.",
            ),
        },
    },
}

DIAGNOSE = {
    22: {
        "en": "We are struggling because the press is on top of us. They win the ball high, we turn it over {turnovers} times, and the shot arrives at {shot} km/h. PPDA against that press is {ppda}.",
        "es": "Sufrimos porque la presión nos cae encima. Nos roban arriba, perdemos el balón {turnovers} veces y el tiro llega a {shot} km/h. El PPDA de esa presión es {ppda}.",
        "ar": "نعاني لأن الضغط فوقنا. يستعيدون الكرة عالياً ونفقدها {turnovers} مرات وتصل التسديدة بسرعة {shot} كم/س. PPDA لهذا الضغط {ppda}.",
    },
    54: {
        "en": "We are struggling because their full-back has stepped {shift} metres inside and we have stopped pressing. Our PPDA has drifted from {ppda_base} to {ppda}. They hold {poss_mcb} percent and the centre is a 3v2.",
        "es": "Sufrimos porque su lateral ha entrado {shift} metros y nosotros hemos dejado de presionar. Nuestro PPDA pasa de {ppda_base} a {ppda}. Ellos tienen el {poss_mcb} por ciento y el centro es un 3v2.",
        "ar": "نعاني لأن ظهيرهم دخل {shift} متراً وتوقفنا عن الضغط. PPDA لدينا انتقل من {ppda_base} إلى {ppda}. هم يملكون {poss_mcb} في المئة والوسط 3v2.",
    },
    67: {
        "en": "We are struggling because the yellow card took our left-side press. Those runs are down {drop} percent and we have {entries} final-third entries. CCI {cci} says the game is end to end.",
        "es": "Sufrimos porque la amarilla se llevó la presión de nuestro costado. Esas carreras bajan un {drop} por ciento y tenemos {entries} entradas al último tercio. El CCI {cci} dice que el partido es de banda a banda.",
        "ar": "نعاني لأن البطاقة أخذت ضغط طرفنا الأيسر. تلك الركضات انخفضت {drop} بالمئة ولدينا {entries} دخول للثلث الأخير. CCI {cci} يقول إن المباراة من مرمانا إلى مرماهم.",
    },
    82: {
        "en": "We are struggling because their substitute is running at {sprint} km/h and our full-back is at {tired} km/h. The pass that beats us rates {pdr}. Pace, not luck, is the gap.",
        "es": "Sufrimos porque su cambio corre a {sprint} km/h y nuestro lateral está a {tired} km/h. El pase que nos supera vale {pdr}. La diferencia es de ritmo, no de suerte.",
        "ar": "نعاني لأن بديلهم يركض بسرعة {sprint} كم/س وظهيرنا عند {tired} كم/س. التمريرة التي تتجاوزنا صعوبتها {pdr}. الفارق إيقاع لا حظ.",
    },
    90: {
        "en": "The match is over at {nlr} to {mcb}. If we are asking why it slipped, the three turns are the press, the full-back step-in, and the substitute sprint. xG ends {xg_nlr} to {xg_mcb}.",
        "es": "El partido terminó {nlr} a {mcb}. Si preguntamos por qué se escapó, los tres giros son la presión, la entrada del lateral y el sprint del cambio. La xG acaba {xg_nlr} a {xg_mcb}.",
        "ar": "انتهت المباراة {nlr} لـ {mcb}. إن سألنا لماذا أفلتت، فالمنعطفات الثلاثة هي الضغط ودخول الظهير وانطلاقة البديل. xG تنتهي {xg_nlr} مقابل {xg_mcb}.",
    },
}

NOT_US = {
    "en": "We are not the side struggling in this window. The tracking shows {other} carrying the stress while our picture is the cleaner one. The badges are the proof.",
    "es": "No somos quienes sufren en esta ventana. El rastreo muestra que {other} carga con la tensión y nuestra foto es la más limpia. Las chapas son la prueba.",
    "ar": "لسنا الطرف الذي يعاني في هذه النافذة. التتبع يُظهر أن {other} يحمل الضغط وصورتنا هي الأنظف. الشارات هي الدليل.",
}

GENERIC = {
    "en": {
        "CASUAL_FAN": (
            "Minute {minute} is still an open phase",
            "The score is {nlr} to {mcb}. North London Red have {poss_nlr} percent of this window and the chaos index is {cci}. Nothing here is one of the match's big turns yet.",
            "The tagged bookmarks are where the shape of the match actually changes.",
        ),
        "TACTICO_ANALYST": (
            "No structural anomaly at minute {minute}",
            "Score {nlr}-{mcb}. CCI {cci}. Possession NLR {poss_nlr} / MCB {poss_mcb}. The rolling windows do not clear a press, inversion, collapse, or pace-mismatch trigger.",
            "Wait for a window that moves a centroid far enough to count as a structural shift.",
        ),
        "BROADCAST_STUDIO": (
            "Keep the score bug, this phase is quiet",
            "Minute {minute}, {nlr} to {mcb}. Chaos index {cci}. Do not force a graphic. The next bookmark is the picture.",
            "Stay on the wide shot until a tagged turn arrives.",
        ),
    },
    "es": {
        "CASUAL_FAN": (
            "El minuto {minute} sigue siendo una fase abierta",
            "El marcador es {nlr} a {mcb}. El Rojo tiene el {poss_nlr} por ciento de esta ventana y el índice de caos es {cci}. Aquí todavía no hay un giro grande.",
            "Las marcas guardadas son donde el partido cambia de forma.",
        ),
        "TACTICO_ANALYST": (
            "Sin anomalía estructural en el minuto {minute}",
            "Marcador {nlr}-{mcb}. CCI {cci}. Posesión NLR {poss_nlr} / MCB {poss_mcb}. Las ventanas no disparan presión, inversión, colapso ni desajuste de ritmo.",
            "Espera un centroide que se desplace lo bastante para contar como cambio estructural.",
        ),
        "BROADCAST_STUDIO": (
            "Deja el marcador: esta fase está quieta",
            "Minuto {minute}, {nlr} a {mcb}. Índice de caos {cci}. No fuerces un gráfico. El siguiente marcador es la foto.",
            "Quédate en el plano abierto hasta el próximo giro.",
        ),
    },
    "ar": {
        "CASUAL_FAN": (
            "الدقيقة {minute} ما زالت مرحلة مفتوحة",
            "النتيجة {nlr} لـ {mcb}. الأحمر يملك {poss_nlr} في المئة من هذه النافذة ومؤشر الفوضى {cci}. لا منعطف كبيراً هنا بعد.",
            "العلامات المحفوظة هي حيث يتغير شكل المباراة.",
        ),
        "TACTICO_ANALYST": (
            "لا شذوذ بنيوي في الدقيقة {minute}",
            "النتيجة {nlr}-{mcb}. CCI {cci}. الاستحواذ NLR {poss_nlr} / MCB {poss_mcb}. النوافذ لا تطلق ضغطاً ولا انقلاباً ولا انهياراً ولا تفاوت إيقاع.",
            "انتظر مركز ثقل يتحرك بما يكفي ليُحسب تحولاً بنيوياً.",
        ),
        "BROADCAST_STUDIO": (
            "أبق لوحة النتيجة فهذه المرحلة هادئة",
            "الدقيقة {minute} والنتيجة {nlr} لـ {mcb}. مؤشر الفوضى {cci}. لا تفرض رسماً. العلامة التالية هي الصورة.",
            "ابق على اللقطة الواسعة حتى يصل المنعطف.",
        ),
    },
}

WHY_DIAG = {
    "en": "The struggle is spatial. The stream can show where our players stopped arriving. It cannot show fitness, mood, or the dressing room.",
    "es": "El sufrimiento es espacial. El flujo muestra dónde dejaron de llegar nuestros jugadores. No muestra el estado físico ni el vestuario.",
    "ar": "المعاناة مكانية. التدفق يُظهر أين توقف لاعبونا عن الوصول. لا يُظهر اللياقة ولا غرفة الملابس.",
}


def _clip(text: str, limit: int) -> str:
    words = [w for w in (text or "").split() if w]
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit])


def _fmt(value, digits: int) -> str:
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def facts(telemetry: dict, spotlight: dict | None) -> dict[str, str]:
    nlr = (telemetry.get("team_metrics") or {}).get("NLR") or {}
    mcb = (telemetry.get("team_metrics") or {}).get("MCB") or {}
    anomalies = telemetry.get("tactical_anomalies") or []
    anomaly = anomalies[0] if anomalies else {}
    by_type = {h.get("type"): h for h in telemetry.get("speed_and_pass_highlights") or []}
    pdr = by_type.get("HIGH_DIFFICULTY_LINE_BREAKER") or {}
    shot = by_type.get("SHOT_SPEED") or {}
    sprint = by_type.get("SPRINT_THRESHOLD_ALERT") or {}
    roll = telemetry.get("match_rollup") or {}
    xg = roll.get("xg") or {}
    base = mcb.get("xt_central_baseline") or 0
    now = mcb.get("xt_central_5m") or 0
    lift = str(round((now - base) / base * 100)) if base else ""
    score = telemetry.get("scoreline") or {}
    minute = telemetry.get("current_minute") or ""
    tired = anomaly.get("tired_fullback_speed_kmh")
    return {
        "cci": _fmt(telemetry.get("control_vs_chaos_index"), 1),
        "ppda": _fmt(nlr.get("ppda_5m"), 1),
        "ppda_base": _fmt(nlr.get("ppda_baseline"), 1),
        "poss_nlr": _fmt(nlr.get("possession_pct_5m"), 0),
        "poss_mcb": _fmt(mcb.get("possession_pct_5m"), 0),
        "shift": _fmt(anomaly.get("shift_distance_m"), 1),
        "xt": _fmt(now, 2),
        "lift": lift,
        "pdr": _fmt(pdr.get("value"), 1),
        "ball": _fmt(pdr.get("ball_speed_kmh"), 1),
        "shot": _fmt(shot.get("value"), 1),
        "sprint": _fmt(sprint.get("value") or anomaly.get("peak_speed_kmh"), 1),
        "tired": _fmt(tired, 1),
        "threshold": _fmt(telemetry.get("sprint_threshold_kmh"), 1),
        "turnovers": str(telemetry.get("turnovers_5m") or 0),
        "drop": str(telemetry.get("nlr_flank_press_drop_pct") or 0),
        "entries": str(telemetry.get("nlr_final_third_entries_5m") or 0),
        "xg_nlr": _fmt(xg.get("NLR"), 2),
        "xg_mcb": _fmt(xg.get("MCB"), 2),
        "peak": _fmt(roll.get("peak_pdr"), 1),
        "shifts": str(roll.get("tactical_shifts") or 0),
        "nlr": str(score.get("NLR", 0)),
        "mcb": str(score.get("MCB", 0)),
        "minute": str(minute),
        "name": (spotlight or {}).get("player_name") or "",
        "spot_pdr": _fmt((spotlight or {}).get("avg_pass_difficulty"), 1),
        "spot_speed": _fmt((spotlight or {}).get("max_speed_kmh"), 1),
    }


def _voice(language: str, club: str, minute: int) -> str:
    pressured = PRESSURED.get(minute)
    if pressured is None:
        kind = "neutral"
    elif club == pressured:
        kind = "pressure"
    else:
        kind = "control"
    return VOICE[language][kind]


def _spotlight_clause(spotlight: dict | None, language: str, data: dict[str, str]) -> str:
    if not spotlight:
        return ""
    name = spotlight.get("player_name") or ""
    bits = {
        "en": [f"Spotlight on {name}."],
        "es": [f"Foco en {name}."],
        "ar": [f"التسليط على {name}."],
    }
    if spotlight.get("avg_pass_difficulty") is not None and data["spot_pdr"]:
        bits["en"].append(f"Pass difficulty {data['spot_pdr']}.")
        bits["es"].append(f"Dificultad de pase {data['spot_pdr']}.")
        bits["ar"].append(f"صعوبة التمرير {data['spot_pdr']}.")
    speed = float(spotlight.get("max_speed_kmh") or 0)
    if speed >= 20 and data["spot_speed"]:
        bits["en"].append(f"Peak speed {data['spot_speed']} km/h.")
        bits["es"].append(f"Velocidad punta {data['spot_speed']} km/h.")
        bits["ar"].append(f"السرعة القصوى {data['spot_speed']} كم/س.")
    return " ".join(bits[language])


def _fill(template: str, data: dict[str, str]) -> str:
    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return ""

    return template.format_map(_Safe(data))


def overlay(telemetry: dict, title: str, subtitle: str) -> dict:
    vectors = []
    for row in telemetry.get("positions_22_players") or []:
        vectors.append(
            {
                "player_id": row["player_id"],
                "team_id": row["team_id"],
                "shirt_number": row["shirt_number"],
                "from_xy": row["baseline_xy"],
                "to_xy": row["active_xy"],
                "shift_m": row["shift_m"],
            }
        )
    featured = None
    anomalies = telemetry.get("tactical_anomalies") or []
    if anomalies:
        featured = anomalies[0].get("primary_player_id")
    return {
        "title": title,
        "subtitle": subtitle,
        "featured_player_id": featured,
        "graphic_vectors": vectors,
    }


def render_copy(
    telemetry: dict,
    *,
    persona: str,
    language: str,
    favorite_club: str,
    spotlight: dict | None,
    intent: str | None = None,
) -> dict:
    minute = int(telemetry.get("current_minute") or 54)
    language = language if language in LANGUAGES else "en"
    persona = persona if persona in PERSONAS else "CASUAL_FAN"
    club = favorite_club if favorite_club in CLUBS else "NLR"
    pack = (STORIES.get(minute) or GENERIC)[language][persona]
    data = facts(telemetry, spotlight)
    headline = _clip(_fill(pack[0], data), 12)
    voice = _voice(language, club, minute)
    spot = _spotlight_clause(spotlight, language, data)
    if intent == "diagnose":
        body = _diagnose_body(minute, language, club, data)
        why = WHY_DIAG[language]
        headline = _clip(body, 12)
    else:
        body = _fill(pack[1], data)
        why = _fill(pack[2], data)
    narrative = _clip(f"{spot} {voice} {body}".strip(), 55)
    why = _clip(why, 40)
    return {
        "headline": headline,
        "narrative_body": narrative,
        "why_it_matters": why,
        "broadcast_overlay": overlay(telemetry, headline, why),
    }


def _diagnose_body(minute: int, language: str, club: str, data: dict[str, str]) -> str:
    pressured = PRESSURED.get(minute)
    if minute == 90 or pressured is None or club == pressured:
        return _fill(DIAGNOSE.get(minute, DIAGNOSE[90])[language], data)
    other = TEAM_NAME[language]["MCB" if club == "NLR" else "NLR"]
    return NOT_US[language].format(other=other)


def causal_from_copy(copy: dict, telemetry: dict) -> dict:
    anomalies = telemetry.get("tactical_anomalies") or []
    cited = []
    if anomalies:
        cited.append(anomalies[0].get("metric_proof") or "")
    for badge in telemetry.get("_badges") or []:
        cited.append(badge.get("label"))
    return {
        "causal_diagnosis": copy["headline"],
        "why_it_matters": copy["why_it_matters"],
        "cited_metrics": [c for c in cited if c],
        "uncertainty_note": None,
    }
