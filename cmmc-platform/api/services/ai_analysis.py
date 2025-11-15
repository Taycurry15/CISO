"""
AI Control Analysis Service
Analyzes CMMC controls using GPT-4 and Claude with RAG-enhanced context
"""

import os
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

import asyncpg

from .rag_engine import RAGEngine, RAGContext
from .confidence_scorer import ConfidenceScorer, ConfidenceFactors

logger = logging.getLogger(__name__)


class FindingStatus(str, Enum):
    """Control finding status per CMMC assessment"""
    MET = "Met"
    NOT_MET = "Not Met"
    PARTIALLY_MET = "Partially Met"
    NOT_APPLICABLE = "Not Applicable"
    NOT_ASSESSED = "Not Assessed"


class AIModel(str, Enum):
    """Available AI models"""
    GPT4_TURBO = "gpt-4-turbo-preview"
    GPT4 = "gpt-4"
    CLAUDE_35_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"


@dataclass
class EvidenceReference:
    """Reference to evidence used in analysis"""
    evidence_id: str
    document_id: str
    document_title: str
    chunk_text: str
    relevance_score: float
    evidence_type: Optional[str] = None


@dataclass
class ProviderInheritance:
    """Provider inheritance information"""
    provider_name: str
    responsibility: str  # Inherited, Shared, Customer
    inherited_controls: List[str]
    documentation_url: Optional[str] = None
    narrative: Optional[str] = None


@dataclass
class FindingResult:
    """Result of AI control analysis"""
    control_id: str
    objective_id: Optional[str]
    status: FindingStatus
    assessor_narrative: str
    ai_confidence_score: float
    ai_rationale: str
    evidence_references: List[EvidenceReference]
    provider_inheritance: Optional[ProviderInheritance]
    model_used: str
    tokens_used: int
    analysis_timestamp: datetime
    requires_human_review: bool


