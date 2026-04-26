"""
链路监控模块单元测试

测试链路监控、延迟跟踪和调试功能
"""
import pytest
from datetime import datetime, timedelta
from src.agents_v2.monitoring import (
    ChainMonitor,
    ChainEvent,
    EventType,
    LatencyTracker,
    LatencyRecord,
    LatencyStats,
    ChainDebugger,
    DebugSnapshot,
    DebugLevel,
    create_monitor,
    create_tracker,
    create_debugger,
)


class TestEventType:
    """EventType 测试"""

    def test_all_event_types_exist(self):
        """测试所有事件类型存在"""
        assert EventType.CHAIN_START.value == "chain_start"
        assert EventType.CHAIN_END.value == "chain_end"
        assert EventType.PHASE_START.value == "phase_start"
        assert EventType.AGENT_START.value == "agent_start"
        assert EventType.ERROR.value == "error"


class TestChainEvent:
    """ChainEvent 测试"""

    def test_create_event(self):
        """测试创建事件"""
        event = ChainEvent(
            event_id="evt_1",
            event_type=EventType.CHAIN_START,
            chain_id="chain_123"
        )
        assert event.event_id == "evt_1"
        assert event.success is True

    def test_to_dict(self):
        """测试转换为字典"""
        event = ChainEvent(
            event_id="evt_1",
            event_type=EventType.AGENT_END,
            duration_ms=100.0
        )
        d = event.to_dict()
        assert d["event_id"] == "evt_1"
        assert d["duration_ms"] == 100.0


class TestChainMonitor:
    """ChainMonitor 测试"""

    def setup_method(self):
        self.monitor = ChainMonitor()

    def test_record_event(self):
        """测试记录事件"""
        event = ChainEvent(
            event_id="evt_1",
            event_type=EventType.CHAIN_START
        )
        self.monitor.record_event(event)

        events = self.monitor.get_events()
        assert len(events) == 1

    def test_create_event(self):
        """测试创建事件"""
        event = self.monitor.create_event(
            event_type=EventType.PHASE_START,
            chain_id="chain_123",
            phase="literature"
        )
        assert event.event_type == EventType.PHASE_START
        assert event.chain_id == "chain_123"

    def test_track_event_context(self):
        """测试追踪上下文"""
        with self.monitor.track_event(
            EventType.AGENT_START,
            chain_id="chain_1",
            agent="Retriever"
        ):
            pass

        events = self.monitor.get_events()
        assert len(events) >= 1

    def test_get_stats(self):
        """测试获取统计"""
        event = ChainEvent(
            event_id="evt_1",
            event_type=EventType.CHAIN_START,
            success=False
        )
        self.monitor.record_event(event)

        stats = self.monitor.get_stats()
        assert stats["total_events"] >= 1
        assert stats["error_count"] >= 1

    def test_get_chain_timeline(self):
        """测试获取链路时间线"""
        self.monitor.record_event(ChainEvent(
            event_id="evt_1",
            event_type=EventType.CHAIN_START,
            chain_id="chain_X"
        ))

        timeline = self.monitor.get_chain_timeline("chain_X")
        assert len(timeline) >= 1


class TestLatencyRecord:
    """LatencyRecord 测试"""

    def test_create_record(self):
        """测试创建记录"""
        now = datetime.now()
        record = LatencyRecord(
            component="Retriever",
            operation="search",
            start_time=now,
            end_time=now + timedelta(milliseconds=100),
            duration_ms=100.0
        )
        assert record.duration_ms == 100.0
        assert record.duration_seconds == 0.1


class TestLatencyStats:
    """LatencyStats 测试"""

    def test_create_stats(self):
        """测试创建统计"""
        stats = LatencyStats(
            component="Retriever",
            count=100,
            avg_ms=50.0
        )
        assert stats.count == 100
        assert stats.avg_ms == 50.0

    def test_to_dict(self):
        """测试转换为字典"""
        stats = LatencyStats(component="Test", avg_ms=10.0)
        d = stats.to_dict()
        assert d["component"] == "Test"
        assert d["avg_ms"] == 10.0


