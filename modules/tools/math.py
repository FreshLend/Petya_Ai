import math
import cmath
import re
import discord
from discord import app_commands
from decimal import Decimal, getcontext
from sympy import *
from typing import Optional

def convert_integral_expression(expr: str) -> str:
    import re
    pattern = r'∫\(([^)]+)\)\s+d([a-zA-Z])'
    match = re.search(pattern, expr)
    if match:
        inner = match.group(1)
        var = match.group(2)
        if ' to ' in inner:
            parts = inner.split(' to ')
            if len(parts) == 2:
                func = parts[0].strip()
                upper = parts[1].strip()
                new_expr = f"integrate({func}, ({var}, 0, {upper}))"
                return expr[:match.start()] + new_expr + expr[match.end():]
    expr = re.sub(r'∫\s*([a-zA-Z0-9\(\)\+\-\*\/\^]+)\s+d([a-zA-Z])', r'integrate(\1, \2)', expr)
    return expr

def convert_limit_expression(expr: str) -> str:
    import re
    expr = expr.replace('lim', 'limit')
    expr = expr.replace('→', ', ')
    expr = expr.replace('->', ', ')
    pattern = r'limit\s*\{\s*([a-zA-Z])\s*->\s*([^}]+)\s*\}\s*(.+)'
    match = re.search(pattern, expr)
    if match:
        var = match.group(1)
        point = match.group(2).strip()
        func = match.group(3).strip()
        return f"limit({func}, {var}, {point})"
    pattern2 = r'limit\s*\(\s*([^,]+)\s*,\s*([a-zA-Z]+)\s*,\s*([^)]+)\s*\)'
    match2 = re.search(pattern2, expr)
    if match2:
        return expr
    pattern3 = r'limit\s*\(\s*([^,]+)\s*,\s*([a-zA-Z]+)\s*->\s*([^)]+)\s*\)'
    match3 = re.search(pattern3, expr)
    if match3:
        func = match3.group(1)
        var = match3.group(2)
        point = match3.group(3)
        return f"limit({func}, {var}, {point})"
    return expr

def convert_greek_symbols(expr: str) -> str:
    greek_symbols = {
        'Γ': 'gamma', 'γ': 'gamma', 'Δ': 'Delta', 'δ': 'delta', 'ε': 'epsilon',
        'ζ': 'zeta', 'η': 'eta', 'θ': 'theta', 'Θ': 'Theta', 'ι': 'iota',
        'κ': 'kappa', 'λ': 'lambda', 'Λ': 'Lambda', 'μ': 'mu', 'ν': 'nu',
        'ξ': 'xi', 'Ξ': 'Xi', 'π': 'pi', 'Π': 'Pi', 'ρ': 'rho', 'σ': 'sigma',
        'Σ': 'Sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi', 'Φ': 'Phi',
        'χ': 'chi', 'ψ': 'psi', 'Ψ': 'Psi', 'ω': 'omega', 'Ω': 'Omega',
        '∞': 'oo', '∂': 'diff', '∇': 'nabla', 'ℏ': 'hbar',
        'α': 'alpha', 'β': 'beta'
    }
    for symbol, replacement in greek_symbols.items():
        expr = expr.replace(symbol, replacement)
    return expr

def evaluate_expression(expr: str, var: str = 'x'):
    try:
        x = symbols(var)
        expr_clean = expr.replace('log', 'ln').replace('ln', 'log')
        try:
            expr_sym = sympify(expr_clean, locals={var: x, 'gamma': gamma})
            if expr_sym.free_symbols:
                try:
                    f = lambdify(x, expr_sym, modules='math')
                    return f"f({var}) = {latex(expr_sym)}"
                except:
                    return latex(expr_sym)
            else:
                result_value = float(expr_sym)
                return format_number(result_value)
        except Exception:
            safe_dict = create_safe_dict()
            result = eval(expr_clean, {"__builtins__": {}}, safe_dict)
            if isinstance(result, (int, float, complex)):
                return format_number(result)
            return str(result)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить выражение: {str(e)}")

