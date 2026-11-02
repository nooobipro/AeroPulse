"""Генерация отчётов: Excel (openpyxl), PDF (ReportLab + matplotlib) и CSV."""
import csv
import io
import os
from datetime import datetime

from matplotlib import get_data_path
from matplotlib.figure import Figure
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app import stats_service as svc
from app.domain import DAYS_OF_WEEK
from app.stats_service import Filters

AMBER, NAVY, TEAL = "#E9A400", "#17324F", "#1F8A70"
DEMO_NOTE = "Внимание: отчёт построен на демонстрационных (синтетических) данных, а не на реальной статистике рейсов."
CAVEAT = ("Показатели описывают наблюдаемые доли и средние значения. Они показывают связь с признаками рейса, "
          "но не причины задержек: погода, загрузка аэропортов и задержка предыдущего рейса в данных отсутствуют.")


# ───────── Данные отчёта ─────────
def build_context(db: Session, f: Filters, user_email: str = "") -> dict:
    airlines, airports = svc.airline_map(db), svc.airport_map(db)
    return {
        "f": f,
        "filters": f.describe(airlines, airports),
        "kpi": svc.kpi(db, f),
        "airlines": svc.by_airline(db, f),
        "hourly": svc.by_hour(db, f),
        "periods": svc.by_period(db, f),
        "airports": svc.by_airport(db, f, "share", "desc", 500, 30),
        "categories": svc.categories(db, f),
        "heatmap": svc.heatmap(db, f),
        "monthly": svc.monthly(db, f),
        "version": svc.data_version(db),
        "generated": datetime.now(),
        "user": user_email,
    }


def _pct(x, digits=1):
    return "—" if x is None else f"{x * 100:.{digits}f}".replace(".", ",") + " %"


def _int(n):
    return f"{int(n):,}".replace(",", "\u00a0")


def _num(x, digits=1):
    return "—" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _avg_label(ctx) -> str:
    return "Средняя задержка, мин (по всем рейсам)" if ctx["f"].avg_mode == "all" else \
        "Средняя задержка, мин (среди задержанных)"


# ───────── Excel ─────────
_HEAD_FILL = PatternFill("solid", fgColor="17324F")
_HEAD_FONT = Font(bold=True, color="FFFFFF")


def _table(ws, header: list[str], rows: list[list], fmts: dict[int, str], row0: int = 1) -> int:
    for j, h in enumerate(header, 1):
        c = ws.cell(row=row0, column=j, value=h)
        c.fill, c.font = _HEAD_FILL, _HEAD_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(j)].width = max(14, min(40, len(h) + 2))
    for i, row in enumerate(rows, row0 + 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(row=i, column=j, value=v)
            if (j - 1) in fmts:
                c.number_format = fmts[j - 1]
    ws.freeze_panes = ws.cell(row=row0 + 1, column=1)
    return row0 + len(rows)


def _bar_chart(ws, title: str, x_title: str, y_title: str, cats_col: int, data_col: int, last_row: int,
               anchor: str, horizontal: bool = False, line: bool = False):
    chart = LineChart() if line else BarChart()
    if not line:
        chart.type = "bar" if horizontal else "col"
    chart.title, chart.height, chart.width = title, 9, 20
    chart.x_axis.title, chart.y_axis.title = x_title, y_title
    chart.x_axis.delete = chart.y_axis.delete = False
    chart.legend = None
    chart.add_data(Reference(ws, min_col=data_col, min_row=1, max_row=last_row), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=cats_col, min_row=2, max_row=last_row))
    chart.series[0].graphicalProperties.solidFill = AMBER[1:]
    chart.series[0].graphicalProperties.line.solidFill = AMBER[1:]
    ws.add_chart(chart, anchor)


