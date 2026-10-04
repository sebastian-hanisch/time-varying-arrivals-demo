"""Rechnet die teure Studie vor (Build-Zeit, nicht in der App): `python generate_precomputed.py [Prozesse]` schreibt
`precomputed_sweep.json`.

  study  Angebot × Amplitude × Periode × Planungsraster × Staffelung (momentanes oder verzögertes Angebot): Wartewahrscheinlichkeit je
         Phase des Zyklus aus je 3 Wiederholungen à 800 000 Lkw, mittlere Spurzahl, Ziel 20 % Wartende zu jeder Tageszeit"""

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import tva_constants as C
from tva_evaluation import PRECOMPUTED_PATH, study_cell_run


def _task(args):
    a, amp, period, raster, kind, idx = args
    return study_cell_run(a, amp, period, C.STUDY_ALPHA, raster, kind, C.STUDY_CUSTOMERS, seed=10_000 + 97 * idx, reps=C.STUDY_REPS)


def main(workers):
    t0 = time.time()
    jobs, idx = [], 0
    for a in C.STUDY_A:
        for amp in C.STUDY_AMP:
            for period in C.STUDY_PERIOD:
                for raster in C.STUDY_RASTER:
                    for kind in ("psa", "mol"):
                        jobs.append((a, amp, period, raster, kind, idx))
                        idx += 1
    with ProcessPoolExecutor(max_workers=workers) as ex:
        study = list(ex.map(_task, jobs))
    out = {"study_alpha": C.STUDY_ALPHA, "study_customers": C.STUDY_CUSTOMERS, "study_reps": C.STUDY_REPS, "study": study}
    Path(PRECOMPUTED_PATH).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"fertig in {time.time() - t0:.0f} s -> {PRECOMPUTED_PATH}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else min(6, os.cpu_count() or 1))
