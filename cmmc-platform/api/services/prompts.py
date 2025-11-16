"""
CMMC Compliance Platform - AI Prompt Templates
Assessor-grade prompts for NIST SP 800-171 control analysis
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


class CMCCPromptTemplates:
    """Prompt templates optimized for CMMC L1/L2 assessments"""

    @staticmethod
    def control_analysis_prompt(
        control_id: str,
        control_title: str,
        requirement_text: str,
        objective_id: Optional[str],
        objective_text: Optional[str],
        method: Optional[str],
        evidence_items: List[Dict[str, Any]],
        provider_inheritance: Optional[Dict[str, Any]],
        graph_context: Optional[Dict[str, Any]],
        relevant_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Generate prompt for AI-assisted control analysis

        Returns a prompt that asks the AI to:
        1. Analyze evidence against the control requirement
        2. Consider provider inheritance (if applicable)
        3. Use system architecture context
        4. Make a determination (Met/Not Met/Partially Met/N/A)
        5. Provide detailed rationale with evidence references
        """

        prompt = f"""You are an expert CMMC assessor analyzing compliance with NIST SP 800-171 controls for a Defense Industrial Base (DIB) contractor.

**Control Information:**
- Control ID: {control_id}
- Control Title: {control_title}
- Requirement: {requirement_text}
"""

        if objective_id and objective_text:
            prompt += f"""
**Assessment Objective:**
- Objective ID: {objective_id}
- Method: {method}
- Determination Statement: {objective_text}
"""

        prompt += f"""
**Evidence Provided ({len(evidence_items)} items):**
"""

        for idx, evidence in enumerate(evidence_items, 1):
            prompt += f"""
{idx}. {evidence.get('title', 'Untitled Evidence')}
   - Type: {evidence.get('evidence_type', 'Unknown')}
   - Method: {evidence.get('method', 'Not specified')}
   - Collected: {evidence.get('collected_date', 'Unknown')}
   - Description: {evidence.get('description', 'No description provided')}
"""

            # If evidence has extracted content, include it
            if evidence.get('content'):
                prompt += f"   - Content Summary: {evidence['content'][:500]}...\n"

        if provider_inheritance:
            prompt += f"""
**Provider Inheritance:**
- Provider: {provider_inheritance.get('provider_name')}
- Offering: {provider_inheritance.get('offering_name')}
- Responsibility: {provider_inheritance.get('responsibility')}
- Provider Implementation: {provider_inheritance.get('provider_narrative', 'Not documented')}
- Customer Responsibility: {provider_inheritance.get('customer_narrative', 'Not documented')}
"""

        if graph_context:
            prompt += f"""
**System Architecture Context:**
- Diagram: {graph_context.get('title', 'System Diagram')}
- Summary: {graph_context.get('graph_summary', 'No summary available')}
"""

        if relevant_docs:
            prompt += f"""
**Relevant Documentation ({len(relevant_docs)} chunks retrieved via RAG):**
"""
            for idx, doc in enumerate(relevant_docs, 1):
                prompt += f"""
{idx}. {doc.get('document_title', 'Document')} (Control: {doc.get('control_id', 'N/A')})
   - Excerpt: {doc.get('chunk_text', '')[:400]}...
   - Relevance Score: {doc.get('similarity_score', 0):.2f}
"""

        prompt += """
**Your Task:**
As a professional CMMC assessor, analyze the provided evidence and determine the compliance status for this control/objective.

**Analysis Framework:**
1. **Evidence Sufficiency**: Is there enough evidence of appropriate quality and type (Examine/Interview/Test)?
2. **Implementation Verification**: Does the evidence demonstrate actual implementation (not just policy)?
3. **Coverage**: Does the implementation apply to all relevant systems/assets/personnel?
4. **Effectiveness**: Is the control operating as intended?
5. **Provider Inheritance**: If applicable, is the shared responsibility model properly documented?

**Provide your response in the following JSON format:**

{
    "determination": "Met" | "Not Met" | "Partially Met" | "Not Applicable" | "Not Assessed",
    "confidence_score": <0-100>,
    "assessor_narrative": "<Professional narrative explaining the determination, written as if for a SAR>",
    "key_findings": [
        "<Finding 1>",
        "<Finding 2>",
        "..."
    ],
    "evidence_analysis": {
        "<evidence_id>": {
            "contribution": "<How this evidence supports/refutes compliance>",
            "weight": <0-100>,
            "issues": ["<Any issues with this evidence>"]
        }
    },
    "gaps_identified": [
        "<Gap 1 if Not Met or Partially Met>",
        "..."
    ],
    "recommendations": [
        "<Recommendation 1 for remediation>",
        "..."
    ],
    "rationale": "<Detailed explanation of your analytical process and reasoning>"
}

**Important Guidelines:**
- Be objective and evidence-based
- Use assessor-appropriate language (avoid overly technical jargon)
- Reference specific evidence items in your narrative
- If status is "Partially Met" or "Not Met", clearly explain what's missing
- For "Not Applicable", provide justification based on organizational scope
- Confidence score should reflect quality and completeness of evidence
- Consider continuous monitoring vs. point-in-time assessment

Provide your analysis now:
"""

        return prompt

    @staticmethod
    def document_chunking_prompt(text: str, control_id: Optional[str] = None) -> str:
        """
        Generate prompt for intelligent document chunking

        Used to identify control-relevant sections in policies, procedures, etc.
        """

        prompt = f"""You are analyzing a compliance document to identify sections relevant to NIST SP 800-171 controls.

**Document Text:**
{text[:4000]}

**Your Task:**
Identify logical chunks in this document that correspond to specific CMMC/800-171 controls or practices.

For each chunk, provide:
1. The text content (verbatim excerpt)
2. Relevant control ID(s) (e.g., AC.L2-3.1.1, AU.L2-3.3.1)
3. Assessment method (Examine, Interview, or Test)
4. Brief explanation of relevance

**Return JSON format:**
{{
    "chunks": [
        {{
            "chunk_index": 0,
            "chunk_text": "<verbatim text>",
            "control_ids": ["AC.L2-3.1.1", ...],
            "assessment_method": "Examine",
            "relevance_explanation": "<why this chunk is relevant>"
        }}
    ]
}}

Focus on content that demonstrates:
- Policy statements
- Procedural steps
- Technical configurations
- Roles and responsibilities
- Evidence of implementation

Provide your analysis:
"""
        return prompt

    @staticmethod
    def diagram_extraction_prompt(diagram_description: str) -> str:
        """
        Generate prompt for extracting graph structure from system diagrams

        Used with vision models to convert architecture diagrams to JSON graphs
        """

        prompt = f"""You are analyzing a system architecture diagram for CMMC compliance assessment.

**Diagram Information:**
{diagram_description}

**Your Task:**
Extract the graph structure (nodes and edges) from this diagram. This will be used to understand:
- System boundaries
- Data flows (especially for CUI)
- Network segregation
- Access control points
- External connections

**Return JSON format:**
{{
    "nodes": [
        {{
            "id": "node_1",
            "label": "<system/component name>",
            "type": "server|workstation|network|database|user|boundary|cloud_service|external",
            "properties": {{
                "description": "<description>",
                "cui_present": true|false,
                "security_zone": "trusted|dmz|untrusted|external"
            }}
        }}
    ],
    "edges": [
        {{
            "id": "edge_1",
            "source": "node_1",
            "target": "node_2",
            "type": "data_flow|network_connection|trust_boundary|authentication",
            "label": "<connection description>",
            "properties": {{
                "protocol": "<protocol if known>",
                "encrypted": true|false|unknown,
                "direction": "unidirectional|bidirectional"
            }}
        }}
    ],
    "security_zones": [
        {{
            "name": "<zone name>",
            "node_ids": ["node_1", "node_2"],
            "description": "<zone purpose>"
        }}
    ],
    "cui_flows": [
        {{
            "from": "node_id",
            "to": "node_id",
            "description": "<CUI data flow description>"
        }}
    ]
}}

**Focus on:**
- Identifying all systems/components
- Mapping network connections and data flows
- Identifying trust boundaries (firewalls, segmentation)
- Noting external connections (internet, third parties)
- Highlighting where CUI is processed/stored/transmitted

Provide your graph extraction:
"""
        return prompt

    @staticmethod
    def poam_generation_prompt(
        control_id: str,
        finding_status: str,
        gaps_identified: List[str],
        control_requirement: str
    ) -> str:
        """
        Generate POA&M items from gaps identified during assessment
        """

        prompt = f"""You are creating a Plan of Action & Milestones (POA&M) item for a CMMC assessment.

**Control Information:**
- Control ID: {control_id}
- Status: {finding_status}
- Requirement: {control_requirement}

**Gaps Identified:**
"""
        for idx, gap in enumerate(gaps_identified, 1):
            prompt += f"{idx}. {gap}\n"

        prompt += """
**Your Task:**
Create a professional POA&M entry for this deficiency.

**Return JSON format:**
{
    "weakness_description": "<Clear description of the control deficiency>",
    "risk_level": "Critical|High|Medium|Low",
    "risk_rationale": "<Why this risk level was assigned>",
    "remediation_plan": "<Step-by-step plan to achieve compliance>",
    "resources_required": "<Budget, personnel, tools, vendors needed>",
    "milestones": [
        {
            "name": "<Milestone 1>",
            "description": "<What will be accomplished>",
            "target_date": "<Estimated completion date>",
            "owner": "<Role responsible>"
        }
    ],
    "estimated_completion_date": "<Overall target date>",
    "estimated_cost": "<If applicable>",
    "residual_risk": "<Risk remaining after implementation>"
}

**Guidelines:**
- Risk level should consider: likelihood of exploit, impact if CUI compromised, scope of deficiency
- Remediation plan should be specific and actionable
- Milestones should be realistic (consider resource constraints)
- Include both technical and process remediation steps
- Consider quick wins vs. long-term solutions

Provide your POA&M item:
"""
        return prompt

    @staticmethod
    def ssp_narrative_prompt(
        control_id: str,
        control_requirement: str,
        evidence_summary: str,
        implementation_details: str,
        provider_inheritance: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate SSP control narrative from evidence and implementation details
        """

        prompt = f"""You are writing a System Security Plan (SSP) control narrative for a CMMC assessment.

**Control Information:**
- Control ID: {control_id}
- Requirement: {control_requirement}

**Implementation Details:**
{implementation_details}

**Evidence Summary:**
{evidence_summary}
"""

        if provider_inheritance:
            prompt += f"""
**Provider Inheritance:**
- Provider: {provider_inheritance.get('provider_name')}
- Responsibility: {provider_inheritance.get('responsibility')}
- Provider Implementation: {provider_inheritance.get('provider_narrative')}
"""

        prompt += """
**Your Task:**
Write a professional SSP control narrative that explains HOW this control is implemented.

**Format Requirements:**
- Present tense ("The organization implements...")
- Factual and specific (avoid vague statements like "as needed")
- Include: responsible roles, tools/systems used, frequency, process steps
- If hybrid/shared responsibility, clearly delineate provider vs. customer implementation
- Reference specific evidence where appropriate

**Return JSON format:**
{
    "control_summary": "<1-2 sentence overview>",
    "implementation_description": "<Detailed narrative of HOW the control is implemented>",
    "responsible_roles": ["<Role 1>", "<Role 2>"],
    "tools_and_systems": ["<Tool 1>", "<System 1>"],
    "frequency": "<Continuous|Daily|Weekly|Monthly|Annual|As Needed>",
    "provider_responsibility": "<If applicable, what provider does>",
    "customer_responsibility": "<If applicable, what customer does>",
    "evidence_references": ["<Evidence title 1>", "..."]
}

**Good Example:**
"The organization implements multi-factor authentication (MFA) for all privileged access through Microsoft Entra ID (formerly Azure AD). The IT Security Team configures Conditional Access policies requiring MFA for administrative roles accessing cloud resources, on-premises Active Directory, and the CMMC assessment boundary. MFA enforcement is verified through Entra ID sign-in logs reviewed monthly. Configuration screenshots and Conditional Access policy exports serve as examination evidence."

**Avoid:**
- Vague statements ("Security is implemented as needed")
- Future tense ("The organization will implement...")
- Policy restatement without implementation details

Provide your SSP narrative:
"""
        return prompt

    @staticmethod
    def evidence_quality_assessment_prompt(
        evidence_title: str,
        evidence_type: str,
        evidence_content: str,
        control_id: str,
        objective_text: str,
        method: str
    ) -> str:
        """
        Assess the quality and sufficiency of a piece of evidence
        """

        prompt = f"""You are reviewing evidence submitted for a CMMC assessment.

**Evidence Information:**
- Title: {evidence_title}
- Type: {evidence_type}
- Collection Method: {method}

**Control/Objective:**
- Control: {control_id}
- Objective: {objective_text}
- Expected Method: {method}

**Evidence Content:**
{evidence_content[:2000]}

**Your Task:**
Assess the quality and relevance of this evidence for the specified control/objective.

**Return JSON format:**
{{
    "quality_score": <0-100>,
    "relevance_score": <0-100>,
    "sufficiency": "Sufficient|Insufficient|Partially Sufficient",
    "strengths": [
        "<Strength 1>",
        "..."
    ],
    "weaknesses": [
        "<Weakness 1>",
        "..."
    ],
    "recommendation": "Accept|Request Additional Evidence|Reject",
    "assessor_notes": "<Professional notes for the assessment team>",
    "suggested_improvements": [
        "<How to strengthen this evidence>",
        "..."
    ]
}}

**Quality Criteria:**
- **Authenticity**: Is it from the actual production environment?
- **Timeliness**: Is it recent (within assessment period)?
- **Completeness**: Does it show full implementation?
- **Clarity**: Is it readable and understandable?
- **Relevance**: Does it directly address the objective?
- **Method Alignment**: Is it appropriate for {method} method?

**Common Issues to Check:**
- Screenshots without context (no timestamps, user, system info)
- Outdated evidence (>90 days old for Test evidence)
- Sanitized test environments vs. production
- Policy documents without evidence of enforcement
- Interview notes without corroborating evidence

Provide your evidence assessment:
"""
        return prompt

    @staticmethod
    def system_prompt_assessor() -> str:
        """System prompt establishing AI's role as CMMC assessor"""
        return """You are an expert CMMC assessor with deep knowledge of:
- NIST SP 800-171 Rev 2 (all 110 controls)
- NIST SP 800-171A (assessment objectives and methods)
- CMMC Level 1 and Level 2 requirements
- DoD assessment procedures and reporting standards
- Evidence evaluation and determination-making

Your analysis must be:
- Objective and evidence-based
- Aligned with 800-171A determination statements
- Written in professional assessor language
- Defensible in audit situations
- Supportive of DIB contractors while maintaining rigor

When uncertain, request additional evidence rather than making assumptions.
Always provide detailed rationale for your determinations.
"""


class PromptBuilder:
    """Helper class to build prompts with dynamic context"""

    def __init__(self, templates: CMCCPromptTemplates = None):
        self.templates = templates or CMCCPromptTemplates()

    def build_control_analysis(
        self,
        control_data: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Build message array for control analysis

        Returns OpenAI/Anthropic compatible message format:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ]
        """

        context = context or {}

        messages = [
            {
                "role": "system",
                "content": self.templates.system_prompt_assessor()
            },
            {
                "role": "user",
                "content": self.templates.control_analysis_prompt(
                    control_id=control_data.get('id'),
                    control_title=control_data.get('title'),
                    requirement_text=control_data.get('requirement_text'),
                    objective_id=control_data.get('objective_id'),
                    objective_text=control_data.get('objective_text'),
                    method=control_data.get('method'),
                    evidence_items=evidence_items,
                    provider_inheritance=context.get('provider_inheritance'),
                    graph_context=context.get('graph_context'),
                    relevant_docs=context.get('relevant_docs', [])
                )
            }
        ]

        return messages

    def token_count_estimate(self, text: str) -> int:
        """Rough estimate of token count (actual count requires tiktoken)"""
        # Rough heuristic: 1 token ≈ 4 characters for English
        return len(text) // 4
