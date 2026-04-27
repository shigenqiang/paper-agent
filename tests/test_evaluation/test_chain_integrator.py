"""
Chain Integrator Tests

Tests for:
- ChainIntegrator: End-to-end chain testing
- IntegrationTester: Integration test orchestration
"""
import pytest
from src.agents_v2.evaluation.chain_integrator import (
    ChainIntegrator,
    IntegrationTester,
    IntegrationStage,
    IntegrationStep,
    IntegrationResult,
    ChainTestResult
)


class TestIntegrationStep:
    """IntegrationStep Tests"""

    def test_create_step(self):
        """Test creating an integration step"""
        step = IntegrationStep(
            name="test_step",
            stage=IntegrationStage.INPUT,
            component="TestComponent",
            input_schema={"query": str},
            output_schema={"result": str},
            timeout=30.0,
            retry_count=3
        )
        assert step.name == "test_step"
        assert step.stage == IntegrationStage.INPUT
        assert step.component == "TestComponent"
        assert step.timeout == 30.0


class TestIntegrationResult:
    """IntegrationResult Tests"""

    def test_create_result(self):
        """Test creating an integration result"""
        result = IntegrationResult(
            step_name="test",
            success=True,
            duration=1.5,
            input_data={"query": "test"},
            output_data={"result": "success"}
        )
        assert result.step_name == "test"
        assert result.success is True
        assert result.duration == 1.5


class TestChainTestResult:
    """ChainTestResult Tests"""

    def test_create_chain_result(self):
        """Test creating a chain test result"""
        result = ChainTestResult(
            chain_name="test_chain",
            overall_success=True,
            total_duration=5.0,
            step_results=[],
            failed_steps=[]
        )
        assert result.chain_name == "test_chain"
        assert result.overall_success is True
        assert result.total_duration == 5.0


class TestChainIntegrator:
    """ChainIntegrator Tests"""

    def setup_method(self):
        self.integrator = ChainIntegrator()

    def test_init(self):
        """Test initialization"""
        assert len(self.integrator._chains) > 0
        assert "paper_search" in self.integrator._chains
        assert "paper_writing" in self.integrator._chains

    def test_register_component(self):
        """Test registering components"""
        class MockComponent:
            pass

        self.integrator.register_component("test_component", MockComponent())
        assert "test_component" in self.integrator._components

    def test_get_chain_info(self):
        """Test getting chain info"""
        info = self.integrator.get_chain_info("paper_search")
        assert info["name"] == "paper_search"
        assert info["total_steps"] > 0
        assert "stages" in info

    def test_get_chain_info_not_found(self):
        """Test getting info for non-existent chain"""
        info = self.integrator.get_chain_info("nonexistent")
        assert info == {}

    def test_list_chains(self):
        """Test listing chains"""
        chains = self.integrator.list_chains()
        assert "paper_search" in chains
        assert "paper_writing" in chains

    @pytest.mark.asyncio
    async def test_test_chain_success(self):
        """Test successful chain execution"""
        result = await self.integrator.test_chain(
            "paper_search",
            {"query": "machine learning"},
            mock_components=True
        )
        assert result.chain_name == "paper_search"
        assert len(result.step_results) > 0

    @pytest.mark.asyncio
    async def test_chain_not_found(self):
        """Test chain not found"""
        result = await self.integrator.test_chain(
            "nonexistent_chain",
            {},
            mock_components=True
        )
        assert result.overall_success is False
        assert "not found" in str(result.failed_steps)


class TestIntegrationTester:
    """IntegrationTester Tests"""

    def setup_method(self):
        self.tester = IntegrationTester()
        self.integrator = ChainIntegrator()

    @pytest.mark.asyncio
    async def test_run_integration_tests(self):
        """Test running integration tests"""
        test_cases = [
            {
                "chain_name": "paper_search",
                "input_data": {"query": "test query"}
            }
        ]

        report = await self.tester.run_integration_tests(
            self.integrator,
            test_cases
        )

        assert "total_tests" in report
        assert report["total_tests"] >= 1


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.asyncio
    async def test_run_paper_search_chain(self):
        """Test paper search chain convenience function"""
        from src.agents_v2.evaluation.chain_integrator import run_paper_search_chain
        result = await run_paper_search_chain({"query": "test"})
        assert result.chain_name == "paper_search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])