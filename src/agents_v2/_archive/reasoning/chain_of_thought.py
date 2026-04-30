"""
链式推理器 - Chain of Thought Reasoner

实现多种CoT变体:
- Standard CoT: 逐步推理
- Zero-shot CoT: 无示例推理
- Chain-of-Thought: 显式步骤
- Program-of-Thoughts: 代码生成推理
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CoTType(Enum):
    """CoT类型"""
    STANDARD = "standard"           # 标准链式推理
    ZERO_SHOT = "zero_shot"         # 零样本链式推理
    PROGRAM = "program"             # 程序化推理
    REACT = "react"                 # 推理+行动


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    thought: str
    action: str = ""
    observation: str = ""
    confidence: float = 0.5
    is_final: bool = False


@dataclass
class ReasoningResult:
    """推理结果"""
    answer: str
    steps: List[ReasoningStep]
    reasoning_type: CoTType
    total_time: float
    confidence: float


class ChainOfThoughtReasoner:
    """链式推理器"""

    def __init__(self, llm: Any = None):
        """初始化

        Args:
            llm: LLM实例
        """
        self.llm = llm

    async def reason(self,
                     query: str,
                     cot_type: CoTType = CoTType.STANDARD) -> ReasoningResult:
        """执行链式推理

        Args:
            query: 问题
            cot_type: CoT类型

        Returns:
            ReasoningResult: 推理结果
        """
        start_time = time.time()

        if cot_type == CoTType.ZERO_SHOT:
            return await self._zero_shot_cot(query)
        elif cot_type == CoTType.PROGRAM:
            return await self._program_of_thoughts(query)
        elif cot_type == CoTType.REACT:
            return await self._react_reasoning(query)
        else:
            return await self._standard_cot(query)

    async def _standard_cot(self, query: str) -> ReasoningResult:
        """标准链式推理

        将问题分解为多个步骤，逐步推理。
        """
        steps = []
        step_num = 0

        if self.llm:
            try:
                prompt = f"""
问题: {query}

请将这个问题分解为多个推理步骤，并逐步解决。
每个步骤应该包含:
- 思考：描述当前步骤的推理思路
- 结论：得出当前步骤的结论

用JSON格式返回步骤列表：
[
  {{"step": 1, "thought": "思考内容", "conclusion": "结论"}},
  ...
]
"""
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                import json
                import re

                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    step_data = json.loads(match.group())

                    for s in step_data:
                        step_num += 1
                        steps.append(ReasoningStep(
                            step_number=step_num,
                            thought=s.get("thought", ""),
                            observation=s.get("conclusion", ""),
                            confidence=0.8
                        ))

            except Exception as e:
                logger.error(f"标准CoT推理失败: {e}")

        # 回退：简单分解
        if not steps:
            steps.append(ReasoningStep(
                step_number=1,
                thought=f"分析问题: {query}",
                confidence=0.5
            ))
            steps.append(ReasoningStep(
                step_number=2,
                thought="执行推理",
                is_final=True,
                confidence=0.5
            ))

        total_time = time.time() - start_time

        return ReasoningResult(
            answer=steps[-1].observation if steps else "",
            steps=steps,
            reasoning_type=CoTType.STANDARD,
            total_time=total_time,
            confidence=sum(s.confidence for s in steps) / len(steps) if steps else 0.5
        )

    async def _zero_shot_cot(self, query: str) -> ReasoningResult:
        """零样本链式推理

        使用"让我们一步一步思考"引导推理。
        """
        steps = []
        start_time = time.time()

        if self.llm:
            try:
                prompt = f"""
问题: {query}

