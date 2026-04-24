"""
LLM 摘要器：将一段对话原文压缩为摘要，并抽取可入长期记忆的事实条目。

输出采用严格 JSON，便于校验与幂等处理。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExtractedFact:
    text: str
    importance: float
    compression: str  # keep | light | compress
    tags: List[str]
    evidence: List[str]


class LLMSummarizer:
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config or {}

    def _build_messages(self, conversations: List[Dict[str, str]], overlap_tail: Optional[List[Dict[str, str]]] = None,
                        max_facts: int = 20) -> List[Dict[str, str]]:
        overlap_tail = overlap_tail or []
        payload = {
            "overlap_tail": overlap_tail,
            "chunk_messages": conversations,
            "requirements": {
                "output_format": "strict_json",
                "no_hallucination": True,
                "facts_must_have_evidence": True,
                "max_facts": max_facts,
                "compression_levels": ["keep", "light", "compress"],
                "importance_range": [0.0, 1.0],
            },
            "schema": {
                "chunk_summary": "string",
                "facts": [
                    {
                        "text": "string",
                        "importance": "number(0..1)",
                        "compression": "keep|light|compress",
                        "tags": ["string"],
                        "evidence": ["string (direct quotes from input)"],
                    }
                ],
                "open_loops": ["string"],
                "topics": ["string"],
            },
        }

        system = (
            "你是一个“对话记忆摘要与事实抽取器”。\n"
            "严格遵守：\n"
            "1) 只能基于输入内容，不得编造。\n"
            "2) 输出必须是单个 JSON 对象，不要包含任何额外文本。\n"
            "3) facts 中每条必须给出 1-3 条 evidence（直接引用输入原文，尽量短）。\n"
            "4) 如果没有足够证据，facts 里不要输出该条。\n"
        )
        user = "请根据以下输入生成摘要与事实抽取结果：\n" + json.dumps(payload, ensure_ascii=False)
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        # 尝试从包裹文本中抠出 JSON（容错）
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError("未找到JSON对象")
        return json.loads(m.group(0))

    def _validate(self, obj: Dict[str, Any], max_facts: int) -> Tuple[str, List[ExtractedFact], List[str], List[str]]:
        if not isinstance(obj, dict):
            raise ValueError("JSON根不是对象")

        summary = obj.get("chunk_summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("chunk_summary缺失或为空")

        facts_raw = obj.get("facts", [])
        if facts_raw is None:
            facts_raw = []
        if not isinstance(facts_raw, list):
            raise ValueError("facts不是数组")

        facts: List[ExtractedFact] = []
        for item in facts_raw[:max_facts]:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            importance = item.get("importance")
            compression = item.get("compression", "compress")
            tags = item.get("tags", [])
            evidence = item.get("evidence", [])
            if not isinstance(text, str) or not text.strip():
                continue
            try:
                importance = float(importance)
            except Exception:
                continue
            importance = max(0.0, min(1.0, importance))
            if compression not in ("keep", "light", "compress"):
                compression = "compress"
            if not isinstance(tags, list):
                tags = []
            tags = [str(t) for t in tags if str(t).strip()]
            if not isinstance(evidence, list) or len(evidence) == 0:
                continue
            evidence = [str(e) for e in evidence if str(e).strip()][:3]
            if len(evidence) == 0:
                continue
            facts.append(
                ExtractedFact(
                    text=text.strip(),
                    importance=importance,
                    compression=compression,
                    tags=tags,
                    evidence=evidence,
                )
            )

        open_loops = obj.get("open_loops", [])
        if not isinstance(open_loops, list):
            open_loops = []
        open_loops = [str(x) for x in open_loops if str(x).strip()]

        topics = obj.get("topics", [])
        if not isinstance(topics, list):
            topics = []
        topics = [str(x) for x in topics if str(x).strip()]

        return summary.strip(), facts, open_loops, topics

    async def summarize_and_extract(
        self,
        conversations: List[Dict[str, str]],
        overlap_tail: Optional[List[Dict[str, str]]] = None,
        max_facts: int = 20,
    ) -> Tuple[str, List[ExtractedFact], Dict[str, Any]]:
        if not conversations:
            return "无有效对话内容", [], {"error": "empty_conversations"}

        messages = self._build_messages(conversations, overlap_tail=overlap_tail, max_facts=max_facts)

        # 延迟导入，避免潜在循环依赖
        from ..providers import get_provider

        provider_name = self.llm_config.get("provider") or "openai"
        provider = get_provider(provider_name, llm_config=self.llm_config)

        raw = await provider.chat(messages)
        obj = self._extract_json_object(raw)
        summary, facts, open_loops, topics = self._validate(obj, max_facts=max_facts)

        meta = {
            "raw_model_output": raw[:2000],
            "open_loops": open_loops,
            "topics": topics,
        }
        return summary, facts, meta

