# 模型量化技术调研 - 临时文件1

## 搜索记录 1-25

### 核心发现

1. **PyTorch量化体系**
   - 动态量化(dynamic quantization): 权重动态转为INT8，activation保持FP32
   - 静态量化(static quantization): 需校准数据集，整体转为INT8
   - QAT量化感知训练: 在训练中模拟量化效果

2. **主流LLM量化方法**
   - GPTQ: 基于Hessian矩阵的后训练量化，支持4-bit
   - AWQ: 观察activation分布，权重量化更精准
   - GGUF: llama.cpp专用格式，支持多种量化级别(Q2-Q8)
   - bitsandbytes: 实现4-bit NormalFloat (NF4)
   - SqueezeLLM: 基于敏感度的量化

3. **量化级别对照**
   - FP16: 16位浮点，原始精度
   - INT8: 8位整数，最常用
   - INT4: 4位整数，高压缩
   - INT2/INT1: 极端压缩，研究阶段

4. **关键挑战**
   - 精度损失控制
   - 校准数据集选择
   - 硬件兼容性
   - 量化感知训练成本

## 待继续搜索方向

- 量化推理框架对比
- 量化在边缘设备应用
- 最新FP8量化进展
- 企业级量化方案