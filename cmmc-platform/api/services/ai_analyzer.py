"""
CMMC Compliance Platform - AI Analyzer Service
AI-assisted control analysis using GPT-4 or Claude
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

# Optional imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .prompts import CMCCPromptTemplates, PromptBuilder
from .rag_service import RAGService


logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AIConfig:
    """Configuration for AI analyzer"""

    def __init__(
        self,
        provider: AIProvider = AIProvider.OPENAI,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,  # Low for consistent compliance analysis
        max_tokens: int = 4000,
        max_retries: int = 3,
        timeout: int = 60
    ):
        self.provider = provider
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.timeout = timeout

        # Set default models
        if model_name is None:
            if provider == AIProvider.OPENAI:
                self.model_name = "gpt-4-turbo-preview"  # or "gpt-4o"
            elif provider == AIProvider.ANTHROPIC:
                self.model_name = "claude-3-5-sonnet-20241022"
            else:
                self.model_name = "default"
        else:
            self.model_name = model_name


class AIAnalyzer:
    """
    AI-powered control analyzer for CMMC assessments

    Features:
    - Multi-provider support (OpenAI GPT-4, Anthropic Claude)
    - Structured output parsing
    - Confidence scoring
    - Evidence traceability
    - Human-in-the-loop workflow
    """

    def __init__(
        self,
        config: AIConfig,
        rag_service: Optional[RAGService] = None
    ):
        self.config = config
        self.provider = config.provider
        self.rag_service = rag_service
        self._client = None

        # Initialize AI client
        if self.provider == AIProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            if not config.api_key:
                raise ValueError("OpenAI API key required")
            self._client = openai.AsyncOpenAI(api_key=config.api_key)
            logger.info(f"Initialized OpenAI client with model: {config.model_name}")

        elif self.provider == AIProvider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            if not config.api_key:
                raise ValueError("Anthropic API key required")
            self._client = anthropic.AsyncAnthropic(api_key=config.api_key)
            logger.info(f"Initialized Anthropic client with model: {config.model_name}")

        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

        # Initialize prompt templates
        self.templates = CMCCPromptTemplates()
        self.prompt_builder = PromptBuilder(self.templates)

    async def analyze_control(
        self,
        control_data: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        assessment_id: str,
        include_rag: bool = True,
        provider_inheritance: Optional[Dict[str, Any]] = None,
        graph_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a control using AI

        Args:
            control_data: Control and objective information
            evidence_items: List of evidence items
            assessment_id: Assessment context
            include_rag: Whether to include RAG retrieval
            provider_inheritance: Provider responsibility info
            graph_context: System architecture context

        Returns:
            Analysis result with determination, confidence, narrative, etc.
        """
        start_time = datetime.utcnow()

        # Retrieve relevant context via RAG if enabled
        relevant_docs = []
        if include_rag and self.rag_service:
            try:
                rag_context = await self.rag_service.retrieve_for_control_analysis(
                    control_id=control_data['id'],
                    objective_id=control_data.get('objective_id'),
                    assessment_id=assessment_id,
                    method=control_data.get('method')
                )
                relevant_docs = rag_context.get('relevant_docs', [])

                # Use RAG-retrieved provider inheritance if not provided
                if not provider_inheritance:
                    provider_inheritance = rag_context.get('provider_inheritance')

                # Use RAG-retrieved diagram context if not provided
                if not graph_context:
                    graph_context = rag_context.get('diagram_context')

            except Exception as e:
                logger.warning(f"RAG retrieval failed, continuing without: {e}")

        # Build messages for AI
        messages = self.prompt_builder.build_control_analysis(
            control_data=control_data,
            evidence_items=evidence_items,
            context={
                'provider_inheritance': provider_inheritance,
                'graph_context': graph_context,
                'relevant_docs': relevant_docs
            }
        )

        # Call AI provider
        try:
            if self.provider == AIProvider.OPENAI:
                response_text = await self._call_openai(messages)
            elif self.provider == AIProvider.ANTHROPIC:
                response_text = await self._call_anthropic(messages)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Parse structured response
            analysis = self._parse_analysis_response(response_text)

            # Add metadata
            analysis['_metadata'] = {
                'ai_provider': self.provider.value,
                'ai_model': self.config.model_name,
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                'rag_docs_used': len(relevant_docs),
                'evidence_items_provided': len(evidence_items),
                'timestamp': datetime.utcnow().isoformat()
            }

            logger.info(
                f"AI analysis complete: control={control_data['id']}, "
                f"determination={analysis.get('determination')}, "
                f"confidence={analysis.get('confidence_score')}"
            )

            return analysis

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            raise

    async def _call_openai(self, messages: List[Dict[str, str]]) -> str:
        """Call OpenAI API"""
        try:
            response = await self._client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"}  # Request JSON output
            )

            content = response.choices[0].message.content

            logger.debug(
                f"OpenAI API call: model={self.config.model_name}, "
                f"tokens={response.usage.total_tokens}"
            )

            return content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    async def _call_anthropic(self, messages: List[Dict[str, str]]) -> str:
        """Call Anthropic API"""
        try:
            # Anthropic requires system message separate from user messages
            system_message = next(
                (msg['content'] for msg in messages if msg['role'] == 'system'),
                None
            )
            user_messages = [msg for msg in messages if msg['role'] != 'system']

            response = await self._client.messages.create(
                model=self.config.model_name,
                system=system_message,
                messages=user_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            content = response.content[0].text

            logger.debug(
                f"Anthropic API call: model={self.config.model_name}, "
                f"tokens_in={response.usage.input_tokens}, "
                f"tokens_out={response.usage.output_tokens}"
            )

            return content

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse AI response into structured format

        Expected JSON format:
        {
            "determination": "Met" | "Not Met" | "Partially Met" | "Not Applicable",
            "confidence_score": 0-100,
            "assessor_narrative": "...",
            "key_findings": [...],
            "evidence_analysis": {...},
            "gaps_identified": [...],
            "recommendations": [...],
            "rationale": "..."
        }
        """
        try:
            # Try to parse as JSON
            analysis = json.loads(response_text)

            # Validate required fields
            required_fields = ['determination', 'confidence_score', 'assessor_narrative', 'rationale']
            missing = [f for f in required_fields if f not in analysis]

            if missing:
                logger.warning(f"AI response missing required fields: {missing}")
                # Fill in defaults
                for field in missing:
                    if field == 'determination':
                        analysis[field] = 'Not Assessed'
                    elif field == 'confidence_score':
                        analysis[field] = 0.0
                    else:
                        analysis[field] = 'Not provided by AI'

            # Normalize determination
            valid_determinations = ['Met', 'Not Met', 'Partially Met', 'Not Applicable', 'Not Assessed']
            if analysis['determination'] not in valid_determinations:
                logger.warning(f"Invalid determination: {analysis['determination']}")
                analysis['determination'] = 'Not Assessed'

            # Ensure confidence is in range
            if not (0 <= analysis['confidence_score'] <= 100):
                logger.warning(f"Confidence out of range: {analysis['confidence_score']}")
                analysis['confidence_score'] = max(0, min(100, analysis['confidence_score']))

            # Ensure lists exist
            for list_field in ['key_findings', 'gaps_identified', 'recommendations']:
                if list_field not in analysis:
                    analysis[list_field] = []

            # Ensure evidence_analysis exists
            if 'evidence_analysis' not in analysis:
                analysis['evidence_analysis'] = {}

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")

            # Fallback: extract what we can
            return {
                'determination': 'Not Assessed',
                'confidence_score': 0.0,
                'assessor_narrative': response_text[:1000],
                'key_findings': [],
                'evidence_analysis': {},
                'gaps_identified': [],
                'recommendations': [],
                'rationale': 'Failed to parse structured AI response',
                '_parse_error': str(e)
            }

    async def generate_poam_item(
        self,
        control_id: str,
        finding_status: str,
        gaps_identified: List[str],
        control_requirement: str
    ) -> Dict[str, Any]:
        """
        Generate POA&M item using AI

        Args:
            control_id: Control with deficiency
            finding_status: "Not Met" or "Partially Met"
            gaps_identified: List of gaps
            control_requirement: Control requirement text

        Returns:
            POA&M item structure
        """
        prompt = self.templates.poam_generation_prompt(
            control_id=control_id,
            finding_status=finding_status,
            gaps_identified=gaps_identified,
            control_requirement=control_requirement
        )

        messages = [
            {"role": "system", "content": self.templates.system_prompt_assessor()},
            {"role": "user", "content": prompt}
        ]

        if self.provider == AIProvider.OPENAI:
            response_text = await self._call_openai(messages)
        else:
            response_text = await self._call_anthropic(messages)

        try:
            poam_item = json.loads(response_text)
            return poam_item
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse POA&M response: {e}")
            return {
                'weakness_description': f"Deficiency in {control_id}",
                'risk_level': 'Medium',
                'remediation_plan': 'To be determined',
                'milestones': [],
                '_parse_error': str(e)
            }

    async def generate_ssp_narrative(
        self,
        control_id: str,
        control_requirement: str,
        evidence_summary: str,
        implementation_details: str,
        provider_inheritance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate SSP control narrative using AI

        Args:
            control_id: Control ID
            control_requirement: Control requirement text
            evidence_summary: Summary of evidence
            implementation_details: How control is implemented
            provider_inheritance: Provider responsibility info

        Returns:
            SSP narrative structure
        """
        prompt = self.templates.ssp_narrative_prompt(
            control_id=control_id,
            control_requirement=control_requirement,
            evidence_summary=evidence_summary,
            implementation_details=implementation_details,
            provider_inheritance=provider_inheritance
        )

        messages = [
            {"role": "system", "content": self.templates.system_prompt_assessor()},
            {"role": "user", "content": prompt}
        ]

        if self.provider == AIProvider.OPENAI:
            response_text = await self._call_openai(messages)
        else:
            response_text = await self._call_anthropic(messages)

        try:
            ssp_narrative = json.loads(response_text)
            return ssp_narrative
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SSP narrative: {e}")
            return {
                'control_summary': f"Implementation of {control_id}",
                'implementation_description': implementation_details,
                'responsible_roles': [],
                'tools_and_systems': [],
                '_parse_error': str(e)
            }

    async def assess_evidence_quality(
        self,
        evidence_title: str,
        evidence_type: str,
        evidence_content: str,
        control_id: str,
        objective_text: str,
        method: str
    ) -> Dict[str, Any]:
        """
        Assess quality of evidence using AI

        Args:
            evidence_title: Evidence title
            evidence_type: Evidence type
            evidence_content: Evidence content/description
            control_id: Related control
            objective_text: Assessment objective
            method: Assessment method

        Returns:
            Quality assessment with scores and recommendations
        """
        prompt = self.templates.evidence_quality_assessment_prompt(
            evidence_title=evidence_title,
            evidence_type=evidence_type,
            evidence_content=evidence_content,
            control_id=control_id,
            objective_text=objective_text,
            method=method
        )

        messages = [
            {"role": "system", "content": self.templates.system_prompt_assessor()},
            {"role": "user", "content": prompt}
        ]

        if self.provider == AIProvider.OPENAI:
            response_text = await self._call_openai(messages)
        else:
            response_text = await self._call_anthropic(messages)

        try:
            assessment = json.loads(response_text)
            return assessment
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evidence assessment: {e}")
            return {
                'quality_score': 50,
                'relevance_score': 50,
                'sufficiency': 'Partially Sufficient',
                'recommendation': 'Request Additional Evidence',
                '_parse_error': str(e)
            }

    async def healthcheck(self) -> Dict[str, Any]:
        """Check AI analyzer health"""
        try:
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Respond with: {\"status\": \"ok\"}"}
            ]

            if self.provider == AIProvider.OPENAI:
                response = await self._call_openai(test_messages)
            else:
                response = await self._call_anthropic(test_messages)

            return {
                "status": "healthy",
                "provider": self.provider.value,
                "model": self.config.model_name,
                "test_response": response[:100]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider.value,
                "model": self.config.model_name,
                "error": str(e)
            }


# Factory function
def create_ai_analyzer(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    rag_service: Optional[RAGService] = None
) -> AIAnalyzer:
    """
    Factory function to create AI analyzer

    Args:
        provider: "openai" or "anthropic"
        api_key: API key
        model_name: Optional model override
        rag_service: Optional RAG service for context retrieval

    Returns:
        Configured AIAnalyzer instance

    Example:
        analyzer = create_ai_analyzer(
            provider="openai",
            api_key="sk-...",
            model_name="gpt-4-turbo-preview"
        )
    """
    provider_enum = AIProvider(provider.lower())

    config = AIConfig(
        provider=provider_enum,
        model_name=model_name,
        api_key=api_key
    )

    return AIAnalyzer(config, rag_service=rag_service)
