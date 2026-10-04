import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class ScriptedRng:
    """Liefert vorgegebene Werte statt Zufall (Mini-Instanzen von Hand gerechnet). `expovariate(rate)` ignoriert die Rate und gibt der
    Reihe nach die Werte zurück, `uniform()` ebenso aus einer eigenen Liste."""

    def __init__(self, exp_values=(), uniform_values=()):
        self.exp_values, self.uniform_values = list(exp_values), list(uniform_values)
        self.n_exp = self.n_uniform = 0

    def expovariate(self, rate):
        v = self.exp_values[self.n_exp]
        self.n_exp += 1
        return v

    def uniform(self):
        v = self.uniform_values[self.n_uniform]
        self.n_uniform += 1
        return v


@pytest.fixture
def growing_capacity_streams():
    """Periode 4 min, Spurzahl je Minute [1, 1, 2, 2], 2 Phasen (0 bis 2, 2 bis 4), Angebot konstant (Amplitude 0, Annahme immer).
    Kandidaten bei 0.5, 1.0, 1.5, 3.5 (Abstände 0.5 / 0.5 / 0.5 / 2.0, danach 100), Abfertigungen 2.5 / 2.5 / 0.4 / 0.2.
    Von Hand: Lkw 1 startet bei 0.5 (Abgang 3.0); Lkw 2 und 3 warten; bei 2.0 wächst die Spurzahl auf 2: Lkw 2 startet (Abgang 4.5);
    bei 3.0 geht Lkw 1, Lkw 3 startet (Abgang 3.4); Lkw 4 findet bei 3.5 eine freie Spur (Abgang 3.7)."""
    return (ScriptedRng(exp_values=[0.5, 0.5, 0.5, 2.0, 100.0]), ScriptedRng(uniform_values=[0.0] * 5),
            ScriptedRng(exp_values=[2.5, 2.5, 0.4, 0.2]))


@pytest.fixture
def shrinking_capacity_streams():
    """Periode 4 min, Spurzahl je Minute [2, 2, 1, 1]. Kandidaten bei 0.5, 1.0, 2.5 (Abstände 0.5 / 0.5 / 1.5, danach 100),
    Abfertigungen 3.2 / 3.2 / 0.3. Von Hand: Lkw 1 und 2 starten sofort (Abgang 3.7 und 4.2); bei 2.0 sinkt die Spurzahl auf 1 bei 2
    Beschäftigten: Lkw 3 (Ankunft 2.5) wartet, auch nach dem Abgang von Lkw 1 bei 3.7 (1 Beschäftigter, Spurzahl 1); erst bei 4.0
    (Spurzahl wieder 2) startet er (Wartezeit 1.5)."""
    return (ScriptedRng(exp_values=[0.5, 0.5, 1.5, 100.0]), ScriptedRng(uniform_values=[0.0] * 4),
            ScriptedRng(exp_values=[3.2, 3.2, 0.3]))
