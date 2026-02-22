"""
Path Planner — Rapidfire-first path ranking with deterministic fallback.
"""

import json
import re

from backend.engines.path_builder import PathBuilder
from backend.models.path import CareerPath
from backend.services.llm_service import LLMService


class PathPlanner:
    """Plan and rank career paths using Rapidfire + RAG evidence."""

    def __init__(self, path_builder: PathBuilder, llm_service: LLMService | None = None):
        self.path_builder = path_builder
        self.llm_service = llm_service
        # Global in-memory exposure counter to reduce repeated path templates.
        self._path_impression_counts: dict[str, int] = {}

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
            top_n=max(top_n, 12),
        )
        rag_hits = rag_hits or []
        evidence_count = len({h.get("profile_id", "") for h in rag_hits if h.get("profile_id")})

        if not base_paths:
            return [], {"source": "fallback", "evidence_count": evidence_count}

        if not self.llm_service or not rag_hits:
            selected = self._select_diverse_paths(base_paths, top_n)
            fallback_paths = [
                p.model_copy(
                    update={
                        "source": "fallback",
                        "confidence": 0.55,
                        "evidence_count": evidence_count,
                    }
                )
                for p in selected
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
            selected = self._select_diverse_paths(base_paths, top_n)
            fallback_paths = [
                p.model_copy(
                    update={
                        "source": "fallback",
                        "confidence": 0.55,
                        "evidence_count": evidence_count,
                    }
                )
                for p in selected
            ]
            return fallback_paths, {"source": "fallback", "evidence_count": evidence_count}

    @staticmethod
    def _path_signature(path: CareerPath) -> set[str]:
        """
        Normalize path labels into a token set for simple similarity checks.
        """
        text = " ".join(node.label.lower() for node in path.nodes)
        return set(re.findall(r"[a-z0-9]+", text))

    def _path_signature_key(self, path: CareerPath) -> str:
        # Stable key for repetition tracking across requests.
        return " | ".join(node.label.strip().lower() for node in path.nodes)

    def _select_diverse_paths(self, paths: list[CareerPath], top_n: int) -> list[CareerPath]:
        """
        Greedy diversity selection from candidate paths.
        Keeps high-support paths while avoiding near-duplicates.
        """
        if len(paths) <= top_n:
            return paths[:top_n]

        max_people = max((p.total_people for p in paths), default=1) or 1
        selected: list[CareerPath] = []
        selected_signatures: list[set[str]] = []
        remaining = list(paths)

        while remaining and len(selected) < top_n:
            min_seen_in_pool = min(
                self._path_impression_counts.get(self._path_signature_key(p), 0)
                for p in remaining
            )
            best_idx = 0
            best_score = -1.0
            for idx, candidate in enumerate(remaining):
                support = candidate.total_people / max_people
                sig = self._path_signature(candidate)
                seen = self._path_impression_counts.get(self._path_signature_key(candidate), 0)
                freshness = 1.0 / (1.0 + seen)
                if not selected:
                    if seen > min_seen_in_pool:
                        # Force first pick to rotate toward less-exposed templates.
                        continue
                    # For the first pick, balance quality with anti-repeat freshness.
                    score = 0.60 * support + 0.40 * freshness
                    if score > best_score:
                        best_score = score
                        best_idx = idx
                    continue
                max_overlap = 0.0
                for picked in selected_signatures:
                    union = len(sig | picked) or 1
                    overlap = len(sig & picked) / union
                    if overlap > max_overlap:
                        max_overlap = overlap
                novelty = 1.0 - max_overlap
                # Bias toward diversity while preserving path quality, and penalize repeats.
                score = 0.45 * novelty + 0.35 * support + 0.20 * freshness
                if score > best_score:
                    best_score = score
                    best_idx = idx

            chosen = remaining.pop(best_idx)
            selected.append(chosen)
            selected_signatures.append(self._path_signature(chosen))

        # Update repetition memory with selected items.
        for path in selected:
            key = self._path_signature_key(path)
            self._path_impression_counts[key] = self._path_impression_counts.get(key, 0) + 1

        return selected

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
