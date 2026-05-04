"""Quick test script for paper generation"""
import sys
sys.path.insert(0, '.')

print('Testing imports...')
from src.agents_v2.langgraph_workflow.unified_workflow import UnifiedWorkflow
print('UnifiedWorkflow imported successfully')

from src.agents_v2.writing.reference_processor import ReferenceProcessorAgent
print('ReferenceProcessorAgent imported successfully')

print('All imports OK')