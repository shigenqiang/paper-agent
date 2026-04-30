"""Agent Skills System

Implements Anthropic's Agent Skills standard (SKILL.md) with progressive disclosure.

Three-layer loading:
  Layer 1 - Metadata: All skill names + descriptions loaded at startup (~50 tokens/skill)
  Layer 2 - Core Instructions: Full SKILL.md body loaded when skill is activated (~500-2000 tokens)
  Layer 3 - Reference Materials: scripts/, references/, assets/ loaded on deep need

Usage:
    loader = SkillsLoader()
    # Scan and index all SKILL.md files
    await loader.scan_definitions()
    # Get metadata for all skills (Layer 1)
    summaries = loader.get_all_summaries()
    # Activate a skill (Layer 2)
    skill = await loader.activate("query-router")
    # Deeper reference (Layer 3)
    refs = await loader.load_references("query-router")
"""

from .loader import SkillsLoader, SkillDefinition

__all__ = ["SkillsLoader", "SkillDefinition"]