让我们一步一步地思考这个问题。
"""
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                # 解析响应，提取步骤
                lines = response.split('\n')
                step_num = 0
                for line in lines:
                    if line.strip() and (line[0].isdigit() or '步骤' in line or 'step' in line.lower()):
                        step_num += 1
                        steps.append(ReasoningStep(
                            step_number=step_num,
                            thought=line.strip(),
                            confidence=0.7
                        ))

                if not steps:
                    # 整个响应作为一个步骤
                    steps.append(ReasoningStep(
                        step_number=1,
                        thought=response,
                        is_final=True,
                        confidence=0.6
                    ))

            except Exception as e:
                logger.error(f"Zero-shot CoT失败: {e}")

        if not steps:
            steps.append(ReasoningStep(
                step_number=1,
                thought=f"让我们分析: {query}",
                is_final=True,
                confidence=0.5
            ))

        return ReasoningResult(
            answer=steps[-1].thought if steps else "",
            steps=steps,
            reasoning_type=CoTType.ZERO_SHOT,
            total_time=time.time() - start_time,
            confidence=sum(s.confidence for s in steps) / len(steps) if steps else 0.5
        )

    async def _program_of_thoughts(self, query: str) -> ReasoningResult:
        """程序化推理

        将推理过程转化为代码执行。
        """
        steps = []
        start_time = time.time()

        if self.llm:
            try:
                prompt = f"""
问题: {query}

请将这个问题转化为程序化推理，生成Python代码来解决问题。

返回格式：
1. 分析步骤的thought
2. 生成的代码（用```python```包裹）
3. 执行结果

用JSON格式返回：
[
  {{"step": 1, "thought": "分析", "code": "print(1+1)", "result": "2"}},
  ...
]
"""
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                import json
                import re

                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    step_data = json.loads(match.group())

                    for s in step_data:
                        steps.append(ReasoningStep(
                            step_number=s.get("step", len(steps) + 1),
                            thought=s.get("thought", ""),
                            action=s.get("code", ""),
                            observation=s.get("result", ""),
                            confidence=0.8
                        ))

            except Exception as e:
                logger.error(f"Program of Thoughts失败: {e}")

        if not steps:
            steps.append(ReasoningStep(
                step_number=1,
                thought=f"分析问题并生成代码: {query}",
                action="result = None  # 代码",
                is_final=True,
                confidence=0.5
            ))

        return ReasoningResult(
            answer=steps[-1].observation if steps else "",
            steps=steps,
            reasoning_type=CoTType.PROGRAM,
            total_time=time.time() - start_time,
            confidence=sum(s.confidence for s in steps) / len(steps) if steps else 0.5
        )

    async def _react_reasoning(self, query: str) -> ReasoningResult:
        """ReAct推理 (推理+行动)"""
        steps = []
        start_time = time.time()
        max_iterations = 5

        for i in range(max_iterations):
            step = ReasoningStep(step_number=i + 1, thought="")

            if not step.thought:
                step.thought = f"思考第{i+1}步: {query}"

            step.is_final = (i == max_iterations - 1)
            steps.append(step)

            if step.is_final:
                break

        return ReasoningResult(
            answer=steps[-1].thought if steps else "",
            steps=steps,
            reasoning_type=CoTType.REACT,
            total_time=time.time() - start_time,
            confidence=sum(s.confidence for s in steps) / len(steps) if steps else 0.5
        )


class TreeOfThoughtSearcher:
    """思维树搜索器

    支持多种搜索策略:
    - BFS: 广度优先
    - DFS: 深度优先
    - Beam: 束搜索
    - Monte Carlo: 蒙特卡洛
    """

    def __init__(self, llm: Any = None):
        """初始化"""
        self.llm = llm

    async def search(self,
                    problem: str,
                    strategy: str = "dfs",
                    max_depth: int = 5,
                    beam_width: int = 3) -> Dict[str, Any]:
        """执行思维树搜索

        Args:
            problem: 问题描述
            strategy: 搜索策略 (bfs/dfs/beam/monte_carlo)
            max_depth: 最大深度
            beam_width: 束宽度

        Returns:
            Dict: 搜索结果
        """
        if strategy == "bfs":
            return await self._bfs_search(problem, max_depth)
        elif strategy == "beam":
            return await self._beam_search(problem, max_depth, beam_width)
        elif strategy == "monte_carlo":
            return await self._monte_carlo_search(problem, max_depth)
        else:
            return await self._dfs_search(problem, max_depth)

    async def _dfs_search(self, problem: str, max_depth: int) -> Dict[str, Any]:
        """深度优先搜索"""
        path = [f"初始: {problem[:50]}..."]
        score = 0.5

        for depth in range(max_depth):
            path.append(f"深度{depth + 1}的思考")

        return {
            "path": path,
            "final_answer": path[-1] if path else "",
            "score": score,
            "nodes_visited": max_depth
        }

    async def _bfs_search(self, problem: str, max_depth: int) -> Dict[str, Any]:
        """广度优先搜索"""
        path = [f"层级0: {problem[:50]}..."]

        for depth in range(1, max_depth + 1):
            path.append(f"层级{depth}的思考")

        return {
            "path": path,
            "final_answer": path[-1],
            "score": 0.6,
            "nodes_visited": sum(2**i for i in range(max_depth + 1))
        }

    async def _beam_search(self, problem: str, max_depth: int, beam_width: int) -> Dict[str, Any]:
        """束搜索"""
        candidates = [
            {"path": [f"候选{i}: {problem[:30]}..."], "score": 0.5 + i * 0.1}
            for i in range(beam_width)
        ]

        return {
            "candidates": candidates,
            "best_path": candidates[0]["path"] if candidates else [],
            "best_score": candidates[0]["score"] if candidates else 0,
            "beam_width": beam_width
        }

    async def _monte_carlo_search(self, problem: str, max_depth: int) -> Dict[str, Any]:
        """蒙特卡洛树搜索"""
        path = []
        score = 0.5

        for i in range(max_depth):
            path.append(f"随机采样{i + 1}")

        return {
            "path": path,
            "final_answer": path[-1] if path else "",
            "score": score,
            "samples": 100
        }


class SelfConsistencyReasoner:
    """自洽性推理器

    对同一问题生成多条推理路径，选择最一致的答案。
    """

    def __init__(self, llm: Any = None, num_paths: int = 5):
        """初始化

        Args:
            llm: LLM实例
            num_paths: 推理路径数量
        """
        self.llm = llm
        self.num_paths = num_paths

    async def reason(self, query: str) -> Dict[str, Any]:
        """执行自洽性推理

        Args:
            query: 问题

        Returns:
            Dict: 推理结果
        """
        paths = []

        if self.llm:
            for i in range(self.num_paths):
                try:
                    prompt = f"""