class AIAnalysisService:
    """
    AI-powered control analysis service for CMMC compliance

    Features:
    - Multi-model support (GPT-4, Claude)
    - RAG-enhanced context retrieval
    - Evidence traceability
    - Confidence scoring
    - Provider inheritance integration
    - Structured output with reasoning
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        rag_engine: RAGEngine,
        confidence_scorer: ConfidenceScorer,
        primary_model: AIModel = AIModel.GPT4_TURBO,
        fallback_model: Optional[AIModel] = AIModel.CLAUDE_35_SONNET,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        """
        Initialize AI analysis service

        Args:
            db_pool: Database connection pool
            rag_engine: RAG engine for context retrieval
            confidence_scorer: Confidence scoring service
            primary_model: Primary AI model to use
            fallback_model: Fallback model if primary fails
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
        """
        self.db_pool = db_pool
        self.rag_engine = rag_engine
        self.confidence_scorer = confidence_scorer
        self.primary_model = primary_model
        self.fallback_model = fallback_model

        # Initialize OpenAI client
        if primary_model.value.startswith('gpt') or (fallback_model and fallback_model.value.startswith('gpt')):
            if AsyncOpenAI is None:
                raise ImportError("openai package required. Install with: pip install openai")

            self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if not self.openai_api_key:
                raise ValueError("OpenAI API key required")

            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None

        # Initialize Anthropic client
        if primary_model.value.startswith('claude') or (fallback_model and fallback_model.value.startswith('claude')):
            if AsyncAnthropic is None:
                raise ImportError("anthropic package required. Install with: pip install anthropic")

            self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key required")

            self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = None

        logger.info(f"Initialized AI Analysis Service with {primary_model.value} (fallback: {fallback_model})")

    async def get_control_details(
        self,
        control_id: str
    ) -> Dict[str, Any]:
        """
        Get control details from database

        Args:
            control_id: Control ID (e.g., "AC.L2-3.1.1")

        Returns:
            Control details dictionary
        """
        async with self.db_pool.acquire() as conn:
            control = await conn.fetchrow("""
                SELECT
                    c.id,
                    c.control_number,
                    c.title,
                    c.requirement_text,
                    c.discussion,
                    c.nist_800_171_ref,
                    c.cmmc_level,
                    cd.name as domain_name
                FROM controls c
                JOIN control_domains cd ON c.domain_id = cd.id
                WHERE c.id = $1
            """, control_id)

            if not control:
                raise ValueError(f"Control {control_id} not found")

            return dict(control)

    async def get_assessment_objectives(
        self,
        control_id: str,
        objective_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get assessment objectives for control

        Args:
            control_id: Control ID
            objective_id: Specific objective ID (optional)

        Returns:
            List of assessment objectives
        """
        async with self.db_pool.acquire() as conn:
            if objective_id:
                objectives = await conn.fetch("""
                    SELECT id, objective_letter, method, determination_statement, potential_assessment_methods
                    FROM assessment_objectives
                    WHERE control_id = $1 AND id = $2
                """, control_id, objective_id)
            else:
                objectives = await conn.fetch("""
                    SELECT id, objective_letter, method, determination_statement, potential_assessment_methods
                    FROM assessment_objectives
                    WHERE control_id = $1
                    ORDER BY objective_letter
                """, control_id)

            return [dict(obj) for obj in objectives]

    async def get_provider_inheritance(
        self,
        control_id: str,
        assessment_id: str
    ) -> Optional[ProviderInheritance]:
        """
        Get provider inheritance information for control

        Args:
            control_id: Control ID
            assessment_id: Assessment ID

        Returns:
            Provider inheritance details if applicable
        """
        async with self.db_pool.acquire() as conn:
            inheritance = await conn.fetchrow("""
                SELECT
                    po.provider_name,
                    pci.responsibility,
                    pci.inherited_narrative,
                    pci.documentation_url
                FROM provider_control_inheritance pci
                JOIN provider_offerings po ON pci.provider_offering_id = po.id
                JOIN assessments a ON a.organization_id = po.organization_id
                WHERE pci.control_id = $1 AND a.id = $2
                LIMIT 1
            """, control_id, assessment_id)

            if not inheritance:
                return None

            return ProviderInheritance(
                provider_name=inheritance['provider_name'],
                responsibility=inheritance['responsibility'],
                inherited_controls=[control_id],
                documentation_url=inheritance['documentation_url'],
                narrative=inheritance['inherited_narrative']
            )

    def build_analysis_prompt(
        self,
        control: Dict[str, Any],
        objectives: List[Dict[str, Any]],
        rag_context: RAGContext,
        provider_inheritance: Optional[ProviderInheritance] = None
    ) -> Tuple[str, str]:
        """
        Build prompt for AI analysis

        Args:
            control: Control details
            objectives: Assessment objectives
            rag_context: Retrieved evidence context
            provider_inheritance: Provider inheritance info

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # System prompt
        system_prompt = """You are an expert CMMC Level 2 assessor with deep knowledge of NIST SP 800-171 and the CMMC Assessment Guide.

Your role is to analyze controls based on available evidence and determine compliance status according to 800-171A assessment objectives.

You must:
1. Base your analysis ONLY on the evidence provided
2. Map evidence to specific assessment objectives (Examine/Interview/Test)
3. Determine if objectives are Met, Not Met, or Partially Met
4. Provide clear, assessor-grade narratives
5. Reference specific evidence for every claim
6. Be conservative - if evidence is insufficient, mark as Not Met or require additional evidence
7. Output your response in valid JSON format

Remember: Assessors must be able to defend every finding in a C3PAO audit."""

        # User prompt with context
        user_prompt = f"""# CONTROL ANALYSIS REQUEST

## Control Information
**Control ID:** {control['id']}
**Title:** {control['title']}
**Requirement:** {control['requirement_text']}

**Discussion:** {control.get('discussion', 'N/A')}

## Assessment Objectives (800-171A)
"""

        for obj in objectives:
            user_prompt += f"""
### Objective {obj['objective_letter']} ({obj['method']})
**Determination Statement:** {obj['determination_statement']}
**Potential Methods:** {obj.get('potential_assessment_methods', 'N/A')}
"""

        # Add provider inheritance if applicable
        if provider_inheritance:
            user_prompt += f"""
## Provider Inheritance
**Provider:** {provider_inheritance.provider_name}
**Responsibility:** {provider_inheritance.responsibility}
**Provider Narrative:** {provider_inheritance.narrative or 'N/A'}
**Documentation:** {provider_inheritance.documentation_url or 'N/A'}

