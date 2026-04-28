"""
数学公式处理器

功能:
1. 公式检测（行内公式、显示公式）
2. LaTeX转换
3. 符号映射表
4. 公式验证

设计原则:
- 支持多种公式格式
- 自动识别公式类型
- 提供验证和错误提示
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FormulaType(str, Enum):
    """公式类型"""
    INLINE = "inline"       # 行内公式 $...$
    DISPLAY = "display"     # 显示公式 $$...$$
    TEXT = "text"           # 文本形式的公式
    IMAGE = "image"         # 图片公式（需要OCR）


@dataclass
class Formula:
    """公式对象"""
    type: FormulaType
    raw_text: str
    latex: str = ""
    is_valid: bool = False
    error_message: str = ""
    position: int = 0  # 在文本中的位置


@dataclass
class FormulaProcessingResult:
    """公式处理结果"""
    formulas: List[Formula]
    total_count: int
    valid_count: int
    invalid_count: int


class SymbolMapper:
    """符号映射器

    Unicode数学符号 -> LaTeX命令
    """

    # 希腊字母
    GREEK_SYMBOLS = {
        'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
        'ε': r'\epsilon', 'ζ': r'\zeta', 'η': r'\eta', 'θ': r'\theta',
        'ι': r'\iota', 'κ': r'\kappa', 'λ': r'\lambda', 'μ': r'\mu',
        'ν': r'\nu', 'ξ': r'\xi', 'ο': r'\omicron', 'π': r'\pi',
        'ρ': r'\rho', 'σ': r'\sigma', 'τ': r'\tau', 'υ': r'\upsilon',
        'φ': r'\phi', 'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega',
        'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda',
        'Ξ': r'\Xi', 'Π': r'\Pi', 'Σ': r'\Sigma', 'Φ': r'\Phi',
        'Ψ': r'\Psi', 'Ω': r'\Omega',
    }

    # 运算符
    OPERATORS = {
        '≤': r'\leq', '≥': r'\geq', '≠': r'\neq', '≈': r'\approx',
        '≡': r'\equiv', '∝': r'\propto', '±': r'\pm', '×': r'\times',
        '÷': r'\div', '·': r'\cdot', '∩': r'\cap', '∪': r'\cup',
        '∈': r'\in', '∉': r'\notin', '⊂': r'\subset', '⊃': r'\supset',
        '∅': r'\emptyset', '∞': r'\infty', '∂': r'\partial',
        '∇': r'\nabla', '∑': r'\sum', '∏': r'\prod', '∫': r'\int',
    }

    # 关系符
    RELATIONS = {
        '→': r'\rightarrow', '←': r'\leftarrow', '↔': r'\leftrightarrow',
        '⇒': r'\Rightarrow', '⇐': r'\Leftarrow', '⇔': r'\Leftrightarrow',
        '⊕': r'\oplus', '⊗': r'\otimes', '⊖': r'\ominus',
    }

    # 箭头
    ARROWS = {
        '→': r'\rightarrow', '←': r'\leftarrow', '↑': r'\uparrow',
        '↓': r'\downarrow', '↔': r'\leftrightarrow', '↕': r'\updownarrow',
    }

    ALL_SYMBOLS: Dict[str, str]

    def __init__(self):
        self.ALL_SYMBOLS = {}
        self.ALL_SYMBOLS.update(self.GREEK_SYMBOLS)
        self.ALL_SYMBOLS.update(self.OPERATORS)
        self.ALL_SYMBOLS.update(self.RELATIONS)
        self.ALL_SYMBOLS.update(self.ARROWS)

    def map(self, symbol: str) -> Optional[str]:
        """映射单个符号"""
        return self.ALL_SYMBOLS.get(symbol)

    def has_symbol(self, text: str) -> bool:
        """检查文本是否包含需要映射的符号"""
        return any(sym in self.ALL_SYMBOLS for sym in text)


class LaTeXConverter:
    """LaTeX转换器"""

    def __init__(self):
        self.symbol_mapper = SymbolMapper()
        self._init_patterns()

    def _init_patterns(self):
        """初始化正则模式"""
        # 上标模式: x^2, x^{n+1}
        self.sup_pattern = re.compile(r'(\w+)\^(\d+|\w+)')

        # 下标模式: x_1, x_{i}
        self.sub_pattern = re.compile(r'(\w+)_(\d+|\w+)')

        # 分数模式: a/b -> \frac{a}{b}
        self.frac_pattern = re.compile(r'\(([^)]+)\)/\(([^)]+)\)')

        # 根号模式
        self.sqrt_pattern = re.compile(r'√(\d+)', re.UNICODE)

    def convert(self, formula_text: str) -> str:
        """将文本公式转为LaTeX

        Args:
            formula_text: 原始公式文本

        Returns:
            str: LaTeX格式
        """
        latex = formula_text

        # 1. 映射Unicode符号
        latex = self._map_symbols(latex)

        # 2. 处理上下标
        latex = self._process_supsub(latex)

        # 3. 处理分数
        latex = self._process_fractions(latex)

        # 4. 处理根号
        latex = self._process_radicals(latex)

        # 5. 处理矩阵
        latex = self._process_matrices(latex)

        return latex

    def _map_symbols(self, text: str) -> str:
        """映射所有Unicode符号"""
        result = text
        for unicode_sym, latex_sym in self.symbol_mapper.ALL_SYMBOLS.items():
            result = result.replace(unicode_sym, latex_sym)
        return result

    def _process_supsub(self, text: str) -> str:
        """处理上下标"""
        # 处理 x^{n} 格式
        text = re.sub(r'(\w+)\^{(\w+)}', r'\1^{\2}', text)

        # 处理 x^n 格式 (单个字符)
        text = re.sub(r'(\w+)\^(\w)', r'\1^{\2}', text)

        # 处理 x_{n} 格式
        text = re.sub(r'(\w)_{(\w+)}', r'\1_{\2}', text)

        # 处理 x_n 格式 (单个字符)
        text = re.sub(r'(\w)_(\w)', r'\1_{\2}', text)

        return text

    def _process_fractions(self, text: str) -> str:
        """处理分数

        将 a/b 转换为 \frac{a}{b}，但需要判断是否真的是分数
        """
        # 简单处理：分子分母都是简单表达式的情况
        # 避免处理如 2024/01 这样的日期

        lines = text.split('\n')
        result_lines = []

        for line in lines:
            # 检测分数模式：数字/数字 或 字母/字母
            fraction_pattern = r'(?<![/])(\w+)/(\w+)(?![/])'
            matches = list(re.finditer(fraction_pattern, line))

            for match in reversed(matches):
                numerator = match.group(1)
                denominator = match.group(2)

                # 判断是否应该转换为分数
                # 排除明显的日期或版本号
                if self._should_convert_fraction(numerator, denominator):
                    original = match.group(0)
                    replacement = rf'\frac{{{numerator}}}{{{denominator}}}'
                    line = line[:match.start()] + replacement + line[match.end():]

            result_lines.append(line)

        return '\n'.join(result_lines)

    def _should_convert_fraction(self, numerator: str, denominator: str) -> bool:
        """判断是否应该转换为分数"""
        # 排除日期格式
        if numerator.isdigit() and len(numerator) <= 2 and denominator.isdigit() and len(denominator) <= 2:
            # 可能是日期如 01/2024
            if len(numerator) == 2 and len(denominator) == 4:
                return False

        # 排除版本号格式
        if numerator.startswith('v') or denominator.startswith('v'):
            return False

        # 排除行号
        if numerator.isdigit() and denominator.isdigit():
            return False

        return True

    def _process_radicals(self, text: str) -> str:
        """处理根号"""
        # 平方根 √x -> \sqrt{x}
        text = re.sub(r'√(\w+)', r'\\sqrt{\1}', text)

        # n次根 √[n]{x} -> \sqrt[n]{x}
        text = re.sub(r'√\[(\d+)\](\w+)', r'\\sqrt[\1]{\2}', text)

        return text

    def _process_matrices(self, text: str) -> str:
        """处理矩阵

        简单检测方括号包围的数组格式
        """
        # 检测 [a, b; c, d] 格式
        matrix_pattern = r'\[([^\]]+)\]'
        matches = re.finditer(matrix_pattern, text)

        for match in matches:
            content = match.group(1)
            # 简单处理：假设是2x2矩阵
            if ',' in content and ';' in content:
                # 转换为 LaTeX 矩阵格式
                rows = content.split(';')
                latex_rows = []
                for row in rows:
                    cells = [c.strip() for c in row.split(',')]
                    latex_cells = ' & '.join(cells)
                    latex_rows.append(latex_cells)

                matrix_latex = '\\begin{bmatrix}\n' + ' \\\\\n'.join(latex_rows) + '\\end{bmatrix}'
                text = text[:match.start()] + matrix_latex + text[match.end():]

        return text

    def validate(self, latex: str) -> Tuple[bool, Optional[str]]:
        """验证LaTeX语法

        Args:
            latex: LaTeX字符串

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        errors = []

        # 检查括号匹配
        if not self._check_bracket_balance(latex):
            errors.append("括号不匹配")

        # 检查花括号匹配
        if latex.count('{') != latex.count('}'):
            errors.append("花括号不匹配")

        # 检查方括号匹配
        if latex.count('[') != latex.count(']'):
            errors.append("方括号不匹配")

        # 检查环境是否正确
        env_pattern = r'\\begin\{(\w+)\}'
        envs = re.findall(env_pattern, latex)
        for env in envs:
            end_env = rf'\\end{{{env}}}'
            if end_env not in latex:
                errors.append(f"环境 {env} 未正确关闭")

        if errors:
            return False, "; ".join(errors)

        return True, None

    def _check_bracket_balance(self, text: str) -> bool:
        """检查括号平衡"""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}

        for char in text:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs.get(stack[-1]) != char:
                    return False
                stack.pop()

        return len(stack) == 0