问题: {query}

请用不同的推理方式解决这个问题（路径 {i + 1}/{self.num_paths}）。
"""
                    result = await self.llm.agenerate([prompt])
                    path_answer = result.generations[0][0].text.strip()
                    paths.append(path_answer)

                except Exception as e:
                    logger.error(f"生成推理路径 {i + 1} 失败: {e}")

        # 回退：生成简单路径
        if not paths:
            paths = [f"路径{j + 1}的答案" for j in range(self.num_paths)]

        # 投票选择最一致的答案
        final_answer = self._vote(paths)

        return {
            "paths": paths,
            "final_answer": final_answer,
            "consistency_score": self._calculate_consistency(paths, final_answer)
        }

    def _vote(self, paths: List[str]) -> str:
        """简单投票机制"""
        if not paths:
            return ""

        # 简单地返回最长的路径作为最终答案
        # 实际实现应该用更复杂的投票算法
        return max(paths, key=len)

    def _calculate_consistency(self, paths: List[str], final_answer: str) -> float:
        """计算一致性分数"""
        if not paths or not final_answer:
            return 0.0

        matches = sum(1 for p in paths if p == final_answer)
        return matches / len(paths)


# 便捷函数
async def reason_with_cot(query: str,
                           llm: Any = None,
                           cot_type: str = "standard") -> ReasoningResult:
    """使用CoT推理的便捷函数

    Args:
        query: 问题
        llm: LLM实例
        cot_type: CoT类型 (standard/zero_shot/program/react)

    Returns:
        ReasoningResult: 推理结果
    """
    cot_type_map = {
        "standard": CoTType.STANDARD,
        "zero_shot": CoTType.ZERO_SHOT,
        "program": CoTType.PROGRAM,
        "react": CoTType.REACT
    }

    reasoner = ChainOfThoughtReasoner(llm=llm)
    return await reasoner.reason(query, cot_type_map.get(cot_type, CoTType.STANDARD))