NOTE: If responsibility is "Inherited", the customer does not need to implement this control.
If "Shared", analyze customer's portion of the responsibility.
"""

        # Add evidence context
        user_prompt += "\n## Available Evidence\n"

        if rag_context.retrieved_chunks:
            for i, chunk in enumerate(rag_context.retrieved_chunks, 1):
                user_prompt += f"""
### Evidence {i}: {chunk.document_title}
**Type:** {chunk.document_type or 'Unknown'}
**Relevance:** {(1.0 - chunk.similarity_score) * 100:.1f}%

```
{chunk.chunk_text}
```
---
"""
        else:
            user_prompt += "\n**No evidence found in the document repository.**\n"

        # Analysis instructions
        user_prompt += """
## Analysis Instructions

Based on the evidence provided above, analyze this control and provide your assessment in the following JSON format:

```json
{
  "status": "Met | Not Met | Partially Met | Not Applicable",
  "narrative": "Detailed assessor narrative explaining the finding. Reference specific evidence. Be thorough but concise (2-4 paragraphs).",
  "rationale": "Your reasoning process. Why did you reach this conclusion? What evidence was most important? What's missing?",
  "evidence_mapping": [
    {
      "evidence_number": 1,
      "objective_letter": "a",
      "supports": "Met | Not Met | Partially Met",
      "explanation": "How this evidence supports (or doesn't support) this objective"
    }
  ],
  "confidence": "0-100 (your confidence in this assessment)",
  "gaps": ["List any evidence gaps or concerns"],
  "recommendations": ["Recommendations for addressing gaps or improving compliance"]
}
```

