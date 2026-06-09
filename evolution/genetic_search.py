import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.evolution.genetic")


ARCHITECTURE_GENES = {
    "agent_count": [3, 5, 7, 10, 15],
    "topology": ["flat", "layered", "mesh", "hub"],
    "has_cache_layer": [True, False],
    "has_priority_queue": [True, False],
    "parallel_agents": [True, False],
    "agent_timeout": [5, 10, 15, 30],
    "max_retries": [1, 2, 3, 5],
    "use_llm_routing": [True, False]
}


class GeneticArchitectureSearch:
    def __init__(self, llm_client=None, user_simulator=None) -> None:
        self._llm = llm_client
        self._simulator = user_simulator
        self._data_dir = Path("data/evolution")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._pop_path = self._data_dir / "genetic_population.json"
        self._population: list[dict[str, Any]] = self._load_population()
        self._generation = 0
        self._best_fitness = 0.0

    def _load_population(self) -> list[dict[str, Any]]:
        if self._pop_path.exists():
            try:
                with open(self._pop_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_population(self) -> None:
        with open(self._pop_path, "w", encoding="utf-8") as f:
            json.dump(self._population[-100:], f, ensure_ascii=False, indent=2)

    def _random_genome(self) -> dict[str, Any]:
        return {
            key: random.choice(values)
            for key, values in ARCHITECTURE_GENES.items()
        }

    def _mutate(self, genome: dict[str, Any], rate: float = 0.3) -> dict[str, Any]:
        mutated = dict(genome)
        for key in ARCHITECTURE_GENES:
            if random.random() < rate:
                mutated[key] = random.choice(ARCHITECTURE_GENES[key])
        return mutated

    def _crossover(self, parent1: dict[str, Any],
                    parent2: dict[str, Any]) -> dict[str, Any]:
        child = {}
        for key in ARCHITECTURE_GENES:
            child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
        return child

    def _fitness(self, genome: dict[str, Any]) -> float:
        score = 0.5
        if genome.get("has_cache_layer"):
            score += 0.15
        if genome.get("has_priority_queue"):
            score += 0.1
        if genome.get("parallel_agents"):
            score += 0.1
        if genome.get("use_llm_routing"):
            score += 0.05
        agent_count = genome.get("agent_count", 5)
        if 5 <= agent_count <= 10:
            score += 0.1
        topology = genome.get("topology", "flat")
        if topology == "layered":
            score += 0.1
        elif topology == "mesh":
            score += 0.05
        timeout = genome.get("agent_timeout", 10)
        score -= abs(timeout - 10) * 0.01
        score = max(0.1, min(1.0, score))
        return score

    def _simulate_fitness(self, genome: dict[str, Any]) -> float:
        base = self._fitness(genome)

        if self._simulator:
            try:
                json.dumps(genome, ensure_ascii=False)
                report = self._simulator.run_session(
                    lambda cmd: f"Simulated: {cmd}",
                    num_commands=5
                )
                error_rate = report.get("error_rate", 0.5)
                base *= (1.0 - error_rate * 0.3)
            except Exception:
                pass

        return base

    def seed_population(self, size: int = 10) -> None:
        self._population = []
        for _ in range(size):
            genome = self._random_genome()
            fitness = self._simulate_fitness(genome)
            self._population.append({
                "genome": genome,
                "fitness": fitness,
                "generation": 0,
                "created": datetime.now().isoformat()
            })
        self._population.sort(key=lambda x: -x["fitness"])
        self._best_fitness = self._population[0]["fitness"]
        self._save_population()
        logger.info(f"Seed population: {size} individuals")

    def evolve(self, generations: int = 5, population_size: int = 10) -> dict[str, Any]:
        if not self._population:
            self.seed_population(population_size)

        history = []
        for _gen in range(generations):
            self._generation += 1
            next_gen = []

            top = self._population[:max(2, population_size // 3)]
            next_gen.extend(top)

            while len(next_gen) < population_size:
                parent1 = random.choice(top)
                parent2 = random.choice(self._population[:population_size // 2])
                child_genome = self._crossover(parent1["genome"], parent2["genome"])
                child_genome = self._mutate(child_genome)
                fitness = self._simulate_fitness(child_genome)
                next_gen.append({
                    "genome": child_genome,
                    "fitness": fitness,
                    "generation": self._generation,
                    "created": datetime.now().isoformat()
                })

            next_gen.sort(key=lambda x: -x["fitness"])
            self._population = next_gen[:population_size]
            self._best_fitness = self._population[0]["fitness"]

            history.append({
                "generation": self._generation,
                "best_fitness": self._best_fitness,
                "avg_fitness": sum(i["fitness"] for i in self._population) / len(self._population)
            })
            logger.info(f"Gen {self._generation}: best={self._best_fitness:.3f}")

        self._save_population()
        best = self._population[0]
        return {
            "best_genome": best["genome"],
            "best_fitness": best["fitness"],
            "generations_run": generations,
            "history": history,
            "population_size": len(self._population)
        }

    def get_genetic_summary(self) -> str:
        if not self._population:
            return "Population empty. Run seed or evolve."
        best = self._population[0]
        lines = ["── Genetic Architecture Search ──"]
        lines.append(f"Generation: {self._generation}")
        lines.append(f"Population: {len(self._population)}")
        lines.append(f"Best fitness: {self._best_fitness:.3f}")
        lines.append("Best genome:")
        for key, val in best["genome"].items():
            lines.append(f"  {key}: {val}")
        return "\n".join(lines)
