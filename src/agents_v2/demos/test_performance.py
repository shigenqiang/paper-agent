"""
Paper Agent 性能测试脚本

使用方法:
1. 设置环境变量: set OPENAI_API_KEY=your_minimax_api_key
2. 运行测试: python -m src.agents_v2.demos.test_performance

测试内容:
- 各功能模块响应时间
- 输出质量基本验证
- 成功率统计
"""
import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果"""
    name: str
    success: bool
    response_time: float  # 秒
    output_preview: str = ""
    error: Optional[str] = None
    quality_notes: str = ""


@dataclass
class TestReport:
    """测试报告"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    results: List[TestResult] = field(default_factory=list)

    @property
    def total_tests(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_tests * 100 if self.total_tests > 0 else 0

    @property
    def avg_response_time(self) -> float:
        times = [r.response_time for r in self.results if r.success]
        return sum(times) / len(times) if times else 0


class PerformanceTester:
    """性能测试器"""

    def __init__(self):
        self.report = TestReport()
        self._check_api_key()

    def _check_api_key(self):
        """检查API Key配置"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("未设置 OPENAI_API_KEY 环境变量，LLM功能可能无法正常工作")
        else:
            logger.info(f"API Key已配置: {api_key[:10]}...")

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*70)
        print("Paper Agent 性能测试")
        print(f"测试时间: {self.report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        # 按优先级执行测试
        tests = [
            ("P0-意图路由", self.test_intent_router),
            ("P0-选题推荐", self.test_topic_agent),
            ("P0-文献搜索", self.test_paper_search),
            ("P0-大纲生成", self.test_outline_agent),
            ("P1-文献综述", self.test_literature_review),
            ("P1-开题报告", self.test_proposal_generator),
        ]

        for test_name, test_func in tests:
            print(f"\n{'─'*50}")
            print(f"测试: {test_name}")
            print(f"{'─'*50}")

            try:
                result = await test_func()
                self.report.results.append(result)

                status = "✅ 成功" if result.success else "❌ 失败"
                print(f"  状态: {status}")
                print(f"  响应时间: {result.response_time:.2f}秒")
                if result.output_preview:
                    print(f"  输出预览: {result.output_preview[:100]}...")
                if result.error:
                    print(f"  错误: {result.error}")

            except Exception as e:
                logger.error(f"测试 {test_name} 异常: {e}")
                self.report.results.append(TestResult(
                    name=test_name,
                    success=False,
                    response_time=0,
                    error=str(e)
                ))

            # 测试间隔，避免API限流
            await asyncio.sleep(2)

        # 生成报告
        self.report.end_time = datetime.now()
        self._print_summary()

    async def test_intent_router(self) -> TestResult:
        """测试意图路由"""
        start_time = time.time()

        try:
            from src.agents_v2.unified import IntentRouter

            router = IntentRouter()

            test_requests = [
                "我想写一篇关于深度学习的论文",
                "帮我搜索Transformer相关论文",
            ]

            results = []
            for req in test_requests:
                result = await router.route(req)
                results.append(result)

            response_time = time.time() - start_time

            # 验证输出
            success = all(r.get("intent") for r in results)
            preview = f"意图: {results[0].get('intent')}, Agent: {results[0].get('suggested_agents')}"

            return TestResult(
                name="意图路由",
                success=success,
                response_time=response_time,
                output_preview=preview
            )

        except Exception as e:
            return TestResult(
                name="意图路由",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def test_topic_agent(self) -> TestResult:
        """测试选题推荐"""
        start_time = time.time()

        try:
            from src.agents_v2.paper_agents import TopicAgent
            from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

            llm_config = LLMConfig(
                provider="openai",
                model_name="minimax",
                temperature=0.7
            )

            agent = TopicAgent(llm_config)
            result = await agent.execute({
                "user_request": "我想研究人工智能在医疗领域的应用"
            })

            response_time = time.time() - start_time

            # 验证输出
            success = result.success and result.result is not None
            preview = ""
            if result.result:
                topics = result.result.get("topics", [])
                if topics:
                    preview = f"选题: {topics[0].get('title', 'N/A')[:60]}..."

            return TestResult(
                name="选题推荐",
                success=success,
                response_time=response_time,
                output_preview=preview,
                error=result.error if not success else None
            )

        except Exception as e:
            return TestResult(
                name="选题推荐",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def test_paper_search(self) -> TestResult:
        """测试文献搜索"""
        start_time = time.time()

        try:
            from src.agents_v2.paper_search import PaperSearchAgent

            agent = PaperSearchAgent()
            result = await agent.execute(
                "transformer attention mechanism",
                {"source": "arxiv", "max_results": 3}
            )

            response_time = time.time() - start_time

            # 验证输出
            papers = result.get("papers", [])
            success = len(papers) > 0
            preview = f"找到 {len(papers)} 篇论文"
            if papers:
                preview += f", 首篇: {papers[0].get('title', 'N/A')[:40]}..."

            return TestResult(
                name="文献搜索",
                success=success,
                response_time=response_time,
                output_preview=preview
            )

        except Exception as e:
            return TestResult(
                name="文献搜索",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def test_outline_agent(self) -> TestResult:
        """测试大纲生成"""
        start_time = time.time()

        try:
            from src.agents_v2.paper_agents import OutlineAgent
            from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

            llm_config = LLMConfig(
                provider="openai",
                model_name="minimax",
                temperature=0.7
            )

            agent = OutlineAgent(llm_config)
            result = await agent.execute({
                "topic": "深度学习模型压缩技术研究",
                "requirements": "包含模型剪枝、量化、知识蒸馏三个方面"
            })

            response_time = time.time() - start_time

            # 验证输出
            success = result.success and result.result is not None
            preview = ""
            if result.result:
                outline = result.result.get("outline", "")
                preview = outline[:80] + "..." if len(outline) > 80 else outline

            return TestResult(
                name="大纲生成",
                success=success,
                response_time=response_time,
                output_preview=preview,
                error=result.error if not success else None
            )

        except Exception as e:
            return TestResult(
                name="大纲生成",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def test_literature_review(self) -> TestResult:
        """测试文献综述"""
        start_time = time.time()

        try:
            from src.agents_v2.writing import LiteratureReviewAgent

            agent = LiteratureReviewAgent()
            result = await agent.execute({
                "topic": "大语言模型的发展历程"
            })

            response_time = time.time() - start_time

            # 验证输出
            success = result.success and result.result is not None
            preview = ""
            if result.result:
                review = result.result.get("review", "")
                preview = review[:80] + "..." if len(review) > 80 else review

            return TestResult(
                name="文献综述",
                success=success,
                response_time=response_time,
                output_preview=preview,
                error=result.error if not success else None
            )

        except Exception as e:
            return TestResult(
                name="文献综述",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def test_proposal_generator(self) -> TestResult:
        """测试开题报告生成"""
        start_time = time.time()

        try:
            from src.agents_v2.writing import ProposalGeneratorAgent

            agent = ProposalGeneratorAgent()
            result = await agent.execute({
                "topic": "基于深度学习的图像超分辨率算法研究",
                "research_background": "图像超分辨率在医学影像、卫星遥感等领域有重要应用",
                "research_significance": "提高图像质量对下游任务有显著帮助"
            })

            response_time = time.time() - start_time

            # 验证输出
            success = result.success and result.result is not None
            preview = ""
            if result.result:
                proposal = result.result.get("proposal", "")
                preview = proposal[:80] + "..." if len(proposal) > 80 else proposal

            return TestResult(
                name="开题报告",
                success=success,
                response_time=response_time,
                output_preview=preview,
                error=result.error if not success else None
            )

        except Exception as e:
            return TestResult(
                name="开题报告",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )

    def _print_summary(self):
        """打印测试汇总"""
        print("\n" + "="*70)
        print("测试汇总报告")
        print("="*70)

        print(f"\n测试时间: {self.report.start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {self.report.end_time.strftime('%H:%M:%S')}")
        print(f"总测试数: {self.report.total_tests}")
        print(f"成功数量: {self.report.success_count}")
        print(f"成功率: {self.report.success_rate:.1f}%")
        print(f"平均响应时间: {self.report.avg_response_time:.2f}秒")

        print("\n详细结果:")
        print(f"{'─'*70}")
        print(f"{'功能':<15} {'状态':<8} {'响应时间':<12} {'备注'}")
        print(f"{'─'*70}")

        for result in self.report.results:
            status = "✅" if result.success else "❌"
            time_str = f"{result.response_time:.2f}s"
            note = result.output_preview[:30] if result.output_preview else result.error[:30] if result.error else ""
            print(f"{result.name:<15} {status:<8} {time_str:<12} {note}")

        print(f"{'─'*70}")

        # 保存报告到文件
        self._save_report()

    def _save_report(self):
        """保存测试报告"""
        report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "test_outputs")
        os.makedirs(report_dir, exist_ok=True)

        report_file = os.path.join(report_dir, f"performance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("Paper Agent 性能测试报告\n")
            f.write("="*50 + "\n")
            f.write(f"测试时间: {self.report.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总测试数: {self.report.total_tests}\n")
            f.write(f"成功率: {self.report.success_rate:.1f}%\n")
            f.write(f"平均响应时间: {self.report.avg_response_time:.2f}秒\n\n")

            f.write("详细结果:\n")
            f.write("-"*50 + "\n")
            for result in self.report.results:
                status = "成功" if result.success else "失败"
                f.write(f"\n功能: {result.name}\n")
                f.write(f"状态: {status}\n")
                f.write(f"响应时间: {result.response_time:.2f}秒\n")
                if result.output_preview:
                    f.write(f"输出预览: {result.output_preview}\n")
                if result.error:
                    f.write(f"错误: {result.error}\n")

        print(f"\n测试报告已保存: {report_file}")


async def main():
    """主函数"""
    tester = PerformanceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
