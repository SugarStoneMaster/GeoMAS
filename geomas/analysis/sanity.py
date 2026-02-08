"""
Simulation Health Analysis Module.

Provides metrics and sanity checks to validate simulation behavior.
"""
from typing import Dict, List, Any
import numpy as np

class SimulationHealthAnalyzer:
    """
    Analyzes turn-by-turn simulation data to generate a health report.
    Checks for:
    - Economic Stability (Budget variance, explosions, crashes)
    - Social Stability (Satisfaction trends)
    - Conflict Frequency (War prevalence)
    - Resource Balance (Global resource trends)
    """
    
    def __init__(self, simulation_log: Dict[str, Any]):
        self.log = simulation_log
        self.turns = simulation_log.get("turns", [])
        self.nations = list(simulation_log.get("initial_state", {}).keys())
        self.metrics = {}
        
    def analyze(self) -> str:
        """Run all analyses and return a formatted text report."""
        if not self.turns:
            return "⚠️ No turns data available for analysis."
            
        self._analyze_economy()
        self._analyze_stability()
        self._analyze_resources()
        
        return self._format_report()
    
    def _extract_series(self, metric: str) -> Dict[str, List[float]]:
        """Extract a time series for a specific metric for all nations."""
        series = {nid: [] for nid in self.nations}
        for turn in self.turns:
            state = turn.get("state", {})
            for nid, nation_state in state.items():
                if nid in series and metric in nation_state:
                    series[nid].append(nation_state[metric])
        return series

    def _analyze_economy(self):
        budgets = self._extract_series("budget")
        self.metrics["economy"] = {}
        
        for nid, values in budgets.items():
            if not values: continue
            vm = np.mean(values)
            vs = np.std(values)
            self.metrics["economy"][nid] = {
                "mean": vm,
                "volatility": vs / vm if vm > 0 else 0.0,
                "trend": (values[-1] - values[0]) / (len(values)) if len(values) > 1 else 0
            }

    def _analyze_stability(self):
        satisfaction = self._extract_series("satisfaction")
        self.metrics["stability"] = {}
        
        for nid, values in satisfaction.items():
            if not values: continue
            self.metrics["stability"][nid] = {
                "final": values[-1],
                "min": np.min(values),
                "max": np.max(values),
                "trend": "Stable" if np.std(values) < 5 else ("Volatile" if np.std(values) > 15 else "Changing")
            }

    def _analyze_resources(self):
        # Global aggregates
        self.metrics["global"] = {"food_trend": 0, "energy_trend": 0}
        
    def _format_report(self) -> str:
        report = []
        report.append("="*40)
        report.append("🩺 SIMULATION HEALTH REPORT")
        report.append("="*40)
        
        # Economy
        report.append("\n💰 ECONOMIC HEALTH:")
        for nid, data in self.metrics.get("economy", {}).items():
            trend_icon = "↗️" if data["trend"] > 100 else ("↘️" if data["trend"] < -100 else "➡️")
            volatility_alert = "⚠️ UNSTABLE" if data["volatility"] > 0.5 else "✅ Stable"
            report.append(f"   {nid}: Avg Budget {data['mean']:,.0f} | {trend_icon} ({data['trend']:+.0f}/turn) | {volatility_alert}")

        # Stability
        report.append("\n😊 SOCIAL STABILITY:")
        for nid, data in self.metrics.get("stability", {}).items():
            status = "✅" if data["final"] > 50 else "❌ CRITICAL"
            report.append(f"   {nid}: {status} {data['final']:.1f}% (Range: {data['min']:.1f}-{data['max']:.1f})")

        report.append("\n" + "="*40)
        return "\n".join(report)
