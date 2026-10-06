"""Dependency-free SVG EDA exports; no interactive plotting required."""

from html import escape
from math import isfinite
from pathlib import Path

from .quality import numeric_summary
from .eda import pearson


def frame(title: str, body: str, x_label: str = "", y_label: str = "", width: int = 900, height: int = 520) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            '<rect width="100%" height="100%" fill="white"/>'
            '<style>text{font:13px sans-serif;fill:#25334a}.title{font-size:20px;font-weight:bold}</style>'
            f'<text x="65" y="30" class="title">{escape(title)}</text>{body}'
            f'<text x="370" y="{height-10}">{escape(x_label)}</text>'
            f'<text transform="translate(18,320) rotate(-90)">{escape(y_label)}</text></svg>')


def xy_plot(path: Path, title: str, points: list[tuple[float, float]], x_label: str, y_label: str,
            *, line: bool = False, highlights: set[int] | None = None) -> None:
    finite = [(i, x, y) for i, (x, y) in enumerate(points) if isfinite(x) and isfinite(y)]
    if not finite:
        path.write_text(frame(title, '<text x="100" y="100">No valid observations</text>'), encoding="utf-8")
        return
    xmin, xmax = min(x for _, x, _ in finite), max(x for _, x, _ in finite)
    ymin, ymax = min(y for _, _, y in finite), max(y for _, _, y in finite)
    if xmax == xmin:
        xmax = xmin + 1
    if ymax == ymin:
        ymax = ymin + 1
    def position(x: float, y: float) -> tuple[float, float]:
        return 80 + (x - xmin) / (xmax - xmin) * 770, 450 - (y - ymin) / (ymax - ymin) * 390
    body = '<path d="M80 60V450H850" fill="none" stroke="#54657c"/>'
    for k in range(6):
        x = xmin + (xmax - xmin) * k / 5
        y = ymin + (ymax - ymin) * k / 5
        px, py = position(x, y)
        body += f'<text x="{px-15:.2f}" y="472">{x:.3g}</text><text x="28" y="{py+4:.2f}">{y:.3g}</text>'
    previous = None
    for index, x, y in finite:
        px, py = position(x, y)
        if line and previous is not None and index == previous[0] + 1:
            body += f'<line x1="{previous[1]:.2f}" y1="{previous[2]:.2f}" x2="{px:.2f}" y2="{py:.2f}" stroke="#2877b5" stroke-width="1"/>'
        color = '#e05a25' if highlights and index in highlights else '#2877b5'
        body += f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{3 if line else 4}" fill="{color}" opacity=".7"><title>{escape(x_label)}={x:.6g}; {escape(y_label)}={y:.6g}</title></circle>'
        previous = (index, px, py)
    path.write_text(frame(title, body, x_label, y_label), encoding="utf-8")


def histogram(path: Path, title: str, values: list[float], unit: str) -> None:
    values = [v for v in values if isfinite(v)]
    if not values:
        path.write_text(frame(title, '<text x="100" y="100">No valid observations</text>'), encoding="utf-8")
        return
    low, high = min(values), max(values)
    if high == low:
        high = low + 1
    counts = [0] * 20
    for v in values:
        counts[min(19, int((v-low)/(high-low)*20))] += 1
    body = '<path d="M80 60V450H850" fill="none" stroke="#54657c"/>'
    for i, count in enumerate(counts):
        height = count / max(counts) * 360
        body += f'<rect x="{80+i*38.5:.2f}" y="{450-height:.2f}" width="36.5" height="{height:.2f}" fill="#2877b5"><title>bin {low+i*(high-low)/20:.4g} to {low+(i+1)*(high-low)/20:.4g}: {count}</title></rect>'
    body += f'<text x="80" y="475">{low:.4g}</text><text x="795" y="475">{high:.4g}</text><text x="28" y="80">{max(counts)}</text><text x="50" y="450">0</text>'
    path.write_text(frame(title, body, unit, "Sample count"), encoding="utf-8")


def boxplot(path: Path, title: str, groups: dict[str, list[float]], unit: str) -> None:
    summaries = [(name, numeric_summary(values)) for name, values in groups.items()]
    summaries = [(name, s) for name, s in summaries if s["finite_count"]]
    if not summaries:
        path.write_text(frame(title, '<text x="100" y="100">No valid observations</text>'), encoding="utf-8")
        return
    low, high = min(s["min"] for _, s in summaries), max(s["max"] for _, s in summaries)
    if high == low:
        high = low + 1
    def y(v: float) -> float:
        return 450 - (v-low)/(high-low)*380
    body = '<path d="M80 60V450H850" fill="none" stroke="#54657c"/>'
    for i, (name, s) in enumerate(summaries):
        x = 150 + i * 650 / max(1, len(summaries)-1)
        body += (f'<line x1="{x}" x2="{x}" y1="{y(s["min"])}" y2="{y(s["max"])}" stroke="#2877b5"/>'
                 f'<rect x="{x-30}" y="{y(s["p75"])}" width="60" height="{y(s["p25"])-y(s["p75"])}" fill="#bddbf0" stroke="#2877b5"/>'
                 f'<line x1="{x-30}" x2="{x+30}" y1="{y(s["median"])}" y2="{y(s["median"])}" stroke="#e05a25"/>'
                 f'<text x="{x-50}" y="480">{escape(name)}</text>')
    for k in range(6):
        v = low + (high-low)*k/5
        body += f'<text x="25" y="{y(v)+4}">{v:.3g}</text>'
    path.write_text(frame(title + ' (whiskers: min/max)', body, "Group", unit), encoding="utf-8")


def correlation_matrix(path: Path, windows: list[dict], fields: list[str]) -> None:
    size = 58
    body = ''
    for i, field in enumerate(fields):
        body += f'<text x="5" y="{180+i*size+32}" font-size="10">{escape(field)}</text>'
        body += f'<text transform="translate({230+i*size+30},170) rotate(-55)">{escape(field)}</text>'
        for j, other in enumerate(fields):
            value = pearson([w[field] for w in windows], [w[other] for w in windows])
            opacity = abs(value) if value is not None else 0
            color = '#dc5a39' if value is not None and value > 0 else '#2877b5'
            body += f'<rect x="{230+j*size}" y="{180+i*size}" width="{size}" height="{size}" fill="{color}" fill-opacity="{opacity:.3f}" stroke="#e0e0e0"/>'
            text = f'{value:.2f}' if value is not None else 'NA'
            body += f'<text x="{238+j*size}" y="{213+i*size}">{text}</text>'
    path.write_text(frame('Pearson correlation: eligible operating periods', body,
                          width=230+size*len(fields)+30, height=220+size*len(fields)), encoding="utf-8")
