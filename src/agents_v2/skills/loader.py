"""
SkillsLoader — Anthropic Agent Skills progressive disclosure implementation.

Three-layer loading pattern:
  Layer 1 (Metadata):   YAML frontmatter only — name, description, tags (~50 tokens/skill)
  Layer 2 (Core Instr): Full SKILL.md body — loaded when skill is activated (~500-2000 tokens)
  Layer 3 (References):  scripts/, references/, assets/ — loaded only on explicit request

Directory structure:
  skills/definitions/{skill-name}/
    SKILL.md           # Required: YAML frontmatter + markdown body
    scripts/           # Optional: executable scripts
    references/        # Optional: additional reference docs
    assets/            # Optional: images, templates, etc.
"""
import logging
import re
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SKILL_MD_FILENAME = "SKILL.md"
DEFINITIONS_DIR = "definitions"


@dataclass
class SkillDefinition:
    """Parsed SKILL.md with frontmatter and body separated for progressive disclosure."""

    name: str
    description: str
    category: str = "general"
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    # File paths
    skill_dir: str = ""
    md_path: str = ""
    # Layer 2/3 content (loaded on demand, None until activated)
    _body: Optional[str] = field(default=None, repr=False)
    _references: Optional[Dict[str, str]] = field(default=None, repr=False)
    _assets: Optional[List[str]] = field(default=None, repr=False)
    # Stats
    activation_count: int = 0

    @property
    def summary(self) -> str:
        """Layer 1 summary — ~50 tokens, suitable for loading all skills into context."""
        tags_str = ", ".join(self.tags[:5])
        return f"- **{self.name}** [{self.category}]: {self.description}" + (
            f" (tags: {tags_str})" if tags_str else ""
        )

    @property
    def body(self) -> Optional[str]:
        """Layer 2 — full SKILL.md body content."""
        return self._body

    @property
    def references(self) -> Dict[str, str]:
        """Layer 3 — reference file contents."""
        return self._references or {}

    def to_context_block(self, layer: int = 2) -> str:
        """Render the skill for injection into LLM context.

        Args:
            layer: 1 = summary only, 2 = full body, 3 = body + references
        """
        if layer == 1:
            return self.summary
        if layer == 2:
            return self._body or ""
        # Layer 3
        parts = [self._body or ""]
        if self._references:
            parts.append("\n## Reference Materials\n")
            for name, content in self._references.items():
                parts.append(f"### {name}\n{content}")
        return "\n".join(parts)


