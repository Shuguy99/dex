import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.research")


class ResearchAgent:
    def __init__(self, llm_client=None, rag_engine=None, vector_memory=None) -> None:
        self._llm = llm_client
        self._rag = rag_engine
        self._vector_memory = vector_memory
        self._reports_dir = Path("data/research")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def investigate(self, topic: str, depth: str = "standard") -> dict[str, Any]:
        logger.info(f"Research started: {topic} (depth={depth})")
        plan = self._create_research_plan(topic)
        findings = self._execute_plan(plan)
        report = self._synthesize_report(topic, findings)
        self._save_report(topic, report)
        return report

    def _create_research_plan(self, topic: str) -> list[dict[str, Any]]:
        if self._llm and self._llm.ready:
            schema = {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "source": {"type": "string", "enum": ["local", "web"]},
                                "purpose": {"type": "string"}
                            }
                        }
                    }
                }
            }
            prompt = (
                f"Create a research plan for topic: '{topic}'. "
                f"Generate 3-5 search queries to explore this topic thoroughly. "
                f"For each query, specify source (local for knowledge base, web for online)."
            )
            result = self._llm.generate_structured(prompt, schema)
            if result and "queries" in result:
                return result["queries"]

        return [
            {"query": topic, "source": "local", "purpose": "Основной поиск"},
            {"query": f"Что такое {topic}", "source": "local", "purpose": "Общее описание"},
        ]

    def _execute_plan(self, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
        findings = []
        for step in plan:
            query = step["query"]
            source = step.get("source", "local")
            logger.info(f"Research query: {query} ({source})")

            if source == "local" and self._rag:
                result = self._rag.query(query, use_llm=False)
                if result:
                    findings.append({
                        "query": query,
                        "source": "local",
                        "content": result,
                        "purpose": step.get("purpose", "")
                    })

            if source == "web" and self._llm and self._llm.ready:
                web_result = self._llm.generate(
                    f"Search the web and summarize information about: {query}",
                    system="You are a research assistant. Provide factual, structured information."
                )
                if web_result:
                    findings.append({
                        "query": query,
                        "source": "llm_knowledge",
                        "content": web_result,
                        "purpose": step.get("purpose", "")
                    })

        return findings

    def _synthesize_report(self, topic: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
        if not findings:
            return {
                "topic": topic,
                "summary": "Не удалось найти информацию по теме.",
                "sections": [],
                "sources_count": 0
            }

        if self._llm and self._llm.ready:
            context = "\n\n".join([
                f"[{f['source']}] {f['content'][:1000]}"
                for f in findings
            ])
            prompt = (
                f"Synthesize a structured research report on '{topic}' "
                f"based on the following findings. Include: summary, "
                f"key findings, conclusions.\n\n"
                f"Findings:\n{context}\n\n"
                f"Report (in Russian):"
            )
            synthesis = self._llm.generate(
                prompt,
                system="You write structured research reports.",
                temperature=0.3
            )
        else:
            lines = [f"Тема: {topic}", ""]
            for f in findings:
                lines.append(f"--- {f['purpose']} ---")
                lines.append(f["content"][:500])
            synthesis = "\n".join(lines)

        return {
            "topic": topic,
            "summary": synthesis[:500],
            "sections": [
                {"title": f.get("purpose", f"Query {i}"),
                 "content": f["content"][:300]}
                for i, f in enumerate(findings)
            ],
            "sources_count": len(findings),
            "timestamp": datetime.now().isoformat()
        }

    def _save_report(self, topic: str, report: dict[str, Any]):
        safe = "".join(c if c.isalnum() else "_" for c in topic[:30])
        path = self._reports_dir / f"report_{safe}_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Report saved: {path}")

    def fact_check(self, statement: str) -> dict[str, Any]:
        if not self._rag:
            return {"statement": statement, "match": False, "correction": None}

        results = self._rag.query(statement, use_llm=False)
        if not results or "не найдено" in results.lower():
            return {"statement": statement, "match": False, "correction": None}

        if self._llm and self._llm.ready:
            prompt = (
                f"Fact-check this statement against the provided knowledge. "
                f"If there's a contradiction, explain the correction.\n\n"
                f"Statement: {statement}\n\n"
                f"Knowledge base results:\n{results[:1000]}\n\n"
                f"Does the knowledge support or contradict? "
                f"Respond as JSON: {{\"supports\": bool, \"correction\": str|null}}"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "supports": {"type": "boolean"},
                    "correction": {"type": "string"}
                }
            })
            if result:
                return {
                    "statement": statement,
                    "match": result.get("supports", False),
                    "correction": result.get("correction"),
                    "evidence": results[:300]
                }

        return {"statement": statement, "match": True, "correction": None}

    def list_reports(self) -> list[dict[str, Any]]:
        reports = []
        for f_path in sorted(self._reports_dir.glob("*.json"), reverse=True)[:20]:
            try:
                with open(f_path, encoding="utf-8") as f:
                    data = json.load(f)
                reports.append({
                    "topic": data.get("topic", "unknown"),
                    "sources": data.get("sources_count", 0),
                    "timestamp": data.get("timestamp", ""),
                    "file": f_path.name
                })
            except Exception:
                pass
        return reports
