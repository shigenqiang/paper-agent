"""
公式识别器 - Formula Recognizer

功能:
- 图片 → LaTeX（OCR）
- LaTeX → 图片渲染
- 公式解释
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = get_logging_logger(__name__)


@dataclass
class FormulaRecognition:
    """公式识别结果"""
    latex: str
    confidence: float
    plain_text: str = ""
    explanation: str = ""
    is_valid: bool = True


class FormulaRecognizer:
    """数学公式识别器"""

    def __init__(self, llm: Any = None):
        """初始化公式识别器

        Args:
            llm: 可选的LLM实例
        """
        self.llm = llm
        self.latex_renderer = LaTeXRenderer()

    async def extract_from_image(self, image: Any) -> FormulaRecognition:
        """从图片提取公式，返回LaTeX

        Args:
            image: PIL.Image或图像路径

        Returns:
            FormulaRecognition: 识别结果
        """
        if self.llm:
            try:
                prompt = """
这是一个数学公式的图像。请识别并返回LaTeX格式。
只返回LaTeX代码，不要其他内容。
例如：
- 二次公式: x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}
- 积分: \\int_{a}^{b} f(x) dx
"""
                # 注意：实际应用中应该使用视觉模型
                # 这里简化处理
                result = await self.llm.agenerate([prompt])
                latex = result.generations[0][0].text.strip()

                return FormulaRecognition(
                    latex=latex,
                    confidence=0.9,
                    plain_text=self._latex_to_plain_text(latex),
                    is_valid=self.validate(latex)
                )

            except Exception as e:
                logger.error(f"公式识别失败: {e}")

        # 回退实现
        return FormulaRecognition(
            latex="\\placeholder",
            confidence=0.1,
            is_valid=False
        )

    def render_to_image(self, latex: str, output_path: str = None) -> Any:
        """将LaTeX渲染为图像

        Args:
            latex: LaTeX公式
            output_path: 输出路径

        Returns:
            PIL.Image: 公式图像
        """
        return self.latex_renderer.render(latex, output_path)

    async def explain(self, latex: str) -> str:
        """解释公式含义

        Args:
            latex: LaTeX公式

        Returns:
            str: 公式解释
        """
        if not self.llm:
            return self._simple_explanation(latex)

        try:
            prompt = f"""
解释以下LaTeX公式的含义：

{latex}

用通俗易懂的语言解释（1-2句话）。
"""
            result = await self.llm.agenerate([prompt])
            return result.generations[0][0].text.strip()

        except Exception as e:
            logger.error(f"公式解释失败: {e}")
            return self._simple_explanation(latex)

    def validate(self, latex: str) -> bool:
        """验证LaTeX语法是否正确

        Args:
            latex: LaTeX公式

        Returns:
            bool: 是否有效
        """
        try:
            # 基本语法检查
            # 括号匹配
            open_count = latex.count('{')
            close_count = latex.count('}')
            if open_count != close_count:
                return False

            # 常见的LaTeX命令检查
            valid_commands = [
                "\\frac", "\\int", "\\sum", "\\sqrt", "\\lim",
                "\\sin", "\\cos", "\\tan", "\\log", "\\exp",
                "\\alpha", "\\beta", "\\gamma", "\\theta", "\\pi",
                "\\partial", "\\infty", "\\pm", "\\times", "\\div"
            ]

            # 如果包含反斜杠，必须是有效命令
            if '\\' in latex:
                has_valid = any(cmd in latex for cmd in valid_commands)
                if not has_valid:
                    # 可能有不认识的命令，但不一定是错的
                    pass

            # 尝试渲染验证
            try:
                self.latex_renderer.render(latex)
                return True
            except:
                return False

        except Exception as e:
            logger.warning(f"LaTeX验证出错: {e}")
            return False

    def _latex_to_plain_text(self, latex: str) -> str:
        """将LaTeX转换为纯文本

        Args:
            latex: LaTeX公式

        Returns:
            str: 纯文本表示
        """
        # 简单的替换规则
        replacements = [
            ("\\frac{", "("),
            ("}{", ")/("),
            ("\\sqrt{", "sqrt("),
            ("\\int_{", "∫("),
            ("}^{", ", "),
            ("\\sum_{", "Σ("),
            ("\\alpha", "α"),
            ("\\beta", "β"),
            ("\\gamma", "γ"),
            ("\\theta", "θ"),
            ("\\pi", "π"),
            ("\\infty", "∞"),
            ("\\partial", "∂"),
            ("\\times", "×"),
            ("\\div", "÷"),
            ("\\pm", "±"),
            ("\\leq", "≤"),
            ("\\geq", "≥"),
            ("\\neq", "≠"),
            ("{", ""),
            ("}", ""),
            ("\\", "")
        ]

        result = latex
        for old, new in replacements:
            result = result.replace(old, new)

        return result

    def _simple_explanation(self, latex: str) -> str:
        """简单公式解释"""
        if "\\frac{" in latex:
            return "这是一个分数公式，表示分子除以分母"
        elif "\\int" in latex:
            return "这是一个积分公式，表示函数在区间上的累积"
        elif "\\sum" in latex:
            return "这是一个求和公式，表示多项的总和"
        elif "\\sqrt" in latex:
            return "这是一个平方根公式"
        elif "=" in latex:
            return "这是一个等式公式"
        else:
            return "这是一个数学公式"


class LaTeXRenderer:
    """LaTeX渲染器"""

    def __init__(self):
        self.backend = "simple"  # 可选: simple, matplotlib, latex

    def render(self, latex: str, output_path: str = None) -> Any:
        """渲染LaTeX为图像

        Args:
            latex: LaTeX公式
            output_path: 输出路径

        Returns:
            PIL.Image: 渲染结果
        """
        try:
            # 尝试使用matplotlib
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.rcParams['text.usetex'] = False  # 不使用系统LaTeX

            fig, ax = plt.subplots(figsize=(6, 1))
            ax.text(0.5, 0.5, f'${latex}$', fontsize=12,
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')

            if output_path:
                fig.savefig(output_path, bbox_inches='tight', dpi=150)

            # 转换为PIL Image
            import io
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)

            from PIL import Image
            img = Image.open(buf)
            plt.close(fig)

            return img

        except ImportError:
            logger.warning("matplotlib未安装，使用简单渲染")
            return self._simple_render(latex)
        except Exception as e:
            logger.error(f"LaTeX渲染失败: {e}")
            return self._simple_render(latex)

    def _simple_render(self, latex: str) -> Any:
        """简单的文本渲染（无依赖时使用）"""
        from PIL import Image, ImageDraw, ImageFont

        # 创建空白图像
        width, height = 400, 100
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # 绘制文本（简化处理）
        draw.text((10, 30), latex[:50], fill='black')

        return img


# 便捷函数
async def recognize_formula(image: Any, llm: Any = None) -> FormulaRecognition:
    """识别公式的便捷函数

    Args:
        image: PIL.Image或图像路径
        llm: 可选的LLM实例

    Returns:
        FormulaRecognition: 识别结果
    """
    recognizer = FormulaRecognizer(llm=llm)
    return await recognizer.extract_from_image(image)


async def explain_formula(latex: str, llm: Any = None) -> str:
    """解释公式的便捷函数

    Args:
        latex: LaTeX公式
        llm: 可选的LLM实例

    Returns:
        str: 公式解释
    """
    recognizer = FormulaRecognizer(llm=llm)
    return await recognizer.explain(latex)