def create_safe_dict():
    return {
        'abs': abs, 'round': round, 'min': min, 'max': max, 'pow': pow,
        'sum': sum, 'int': int, 'float': float, 'complex': complex,
        'bool': bool, 'len': len, 'str': str, 'pi': math.pi, 'e': math.e,
        'tau': math.tau, 'inf': float('inf'), 'nan': float('nan'),
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'atan2': math.atan2, 'sinh': math.sinh, 'cosh': math.cosh,
        'tanh': math.tanh, 'asinh': math.asinh, 'acosh': math.acosh,
        'atanh': math.atanh, 'log': math.log, 'log10': math.log10,
        'log2': math.log2, 'log1p': math.log1p, 'exp': math.exp,
        'expm1': math.expm1, 'sqrt': math.sqrt,
        'cbrt': lambda x: x ** (1/3) if x >= 0 else -((-x) ** (1/3)),
        'factorial': math.factorial, 'gamma': math.gamma, 'lgamma': math.lgamma,
        'erf': math.erf, 'erfc': math.erfc, 'gcd': math.gcd,
        'lcm': lambda a, b: abs(a*b) // math.gcd(a,b) if a and b else 0,
        'degrees': math.degrees, 'radians': math.radians, 'ceil': math.ceil,
        'floor': math.floor, 'trunc': math.trunc, 'fmod': math.fmod,
        'fabs': math.fabs, 'copysign': math.copysign, 'fsum': math.fsum,
        'isclose': math.isclose, 'isfinite': math.isfinite, 'isinf': math.isinf,
        'isnan': math.isnan, 'mean': lambda *args: sum(args)/len(args) if args else 0,
        'median': lambda *args: sorted(args)[len(args)//2] if args else 0,
        'i': 1j, 'j': 1j,
        'integrate': lambda func, var, a, b: integrate_expression_numeric(str(func), str(var), float(a), float(b)),
        'limit': lambda func, var, point: calculate_limit_numeric(str(func), str(var), float(point)),
        'oo': float('inf'), 'gamma': gamma,
    }

def simplify_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        simplified = simplify(expr_sym)
        return latex(simplified)
    except Exception as e:
        raise ValueError(f"Не удалось упростить выражение: {str(e)}")

def solve_equation(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        solutions = solve(expr_sym, var_symbol)
        return [latex(sol) for sol in solutions]
    except Exception as e:
        raise ValueError(f"Не удалось решить уравнение: {str(e)}")

def expand_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        expanded = expand(expr_sym)
        return latex(expanded)
    except Exception as e:
        raise ValueError(f"Не удалось разложить выражение: {str(e)}")

def factor_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        factored = factor(expr_sym)
        return latex(factored)
    except Exception as e:
        raise ValueError(f"Не удалось факторизовать выражение: {str(e)}")

def differentiate_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        derivative = diff(expr_sym, var_symbol)
        return latex(derivative)
    except Exception as e:
        raise ValueError(f"Не удалось найти производную: {str(e)}")

def integrate_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        integral = integrate(expr_sym, var_symbol)
        return latex(integral)
    except Exception as e:
        raise ValueError(f"Не удалось найти интеграл: {str(e)}")

def calculate_limit(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        lim = limit(expr_sym, var_symbol, 0)
        return latex(lim)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить предел: {str(e)}")

def series_expansion(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        series_exp = series(expr_sym, var_symbol, 0, 5)
        return latex(series_exp.removeO())
    except Exception as e:
        raise ValueError(f"Не удалось разложить в ряд: {str(e)}")

def evaluate_complex(expr: str):
    try:
        expr = expr.replace('i', 'j').replace('I', 'j')
        safe_dict = {'j': 1j, 'pi': math.pi, 'e': math.e, 'gamma': gamma}
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        if not isinstance(result, complex):
            result = complex(result)
        real = result.real
        imag = result.imag
        if abs(imag) < 1e-12:
            return f"{format_number(real)}"
        elif abs(real) < 1e-12:
            return f"{format_number(imag)}i"
        else:
            sign = '+' if imag >= 0 else '-'
            return f"{format_number(real)} {sign} {format_number(abs(imag))}i"
    except Exception as e:
        raise ValueError(f"Не удалось вычислить комплексное выражение: {str(e)}")

def integrate_expression_numeric(expr: str, var: str, a: float, b: float):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        integral = integrate(expr_sym, (var_symbol, a, b))
        if integral.is_number:
            return float(integral)
        return latex(integral)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить интеграл: {str(e)}")

def calculate_limit_numeric(expr: str, var: str, point: float):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        lim = limit(expr_sym, var_symbol, point)
        if lim.is_number:
            return float(lim)
        return latex(lim)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить предел: {str(e)}")

def format_number(num):
    if isinstance(num, complex):
        return format_complex(num)
    if isinstance(num, (int, Decimal)):
        return str(num)
    if abs(num) > 1e12 or (abs(num) < 1e-6 and abs(num) > 0):
        return f"{num:.10e}".replace('e+', 'e').replace('e-', 'e-').replace('e0', '')
    if hasattr(num, 'is_integer') and num.is_integer():
        return str(int(num))
    formatted = f"{num:.15f}".rstrip('0').rstrip('.')
    if len(formatted) > 15:
        return f"{num:.10g}"
    return formatted

def format_complex(c):
    real = c.real
    imag = c.imag
    if abs(imag) < 1e-12:
        return format_number(real)
    elif abs(real) < 1e-12:
        return f"{format_number(imag)}i"
    else:
        sign = '+' if imag >= 0 else '-'
        return f"{format_number(real)} {sign} {format_number(abs(imag))}i"

def create_calculation_embed(expr, result, steps, precision):
    embed = discord.Embed(
        title="🧮 Математический калькулятор",
        description=f"**Выражение:**\n```\n{expr}\n```",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📊 Результат",
        value=f"```\n{result}\n```",
        inline=False
    )
    if steps:
        steps_text = generate_calculation_steps(expr)
        if steps_text:
            embed.add_field(
                name="🔍 Шаги решения",
                value=steps_text,
                inline=False
            )
    if precision:
        embed.set_footer(text=f"Точность: {precision} знаков")
    return embed

def create_simplify_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Упрощение выражения",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📝 Исходное выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="✅ Упрощенное выражение",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_solve_embed(expr, solutions, var, steps):
    embed = discord.Embed(
        title="🧮 Решение уравнения",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="📝 Уравнение",
        value=f"```\n{expr} = 0\n```",
        inline=False
    )
    if solutions:
        solutions_text = "\n".join([f"**{var} =** `{sol}`" for sol in solutions])
        embed.add_field(
            name=f"🎯 Решения ({len(solutions)})",
            value=solutions_text,
            inline=False
        )
    else:
        embed.add_field(
            name="❌ Решений нет",
            value="Уравнение не имеет действительных решений",
            inline=False
        )
    return embed

def create_expand_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Разложение выражения",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="📝 Исходное выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🔍 Разложенное выражение",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_factor_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Факторизация выражения",
        color=discord.Color.dark_green()
    )
    embed.add_field(
        name="📝 Исходное выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🎯 Факторизованное выражение",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_differentiate_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Дифференцирование",
        color=discord.Color.dark_blue()
    )
    embed.add_field(
        name="📝 Функция",
        value=f"```\nf({var}) = {expr}\n```",
        inline=False
    )
    embed.add_field(
        name="📈 Производная",
        value=f"```\nf'({var}) = {result}\n```",
        inline=False
    )
    return embed

def create_integrate_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Интегрирование",
        color=discord.Color.dark_purple()
    )
    embed.add_field(
        name="📝 Функция",
        value=f"```\n∫ {expr} d{var}\n```",
        inline=False
    )
    embed.add_field(
        name="📊 Интеграл",
        value=f"```\n{result} + C\n```",
        inline=False
    )
    return embed

def create_limit_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Вычисление предела",
        color=discord.Color.dark_orange()
    )
    embed.add_field(
        name="📝 Выражение",
        value=f"```\nlim({var}→0) {expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🎯 Предел",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_series_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Разложение в ряд Тейлора",
        color=discord.Color.dark_red()
    )
    embed.add_field(
        name="📝 Функция",
        value=f"```\nf({var}) = {expr}\n```",
        inline=False
    )
    embed.add_field(
        name="📈 Ряд Тейлора (до 5-го члена)",
        value=f"```\n{result} + O({var}⁶)\n```",
        inline=False
    )
    return embed

def create_complex_embed(expr, result, steps):
    embed = discord.Embed(
        title="🧮 Комплексные числа",
        color=discord.Color.teal()
    )
    embed.add_field(
        name="📝 Выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🎯 Результат",
        value=f"```\n{result}\n```",
        inline=False
    )
    try:
        expr_fixed = expr.replace('i', 'j').replace('I', 'j')
        safe_dict = {'j': 1j, 'pi': math.pi, 'e': math.e, 'gamma': gamma}
        complex_num = eval(expr_fixed, {"__builtins__": {}}, safe_dict)
        if not isinstance(complex_num, complex):
            complex_num = complex(complex_num)
        magnitude = abs(complex_num)
        phase = math.degrees(cmath.phase(complex_num))
        embed.add_field(
            name="📊 Комплексная форма",
            value=(
                f"**Модуль (r):** `{format_number(magnitude)}`\n"
                f"**Аргумент (φ):** `{format_number(phase)}°`\n"
                f"**Тригонометрическая форма:** `{format_number(magnitude)}·e^(i·{format_number(math.radians(phase))})`"
            ),
            inline=False
        )
    except:
        pass
    return embed

def generate_calculation_steps(expr):
    steps = []
    expr_clean = expr.replace(" ", "")
    steps.append(f"**1. Исходное выражение:** `{expr}`")
    if '(' in expr_clean and ')' in expr_clean:
        steps.append("**2. Вычисление выражений в скобках**")
    if '**' in expr_clean or '^' in expr_clean:
        steps.append("**3. Возведение в степень**")
    if '*' in expr_clean or '/' in expr_clean:
        steps.append("**4. Умножение и деление**")
    if '+' in expr_clean or '-' in expr_clean:
        steps.append("**5. Сложение и вычитание**")
    return "\n".join(steps) if steps else ""

@bot.tree.command(name="calc", description="Выполнить математические вычисления")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    expression="Математическое выражение для вычисления",
    precision="Точность вычислений (количество знаков после запятой)"
)
async def calc(interaction: discord.Interaction, expression: str, precision: int = 6):
    await interaction.response.defer()
    class SmartCalculator:
        def __init__(self):
            self.constants = {
                'pi': math.pi, 'π': math.pi, 'e': math.e, 'tau': math.tau,
                'τ': math.tau, 'inf': float('inf'), '∞': float('inf'),
                'phi': 1.618033988749895, 'φ': 1.618033988749895,
            }
            self.functions = {
                'sqrt': lambda x: math.sqrt(x), '√': lambda x: math.sqrt(x),
                'sin': lambda x: math.sin(x), 'cos': lambda x: math.cos(x),
                'tan': lambda x: math.tan(x), 'tg': lambda x: math.tan(x),
                'ctg': lambda x: 1 / math.tan(x) if math.tan(x) != 0 else float('inf'),
                'asin': lambda x: math.asin(x), 'acos': lambda x: math.acos(x),
                'atan': lambda x: math.atan(x), 'arcsin': lambda x: math.asin(x),
                'arccos': lambda x: math.acos(x), 'arctan': lambda x: math.atan(x),
                'ln': lambda x: math.log(x), 'log': lambda x: math.log10(x),
                'log2': lambda x: math.log2(x), 'exp': lambda x: math.exp(x),
                'abs': lambda x: abs(x), 'floor': lambda x: math.floor(x),
                'ceil': lambda x: math.ceil(x), 'round': lambda x: round(x),
                'factorial': lambda x: math.factorial(int(x)) if x >= 0 and x == int(x) else float('nan'),
                '!': lambda x: math.factorial(int(x)) if x >= 0 and x == int(x) else float('nan'),
                'rad': lambda x: math.radians(x), 'deg': lambda x: math.degrees(x),
                'sinh': lambda x: math.sinh(x), 'cosh': lambda x: math.cosh(x),
                'tanh': lambda x: math.tanh(x),
            }
            self.operators = {
                '+': (1, lambda a, b: a + b), '-': (1, lambda a, b: a - b),
                '*': (2, lambda a, b: a * b), '×': (2, lambda a, b: a * b),
                '/': (2, lambda a, b: a / b if b != 0 else float('inf')),
                '÷': (2, lambda a, b: a / b if b != 0 else float('inf')),
                '//': (2, lambda a, b: a // b if b != 0 else float('inf')),
                '%': (2, lambda a, b: a % b if b != 0 else float('inf')),
                '^': (3, lambda a, b: a ** b), '**': (3, lambda a, b: a ** b),
            }
        def preprocess_expression(self, expr: str) -> str:
            expr = expr.lower().replace(' ', '')
            expr = expr.replace('pi', 'π').replace('tau', 'τ').replace('phi', 'φ')
            expr = expr.replace('×', '*').replace('÷', '/').replace('√', 'sqrt')
            expr = re.sub(r'(\d)(\()', r'\1*\2', expr)
            expr = re.sub(r'(\d)([a-zφπτ√])', r'\1*\2', expr)
            expr = re.sub(r'\)\(', ')*(', expr)
            expr = re.sub(r'([πτφ])(\d)', r'\1*\2', expr)
            expr = re.sub(r'([πτφ])(\()', r'\1*\2', expr)
            expr = re.sub(r'\(-', '(0-', expr)
            expr = re.sub(r',-', ',0-', expr)
            expr = re.sub(r'(\d)e([+-]?\d+)', r'\1e\2', expr)
            if expr.startswith('-'):
                expr = '0' + expr
            return expr
        def tokenize(self, expr: str) -> list:
            tokens = []
            i = 0
            while i < len(expr):
                char = expr[i]
                if char.isspace():
                    i += 1
                    continue
                if char.isdigit() or char == '.':
                    num = ''
                    while i < len(expr) and (expr[i].isdigit() or expr[i] == '.' or expr[i] == 'e' or expr[i] == 'E'):
                        num += expr[i]
                        i += 1
                        if (expr[i-1] == 'e' or expr[i-1] == 'E') and i < len(expr) and expr[i] in '+-':
                            num += expr[i]
                            i += 1
                    tokens.append(('number', float(num)))
                    continue
                if char.isalpha() or char in 'πτφ√':
                    name = ''
                    while i < len(expr) and (expr[i].isalpha() or expr[i] in 'πτφ√'):
                        name += expr[i]
                        i += 1
                    if name in self.constants:
                        tokens.append(('number', self.constants[name]))
                    elif name in self.functions:
                        tokens.append(('function', name))
                    else:
                        raise ValueError(f"Неизвестная функция или константа: {name}")
                    continue
                if char in '+-*/^%':
                    if i + 1 < len(expr) and expr[i:i+2] in ['**', '//']:
                        tokens.append(('operator', expr[i:i+2]))
                        i += 2
                    else:
                        tokens.append(('operator', char))
                        i += 1
                    continue
                if char in '(),':
                    tokens.append(('paren', char))
                    i += 1
                    continue
                raise ValueError(f"Неизвестный символ: {char}")
            return tokens
        def shunting_yard(self, tokens: list) -> list:
            output = []
            stack = []
            for token_type, token_value in tokens:
                if token_type == 'number':
                    output.append(token_value)
                elif token_type == 'function':
                    stack.append(('function', token_value))
                elif token_type == 'operator':
                    while (stack and stack[-1][0] == 'operator' and
                           self.operators[stack[-1][1]][0] >= self.operators[token_value][0]):
                        output.append(stack.pop()[1])
                    stack.append(('operator', token_value))
                elif token_type == 'paren' and token_value == '(':
                    stack.append(('paren', '('))
                elif token_type == 'paren' and token_value == ')':
                    while stack and stack[-1] != ('paren', '('):
                        output.append(stack.pop()[1])
                    if not stack:
                        raise ValueError("Несбалансированные скобки")
                    stack.pop()
                    if stack and stack[-1][0] == 'function':
                        output.append(stack.pop()[1])
            while stack:
                if stack[-1][0] == 'paren':
                    raise ValueError("Несбалансированные скобки")
                output.append(stack.pop()[1])
            return output
        def evaluate_rpn(self, rpn: list) -> float:
            stack = []
            for token in rpn:
                if isinstance(token, float):
                    stack.append(token)
                elif token in self.operators:
                    if len(stack) < 2:
                        raise ValueError("Недостаточно операндов для оператора")
                    b = stack.pop()
                    a = stack.pop()
                    result = self.operators[token][1](a, b)
                    stack.append(result)
                elif token in self.functions:
                    if len(stack) < 1:
                        raise ValueError("Недостаточно операндов для функции")
                    x = stack.pop()
                    result = self.functions[token](x)
                    stack.append(result)
            if len(stack) != 1:
                raise ValueError("Некорректное выражение")
            return stack[0]
        def calculate(self, expr: str) -> float:
            try:
                processed_expr = self.preprocess_expression(expr)
                tokens = self.tokenize(processed_expr)
                rpn = self.shunting_yard(tokens)
                result = self.evaluate_rpn(rpn)
                return result
            except Exception as e:
                raise ValueError(f"Ошибка вычисления: {str(e)}")
    try:
        calculator = SmartCalculator()
        result = calculator.calculate(expression)
        if math.isnan(result):
            formatted_result = "Неопределено"
        elif math.isinf(result):
            formatted_result = "∞" if result > 0 else "-∞"
        else:
            if isinstance(result, (int, float)) and result == int(result):
                formatted_result = str(int(result))
            else:
                if abs(result) < 1e-10:
                    formatted_result = "0"
                elif abs(result) < 1e-6 or abs(result) > 1e10:
                    formatted_result = f"{result:.{precision}e}"
                else:
                    formatted_result = f"{result:.{precision}f}".rstrip('0').rstrip('.')
        embed = discord.Embed(title="🧮 Калькулятор", color=discord.Color.green())
        embed.add_field(name="📝 Выражение", value=f"```{expression}```", inline=False)
        embed.add_field(name="📊 Результат", value=f"```{formatted_result}```", inline=False)
        help_text = "**Доступные функции:** sin, cos, tan, sqrt, log, ln, abs, factorial и др.\n"
        help_text += "**Константы:** π, e, τ, φ, ∞\n"
        help_text += f"**Точность:** {precision} знаков"
        embed.add_field(name="ℹ️ Справка", value=help_text, inline=False)
        await interaction.followup.send(embed=embed)
    except ZeroDivisionError:
        await interaction.followup.send("❌ **Ошибка:** Деление на ноль!", ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(f"❌ **Ошибка вычисления:** {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ **Неизвестная ошибка:** {str(e)}", ephemeral=True)

@bot.tree.command(name="math", description="Вычислить математическое выражение")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    expression="Математическое выражение для вычисления (без f(x)=)",
    mode="Режим вычисления",
    variable="Переменная (для дифференцирования/интегрирования)",
    steps="Показать шаги решения",
    precision="Точность вычислений (количество знаков)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="вычислить", value="calculate"),
    app_commands.Choice(name="упростить", value="simplify"),
    app_commands.Choice(name="решить уравнение", value="solve"),
    app_commands.Choice(name="разложить", value="expand"),
    app_commands.Choice(name="факторизовать", value="factor"),
    app_commands.Choice(name="дифференцировать", value="diff"),
    app_commands.Choice(name="проинтегрировать", value="integrate"),
    app_commands.Choice(name="предел", value="limit"),
    app_commands.Choice(name="ряд", value="series"),
    app_commands.Choice(name="комплексные числа", value="complex")
])
async def math_command(
    interaction: discord.Interaction,
    expression: str,
    mode: str = "calculate",
    variable: Optional[str] = "x",
    steps: bool = False,
    precision: Optional[int] = 10
):
    await interaction.response.defer()
    try:
        expression_clean = expression.strip()
        if not expression_clean:
            raise ValueError("Пустое выражение")
        if expression_clean.startswith("f(x) = "):
            expression_clean = expression_clean[7:].strip()
        elif expression_clean.startswith("f(x)="):
            expression_clean = expression_clean[5:].strip()
        elif expression_clean.startswith("y = "):
            expression_clean = expression_clean[4:].strip()
        elif expression_clean.startswith("y="):
            expression_clean = expression_clean[2:].strip()
        expression_clean = expression_clean.replace('^', '**')
        expression_clean = expression_clean.replace('÷', '/')
        expression_clean = expression_clean.replace('×', '*')
        expression_clean = convert_integral_expression(expression_clean)
        expression_clean = convert_limit_expression(expression_clean)
        expression_clean = convert_greek_symbols(expression_clean)
        if precision and 1 <= precision <= 100:
            getcontext().prec = precision
        if mode == "calculate":
            result = evaluate_expression(expression_clean, variable)
            embed = create_calculation_embed(expression, result, steps, precision)
        elif mode == "simplify":
            result = simplify_expression(expression_clean, variable)
            embed = create_simplify_embed(expression, result, variable, steps)
        elif mode == "solve":
            solutions = solve_equation(expression_clean, variable)
            embed = create_solve_embed(expression, solutions, variable, steps)
        elif mode == "expand":
            result = expand_expression(expression_clean, variable)
            embed = create_expand_embed(expression, result, variable, steps)
        elif mode == "factor":
            result = factor_expression(expression_clean, variable)
            embed = create_factor_embed(expression, result, variable, steps)
        elif mode == "diff":
            result = differentiate_expression(expression_clean, variable)
            embed = create_differentiate_embed(expression, result, variable, steps)
        elif mode == "integrate":
            result = integrate_expression(expression_clean, variable)
            embed = create_integrate_embed(expression, result, variable, steps)
        elif mode == "limit":
            result = calculate_limit(expression_clean, variable)
            embed = create_limit_embed(expression, result, variable, steps)
        elif mode == "series":
            result = series_expansion(expression_clean, variable)
            embed = create_series_embed(expression, result, variable, steps)
        elif mode == "complex":
            result = evaluate_complex(expression_clean)
            embed = create_complex_embed(expression, result, steps)
        else:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Неизвестный режим вычисления",
                color=discord.Color.red()
            )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка вычисления",
            description=f"**Выражение:** `{expression}`\n\n**Ошибка:** {str(e)}",
            color=discord.Color.red()
        )
        error_embed.add_field(
            name="💡 Правильный формат",
            value=(
                "Для интегралов используйте: `integrate(tan(t**3), (t, 0, x))`\n"
                "Для пределов используйте: `limit(gamma(x+h)/gamma(x)**(1/h), h, 0)`\n"
                "Или просто введите: `exp(sin(x**2)) * log(1 + cos(3*x))`"
            ),
            inline=False
        )
        await interaction.followup.send(embed=error_embed)