class FormulaDetector:
    """公式检测器"""

    def __init__(self):
        self._init_patterns()

    def _init_patterns(self):
        """初始化检测模式"""
        # 行内公式: $...$
        self.inline_pattern = re.compile(r'\$([^\$]+)\$')

        # 显示公式: $$...$$
        self.display_pattern = re.compile(r'\$\$([^\$]+)\$\$')

        # LaTeX显示公式: \[...\]
        self.latex_display_pattern = re.compile(r'\\\[([^\]]+)\\\]')

        # LaTeX行内公式: \(...\)
        self.latex_inline_pattern = re.compile(r'\\\((.+?)\\\)')

        # 常见的公式指示词（文本形式的公式）
        self.formula_indicators = [
            'where', 'given by', 'equals', 'is defined as',
            '如下', '其中', '定义为', '等于'
        ]

    def detect(self, text: str) -> List[Formula]:
        """检测文本中的公式

        Args:
            text: 输入文本

        Returns:
            List[Formula]: 检测到的公式列表
        """
        formulas = []
        position = 0

        # 检测 $...$ 格式
        for match in self.inline_pattern.finditer(text):
            formulas.append(Formula(
                type=FormulaType.INLINE,
                raw_text=match.group(0),
                latex=match.group(1),
                is_valid=True,
                position=match.start()
            ))

        # 检测 $$...$$ 格式
        for match in self.display_pattern.finditer(text):
            formulas.append(Formula(
                type=FormulaType.DISPLAY,
                raw_text=match.group(0),
                latex=match.group(1),
                is_valid=True,
                position=match.start()
            ))

        # 检测 \[...\] 格式
        for match in self.latex_display_pattern.finditer(text):
            formulas.append(Formula(
                type=FormulaType.DISPLAY,
                raw_text=match.group(0),
                latex=match.group(1),
                is_valid=True,
                position=match.start()
            ))

        # 检测 \(...\) 格式
        for match in self.latex_inline_pattern.finditer(text):
            formulas.append(Formula(
                type=FormulaType.INLINE,
                raw_text=match.group(0),
                latex=match.group(1),
                is_valid=True,
                position=match.start()
            ))

        # 按位置排序
        formulas.sort(key=lambda f: f.position)

        return formulas

    def is_formula_indicator(self, line: str) -> bool:
        """检查是否是公式指示词"""
        line_lower = line.lower().strip()
        return any(indicator in line_lower for indicator in self.formula_indicators)


