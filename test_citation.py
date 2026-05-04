"""Citation processing test"""
import sys
import asyncio
sys.path.insert(0, '.')

from src.agents_v2.writing.reference_processor import ReferenceProcessorAgent
from src.agents_v2.config import LLMConfig
import os

async def test_citation():
    print('=== Citation Processing Test ===')
    print()

    llm_config = LLMConfig(
        provider='openai',
        model_name=os.getenv('LLM_MODEL', 'MiniMax-M2.7'),
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL', 'https://api.minimax.chat/v1'),
        temperature=0.7,
        max_tokens=4096
    )
    agent = ReferenceProcessorAgent(llm_config=llm_config)

    result = await agent.execute({
        'paper_content': '''深度学习在医学影像诊断中取得了显著进展[1]。

Transformer架构[2]已被广泛应用于医学图像分析。

研究表明，ResNet在影像分类任务中表现优异[3]。

引用检测: 这篇论文引用了Attention机制[4]。

近年研究: BERT模型[5]在医学NLP任务中取得突破。
''',
        'raw_references': [
            {'authors': ['Zhang Wei', 'Li Hong'], 'year': '2023', 'title': 'Deep Learning in Medical Imaging', 'journal': 'Medical Image Analysis', 'doi': '10.1016/j.media.2023.01.001'},
            {'authors': ['Vaswani A', 'Shazeer N'], 'year': '2017', 'title': 'Attention Is All You Need', 'journal': 'NeurIPS', 'doi': '10.48550/arXiv.1706.03762'},
            {'authors': ['He K', 'Zhang X'], 'year': '2016', 'title': 'Deep Residual Learning for Image Recognition', 'journal': 'CVPR', 'doi': '10.1109/CVPR.2016.90'},
            {'authors': ['Devlin J', 'Chang M'], 'year': '2019', 'title': 'BERT: Pre-training of Deep Bidirectional Transformers', 'journal': 'NAACL', 'doi': '10.18653/v1/N19-1423'},
        ],
        'citation_style': 'GB_T'
    }, {})

    print(f'处理成功: {result.success}')
    print(f'质量分数: {result.quality_score}')

    if result.result:
        print(f'\n参考文献列表:\n{result.result.get("reference_list", "无")}')
        print(f'\n验证结果: {result.result.get("validation", {})}')

    return result

if __name__ == '__main__':
    result = asyncio.run(test_citation())