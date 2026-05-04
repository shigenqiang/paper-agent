"""Test runner for acceptance tests - run via make test-acceptance"""
import asyncio
import sys
sys.path.insert(0, '.')

from test_full_acceptance import (
    test_ragas_metrics, test_hallucination_detection,
    test_multi_hop_reasoning, test_kg_recall,
    test_memory_system, test_latency, test_state_isolation,
    test_paper_generation_performance, test_paper_quality
)

async def run_all_tests():
    tests = [
        ('RAGAs', test_ragas_metrics),
        ('Hallucination', test_hallucination_detection),
        ('Multi-hop', test_multi_hop_reasoning),
        ('KG recall', test_kg_recall),
        ('Memory', test_memory_system),
        ('Latency', test_latency),
        ('State isolation', test_state_isolation),
        ('Paper perf', test_paper_generation_performance),
        ('Paper quality', test_paper_quality),
    ]
    results = []
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results.append({'name': name, 'status': 'PASS' if result else 'FAIL'})
        except Exception as e:
            results.append({'name': name, 'status': 'FAIL', 'error': str(e)})
    passed = sum(1 for r in results if r['status'] == 'PASS')
    print('='*50)
    print(f'Tests: {passed}/{len(results)} passed')
    print('='*50)
    for r in results:
        status = 'PASS' if r['status'] == 'PASS' else 'FAIL'
        print(f'  [{status}] {r["name"]}')

if __name__ == '__main__':
    asyncio.run(run_all_tests())