**Important:**
- Be objective and evidence-based
- Reference evidence by number (Evidence 1, Evidence 2, etc.)
- If evidence is insufficient, recommend what's needed
- Consider the assessment method (Examine vs Interview vs Test)
- For "Examine" objectives, look for documentation
- For "Interview" objectives, look for interview notes or attestations
- For "Test" objectives, look for test results or technical evidence
"""

        return system_prompt, user_prompt

    async def call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        model: AIModel
    ) -> Tuple[str, int]:
        """
        Call OpenAI API

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model to use

        Returns:
            Tuple of (response_text, tokens_used)
        """
        response = await self.openai_client.chat.completions.create(
            model=model.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            response_format={"type": "json_object"}  # Force JSON output
        )

        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return response_text, tokens_used

    async def call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        model: AIModel
    ) -> Tuple[str, int]:
        """
        Call Anthropic Claude API

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model to use

        Returns:
            Tuple of (response_text, tokens_used)
        """
        response = await self.anthropic_client.messages.create(
            model=model.value,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        response_text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return response_text, tokens_used

    async def call_ai_model(
        self,
        system_prompt: str,
        user_prompt: str,
        model: AIModel
    ) -> Tuple[str, int, str]:
        """
        Call AI model with fallback

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model to use

        Returns:
            Tuple of (response_text, tokens_used, model_used)
        """
        try:
            if model.value.startswith('gpt'):
                response_text, tokens_used = await self.call_openai(system_prompt, user_prompt, model)
            elif model.value.startswith('claude'):
                response_text, tokens_used = await self.call_anthropic(system_prompt, user_prompt, model)
            else:
                raise ValueError(f"Unknown model: {model}")

            return response_text, tokens_used, model.value

        except Exception as e:
            logger.error(f"Error calling {model.value}: {e}")

            # Try fallback model
            if self.fallback_model and self.fallback_model != model:
                logger.info(f"Trying fallback model: {self.fallback_model.value}")

                if self.fallback_model.value.startswith('gpt'):
                    response_text, tokens_used = await self.call_openai(system_prompt, user_prompt, self.fallback_model)
                elif self.fallback_model.value.startswith('claude'):
                    response_text, tokens_used = await self.call_anthropic(system_prompt, user_prompt, self.fallback_model)

                return response_text, tokens_used, self.fallback_model.value
            else:
                raise

    def parse_ai_response(
        self,
        response_text: str
    ) -> Dict[str, Any]:
        """
        Parse AI response JSON

        Args:
            response_text: Raw AI response

        Returns:
            Parsed response dictionary
        """
        try:
            # Try to extract JSON if wrapped in code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response: {response_text[:500]}")
            raise ValueError("AI returned invalid JSON response")

    async def analyze_control(
        self,
        control_id: str,
        assessment_id: str,
        objective_id: Optional[str] = None,
        include_provider_inheritance: bool = True,
        top_k_evidence: int = 10
    ) -> FindingResult:
        """
        Analyze a control using AI

        Args:
            control_id: Control ID (e.g., "AC.L2-3.1.1")
            assessment_id: Assessment ID
            objective_id: Specific objective to analyze (optional)
            include_provider_inheritance: Include provider inheritance info
            top_k_evidence: Number of evidence chunks to retrieve

        Returns:
            FindingResult with AI analysis
        """
        logger.info(f"Analyzing control {control_id} for assessment {assessment_id}")

        # Get control details
        control = await self.get_control_details(control_id)

        # Get assessment objectives
        objectives = await self.get_assessment_objectives(control_id, objective_id)

        if not objectives:
            raise ValueError(f"No assessment objectives found for {control_id}")

        # Retrieve evidence using RAG
        query = f"Evidence for {control['title']}: {control['requirement_text']}"
        rag_context = await self.rag_engine.retrieve_context(
            query=query,
            top_k=5,  # Final results
            rerank_top_k=top_k_evidence,  # Retrieve more, rerank to top 5
            control_id=control_id,
            assessment_id=assessment_id
        )

        # Get provider inheritance if applicable
        provider_inheritance = None
        if include_provider_inheritance:
            provider_inheritance = await self.get_provider_inheritance(control_id, assessment_id)

        # Build prompts
        system_prompt, user_prompt = self.build_analysis_prompt(
            control=control,
            objectives=objectives,
            rag_context=rag_context,
            provider_inheritance=provider_inheritance
        )

        # Call AI model
        response_text, tokens_used, model_used = await self.call_ai_model(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.primary_model
        )

        # Parse response
        ai_response = self.parse_ai_response(response_text)

        # Convert evidence chunks to references
        evidence_references = [
            EvidenceReference(
                evidence_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title or "Unknown",
                chunk_text=chunk.chunk_text,
                relevance_score=1.0 - chunk.similarity_score,
                evidence_type=chunk.document_type
            )
            for chunk in rag_context.retrieved_chunks
        ]

        # Calculate confidence score
        confidence_factors = ConfidenceFactors(
            evidence_quality=self._assess_evidence_quality(evidence_references),
            evidence_quantity=min(len(evidence_references) / 5.0, 1.0),
            evidence_recency=0.8,  # TODO: Calculate from timestamps
            provider_inheritance=1.0 if provider_inheritance and provider_inheritance.responsibility == "Inherited" else 0.5,
            ai_certainty=float(ai_response.get('confidence', 50)) / 100.0
        )

        final_confidence = self.confidence_scorer.calculate_confidence(confidence_factors)

        # Determine if human review is required
        requires_review = (
            final_confidence < 0.7 or
            ai_response['status'] in ['Not Met', 'Partially Met'] or
            len(evidence_references) < 2
        )

        return FindingResult(
            control_id=control_id,
            objective_id=objective_id,
            status=FindingStatus(ai_response['status']),
            assessor_narrative=ai_response['narrative'],
            ai_confidence_score=final_confidence,
            ai_rationale=ai_response['rationale'],
            evidence_references=evidence_references,
            provider_inheritance=provider_inheritance,
            model_used=model_used,
            tokens_used=tokens_used,
            analysis_timestamp=datetime.utcnow(),
            requires_human_review=requires_review
        )

    def _assess_evidence_quality(self, evidence_refs: List[EvidenceReference]) -> float:
        """
        Assess overall evidence quality

        Args:
            evidence_refs: List of evidence references

        Returns:
            Quality score 0-1
        """
        if not evidence_refs:
            return 0.0

        # Average relevance score
        avg_relevance = sum(e.relevance_score for e in evidence_refs) / len(evidence_refs)

        # Bonus for diverse evidence types
        unique_types = len(set(e.evidence_type for e in evidence_refs if e.evidence_type))
        diversity_bonus = min(unique_types / 3.0, 0.2)  # Up to 20% bonus

        return min(avg_relevance + diversity_bonus, 1.0)
