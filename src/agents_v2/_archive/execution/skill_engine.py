"""
技能获取引擎 - Skill Acquisition Engine

实现Voyager式持续技能获取:
1. 从成功案例中提取技能
2. 技能库存储与检索
3. 新任务尝试使用技能
4. 失败时生成新技能
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """技能定义"""
    id: str
    name: str
    description: str
    code: str
    success_rate: float = 0.0
    usage_count: int = 0
    last_used: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_stale(self, days: int = 30) -> bool:
        """检查技能是否过时"""
        return time.time() - self.last_used > days * 24 * 3600


@dataclass
class SkillExecution:
    """技能执行记录"""
    skill_id: str
    task: str
    success: bool
    execution_time: float
    error_message: str = ""


class SkillAcquisitionEngine:
    """技能获取引擎

    核心功能:
    - 从成功执行中提取技能
    - 维护技能库
    - 匹配和应用技能
    - 评估和优化技能
    """

    def __init__(self, llm: Any = None):
        """初始化

        Args:
            llm: LLM实例，用于生成和优化技能代码
        """
        self.llm = llm
        self._skill_library: Dict[str, Skill] = {}
        self._execution_history: deque = deque(maxlen=1000)
        self._task_skill_mapping: Dict[str, List[str]] = {}  # task_pattern -> skill_ids

    def register_skill(self, skill: Skill) -> bool:
        """注册技能

        Args:
            skill: 技能定义

        Returns:
            bool: 是否成功
        """
        if skill.id in self._skill_library:
            logger.warning(f"技能 {skill.id} 已存在，更新")
            return False

        self._skill_library[skill.id] = skill
        self._update_task_mapping(skill)
        logger.info(f"注册技能: {skill.name}")
        return True

    def _update_task_mapping(self, skill: Skill):
        """更新任务-技能映射"""
        keywords = self._extract_keywords(skill.description)

        for keyword in keywords:
            if keyword not in self._task_skill_mapping:
                self._task_skill_mapping[keyword] = []
            if skill.id not in self._task_skill_mapping[keyword]:
                self._task_skill_mapping[keyword].append(skill.id)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取英文单词和中文词
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # 添加可能的关键词
        keywords = set(words)

        return list(keywords)[:10]  # 限制数量

    def find_relevant_skills(self, task: str, top_k: int = 5) -> List[Tuple[Skill, float]]:
        """查找相关技能

        Args:
            task: 任务描述
            top_k: 返回数量

        Returns:
            List[Tuple[Skill, float]]: (技能, 相关度) 列表
        """
        task_lower = task.lower()
        task_keywords = set(task_lower.split())

        scored_skills = []

        for skill in self._skill_library.values():
            # 计算相关度
            skill_keywords = set(self._extract_keywords(skill.description))
            overlap = len(task_keywords & skill_keywords)

            if overlap > 0:
                # 综合使用率和成功率
                relevance = overlap + skill.usage_count * 0.1 + skill.success_rate * 0.5
                scored_skills.append((skill, relevance))

        scored_skills.sort(key=lambda x: x[1], reverse=True)
        return scored_skills[:top_k]

    async def execute_skill(self, skill: Skill, context: Dict) -> Any:
        """执行技能

        Args:
            skill: 技能
            context: 执行上下文

        Returns:
            Any: 执行结果
        """
        start_time = time.time()

        try:
            # 动态执行技能代码
            local_vars = {"context": context, "result": None}
            exec(skill.code, local_vars)
            result = local_vars.get("result")

            execution = SkillExecution(
                skill_id=skill.id,
                task=context.get("task", ""),
                success=True,
                execution_time=time.time() - start_time
            )
            self._execution_history.append(execution)

            # 更新技能统计
            skill.usage_count += 1
            skill.last_used = time.time()

            return result

        except Exception as e:
            execution = SkillExecution(
                skill_id=skill.id,
                task=context.get("task", ""),
                success=False,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
            self._execution_history.append(execution)

            logger.error(f"技能执行失败 {skill.id}: {e}")
            raise

    async def learn_from_execution(self, execution: SkillExecution) -> Optional[Skill]:
        """从执行结果学习

        Args:
            execution: 执行记录

        Returns:
            Optional[Skill]: 如果成功，可能返回新技能
        """
        if execution.success:
            # 更新相关技能的成功率
            for skill in self._skill_library.values():
                if skill.id == execution.skill_id:
                    skill.success_rate = (
                        skill.success_rate * 0.9 + 0.1
                    )
                    return None

        # 失败时，可能需要生成新技能
        if not execution.success and self.llm:
            return await self._generate_remedial_skill(execution)

        return None

    async def _generate_remedial_skill(self, execution: SkillExecution) -> Optional[Skill]:
        """生成补救技能"""
        if not self.llm:
            return None

        try:
            prompt = f"""
