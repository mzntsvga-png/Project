from flask import Flask, render_template, request, session, redirect, url_for
from sympy import symbols, diff, sympify, sqrt, latex, pi as sympy_pi, sin, cos, tan, exp, log, E
import re
import os
import math
import time

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "deltacalc-secret-key-2025")

# ---------------- НАСТРОЙКИ ----------------
DEFAULT_SETTINGS = {
    "precision": 5,
    "scientific_notation": False,
    "show_steps": True
}

# ---------------- ТЕОРИЯ ----------------
ERROR_THEORY = [
    {
        "id": "derivatives",
        "title": "Производные в расчёте погрешностей",
        "text": "Производная функции — это основное понятие математического анализа, показывающее скорость изменения функции. В контексте расчёта погрешностей производные используются для определения, насколько чувствительна искомая величина к изменениям входных параметров.",
        "formula": r"""
        \begin{aligned}
        &\text{Производная функции } f(x):\\
        &f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}
        \end{aligned}
        """,
        "icon": "function"
    },
    {
        "id": "errors",
        "title": "Основы теории погрешностей",
        "text": "Погрешность измерения — количественная характеристика отклонения результата измерения от истинного значения. Никакое измерение не бывает абсолютно точным, поэтому важно правильно оценивать и учитывать погрешности.",
        "formula": r"""
        \begin{aligned}
        &\text{Абсолютная погрешность: } \Delta x = |x - x_0|\\
        &\text{Относительная погрешность: } \delta x = \frac{\Delta x}{|x|} \times 100\%
        \end{aligned}
        """,
        "icon": "percentage"
    },
    {
        "id": "methods",
        "title": "Методы расчёта погрешностей",
        "text": "Существуют различные подходы к расчёту погрешностей в зависимости от типа измерений, характера погрешностей и требуемой точности результатов.",
        "formula": r"""
        \begin{aligned}
        &\text{Метод границ: } F_{\text{min}} \leq F \leq F_{\text{max}}\\
        &\text{Метод квадратичного сложения: } \Delta F = \sqrt{\sum \left( \frac{\partial F}{\partial x_i} \Delta x_i \right)^2}
        \end{aligned}
        """,
        "icon": "calculator"
    },
    {
        "id": "why_this_method",
        "title": "Почему метод квадратичного сложения?",
        "text": "В DeltaCalc используется метод квадратичного сложения погрешностей (формула распространения неопределённостей), так как он является наиболее обоснованным с научной точки зрения и широко применяется в современной метрологии.",
        "formula": r"""
        \Delta F = \sqrt{\sum_{i=1}^{n} \left( \frac{\partial F}{\partial x_i} \Delta x_i \right)^2}
        """,
        "icon": "question-circle"
    },
    {
        "id": "practical",
        "title": "Практические рекомендации",
        "text": "Правильная обработка результатов измерений — важнейший этап экспериментальной работы. Соблюдение определённых правил позволяет получить достоверные и воспроизводимые результаты.",
        "formula": r"""
        \begin{aligned}
        &\text{Правило 1: } \Delta x \text{ округляется до 1-2 значащих цифр}\\
        &\text{Правило 2: } x \text{ округляется до того же разряда, что и } \Delta x
        \end{aligned}
        """,
        "icon": "lightbulb"
    }
]

