"""
Path Planner — Rapidfire-first path ranking with deterministic fallback.
"""

import json

from backend.engines.path_builder import PathBuilder
from backend.models.path import CareerPath
from backend.services.llm_service import LLMService


class PathPlanner:
    """Plan and rank career paths using Rapidfire + RAG evidence."""

    def __init__(self, path_builder: PathBuilder, llm_service: LLMService | None = None):
        self.path_builder = path_builder
        self.llm_service = llm_service

    async def plan_paths(
        self,
        student: dict,
        matched_profiles: list[dict],
        rag_hits: list[dict] | None = None,
        top_n: int = 3,
    ) -> tuple[list[CareerPath], dict]:
        base_paths = self.path_builder.build_paths(
            matched_profiles,
            target_function=student.get("target_function", ""),
            top_n=max(top_n, 5),
        )
        rag_hits = rag_hits or []
        evidence_count = len({h.get("profile_id", "") for h in rag_hits if h.get("profile_id")})

        if not base_paths:
            return [], {"source": "fallback", "evidence_count": evidence_count}

        if not self.llm_service or not rag_hits:
            fallback_paths = [
                p.model_copy(
                    update={
                        "source": "fallback",
                        "confidence": 0.55,
                        "evidence_count": evidence_count,
                    }
                )
                for p in base_paths[:top_n]
            ]
            return fallback_paths, {"source": "fallback", "evidence_count": evidence_count}

        try:
            ranked_indices = await self._rapidfire_rank(student, base_paths, rag_hits, top_n)
            ranked_paths: list[CareerPath] = []
            for rank, idx in enumerate(ranked_indices):
                if idx < 0 or idx >= len(base_paths):
                    continue
                conf = max(0.5, round(0.9 - rank * 0.1, 3))
                ranked_paths.append(
                    base_paths[idx].model_copy(
                        update={
                            "source": "rapidfire",
                            "confidence": conf,
                            "evidence_count": evidence_count,
                        }
                    )
                )

            if not ranked_paths:
                raise RuntimeError("Rapidfire returned no valid ranked path ids")

            return ranked_paths[:top_n], {"source": "rapidfire", "evidence_count": evidence_count}
        except Exception as e:
            print(f"Rapidfire path planner failed, fallback to PathBuilder: {e}")
            fallback_paths = [
                p.model_copy(
                    update={
                        "source": "fallback",
                        "confidence": 0.55,
                        "evidence_count": evidence_count,
                    }
                )
                for p in base_paths[:top_n]
            ]
            return fallback_paths, {"source": "fallback", "evidence_count": evidence_count}

    async def _rapidfire_rank(
        self,
        student: dict,
        paths: list[CareerPath],
        rag_hits: list[dict],
        top_n: int,
    ) -> list[int]:
        path_summaries = []
        for idx, path in enumerate(paths):
            labels = " -> ".join(node.label for node in path.nodes)
            path_summaries.append(
                f"idx={idx}; people={path.total_people}; years={path.avg_years}; labels={labels}"
            )

        evidence_lines = []
        for hit in rag_hits[:12]:
            evidence_lines.append(
                f"profile={hit.get('profile_id','')}; sim={float(hit.get('similarity',0.0)):.3f}; text={str(hit.get('chunk_text',''))[:220]}"
            )

        prompt = f"""
You are ranking candidate career paths for a student using retrieved historical evidence.
Return JSON only: {{"ranked_path_indices":[int,...]}}.
No explanation text.

Student:
- current_education: {student.get("current_education", "N/A")}
- target_function: {student.get("target_function", "N/A")}
- target_level: {student.get("target_level", "N/A")}
- hardship_score: {student.get("hardship_score", 0.5):.2f}
- fips_code: {student.get("fips_code", "N/A")}

Candidate paths:
{chr(10).join(path_summaries)}

Retrieved evidence:
{chr(10).join(evidence_lines)}

Requirements:
1) Prefer paths aligned with target_function and realistic level progression.
2) Use retrieved evidence as primary basis.
3) Return top {top_n} unique indices.
"""
        result = await self.llm_service.generate_with_provider(
            provider="rapidfire",
            prompt=prompt,
            context_documents=[],
            temperature=0.2,
            max_tokens=250,
        )
        return self._parse_ranked_indices(result.text, top_n=top_n)

    @staticmethod
    def _parse_ranked_indices(text: str, top_n: int) -> list[int]:
        text = text.strip()
        if not text:
            return []

        # Best effort extraction for JSON body
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]

        payload = json.loads(text)
        indices = payload.get("ranked_path_indices", [])
        if not isinstance(indices, list):
            return []

        clean: list[int] = []
        for val in indices:
            try:
                idx = int(val)
            except (TypeError, ValueError):
                continue
            if idx not in clean:
                clean.append(idx)
            if len(clean) >= top_n:
                break
        return clean