class FormulaProcessor:
    """公式处理器

    整合检测、转换、验证功能
    """

    def __init__(self):
        self.detector = FormulaDetector()
        self.latex_converter = LaTeXConverter()

    def process(self, text: str) -> FormulaProcessingResult:
        """完整处理文本中的公式

        Args:
            text: 输入文本

        Returns:
            FormulaProcessingResult: 处理结果
        """
        # 1. 检测公式
        formulas = self.detector.detect(text)

        # 2. 转换并验证每个公式
        for formula in formulas:
            if formula.type in (FormulaType.INLINE, FormulaType.DISPLAY):
                # 已经提取了LaTeX，进行验证
                is_valid, error = self.latex_converter.validate(formula.latex)
                formula.is_valid = is_valid
                formula.error_message = error or ""

        valid_count = sum(1 for f in formulas if f.is_valid)
        invalid_count = len(formulas) - valid_count

        return FormulaProcessingResult(
            formulas=formulas,
            total_count=len(formulas),
            valid_count=valid_count,
            invalid_count=invalid_count
        )

    def convert_text_formula(self, text: str) -> str:
        """将文本形式的公式转换为LaTeX

        Args:
            text: 文本公式

        Returns:
            str: LaTeX格式
        """
        return self.latex_converter.convert(text)

    def extract_formulas_from_line(self, line: str) -> List[str]:
        """从一行文本中提取可能的公式

        Args:
            line: 输入行

        Returns:
            List[str]: 可能的公式列表
        """
        formulas = []

        # 检测常见的等式模式
        # 如 "where x = y + z"
        if '=' in line:
            # 提取等式部分
            parts = line.split('=')
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()
                # 检查是否包含数字或变量
                if any(c.isdigit() for c in right) or any(c.isalpha() for c in right):
                    equation = f"{left}={right}"
                    if self.detector.is_formula_indicator(line):
                        formulas.append(equation)

        return formulas


# 便捷函数
def process_formulas(text: str) -> FormulaProcessingResult:
    """处理文本中的公式"""
    processor = FormulaProcessor()
    return processor.process(text)


def convert_to_latex(formula_text: str) -> str:
    """将文本公式转换为LaTeX"""
    converter = LaTeXConverter()
    return converter.convert(formula_text)


def validate_latex(latex: str) -> Tuple[bool, Optional[str]]:
    """验证LaTeX语法"""
    converter = LaTeXConverter()
    return converter.validate(latex)