class SkillsLoader:
    """Loads and manages SKILL.md files with progressive disclosure.

    Usage:
        loader = SkillsLoader(definitions_root="src/agents_v2/skills/definitions")
        await loader.scan_definitions()
        # List all (Layer 1 only — cheap)
        for s in loader.get_all_summaries():
            print(s)
        # Activate a skill (Layer 2)
        skill = await loader.activate("query-router")
        prompt = skill.to_context_block(layer=2)
    """

    def __init__(self, definitions_root: Optional[str] = None):
        if definitions_root is None:
            definitions_root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), DEFINITIONS_DIR
            )
        self.definitions_root = Path(definitions_root)
        self._skills: Dict[str, SkillDefinition] = {}
        self._scanned = False

    # ── Layer 1: Metadata scan ────────────────────────────────────────

    async def scan_definitions(self) -> List[SkillDefinition]:
        """Scan all SKILL.md files and load frontmatter (Layer 1 only).

        This is designed to run at startup — reads only the YAML header of each file.
        """
        if not self.definitions_root.exists():
            logger.warning(f"Definitions directory not found: {self.definitions_root}")
            self._scanned = True
            return []

        skills = []
        for md_file in self.definitions_root.rglob(SKILL_MD_FILENAME):
            if "_template" in str(md_file):
                continue
            try:
                skill = self._parse_frontmatter(md_file)
                if skill:
                    self._skills[skill.name] = skill
                    skills.append(skill)
                    logger.debug(f"Indexed skill: {skill.name} (Layer 1)")
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")

        self._scanned = True
        logger.info(f"Scanned {len(skills)} skills (Layer 1 metadata only)")
        return skills

    def _parse_frontmatter(self, md_path: Path) -> Optional[SkillDefinition]:
        """Extract YAML frontmatter from a SKILL.md file."""
        content = md_path.read_text(encoding="utf-8")

        # Extract YAML frontmatter between --- delimiters
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not match:
            logger.warning(f"No frontmatter found in {md_path}")
            return None

        frontmatter_str = match.group(1)
        body = match.group(2).strip()

        fm = yaml.safe_load(frontmatter_str)
        if not fm or "name" not in fm:
            logger.warning(f"Missing required 'name' field in {md_path}")
            return None

        skill_dir = str(md_path.parent.relative_to(self.definitions_root))

        return SkillDefinition(
            name=fm["name"],
            description=fm.get("description", ""),
            category=fm.get("category", "general"),
            version=str(fm.get("version", "1.0")),
            tags=fm.get("tags", []),
            inputs=fm.get("inputs", {}),
            outputs=fm.get("outputs", {}),
            skill_dir=skill_dir,
            md_path=str(md_path),
            # Don't load body yet — progressive disclosure
        )

    # ── Layer 2: Activate (load full body) ─────────────────────────────

    async def activate(self, skill_name: str) -> Optional[SkillDefinition]:
        """Activate a skill — load its full SKILL.md body (Layer 2).

        Call this when the skill is selected for use. The body content is
        typically 500–2000 tokens.
        """
        skill = self._skills.get(skill_name)
        if not skill:
            logger.warning(f"Skill not found: {skill_name}")
            return None

        if skill._body is None:
            md_path = Path(skill.md_path)
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                # Strip frontmatter to get body
                match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
                if match:
                    skill._body = content[match.end():].strip()
                else:
                    skill._body = content
                logger.debug(f"Activated skill: {skill_name} (Layer 2, "
                           f"~{len(skill._body.split())} words)")

        skill.activation_count += 1
        return skill

    async def activate_all(self) -> Dict[str, SkillDefinition]:
        """Activate all skills — loads Layer 2 for every registered skill."""
        for name in self._skills:
            await self.activate(name)
        return self._skills

    # ── Layer 3: Deep references ───────────────────────────────────────

    async def load_references(self, skill_name: str) -> Dict[str, str]:
        """Load reference materials for a skill (Layer 3).

        Reads all files from the skill's references/ directory.
        Call this only when the agent needs deep context.
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return {}

        if skill._references is not None:
            return skill._references

        refs_dir = Path(skill.md_path).parent / "references"
        skill._references = {}
        if refs_dir.exists():
            for ref_file in refs_dir.iterdir():
                if ref_file.is_file() and ref_file.suffix in (".md", ".txt", ".py"):
                    try:
                        skill._references[ref_file.name] = ref_file.read_text(encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Failed to read reference {ref_file}: {e}")

        return skill._references

    async def load_assets(self, skill_name: str) -> List[str]:
        """List asset files for a skill (Layer 3). Does NOT read content into memory."""
        skill = self._skills.get(skill_name)
        if not skill:
            return []

        if skill._assets is not None:
            return skill._assets

        assets_dir = Path(skill.md_path).parent / "assets"
        skill._assets = []
        if assets_dir.exists():
            skill._assets = [str(f.relative_to(assets_dir)) for f in assets_dir.iterdir() if f.is_file()]

        return skill._assets

    # ── Query helpers ──────────────────────────────────────────────────

    def get(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by name."""
        return self._skills.get(name)

    def get_by_category(self, category: str) -> List[SkillDefinition]:
        """Get all skills in a category."""
        return [s for s in self._skills.values() if s.category == category]

    def get_by_tag(self, tag: str) -> List[SkillDefinition]:
        """Get all skills matching a tag."""
        return [s for s in self._skills.values() if tag in s.tags]

    def get_all_summaries(self) -> List[str]:
        """Get Layer 1 summaries for all skills — cheap, ~50 tokens each."""
        return [s.summary for s in self._skills.values()]

    def get_all(self) -> List[SkillDefinition]:
        """Get all skill definitions (Layer 1 metadata only, unless activated)."""
        return list(self._skills.values())

    def list_names(self) -> List[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def list_categories(self) -> List[str]:
        """List all unique categories."""
        return sorted(set(s.category for s in self._skills.values()))

    @property
    def skill_count(self) -> int:
        return len(self._skills)

    @property
    def scanned(self) -> bool:
        return self._scanned
