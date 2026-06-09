import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.resource.model_evaluator")

BENCHMARK_PROMPTS = {
    "chat": [
        "Расскажи в трёх предложениях, что такое квантовая запутанность.",
        "Напиши короткое письмо-извинение коллеге.",
        "Объясни разницу между SQL и NoSQL простыми словами.",
    ],
    "rag": [
        "На основе документов: Земля вращается вокруг Солнца. Ответь: какая планета ближе всех к Солнцу?",
        "Контекст: 2+2=4. Вопрос: сколько будет 2+2?",
    ],
    "planner": [
        "Распиши план: приготовить ужин на 4 персоны за 2 часа.",
        "Спланируй рабочую неделю: 3 встречи, 2 дедлайна, 1 презентация.",
    ],
    "code": [
        "Напиши функцию на Python для сортировки списка чисел без использования встроенной sorted().",
        "Напиши SQL запрос: найти всех пользователей старше 18 лет, сделавших заказ в последний месяц.",
    ],
    "research": [
        "Суммиризируй: Искусственный интеллект — это область компьютерных наук, занимающаяся созданием систем, способных выполнять задачи, требующие человеческого интеллекта.",
    ],
    "ethics": [
        "Оцени этичность: компания собирает данные пользователей без их явного согласия для улучшения продукта.",
    ],
    "personality": [
        "Представься как дружелюбный ассистент. Расскажи о себе в двух предложениях.",
    ],
}


class ModelEvaluator:
    def __init__(self, data_dir: str = "data/evaluator") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._results_file = self._data_dir / "eval_results.json"
        self._results: list[dict[str, Any]] = self._load_results()

    def _load_results(self) -> list[dict[str, Any]]:
        if self._results_file.exists():
            try:
                return json.loads(self._results_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_results(self) -> None:
        self._results_file.write_text(
            json.dumps(self._results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def evaluate_model(self, model_name: str, llm_client: Any,
                       purposes: list[str] | None = None) -> dict[str, Any]:
        results: dict[str, Any] = {
            "model": model_name,
            "date": datetime.now().isoformat(),
            "purposes": {},
            "overall_score": 0.0,
        }
        total_score = 0.0
        total_weight = 0

        purposes_to_run = purposes or list(BENCHMARK_PROMPTS.keys())
        for purpose in purposes_to_run:
            prompts = BENCHMARK_PROMPTS.get(purpose, [])
            if not prompts:
                continue

            purpose_result = self._eval_purpose(model_name, purpose, prompts, llm_client)
            results["purposes"][purpose] = purpose_result
            total_score += purpose_result.get("avg_score", 0.0) * len(prompts)
            total_weight += len(prompts)

        results["overall_score"] = round(total_score / total_weight, 4) if total_weight else 0.0
        results["overall_score_pct"] = round(results["overall_score"] * 100, 1)

        self._results.append(results)
        self._save_results()
        logger.info(f"Evaluated {model_name}: {results['overall_score_pct']}%")
        return results

    def _eval_purpose(self, model_name: str, purpose: str,
                      prompts: list[str], llm_client: Any) -> dict[str, Any]:
        per_prompt: list[dict[str, Any]] = []
        scores: list[float] = []

        for prompt in prompts:
            start = time.time()
            try:
                response = llm_client.generate(prompt, model=model_name, temperature=0.3)
                elapsed = time.time() - start
                score = self._score_response(prompt, response)
                scores.append(score)
                per_prompt.append({
                    "prompt": prompt[:80],
                    "response_len": len(response),
                    "time_s": round(elapsed, 2),
                    "score": score,
                    "error": None,
                })
                logger.debug(f"[{purpose}] {model_name} scored {score:.2f} in {elapsed:.1f}s")
            except Exception as e:
                per_prompt.append({
                    "prompt": prompt[:80],
                    "response_len": 0,
                    "time_s": 0,
                    "score": 0.0,
                    "error": str(e),
                })
                scores.append(0.0)

        time_values = [float(p["time_s"]) for p in per_prompt]
        return {
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "avg_time_s": round(sum(time_values) / len(per_prompt), 2) if per_prompt else 0,
            "total_time_s": round(sum(time_values), 2),
            "prompts": per_prompt,
        }

    def _score_response(self, prompt: str, response: str) -> float:
        score = 0.5
        r_lower = response.lower()
        if len(response) < 10:
            score -= 0.3
        if len(response) > 500:
            score += 0.1
        if any(w in r_lower for w in ["извини", "не могу", "не знаю"]):
            score -= 0.2
        if any(w in r_lower for w in ["вот", "надеюсь", "помог"]):
            score += 0.1
        return max(0.0, min(1.0, score))

    def get_best_model(self, purpose: str) -> str | None:
        if not self._results:
            return None
        best = None
        best_score = -1.0
        for r in self._results:
            purp = r.get("purposes", {}).get(purpose)
            if purp:
                s = purp.get("avg_score", 0)
                if s > best_score:
                    best_score = s
                    best = r["model"]
        return best

    def model_summary(self, model_name: str) -> dict[str, Any] | None:
        for r in self._results:
            if r["model"] == model_name:
                return r
        return None

    def history(self) -> list[dict[str, Any]]:
        return list(self._results)

    def clear(self) -> None:
        self._results = []
        self._save_results()