执行失败的任务: {execution.task}
错误信息: {execution.error_message}

请生成一个补救技能来解决这个问题。
返回JSON格式：
{{
    "name": "技能名称",
    "description": "技能描述",
    "code": "Python代码"
}}
"""
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip()

            import json
            import re

            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                skill = Skill(
                    id=f"remedial_{int(time.time())}",
                    name=data["name"],
                    description=data["description"],
                    code=data["code"],
                    success_rate=0.5
                )
                self.register_skill(skill)
                return skill

        except Exception as e:
            logger.error(f"生成补救技能失败: {e}")

        return None

    def get_skill_stats(self) -> Dict[str, Any]:
        """获取技能统计"""
        total = len(self._skill_library)
        total_usage = sum(s.usage_count for s in self._skill_library.values())
        avg_success = sum(s.success_rate for s in self._skill_library.values()) / total if total > 0 else 0

        # 最近的执行历史
        recent_executions = list(self._execution_history)[-10:]
        recent_success_rate = sum(1 for e in recent_executions if e.success) / len(recent_executions) if recent_executions else 0

        return {
            "total_skills": total,
            "total_usages": total_usage,
            "avg_success_rate": avg_success,
            "recent_success_rate": recent_success_rate,
            "skill_details": [
                {"id": s.id, "name": s.name, "usage_count": s.usage_count, "success_rate": s.success_rate}
                for s in self._skill_library.values()
            ]
        }

    def prune_skills(self, min_success_rate: float = 0.3, max_age_days: int = 90) -> int:
        """剪除低质量或过时技能

        Args:
            min_success_rate: 最小成功率
            max_age_days: 最大存活天数

        Returns:
            int: 剪除的技能数量
        """
        to_remove = []

        for skill in self._skill_library.values():
            if skill.success_rate < min_success_rate or skill.is_stale(max_age_days):
                to_remove.append(skill.id)

        for skill_id in to_remove:
            del self._skill_library[skill_id]
            logger.info(f"剪除技能: {skill_id}")

        return len(to_remove)


class LongTermTaskExecutor:
    """长期任务执行器

    支持:
    - 分阶段执行
    - 检查点保存
    - 动态调整
    """

    def __init__(self):
        """初始化"""
        self._checkpoints: Dict[str, Dict] = {}
        self._active_tasks: Dict[str, Dict] = {}

    def save_checkpoint(self, task_id: str, phase: str, state: Dict):
        """保存检查点

        Args:
            task_id: 任务ID
            phase: 阶段
            state: 状态
        """
        self._checkpoints[f"{task_id}:{phase}"] = {
            "task_id": task_id,
            "phase": phase,
            "state": state,
            "timestamp": time.time()
        }
        logger.info(f"保存检查点: {task_id}:{phase}")

    def load_checkpoint(self, task_id: str, phase: str) -> Optional[Dict]:
        """加载检查点

        Args:
            task_id: 任务ID
            phase: 阶段

        Returns:
            Optional[Dict]: 检查点状态
        """
        return self._checkpoints.get(f"{task_id}:{phase}")

    async def execute_phases(self,
                            task_id: str,
                            phases: List[Dict],
                            executor: Callable) -> Dict[str, Any]:
        """分阶段执行任务

        Args:
            task_id: 任务ID
            phases: 阶段列表
            executor: 执行器

        Returns:
            Dict: 执行结果
        """
        results = {}
        self._active_tasks[task_id] = {"phases": phases, "completed": []}

        for i, phase in enumerate(phases):
            phase_name = phase.get("name", f"phase_{i}")
            phase_func = phase.get("func")

            # 检查是否有检查点
            checkpoint = self.load_checkpoint(task_id, phase_name)
            if checkpoint:
                logger.info(f"从检查点恢复: {task_id}:{phase_name}")
                results[phase_name] = checkpoint["state"]
                continue

            # 执行阶段
            try:
                if phase_func:
                    result = await phase_func()
                else:
                    result = await executor(phase)

                results[phase_name] = result
                self._active_tasks[task_id]["completed"].append(phase_name)

                # 保存检查点
                self.save_checkpoint(task_id, phase_name, {"result": result})

            except Exception as e:
                logger.error(f"阶段执行失败 {phase_name}: {e}")
                results[phase_name] = {"error": str(e)}

                # 保存失败检查点
                self.save_checkpoint(task_id, phase_name, {"error": str(e)})

        return results


# 便捷函数
def create_skill_engine(llm: Any = None) -> SkillAcquisitionEngine:
    """创建技能获取引擎"""
    return SkillAcquisitionEngine(llm=llm)


def create_long_term_executor() -> LongTermTaskExecutor:
    """创建长期任务执行器"""
    return LongTermTaskExecutor()