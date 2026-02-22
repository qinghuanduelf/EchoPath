"""
Email Generator — RAG-based personalized icebreaker email generation.
Dynamic English-language prompt construction with OpenAI (primary) + fallback.
"""

from typing import Optional

# Async OpenAI client (optional — graceful if not installed)
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from backend.config import OPENAI_API_KEY
from backend.services.llm_service import LLMService


class EmailGenerator:
    """Generate personalized icebreaker emails using structured RAG prompts.
    All generated content is in English (target users are American students).
    """

    def __init__(
        self,
        openai_api_key: str = "",
        rapidfire_client=None,
        llm_service: Optional[LLMService] = None,
    ):
        self.api_key = openai_api_key or OPENAI_API_KEY
        self.rapidfire = rapidfire_client
        self.llm_service = llm_service
        self.last_generation_metadata = {
            "provider": "template",
            "model": "",
            "used_fallback": False,
        }

    async def generate_email(
        self,
        student: dict,
        mentor: dict,
        match_score: float,
    ) -> str:
        """Generate an icebreaker email. Falls back through providers."""
        prompt = self.build_prompt(student, mentor, match_score)

        # Preferred path: unified LLM service with configured provider order
        if self.llm_service:
            try:
                result = await self.llm_service.generate_email(
                    prompt=prompt,
                    context_documents=[mentor],
                    temperature=0.7,
                    max_tokens=500,
                )
                self.last_generation_metadata = {
                    "provider": result.provider,
                    "model": result.model,
                    "used_fallback": result.used_fallback,
                }
                return result.text
            except Exception as e:
                print(f"LLMService failed, falling back to legacy chain: {e}")

        # Primary: Rapidfire AI (if available)
        if self.rapidfire:
            try:
                text = await self.rapidfire.generate(
                    prompt=prompt,
                    context_documents=[mentor],
                    temperature=0.7,
                    max_tokens=500,
                )
                self.last_generation_metadata = {
                    "provider": "rapidfire",
                    "model": "rapidfire-default",
                    "used_fallback": False,
                }
                return text
            except Exception as e:
                print(f"Rapidfire AI failed, falling back to OpenAI: {e}")

        # Fallback: OpenAI
        if HAS_OPENAI and self.api_key:
            try:
                client = openai.AsyncOpenAI(api_key=self.api_key)
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500,
                )
                self.last_generation_metadata = {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "used_fallback": self.rapidfire is not None,
                }
                return response.choices[0].message.content or ""
            except Exception as e:
                print(f"OpenAI API failed: {e}")

        # Final fallback: return the prompt itself as a template
        self.last_generation_metadata = {
            "provider": "template",
            "model": "",
            "used_fallback": True,
        }
        return (
            "[Email generation requires an API key. "
            "Below is the prompt that would be sent to the LLM:]\n\n"
            + prompt
        )

    def get_last_generation_metadata(self) -> dict:
        """Metadata for the latest successful/attempted generation."""
        return dict(self.last_generation_metadata)

    def build_prompt(
        self, student: dict, mentor: dict, match_score: float
    ) -> str:
        """Dynamically build the email generation prompt (English)."""
        common_origin = self._find_common_origin(student, mentor)
        career_highlights = self._extract_highlights(mentor)

        position = mentor.get("position", {})
        company = position.get("company", {})

        prompt = f"""You are a professional career advisor helping a student write an icebreaker email to a potential mentor.

## Student Info
- Location: {student.get('location', 'N/A')} (FIPS: {student.get('fips_code', 'N/A')})
- Economic Hardship Index: {student.get('hardship_score', 0.5):.2f}
- Current Education: {student.get('current_education', 'N/A')}
- Target Career: {student.get('target_function', 'N/A')} — {student.get('target_level', 'N/A')}
- Personal Note: "{student.get('dream_description', 'N/A')}"

## Mentor Info (Match Score: {match_score:.1%})
- Current Role: {position.get('title', 'N/A')} @ {company.get('name', 'N/A')}
- Level: {position.get('level', 'N/A')}
- Industry: {company.get('industry', 'N/A')}
- Education: {self._format_education(mentor.get('education', []))}
- Career Path: {career_highlights}

## Shared Connections
{common_origin}

## Writing Guidelines
1. Tone: Sincere and confident, showing the student's self-drive
2. Explicitly mention shared starting points (geography / school background)
3. Reference a specific part of the mentor's career journey
4. Make a specific, low-commitment ask (e.g., 15-minute call)
5. Keep it 150-200 words
6. Write in English

Output the email body directly."""
        return prompt

    def _find_common_origin(self, student: dict, mentor: dict) -> str:
        """Identify shared starting points between student and mentor."""
        commons = []

        # Geographic overlap
        student_fips = student.get("fips_code", "")
        mentor_fips_codes = set()
        for job in mentor.get("jobs", []):
            loc = job.get("location_details", {}) or {}
            fips = loc.get("fips_code", "")
            if fips:
                mentor_fips_codes.add(fips)

        # Also check origin_fips
        origin_fips = mentor.get("origin_fips", "")
        if origin_fips:
            mentor_fips_codes.add(origin_fips)

        if student_fips and student_fips in mentor_fips_codes:
            commons.append(f"- Same region (FIPS: {student_fips})")
        elif student_fips and any(f[:2] == student_fips[:2] for f in mentor_fips_codes if f):
            commons.append(f"- Same state")

        # School overlap
        student_school = student.get("school_name", "") or ""
        mentor_schools = set()
        for e in mentor.get("education", []):
            s = e.get("school", "") if isinstance(e, dict) else ""
            if s:
                mentor_schools.add(s)

        if student_school and student_school in mentor_schools:
            commons.append(f"- Same school: {student_school}")

        return "\n".join(commons) if commons else "- Similar starting background and geographic area"

    def _extract_highlights(self, mentor: dict) -> str:
        """Extract the last 3 career positions as highlights."""
        jobs = mentor.get("jobs", [])
        sorted_jobs = sorted(
            [j for j in jobs if j.get("title")],
            key=lambda j: j.get("started_at", "") or "",
        )
        highlights = []
        for job in sorted_jobs[-3:]:
            co = job.get("company", {}).get("name", "Unknown")
            title = job.get("title", "Unknown")
            highlights.append(f"{title} @ {co}")
        return " → ".join(highlights) if highlights else "N/A"

    def _format_education(self, education: list) -> str:
        """Format education list into readable string."""
        parts = []
        for e in education:
            if isinstance(e, dict):
                degree = e.get("degree", "N/A")
                field = e.get("field", "N/A")
                school = e.get("school", "N/A")
                parts.append(f"{degree} in {field} @ {school}")
        return "; ".join(parts) if parts else "N/A"