class TestLatencyTracker:
    """LatencyTracker 测试"""

    def setup_method(self):
        self.tracker = LatencyTracker()

    def test_track_context(self):
        """测试追踪上下文"""
        with self.tracker.track("Retriever", "search"):
            pass

        stats = self.tracker.get_stats("Retriever")
        assert stats["Retriever"].count >= 1

    def test_record_manual(self):
        """测试手动记录"""
        now = datetime.now()
        self.tracker.record(
            component="TestComponent",
            operation="test_op",
            start_time=now,
            end_time=now + timedelta(milliseconds=50)
        )

        stats = self.tracker.get_stats("TestComponent")
        assert stats["TestComponent"].count == 1

    def test_get_stats_all(self):
        """测试获取所有统计"""
        with self.tracker.track("A", "op1"):
            pass
        with self.tracker.track("B", "op2"):
            pass

        stats = self.tracker.get_stats()
        assert len(stats) >= 2


class TestDebugSnapshot:
    """DebugSnapshot 测试"""

    def test_create_snapshot(self):
        """测试创建快照"""
        snapshot = DebugSnapshot(
            snapshot_id="snap_1",
            chain_id="chain_123",
            phase="literature"
        )
        assert snapshot.snapshot_id == "snap_1"

    def test_to_dict(self):
        """测试转换为字典"""
        snapshot = DebugSnapshot(
            snapshot_id="snap_1",
            chain_id="chain_123"
        )
        d = snapshot.to_dict()
        assert d["snapshot_id"] == "snap_1"
        assert d["chain_id"] == "chain_123"

    def test_to_json(self):
        """测试转换为JSON"""
        snapshot = DebugSnapshot(
            snapshot_id="snap_1",
            chain_id="chain_123",
            state={"key": "value"}
        )
        json_str = snapshot.to_json()
        assert "snap_1" in json_str


class TestChainDebugger:
    """ChainDebugger 测试"""

    def setup_method(self):
        self.debugger = ChainDebugger()

    def test_snapshot(self):
        """测试创建快照"""
        snap = self.debugger.snapshot(
            chain_id="chain_123",
            phase="literature",
            state={"progress": 50}
        )
        assert snap.chain_id == "chain_123"
        assert snap.state["progress"] == 50

    def test_get_snapshots(self):
        """测试获取快照"""
        self.debugger.snapshot(chain_id="chain_X", phase="topic")
        self.debugger.snapshot(chain_id="chain_X", phase="literature")

        snaps = self.debugger.get_snapshots(chain_id="chain_X")
        assert len(snaps) >= 2

    def test_get_latest(self):
        """测试获取最新快照"""
        self.debugger.snapshot(chain_id="chain_Y", phase="A")
        self.debugger.snapshot(chain_id="chain_Y", phase="B")

        latest = self.debugger.get_latest(chain_id="chain_Y")
        assert latest is not None
        assert latest.phase == "B"

    def test_compare(self):
        """测试比较快照"""
        snap1 = self.debugger.snapshot(
            chain_id="chain_C",
            phase="phase1",
            state={"value": 1}
        )
        snap2 = self.debugger.snapshot(
            chain_id="chain_C",
            phase="phase2",
            state={"value": 2}
        )

        diff = self.debugger.compare(snap1.snapshot_id, snap2.snapshot_id)
        assert "state_changes" in diff
        assert diff["phase_change"] is True

    def test_replay(self):
        """测试回放"""
        for i in range(3):
            self.debugger.snapshot(
                chain_id="chain_replay",
                phase=f"phase_{i}",
                state={"step": i}
            )

        replay = self.debugger.replay("chain_replay")
        assert len(replay) >= 3

    def test_clear(self):
        """测试清除"""
        self.debugger.snapshot(chain_id="chain_clear", phase="A")
        self.debugger.clear()

        stats = self.debugger.get_stats()
        assert stats["total_snapshots"] == 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_monitor(self):
        """测试创建监控器"""
        monitor = create_monitor()
        assert isinstance(monitor, ChainMonitor)

    def test_create_tracker(self):
        """测试创建跟踪器"""
        tracker = create_tracker()
        assert isinstance(tracker, LatencyTracker)

    def test_create_debugger(self):
        """测试创建调试器"""
        debugger = create_debugger(DebugLevel.DETAILED)
        assert isinstance(debugger, ChainDebugger)
        assert debugger.level == DebugLevel.DETAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])