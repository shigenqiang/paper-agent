"""Full paper generation test"""
import sys
import asyncio
import time
import os

# 设置工作目录
os.chdir('D:/pycharmprojects/pythonProject1')
sys.path.insert(0, '.')

# 设置 UTF-8 输出
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src.main import setup_logging

def test_paper_generation():
    from demos.full_paper.runner import FullPaperRunner

    topic = "深度学习在医学影像诊断中的应用"

    print('=' * 60)
    print('论文写作流程测试')
    print('=' * 60)
    print(f'主题: {topic}')
    print()

    runner = FullPaperRunner(enable_hitl=False)

    start = time.time()
    result = asyncio.run(runner.run(topic, paper_only=False))
    elapsed = time.time() - start

    print()
    print('=' * 60)
    print('测试结果')
    print('=' * 60)
    print(f'成功: {result["success"]}')
    print(f'完成阶段: {", ".join(result["phases_completed"]) if result["phases_completed"] else "无"}')
    print(f'论文长度: {len(result["final_paper"])} 字符')
    print(f'质量评分: {result["quality_score"]:.2f}')
    print(f'引用数量: {result["polish_output"].get("citation_count", 0)}')

    polish = result.get('polish_output', {})
    if polish.get('reference_list'):
        ref_list = polish['reference_list']
        print(f'\n参考文献预览:\n{ref_list[:800]}...')

    print(f'\n总耗时: {elapsed:.2f}秒')

    return result

if __name__ == '__main__':
    setup_logging(level='INFO')
    test_paper_generation()