# ---------------- ВСПОМОГАТЕЛЬНЫЕ ----------------
def extract_variables(formula: str):
    """Извлекает переменные из формулы, игнорируя математические функции и константы."""
    # Список математических функций и констант
    math_keywords = {'sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'pi', 'e'}
    
    # Ищем все буквенные последовательности
    pattern = r'\b[a-zA-Z][a-zA-Z0-9]*\b'
    words = re.findall(pattern, formula)
    
    # Фильтруем переменные
    variables = set()
    for word in words:
        if len(word) == 1 and word.lower() not in math_keywords:
            variables.add(word)
    
    return sorted(list(variables))

def safe_float(value):
    """Безопасное преобразование в float."""
    if not value:
        return 0.0
    
    try:
        value = str(value).replace(',', '.').strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def calculate_errors(formula, values, errors, settings):
    """Вычисляет погрешность функции нескольких переменных."""
    try:
        # Подготавливаем формулу
        formula_prepared = formula.replace('^', '**').replace('pi', 'PI_CONST')
        
        # Извлекаем переменные
        variables = extract_variables(formula)
        
        if not variables:
            raise ValueError("Формула не содержит переменных")
        
        # Создаём символьные переменные
        sym_vars = {v: symbols(v) for v in variables}
        
        # Добавляем константы
        local_dict = {
            'sin': sin,
            'cos': cos,
            'tan': tan,
            'exp': exp,
            'log': log,
            'sqrt': sqrt,
            'PI_CONST': sympy_pi,
            'E': E
        }
        local_dict.update(sym_vars)
        
        # Преобразуем в SymPy выражение
        expr = sympify(formula_prepared, locals=local_dict)
        
        # Подготовка значений
        subs_dict = {}
        for v in variables:
            val = safe_float(values.get(v))
            if val is None:
                raise ValueError(f"Не указано значение для переменной {v}")
            subs_dict[sym_vars[v]] = val
        
        # Вычисляем значение функции
        F_value = float(expr.subs(subs_dict))
        
        # Вычисляем частные производные
        derivatives = {}
        error_sum = 0
        
        for v in variables:
            dF = diff(expr, sym_vars[v])
            dF_val = float(dF.subs(subs_dict))
            
            error_v = safe_float(errors.get(v))
            if error_v < 0:
                error_v = abs(error_v)
            
            partial_error = dF_val * error_v
            
            derivatives[v] = {
                "latex": latex(dF).replace('PI_CONST', r'\pi'),
                "value": dF_val,
                "partial_error": abs(partial_error),
                "error_squared": partial_error ** 2
            }
            
            error_sum += partial_error ** 2
        
        # Вычисляем общую погрешность
        abs_error = math.sqrt(abs(error_sum))
        rel_error = (abs(abs_error / F_value) * 100) if F_value != 0 else 0
        
        # Форматируем результаты
        p = settings["precision"]
        sci = settings["scientific_notation"]
        
        def format_num(x):
            if sci or abs(x) >= 1e6 or (abs(x) < 1e-4 and x != 0):
                return f"{x:.{p}e}"
            return f"{x:.{p}f}".rstrip('0').rstrip('.')
        
        return {
            "formula": latex(expr).replace('PI_CONST', r'\pi'),
            "main_value": F_value,
            "absolute_error": abs_error,
            "relative_error": rel_error,
            "formatted": {
                "main_value": format_num(F_value),
                "absolute_error": format_num(abs_error),
                "relative_error": format_num(rel_error),
                "interval": (
                    format_num(F_value - abs_error),
                    format_num(F_value + abs_error)
                )
            },
            "derivatives": derivatives
        }
        
    except Exception as e:
        raise ValueError(f"Ошибка вычисления: {str(e)}")

# ---------------- РОУТЫ ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    """Главная страница с калькулятором."""
    session.setdefault("settings", DEFAULT_SETTINGS.copy())
    session.setdefault("theme", "light")
    
    formula = ""
    variables = []
    values = {}
    errors = {}
    result = None
    error_msg = None
    
    if request.method == "POST":
        formula = request.form.get("formula", "").strip()
        
        if formula:
            try:
                variables = extract_variables(formula)
                
                if request.form.get("action") == "calculate":
                    for v in variables:
                        val = request.form.get(f"value_{v}", "0").strip()
                        err = request.form.get(f"error_{v}", "0").strip()
                        
                        if not val:
                            raise ValueError(f"Не указано значение для переменной {v}")
                        if not err:
                            raise ValueError(f"Не указана погрешность для переменной {v}")
                        
                        values[v] = val
                        errors[v] = err
                    
                    result = calculate_errors(formula, values, errors, session["settings"])
                    
            except ValueError as ve:
                error_msg = str(ve)
            except Exception as e:
                error_msg = f"Ошибка вычислений: {str(e)}"
    
    return render_template(
        "index.html",
        formula=formula,
        variables=variables,
        values=values,
        errors=errors,
        result=result,
        error=error_msg,
        settings=session["settings"],
        theme=session.get("theme", "light")
    )

@app.route("/theory")
def theory():
    """Страница с теорией погрешностей."""
    return render_template(
        "theory.html",
        theory=ERROR_THEORY,
        theme=session.get("theme", "light")
    )

@app.route("/about")
def about():
    """Страница о проекте."""
    return render_template(
        "about.html",
        theme=session.get("theme", "light")
    )

@app.route("/toggle_theme")
def toggle_theme():
    """Переключение темы."""
    current_theme = session.get("theme", "light")
    session["theme"] = "dark" if current_theme == "light" else "light"
    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)