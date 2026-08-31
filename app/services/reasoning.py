"""Chain-of-thought reasoning engine with strict grounding — no assumptions."""

from __future__ import annotations

import json
import re
from typing import Any

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, TEMPERATURE
from app.services.retrieval import retrieve

# ── Configure Gemini ────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """\
You are **MedAdvisor**, a personal medical advisor for doctors. Your role is to help \
doctors retrieve, analyze, and reason about medical documents and reports.

## ABSOLUTE RULES — NEVER VIOLATE THESE

1. **ONLY use information from the PROVIDED CONTEXT below.** Do NOT use your \
   general knowledge, training data, or make ANY assumptions.
2. **If the context does not contain enough information to answer the question, \
   you MUST respond with:** "Based on the uploaded documents, I do not have \
   enough information to answer this question. Please upload relevant documents \
   or rephrase your query."
3. **NEVER fabricate, hallucinate, or guess.** If you are unsure, say so.
4. **Always cite your sources.** For every claim, reference the specific \
   document chunk(s) it came from using [Source: filename — chunk N] format.
5. **Think step-by-step.** Break down your reasoning into clear logical steps \
   before giving a final answer.

## RESPONSE FORMAT

You MUST respond in the following JSON format (no markdown code fences):

{
  "has_answer": true/false,
  "reasoning_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "answer": "Your detailed answer here with inline [Source: ...] citations",
  "citations": [
    {
      "source": "filename — chunk N",
      "relevant_text": "The exact quote from the context that supports this part of the answer"
    }
  ],
  "confidence": "high/medium/low",
  "confidence_reason": "Why you rated the confidence this way"
}

If has_answer is false, set answer to the "I do not have enough information" message, \
leave citations empty, and set confidence to "none".

## CONTEXT FROM UPLOADED DOCUMENTS

{context}

## DOCTOR'S QUESTION

{question}
"""


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    if not chunks:
        return "(No documents have been uploaded or no relevant chunks were found.)"

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"--- Chunk {i} [Source: {chunk['source']}] ---\n"
            f"{chunk['text']}\n"
        )
    return "\n".join(parts)


def _parse_response(raw_text: str) -> dict:
    """Parse the LLM's JSON response, handling common formatting issues."""
    text = raw_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: return the raw text as an answer
        return {
            "has_answer": True,
            "reasoning_steps": ["Direct response from the model."],
            "answer": raw_text,
            "citations": [],
            "confidence": "low",
            "confidence_reason": "Response could not be parsed into structured format.",
        }


def query(question: str) -> dict[str, Any]:
    """
    Full RAG query pipeline:
    1. Retrieve relevant chunks (hybrid search)
    2. Build grounded context
    3. Send to Gemini with strict system prompt
    4. Parse and return structured response

    Returns:
        {
            has_answer, reasoning_steps[], answer, citations[],
            confidence, confidence_reason, sources_used[]
        }
    """
    # 1. Retrieve
    chunks = retrieve(question)

    # 2. Build context
    context = _build_context(chunks)

    # 3. Build prompt
    prompt = SYSTEM_PROMPT.format(context=context, question=question)

    # 4. Call Gemini
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=TEMPERATURE,
        ),
    )

    # 5. Parse response
    result = _parse_response(response.text)

    # Attach the sources used for transparency
    result["sources_used"] = [
        {"source": c["source"], "rrf_score": c["rrf_score"]}
        for c in chunks
    ]

    return result