def build_xlsx(ctx: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Параметры"
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 28, 60
    ws.append(["Отчёт «Анализ задержек авиарейсов»"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append(["Сформирован", ctx["generated"].strftime("%d.%m.%Y %H:%M")])
    ws.append(["Пользователь", ctx["user"]])
    v = ctx["version"]
    if v:
        ws.append(["Период данных", f"{v.period_start} — {v.period_end}"])
        if v.is_demo:
            ws.append(["ВНИМАНИЕ", DEMO_NOTE])
    ws.append([])
    ws.append(["Применённые фильтры"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    for k, val in ctx["filters"]:
        ws.append([k, val])
    ws.append([])
    ws.append(["Примечание", CAVEAT])
    ws.cell(row=ws.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[ws.max_row].height = 60

    k = ctx["kpi"]
    ws = wb.create_sheet("Сводка")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 44, 22
    rows = [
        ("Выполненных рейсов", k["flights"], "#,##0"),
        ("Отменённых рейсов", k["cancelled"], "#,##0"),
        ("Перенаправленных рейсов", k["diverted"], "#,##0"),
        ("Задержанных рейсов", k["delayed"], "#,##0"),
        ("Доля задержанных", k["share"], "0.0%"),
        ("Доверительный интервал 95%, нижняя граница", k["ci_low"], "0.0%"),
        ("Доверительный интервал 95%, верхняя граница", k["ci_high"], "0.0%"),
        (_avg_label(ctx), k["avg_delay"], "0.0"),
        ("Максимальная задержка, мин", k["max_delay"], "#,##0"),
        ("Самый проблемный час вылета", f'{k["worst_hour"]["hour"]:02d}:00' if k["worst_hour"] else None, "@"),
        ("Доля задержанных в этот час", k["worst_hour"]["share"] if k["worst_hour"] else None, "0.0%"),
        ("Самый благополучный час вылета", f'{k["best_hour"]["hour"]:02d}:00' if k["best_hour"] else None, "@"),
        ("Доля задержанных в этот час ", k["best_hour"]["share"] if k["best_hour"] else None, "0.0%"),
    ]
    for i, (name, val, fmt) in enumerate(rows, 1):
        ws.cell(row=i, column=1, value=name).font = Font(bold=True)
        c = ws.cell(row=i, column=2, value=val)
        c.number_format = fmt
        c.alignment = Alignment(horizontal="right")

    rate_fmt = {1: "#,##0", 2: "#,##0", 3: "0.0%", 4: "0.0%", 5: "0.0%", 6: "0.0"}
    rate_head = ["Рейсов", "Задержано", "Доля задержанных", "ДИ 95%, нижняя", "ДИ 95%, верхняя", _avg_label(ctx)]
    rate = lambda r: [r["flights"], r["delayed"], r["share"], r["ci_low"], r["ci_high"], r["avg_delay"]]

    ws = wb.create_sheet("Авиакомпании")
    rows = [[r["name"], *rate(r), r["max_delay"]] for r in ctx["airlines"]]
    last = _table(ws, ["Авиакомпания", *rate_head, "Макс. задержка, мин"], rows, {**rate_fmt, 7: "#,##0"})
    if rows:
        _bar_chart(ws, "Доля задержанных рейсов по авиакомпаниям", "Авиакомпания", "Доля", 1, 4, last, "K2", horizontal=True)

    ws = wb.create_sheet("По часам")
    rows = [[h["hour"], *rate(h)] for h in ctx["hourly"]]
    last = _table(ws, ["Час вылета", *rate_head], rows, {**rate_fmt})
    if rows:
        _bar_chart(ws, "Доля задержанных рейсов по часам вылета", "Час вылета (местное время)", "Доля", 1, 4, last, "J2")

    ws = wb.create_sheet("Периоды суток")
    rows = [[f'{p["label"]} ({p["hour_from"]:02d}:00–{p["hour_to"]:02d}:59)', *rate(p)] for p in ctx["periods"]]
    _table(ws, ["Период суток", *rate_head], rows, rate_fmt)

    ws = wb.create_sheet("Аэропорты")
    rows = [[a["code"], a["name"], a["city"], *rate(a)] for a in ctx["airports"]]
    _table(ws, ["Код", "Название", "Город", *rate_head], rows, {i + 2: f for i, f in rate_fmt.items()})
    ws.cell(row=len(rows) + 3, column=1, value="Показаны аэропорты, у которых не менее 500 рейсов (до 30 с наибольшей долей задержек).")

    ws = wb.create_sheet("Категории")
    rows = [[c["label"], c["flights"], c["share"]] for c in ctx["categories"]]
    last = _table(ws, ["Категория задержки прибытия", "Рейсов", "Доля"], rows, {1: "#,##0", 2: "0.0%"})
    if rows:
        _bar_chart(ws, "Распределение рейсов по категориям задержки", "Категория", "Доля", 1, 3, last, "F2")

    ws = wb.create_sheet("Месяцы")
    rows = [[m["period"], *rate(m)] for m in ctx["monthly"]]
    last = _table(ws, ["Месяц", *rate_head], rows, rate_fmt)
    if rows:
        _bar_chart(ws, "Доля задержанных рейсов по месяцам", "Месяц", "Доля", 1, 4, last, "J2", line=True)

    ws = wb.create_sheet("Тепловая карта")
    ws.cell(row=1, column=1, value="День недели / час").font = Font(bold=True)
    for h in range(24):
        ws.cell(row=1, column=h + 2, value=h).font = Font(bold=True)
    grid = {(c["dow"], c["hour"]): c for c in ctx["heatmap"]}
    for d in range(1, 8):
        ws.cell(row=d + 1, column=1, value=DAYS_OF_WEEK[d]).font = Font(bold=True)
        for h in range(24):
            c = grid.get((d, h))
            cell = ws.cell(row=d + 1, column=h + 2, value=(c["share"] if c and c["reliable"] else None))
            cell.number_format = "0%"
    ws.conditional_formatting.add("B2:Y8", ColorScaleRule(
        start_type="min", start_color="E8F1EF", mid_type="percentile", mid_value=50, mid_color="F7D774",
        end_type="max", end_color="E4572E"))
    ws.cell(row=10, column=1, value="Ячейки с менее чем 30 рейсами не показаны (оценка ненадёжна).")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ───────── PDF ─────────
_FONTS_READY = False


def _register_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return
    base = os.path.join(get_data_path(), "fonts", "ttf")  # DejaVu Sans идёт в комплекте с matplotlib
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(base, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(base, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu", boldItalic="DejaVu-Bold")
    _FONTS_READY = True


def _png(fig: Figure, width_mm: float = 174) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170)
    buf.seek(0)
    w, h = fig.get_size_inches()
    img = Image(buf, width=width_mm * mm, height=width_mm * mm * h / w)
    return img


def _style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)


def _fig_hourly(rows: list[dict]) -> Figure:
    fig = Figure(figsize=(7.4, 3.0), constrained_layout=True)
    ax = fig.add_subplot(111)
    hours = [r["hour"] for r in rows]
    ax.bar(hours, [r["share"] * 100 for r in rows], color=AMBER, width=0.8)
    ax.set_xlabel("Час вылета (местное время)")
    ax.set_ylabel("Доля задержанных, %")
    ax.set_xticks(range(0, 24, 2))
    _style_axes(ax)
    ax2 = fig.axes[0].twinx()
    ax2.plot(hours, [r["avg_delay"] if r["avg_delay"] is not None else float("nan") for r in rows],
             color=NAVY, marker="o", ms=3, lw=1.4)
    ax2.set_ylabel("Средняя задержка, мин")
    ax2.spines["top"].set_visible(False)
    return fig


def _fig_airlines(rows: list[dict], top: int = 15) -> Figure:
    rows = rows[:top][::-1]
    fig = Figure(figsize=(7.4, 0.28 * len(rows) + 1.0), constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.barh([r["name"][:34] for r in rows], [r["share"] * 100 for r in rows], color=AMBER)
    ax.errorbar([r["share"] * 100 for r in rows], range(len(rows)),
                xerr=[[(r["share"] - r["ci_low"]) * 100 for r in rows], [(r["ci_high"] - r["share"]) * 100 for r in rows]],
                fmt="none", ecolor=NAVY, capsize=2, lw=1)
    ax.set_xlabel("Доля задержанных, % (с 95% доверительным интервалом)")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    return fig


def _fig_categories(rows: list[dict]) -> Figure:
    fig = Figure(figsize=(7.4, 2.6), constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.bar([r["label"] for r in rows], [(r["share"] or 0) * 100 for r in rows], color=[TEAL] + [AMBER] * 5)
    ax.set_ylabel("Доля рейсов, %")
    ax.tick_params(axis="x", labelsize=8)
    _style_axes(ax)
    return fig


def _fig_heatmap(cells: list[dict]) -> Figure:
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    mat = np.full((7, 24), np.nan)
    for c in cells:
        if c["reliable"]:
            mat[c["dow"] - 1, c["hour"]] = c["share"] * 100
    fig = Figure(figsize=(7.4, 2.9), constrained_layout=True)
    ax = fig.add_subplot(111)
    cmap = LinearSegmentedColormap.from_list("delay", ["#E8F1EF", "#F7D774", "#E4572E"])
    im = ax.imshow(mat, aspect="auto", cmap=cmap)
    ax.set_yticks(range(7), [DAYS_OF_WEEK[d] for d in range(1, 8)])
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Час вылета")
    fig.colorbar(im, ax=ax, label="Доля задержанных, %")
    return fig


def build_pdf(ctx: dict) -> bytes:
    _register_fonts()
    h1 = ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=17, leading=21, spaceAfter=4, textColor=colors.HexColor(NAVY))
    h2 = ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12, leading=15, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor(NAVY))
    body = ParagraphStyle("body", fontName="DejaVu", fontSize=9, leading=12)
    small = ParagraphStyle("small", fontName="DejaVu", fontSize=8, leading=10.5, textColor=colors.HexColor("#444444"))
    warn = ParagraphStyle("warn", parent=body, textColor=colors.HexColor("#9A3412"), backColor=colors.HexColor("#FEF3C7"), borderPadding=5, spaceAfter=6)

    def table(data, widths, align_right_from=1):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "DejaVu"), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F4F7")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D1DA")),
            ("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    P = lambda text, st=body: Paragraph(text, st)
    k, v = ctx["kpi"], ctx["version"]
    els = [P("Анализ задержек авиарейсов", h1),
           P(f'Отчёт сформирован {ctx["generated"].strftime("%d.%m.%Y %H:%M")}; пользователь: {ctx["user"]}', small)]
    if v and v.is_demo:
        els += [Spacer(1, 4), P(DEMO_NOTE, warn)]
    els.append(P("Параметры отчёта", h2))
    params = [[P(a, small), P(b, small)] for a, b in ctx["filters"]]
    if v:
        params.insert(0, [P("Период данных", small), P(f"{v.period_start} — {v.period_end}", small)])
    els.append(table([["Параметр", "Значение"]] + params, [55 * mm, 119 * mm], 5))

    els.append(P("Ключевые показатели", h2))
    kp = [["Показатель", "Значение"],
          ["Выполненных рейсов", _int(k["flights"])],
          ["Задержанных рейсов", _int(k["delayed"])],
          ["Доля задержанных (95% ДИ)", f'{_pct(k["share"])} ({_pct(k["ci_low"])} — {_pct(k["ci_high"])})'],
          [_avg_label(ctx), _num(k["avg_delay"])],
          ["Максимальная задержка, мин", _int(k["max_delay"])],
          ["Отменённых / перенаправленных", f'{_int(k["cancelled"])} / {_int(k["diverted"])}']]
    if k["worst_hour"]:
        kp.append(["Самый проблемный час вылета", f'{k["worst_hour"]["hour"]:02d}:00 ({_pct(k["worst_hour"]["share"])})'])
        kp.append(["Самый благополучный час вылета", f'{k["best_hour"]["hour"]:02d}:00 ({_pct(k["best_hour"]["share"])})'])
    els.append(table(kp, [95 * mm, 79 * mm]))

    if not ctx["hourly"]:
        els += [Spacer(1, 8), P("По выбранным фильтрам рейсов нет.", body)]
    else:
        els.append(P("Время вылета", h2))
        els.append(_png(_fig_hourly(ctx["hourly"])))
        pt = [["Период суток", "Рейсов", "Доля задержанных", "Средняя задержка, мин"]]
        for p in ctx["periods"]:
            pt.append([f'{p["label"]} ({p["hour_from"]:02d}–{p["hour_to"]:02d} ч)', _int(p["flights"]), _pct(p["share"]), _num(p["avg_delay"])])
        els += [Spacer(1, 4), table(pt, [64 * mm, 30 * mm, 40 * mm, 40 * mm])]
        els.append(P("Доля задержанных по дням недели и часам", h2))
        els.append(_png(_fig_heatmap(ctx["heatmap"])))

        els.append(P("Авиакомпании", h2))
        els.append(_png(_fig_airlines(ctx["airlines"])))
        at = [["Авиакомпания", "Рейсов", "Доля", "ДИ 95%", "Ср. задержка"]]
        for r in ctx["airlines"]:
            at.append([r["name"][:38], _int(r["flights"]), _pct(r["share"]), f'{_pct(r["ci_low"])}–{_pct(r["ci_high"])}', _num(r["avg_delay"])])
        els += [Spacer(1, 4), table(at, [66 * mm, 24 * mm, 20 * mm, 36 * mm, 28 * mm])]

        els.append(KeepTogether([P("Категории задержки прибытия", h2), _png(_fig_categories(ctx["categories"]))]))

        if ctx["airports"]:
            els.append(P("Аэропорты вылета с наибольшей долей задержек (не менее 500 рейсов)", h2))
            apt = [["Код", "Город", "Рейсов", "Доля", "Ср. задержка"]]
            for r in ctx["airports"][:15]:
                apt.append([r["code"], r["city"][:30], _int(r["flights"]), _pct(r["share"]), _num(r["avg_delay"])])
            els.append(table(apt, [20 * mm, 66 * mm, 28 * mm, 28 * mm, 32 * mm], 2))

    els += [Spacer(1, 10), P(CAVEAT, small)]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18 * mm, 10 * mm, "Анализ задержек авиарейсов")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Страница {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title="Анализ задержек авиарейсов",
                      author="Flight Delays Analytics").build(els, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


# ───────── CSV ─────────
DATASETS = ("airlines", "hourly", "periods", "airports", "categories", "heatmap", "monthly")
_RATE_HEAD = ["Рейсов", "Задержано", "Доля задержанных", "ДИ 95% нижняя", "ДИ 95% верхняя", "Средняя задержка, мин"]


def csv_rows(db: Session, f: Filters, dataset: str) -> tuple[list[str], list[list]]:
    rate = lambda r: [r["flights"], r["delayed"], r["share"], r["ci_low"], r["ci_high"], r["avg_delay"]]
    if dataset == "airlines":
        return (["Авиакомпания", "Код", *_RATE_HEAD, "Макс. задержка, мин"],
                [[r["name"], r["code"], *rate(r), r["max_delay"]] for r in svc.by_airline(db, f)])
    if dataset == "hourly":
        return ["Час вылета", *_RATE_HEAD], [[r["hour"], *rate(r)] for r in svc.by_hour(db, f)]
    if dataset == "periods":
        return (["Период суток", "С часа", "По час", *_RATE_HEAD],
                [[r["label"], r["hour_from"], r["hour_to"], *rate(r)] for r in svc.by_period(db, f)])
    if dataset == "airports":
        return (["Код", "Название", "Город", "Штат", *_RATE_HEAD],
                [[r["code"], r["name"], r["city"], r["state"], *rate(r)]
                 for r in svc.by_airport(db, f, "share", "desc", 1, 400)])
    if dataset == "categories":
        return ["Категория", "Рейсов", "Доля"], [[r["label"], r["flights"], r["share"]] for r in svc.categories(db, f)]
    if dataset == "heatmap":
        return (["День недели", "Час вылета", "Рейсов", "Задержано", "Доля задержанных"],
                [[DAYS_OF_WEEK[r["dow"]], r["hour"], r["flights"], r["delayed"], r["share"]] for r in svc.heatmap(db, f)])
    if dataset == "monthly":
        return ["Месяц", *_RATE_HEAD], [[r["period"], *rate(r)] for r in svc.monthly(db, f)]
    raise ValueError(dataset)


def build_csv(header: list[str], rows: list[list], decimal: str = "comma") -> bytes:
    """CSV в UTF-8 с BOM и разделителем «;» — открывается в Excel без настройки."""
    def cell(v):
        if v is None:
            return ""
        if isinstance(v, float):
            s = f"{v:.4f}" if abs(v) < 10 else f"{v:.2f}"
            return s.replace(".", ",") if decimal == "comma" else s
        return v

    out = io.StringIO()
    w = csv.writer(out, delimiter=";", lineterminator="\r\n")
    w.writerow(header)
    for row in rows:
        w.writerow([cell(v) for v in row])
    return ("\ufeff" + out.getvalue()).encode("utf-8")
