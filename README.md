# Zeitvariable Ankünfte – Besetzung für Wellen (Streamlit-Demo)

**[→ Demo live ausprobieren](https://sebastianhanisch-time-varying-arrivals-demo.streamlit.app/)**

Interaktive Demo zur **Besetzung eines Gates mit schwankender Last** (Tagesverlauf, Pulks nach einer Fährankunft). **Sechstes Stück der
Konzepte-Linie „Warteschlangentheorie und Simulation“** im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations
Research und Machine Learning): ein Verfahren, ein wachsendes Beispiel, jedes Folgestück hebt genau eine Annahme auf.

Die Stücke 3 bis 5 ([mmc-queue-demo](https://github.com/sebastian-hanisch/mmc-queue-demo),
[erlang-a-demo](https://github.com/sebastian-hanisch/erlang-a-demo),
[square-root-staffing-demo](https://github.com/sebastian-hanisch/square-root-staffing-demo)) nahmen eine **konstante** Ankunftsrate an.
Hier schwankt sie in einer Welle. Zwei Wege, die Spurzahl über die Zeit zu planen, treten gegeneinander an: nach dem **momentanen
Angebot** (so besetzen, als wäre die Last gerade konstant, die „pointwise stationary approximation“) und nach dem **verzögerten Angebot**
(*Modified Offered Load*: die mittlere Zahl beschäftigter Spuren bei unendlich vielen Spuren, gedämpft und verschoben, weil ein Lkw, der vor
einer Abfertigungsdauer ankam, noch im System ist).

## Kernfrage

Wie schnell darf die Welle sein, bevor die Besetzung nach dem momentanen Angebot das Ziel (hier: höchstens 20 % Wartende zu jeder
Tageszeit) verfehlt, und was rettet sie?

## Modell und Methodik

- **Welle:** λ(t) = a·μ·(1 + A·sin(2πt/P)), mittleres Angebot a (20 bis 200 Erlang), Amplitude A (0 bis 70 %), Periode P (20 min, 1 h, 4 h, 24 h),
  exponentielle Abfertigung (3 min Mittel je Spur), unendliche Geduld.
- **Zwei Angebote** (`tva_formulas.py`): momentan λ(t)/μ; verzögert m(t) = ∫ λ(t − s)·e^(−μs) ds, in geschlossener Form
  a·(1 + A/√(1 + (ω/μ)²)·sin(ωt − arctan(ω/μ))), also um den Faktor 1/√(1 + (ω/μ)²) gedämpft und um arctan(ω/μ)/ω Minuten verschoben.
  Unabhängige Kontrollen im Test: numerische Lösung der Differentialgleichung m′ = λ − μ·m (Runge-Kutta) und das definierende Integral
  (Trapezregel).
- **Besetzung:** je Minute die kleinste Spurzahl, deren Erlang-C-Wartewahrscheinlichkeit beim jeweiligen Angebot höchstens das Ziel ist;
  das **Planungsraster** (1, 15, 60 min) erlaubt Wechsel nur in Blöcken, im Block gilt das Maximum.
- **Simulation** (`tva_simulation.py`): Ankünfte durch **Ausdünnung** (Kandidaten mit der Höchstrate, Annahme mit Wahrscheinlichkeit λ(t)/λ_max),
  Spurzahl je Minute, wer eine Abfertigung begonnen hat, bedient sie fertig; SplitMix64 mit getrennten Strömen. Ergebnis je Phase (24
  Phasen je Zyklus): Anteil der Ankünfte, die warten müssen.
- **Vorgerechnete Studie** (`generate_precomputed.py` → `precomputed_sweep.json`): 2 mittlere Angebote (20, 100) × 2 Amplituden (30, 50 %) × 4 Perioden
  × 3 Raster × 2 Besetzungen, je 3 Läufe à 800 000 Lkw. Live läuft ein kurzer Lauf (150 000 Lkw je Besetzung).

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`. Studie: Angebot 100, Amplitude 50 %, Ziel 20 %, Raster 1 min, wo nichts anderes steht; „je Phase“
heißt Spanne vom kleinsten bis zum größten Wert über die 24 Phasen eines Zyklus.

| Frage | Befund |
|---|---|
| Kostet die richtige Besetzung mehr Spuren? | **Nein:** die mittlere Spurzahl unterscheidet sich zwischen den beiden Besetzungen um höchstens 0.2 Spuren (a = 100: 111.3 bis 111.5, a = 20: 25.5 bis 25.8). Es geht nur ums Timing. |
| Wie viel verzögert sich das Angebot? | Um **3.0 min** (Periode 4 h und 24 h), 2.9 min (1 h), 2.4 min (20 min); gedämpft auf 99.7 % (4 h), 95 % (1 h), 73 % (20 min) der Amplitude. |
| Wie groß ist der Versatz, in der Einheit der Wurzelregel? | **0.07·√a** (24 h), **0.39·√a** (4 h), **1.50·√a** (1 h), **3.43·√a** (20 min). Stück 5 rechnet mit Sicherheitsstufen von etwa 1 bis 2: ein Versatz von 0.4 verschenkt davon schon einen erheblichen Teil. |
| Was passiert mit dem momentanen Angebot? | Wartende je Phase: **0.9 % bis 100.0 %** (20 min), **1.7 % bis 87.7 %** (1 h), **6.4 % bis 35.9 %** (4 h), 14.0 % bis 23.3 % (24 h); das Ziel von 20 % verfehlen 15, 14, 10 und 4 der 24 Phasen. |
| Und mit dem verzögerten Angebot? | **16.4 % bis 21.1 %** (20 min), **15.8 % bis 19.6 %** (1 h), **16.7 % bis 20.4 %** (4 h), 14.7 % bis 19.8 % (24 h): in **keiner** der 16 Zellen verfehlt eine Phase das Ziel um mehr als 2 Prozentpunkte. |
| Gilt das auch für kleine Gates und kleine Wellen? | Ja: a = 20, Amplitude 50 %: momentan 2.3 % bis 79.6 % (20 min), 3.7 % bis 45.8 % (1 h), 11.2 % bis 23.9 % (4 h). a = 100, Amplitude 30 %, 4 h: 9.7 % bis 28.7 % gegen 14.3 % bis 20.4 %. |
| Wird das Ziel genau getroffen? | Im Mittel **nicht ganz**: der Anteil Wartender liegt bei 17.3 bis 18.9 % (a = 100) und 16.3 bis 17.0 % (a = 20), weil ganze Spuren aufgerundet werden. |
| Was kostet ein grobes Planungsraster (verzögertes Angebot)? | Periode 4 h: **111.4** Spuren bei Raster 1 min, **117.6** (+5.6 %) bei 15 min, **137.5** (+23 %) bei 60 min; im Mittel warten 18.3 %, 7.5 %, 3.1 % der Lkw (überbesetzt). Periode 1 h: 111.3 / 134.2 / 161.0, Periode 20 min: 111.5 / 132.8 / 150.0, Periode 24 h: 111.3 / 112.4 / 115.5 (17.3 / 14.9 / 10.0 %). |
| Wie verlässlich sind die Phasenwerte? | Der größte Standardfehler einer Phase beträgt ohne Raster 3.5 Prozentpunkte (a = 100, 24 h), bei Perioden bis 4 h höchstens 3.0, bei 20 min höchstens 1.5. |

## Befunde und Korrekturen gegenüber der Vorab-Messreihe

- **Bei Periode 24 h war die Vorab-Messreihe zu verrauscht.** Sie simulierte nur 20 Zyklen und sah dort „PSA ≈ MOL“. Die Studie (3 Läufe à 800 000
  Lkw) zeigt für Angebot 100 und Amplitude 50 % beim momentanen Angebot noch 4 verfehlte Phasen (14.0 % bis 23.3 %, gegen 14.7 % bis 19.8 % beim
  verzögerten). Der Unterschied liegt allerdings nahe am Rauschen von bis zu 3.5 Punkten und ist bei 24 h am wenigsten belastbar.
- **Sonst bestätigt die Studie die Vorab-Messreihe**, die Spannen wandern nur um Zehntelpunkte: momentan 6–36 % (4 h), 0.6–89 % (1 h), 0.7–99.9 % (20 min)
  in der Vorab-Messreihe gegen 6.4–35.9 %, 1.7–87.7 % und 0.9–100.0 % in der Studie; verzögert 14.6–22.3 %, 15.9–21.4 %, 16.5–21.7 % gegen 16.7–20.4 %,
  15.8–19.6 %, 16.4–21.1 %. Die Raster-Spurzahlen (111.4 / 117.6 / 137.5) sind identisch.
- **Der Versatz wird nicht wieder kleiner, wenn die Welle sehr schnell wird.** Ich hatte im ersten App-Text geschrieben, die Dämpfung verkleinere
  ihn bei sehr schnellen Wellen wieder. Die Rechnung zeigt das Gegenteil: er fällt monoton mit der Periode und nähert sich für sehr schnelle
  Wellen der ganzen Amplitude A·√a (hier 5.0): das verzögerte Angebot glättet die Welle fast weg. Der App-Text ist korrigiert.
- **Zwei Fehlschätzungen im ersten Entwurf der Tests** (Verschiebung 1.8 min statt richtig 2.4 min bei 20 min, 2.8 statt 2.9 bei 1 h; mittlere
  Wartewahrscheinlichkeit „17–19 %“ statt 17.3–18.9 %) kamen aus dem Kopf und sind an der Rechnung korrigiert.

## Ehrliche Grenzen

- Die Welle ist eine reine Sinuskurve mit bekannter Periode und bekannter Amplitude; reale Lasten sind geschätzt und unregelmäßig, Prognosefehler
  kommen hinzu.
- Die Besetzung zielt auf eine feste Wartewahrscheinlichkeit zu jeder Zeit; andere Ziele (Wartezeit in Minuten, Abbruchquote) verlangen, wie in
  Stück 5 gezeigt, andere Aufschläge und wurden hier nicht untersucht.
- Unendliche Geduld und exponentielle Abfertigung: das verzögerte Angebot hängt von der ganzen Verteilung der Abfertigungsdauer ab (nur der
  exponentielle Fall ist hier gerechnet).
- Die Studie deckt nur Angebot 20 und 100 und Amplitude 30 und 50 % ab; die App zeigt für andere Werte die nächste Zelle und sagt es.
- Der Live-Lauf ist kurz (rund 150 000 Lkw je Besetzung, bei langer Periode nur wenige Zyklen) und streut deutlich; maßgeblich ist die Studie.
- Das Raster rundet im Block auf das Maximum auf; eine kostenoptimale Wahl (Wechselaufwand gegen Wartekosten) wird nicht berechnet.

## Verwandte Demos im Portfolio

- [`markov-queue-demo`](https://github.com/sebastian-hanisch/markov-queue-demo) (Zusatzstück: Ketten mit konstanten Raten und ihr exaktes Einschwingen (hier schwanken die Raten)).
- [`square-root-staffing-demo`](https://github.com/sebastian-hanisch/square-root-staffing-demo) (Stück 5): Wurzelregel bei konstanter Last.
- [`erlang-a-demo`](https://github.com/sebastian-hanisch/erlang-a-demo) (Stück 4) und
  [`mmc-queue-demo`](https://github.com/sebastian-hanisch/mmc-queue-demo) (Stück 3): Erlang A und Erlang C, auf denen die Staffelung beruht.
- [`mm1-queue-demo`](https://github.com/sebastian-hanisch/mm1-queue-demo) (Stück 1).
- [`truck-appointment-demo`](https://github.com/sebastian-hanisch/truck-appointment-demo): Terminvergabe für Lkw; dort planen Termine die Ankünfte,
  hier schwankt die Last von selbst.

## Bewusst nicht umgesetzt

Jede dieser Annahmen hebt ein Folgestück der Linie auf:

| Annahme | Folgestück |
|---|---|
| Abfertigungsdauer exponentiell | [M/G/1, Kingman-Näherung](https://github.com/sebastian-hanisch/mg1-kingman-demo) |
| Ein Gate | [Jackson-Netze](https://github.com/sebastian-hanisch/jackson-network-demo) |
| Alle Lkw gleich wichtig | [Prioritätsklassen](https://github.com/sebastian-hanisch/priority-queue-demo) |

Kein Folgestück: Prognosefehler der Welle, Abwanderung in der zeitvariablen Besetzung, Kosten-optimale Besetzung mit Wechselaufwand.

## Tests

90 Tests, rund 50 s: Ankunftsrate und Angebote von Hand, Dämpfung und Verschiebung (ω/μ = 1 gibt 1/√2 und 2.356 min), das verzögerte Angebot gegen die
Differentialgleichung und das Definitionsintegral, Versatz (fällt mit der Periode), exakte Staffelung auf Minimalität (auch mit Startwert), Raster
von Hand, Simulation gegen zwei von Hand gerechnete Mini-Instanzen (wachsende und sinkende Spurzahl, Phasen, Zeitintegral), Ausdünnung (verworfene
Kandidaten), Ankunftszahlen je Phase gegen das Integral der Rate, konstante Last gegen Erlang C, unendlich viele Spuren gegen das verzögerte Angebot,
Vollständigkeit der vorgerechneten Datei, Presets/Permalink, AppTest-Rauchtests, ein Quelltext-Test gegen Satz-Komma-Fehler und `test_claims.py` für
jede Zahl dieser README.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `tva_formulas.py` | Angebote, Besetzung je Minute, Raster, numerische Kontrolle |
| `tva_simulation.py` | Ausdünnung, zeitvariable Spuren, Ergebnis je Phase |
| `tva_evaluation.py` | Kurven, Stabilität, Studien-Zelle |
| `generate_precomputed.py` | rechnet die Studie vor → `precomputed_sweep.json` |
| `tva_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tva_presets.py`, `tva_constants.py` | Presets, Permalink, Grenzen |
| `tests/` | siehe oben |

## Literatur

- Jennings, O. B., Mandelbaum, A., Massey, W. A., Whitt, W. (1996): Server staffing to meet time-varying demand. *Management Science* 42(10),
  1383–1394 (Besetzung nach dem Angebot eines Systems mit unendlich vielen Servern).
- Feldman, Z., Mandelbaum, A., Massey, W. A., Whitt, W. (2008): Staffing of time-varying queues to achieve time-stable performance.
  *Management Science* 54(2), 324–338.

## Lokal ausführen

```
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pip install -r requirements-dev.txt` und `python -m pytest tests/ -v`. Studie neu rechnen: `python generate_precomputed.py`.

Gebaut mit Streamlit und Plotly.
