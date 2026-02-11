"""McKinsey-Quality HTML Report Template

Professional HTML report generator with consulting-grade design:
- Pretendard/Inter typography, clean sans-serif
- Dotted-line tables, KPI cards, section numbering
- SHAP figure frames with captions
- Print-ready A4 layout (@media print)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import html as html_mod


METRIC_DESCRIPTIONS = {
    "accuracy": "전체 예측 중 정답 비율",
    "f1": "Precision과 Recall의 조화 평균 (불균형 데이터에 유용)",
    "precision": "양성 예측 중 실제 양성 비율",
    "recall": "실제 양성 중 모델이 찾아낸 비율",
    "roc_auc": "모든 임계값에서 양성/음성 구분 능력",
    "rmse": "예측 오차의 표준편차 (낮을수록 좋음)",
    "mae": "예측 오차의 평균 절대값 (낮을수록 좋음)",
    "r2": "모델이 설명하는 데이터 변동 비율 (1에 가까울수록 좋음)",
    "mse": "예측 오차의 제곱 평균 (낮을수록 좋음)",
    "log_loss": "확률 예측의 정확도 (낮을수록 좋음)",
    "mape": "예측 오차의 백분율 평균 (낮을수록 좋음)",
}

FIGURE_INTERPRETATIONS = {
    "shap_bar": "각 변수가 모델 예측에 기여하는 평균 영향력을 보여줍니다. 막대가 길수록 해당 변수가 예측에 더 큰 영향을 미칩니다.",
    "shap_summary": "각 데이터 포인트에서 변수들이 예측을 어떻게 밀어내는지 보여줍니다. 빨간 점은 높은 값, 파란 점은 낮은 값을 의미합니다.",
    "shap_waterfall": "하나의 개별 예측이 어떻게 만들어졌는지 분해합니다. 빨간 막대는 예측을 높이고, 파란 막대는 낮춥니다.",
    "shap_beeswarm": "각 데이터 포인트에서 변수들이 예측을 어떻게 밀어내는지 보여줍니다. 빨간 점은 높은 값, 파란 점은 낮은 값을 의미합니다.",
}

STEP_LABELS = {
    "datetime": "DateTime 변환",
    "outlier": "이상치 처리",
    "encoding": "변수 인코딩",
    "label": "라벨 인코딩",
    "missing": "결측값 처리",
    "variance": "저분산 제거",
    "stratif": "층화 분할",
    "sample_weight": "가중치 적용",
    "scale": "스케일링",
    "one-hot": "원핫 인코딩",
    "clipping": "이상치 클리핑",
    "fillna": "결측값 처리",
    "imput": "결측값 대체",
}


class McKinseyReportTemplate:
    """Generates a McKinsey-style HTML report from analysis data."""

    def __init__(self, report_data: Dict[str, Any]):
        self.data = report_data
        self.problem_def = report_data.get("problem_definition", {})
        self.model_data = report_data.get("model_data", {})
        self.insights = report_data.get("insights", {})
        self.research = report_data.get("research_results", {})
        self.data_intel = report_data.get("data_intelligence", {})
        self.preprocessing_log = report_data.get("preprocessing_log", [])
        self.data_profile = report_data.get("data_profile", {})
        self.session_id = report_data.get("session_id", "N/A")
        self.timestamp = report_data.get("timestamp", datetime.now().isoformat())

    def render(
        self,
        executive_summary: str = "",
        shap_images: Optional[List[Dict]] = None,
        feature_importance: Optional[List[Dict]] = None,
    ) -> str:
        """Render the full HTML report."""
        shap_images = shap_images or []
        feature_importance = feature_importance or []
        sections = [
            self._executive_summary_section(executive_summary),
            self._problem_definition_section(),
            self._data_overview_section(),
            self._research_findings_section(),
            self._modeling_results_section(),
            self._shap_section(shap_images, feature_importance),
            self._key_insights_section(),
            self._recommendations_section(),
            self._appendix_section(),
        ]
        body = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Report - {self._esc(self.session_id)}</title>
    {self._css()}
</head>
<body>
    <div class="report">
        {self._cover_section()}
        <div class="content">
{body}
        </div>
        {self._footer()}
    </div>
</body>
</html>"""

    # ── CSS ──────────────────────────────────────────────────────────

    def _css(self) -> str:
        return """<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

    :root {
        --primary: #1B2432;
        --body: #4B5563;
        --muted: #9CA3AF;
        --accent: #2563EB;
        --accent-bg: #EFF6FF;
        --success: #059669;
        --warning: #D97706;
        --danger: #DC2626;
        --border: #E5E7EB;
        --divider: #D1D5DB;
        --bg: #FFFFFF;
        --bg-subtle: #F9FAFB;
        --font: 'Pretendard Variable', 'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: var(--font);
        font-size: 15px;
        line-height: 1.7;
        color: var(--body);
        background: var(--bg-subtle);
        -webkit-font-smoothing: antialiased;
    }

    .report {
        max-width: 920px;
        margin: 0 auto;
        background: var(--bg);
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 6px 16px rgba(0,0,0,0.04);
    }

    /* ── Cover ── */
    .cover {
        padding: 64px 56px 48px;
        border-bottom: 3px solid var(--accent);
    }
    .cover-brand {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 32px;
    }
    .cover-title {
        font-size: 32px;
        font-weight: 700;
        color: var(--primary);
        line-height: 1.25;
        margin-bottom: 12px;
    }
    .cover-badge {
        display: inline-block;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 600;
        color: var(--accent);
        background: var(--accent-bg);
        border-radius: 100px;
        margin-bottom: 32px;
    }
    .cover-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
    }
    .cover-meta-item {
        font-size: 13px;
        color: var(--muted);
    }
    .cover-meta-item strong {
        display: block;
        color: var(--primary);
        font-weight: 600;
        font-size: 14px;
    }

    /* ── Content ── */
    .content {
        padding: 48px 56px 56px;
    }

    /* ── Section Header ── */
    .section {
        margin-bottom: 48px;
        page-break-inside: avoid;
    }
    .section-header {
        display: flex;
        align-items: baseline;
        gap: 14px;
        margin-bottom: 8px;
    }
    .section-number {
        font-size: 28px;
        font-weight: 700;
        color: var(--divider);
        line-height: 1;
        min-width: 36px;
    }
    .section-title {
        font-size: 20px;
        font-weight: 700;
        color: var(--primary);
        line-height: 1.3;
    }
    .section-divider {
        height: 1px;
        background: var(--border);
        margin-bottom: 24px;
    }

    /* ── KPI Cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }
    .kpi-card {
        background: var(--bg-subtle);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--muted);
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--accent);
        line-height: 1.2;
    }
    .kpi-value.success { color: var(--success); }
    .kpi-value.warning { color: var(--warning); }
    .kpi-value.danger  { color: var(--danger); }

    /* ── Dotted Table ── */
    .dotted-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }
    .dotted-table tr {
        border-bottom: 1px dotted var(--divider);
    }
    .dotted-table tr:last-child {
        border-bottom: none;
    }
    .dotted-table td {
        padding: 10px 0;
        font-size: 14px;
        vertical-align: top;
    }
    .dotted-table td:first-child {
        font-weight: 600;
        color: var(--primary);
        width: 180px;
        padding-right: 24px;
    }

    /* ── Standard Table ── */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 14px;
    }
    .data-table th {
        text-align: left;
        padding: 10px 14px;
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--muted);
        border-bottom: 2px solid var(--border);
    }
    .data-table td {
        padding: 10px 14px;
        border-bottom: 1px solid var(--border);
        color: var(--body);
    }
    .data-table tr:last-child td {
        border-bottom: none;
    }
    .data-table tr:hover td {
        background: var(--bg-subtle);
    }

    /* ── Callout ── */
    .callout {
        border-radius: 8px;
        padding: 16px 20px;
        margin: 16px 0;
        font-size: 14px;
        line-height: 1.6;
    }
    .callout.info {
        background: var(--accent-bg);
        border-left: 3px solid var(--accent);
        color: #1E40AF;
    }
    .callout.success {
        background: #ECFDF5;
        border-left: 3px solid var(--success);
        color: #065F46;
    }
    .callout.warning {
        background: #FFFBEB;
        border-left: 3px solid var(--warning);
        color: #92400E;
    }
    .callout.danger {
        background: #FEF2F2;
        border-left: 3px solid var(--danger);
        color: #991B1B;
    }
    .callout-title {
        font-weight: 700;
        font-size: 13px;
        margin-bottom: 4px;
    }

    /* ── KPI Hint ── */
    .kpi-hint {
        font-size: 11px;
        color: var(--muted);
        margin-top: 4px;
        line-height: 1.3;
    }

    /* ── Preprocessing Badges ── */
    .prep-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 12px 0;
    }
    .prep-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 12px;
        font-size: 12px;
        font-weight: 500;
        background: #F0FDF4;
        color: #166534;
        border-radius: 100px;
        border: 1px solid #BBF7D0;
    }

    /* ── Figure ── */
    .figure {
        margin: 24px 0;
        page-break-inside: avoid;
    }
    .figure-caption {
        font-size: 13px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 10px;
    }
    .figure-frame {
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
        background: var(--bg-subtle);
        padding: 16px;
        text-align: center;
    }
    .figure-frame img {
        max-width: 100%;
        height: auto;
    }
    .figure-note {
        font-size: 12px;
        color: var(--muted);
        font-style: italic;
        margin-top: 8px;
    }
    .figure-interp {
        font-size: 13px;
        color: var(--body);
        margin-top: 10px;
        line-height: 1.6;
        padding: 10px 14px;
        background: var(--bg-subtle);
        border-radius: 6px;
    }
    .figure-interp .top-features {
        font-size: 12px;
        color: var(--muted);
        margin-top: 4px;
    }

    /* ── Recommendation Card ── */
    .rec-card {
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px 20px;
        margin: 10px 0;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    .rec-priority {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 4px;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .rec-priority.high   { background: #FEE2E2; color: var(--danger); }
    .rec-priority.medium { background: #FEF3C7; color: var(--warning); }
    .rec-priority.low    { background: #D1FAE5; color: var(--success); }
    .rec-text {
        font-size: 14px;
        color: var(--body);
    }

    /* ── Prose ── */
    .prose p {
        margin-bottom: 14px;
    }
    .prose p:last-child {
        margin-bottom: 0;
    }
    .prose ul {
        padding-left: 20px;
        margin-bottom: 14px;
    }
    .prose li {
        margin-bottom: 6px;
    }

    /* ── Footer ── */
    .report-footer {
        padding: 24px 56px;
        border-top: 1px solid var(--border);
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: var(--muted);
    }

    /* ── Print ── */
    @media print {
        body {
            background: white;
            font-size: 11pt;
            color: #000;
        }
        .report {
            max-width: none;
            box-shadow: none;
            margin: 0;
        }
        .cover {
            padding: 2cm;
            page-break-after: always;
        }
        .content {
            padding: 2cm;
        }
        .section {
            page-break-inside: avoid;
        }
        .kpi-card {
            border: 1px solid #ccc;
        }
        .kpi-value { color: #000 !important; }
        .callout { border-left-width: 2px; }
        .figure-frame { border: 1px solid #ccc; }
        .report-footer {
            padding: 1cm 2cm;
        }
        @page {
            size: A4;
            margin: 2cm;
        }
    }
</style>"""

    # ── Cover ────────────────────────────────────────────────────────

    def _cover_section(self) -> str:
        problem_type = self.problem_def.get("problem_type", "Data Analysis")
        badge_label = self._format_problem_type(problem_type)

        domain_info = self.data_intel.get("domain", {})
        domain = domain_info.get("domain", "general") if domain_info else "general"
        domain_display = domain.replace("_", " ").title() if domain != "general" else ""

        best_model = (self.model_data.get("best_estimator")
                      or self.model_data.get("best_model", ""))

        date_str = self._format_date(self.timestamp)
        short_session = self.session_id[:8] if len(self.session_id) > 8 else self.session_id

        meta_items = [
            ("Date", date_str),
            ("Session", short_session),
        ]
        if domain_display:
            meta_items.insert(1, ("Domain", domain_display))
        if best_model:
            meta_items.insert(-1, ("Model", best_model))

        meta_html = "\n".join(
            f'<div class="cover-meta-item"><strong>{self._esc(v)}</strong>{self._esc(k)}</div>'
            for k, v in meta_items
        )

        return f"""
        <div class="cover">
            <div class="cover-brand">DA SYSTEM</div>
            <div class="cover-title">{self._esc(self._get_report_title())}</div>
            <div class="cover-badge">{self._esc(badge_label)}</div>
            <div class="cover-meta">
                {meta_html}
            </div>
        </div>"""

    # ── Section Helpers ──────────────────────────────────────────────

    def _section_header(self, number: int, title: str) -> str:
        num = f"{number:02d}"
        return f"""
        <div class="section" id="section-{number}">
            <div class="section-header">
                <span class="section-number">{num}</span>
                <span class="section-title">{self._esc(title)}</span>
            </div>
            <div class="section-divider"></div>"""

    @staticmethod
    def _section_close() -> str:
        return "        </div>"

    def _kpi_card(self, label: str, value: str, color: str = "", hint: str = "") -> str:
        cls = f" {color}" if color else ""
        hint_html = f'<div class="kpi-hint">{self._esc(hint)}</div>' if hint else ""
        return f"""<div class="kpi-card">
                <div class="kpi-label">{self._esc(label)}</div>
                <div class="kpi-value{cls}">{self._esc(value)}</div>
                {hint_html}
            </div>"""

    def _kpi_grid(self, cards: List[str]) -> str:
        return f'<div class="kpi-grid">{"".join(cards)}</div>'

    def _dotted_table(self, rows: List[tuple]) -> str:
        row_html = "\n".join(
            f"<tr><td>{self._esc(str(k))}</td><td>{self._esc(str(v))}</td></tr>"
            for k, v in rows if v
        )
        return f'<table class="dotted-table">{row_html}</table>'

    def _data_table(self, headers: List[str], rows: List[List[str]]) -> str:
        th = "".join(f"<th>{self._esc(h)}</th>" for h in headers)
        trs = "\n".join(
            "<tr>" + "".join(f"<td>{self._esc(str(c))}</td>" for c in row) + "</tr>"
            for row in rows
        )
        return f'<table class="data-table"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'

    def _callout(self, text: str, callout_type: str = "info", title: str = "") -> str:
        title_html = f'<div class="callout-title">{self._esc(title)}</div>' if title else ""
        return f'<div class="callout {callout_type}">{title_html}{self._esc(text)}</div>'

    def _figure(self, img_uri: str, caption: str, note: str = "") -> str:
        note_html = f'<div class="figure-note">{self._esc(note)}</div>' if note else ""
        return f"""<div class="figure">
            <div class="figure-caption">{self._esc(caption)}</div>
            <div class="figure-frame"><img src="{img_uri}" alt="{self._esc(caption)}"></div>
            {note_html}
        </div>"""

    # ── Section 01: Executive Summary ────────────────────────────────

    def _executive_summary_section(self, text: str) -> str:
        parts = [self._section_header(1, "Executive Summary")]

        # KPI cards from metrics
        metrics = self.model_data.get("metrics", {})
        if metrics:
            cards = []
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    display = f"{value:.1%}" if value <= 1 else f"{value:,.2f}"
                    color = self._metric_color(value)
                    label = key.upper().replace("_", " ")
                    hint = METRIC_DESCRIPTIONS.get(key.lower(), "")
                    cards.append(self._kpi_card(label, display, color, hint))
            if cards:
                parts.append(self._kpi_grid(cards[:6]))

        # Summary text
        if text:
            parts.append(f'<div class="prose">')
            for para in text.strip().split("\n\n"):
                para = para.strip()
                if para:
                    parts.append(f"<p>{self._esc(para)}</p>")
            parts.append("</div>")
        else:
            parts.append(self._callout("Executive summary not available.", "info"))

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 02: Problem Definition ───────────────────────────────

    def _problem_definition_section(self) -> str:
        parts = [self._section_header(2, "Problem Definition")]

        goal = self.problem_def.get("analysis_goal") or self.problem_def.get("goal", "N/A")
        target = self.problem_def.get("target_column") or self.problem_def.get("target_variable", "N/A")
        metric = self.problem_def.get("evaluation_metric", "N/A")
        problem_type = self.problem_def.get("problem_type", "N/A")

        rows = [
            ("Goal", goal),
            ("Problem Type", self._format_problem_type(problem_type)),
            ("Target Variable", target),
            ("Evaluation Metric", metric),
        ]
        parts.append(self._dotted_table(rows))

        # Data characteristics
        data_chars = self.problem_def.get("data_characteristics", {})
        if data_chars:
            chars_rows = [
                ("Rows", str(data_chars.get("n_rows", "N/A"))),
                ("Columns", str(data_chars.get("n_columns", "N/A"))),
                ("Missing Values", str(data_chars.get("missing_values", "N/A"))),
            ]
            parts.append(self._dotted_table(chars_rows))

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 03: Data Overview ────────────────────────────────────

    def _data_overview_section(self) -> str:
        parts = [self._section_header(3, "Data Quality & Preprocessing")]

        has_content = False

        # Domain detection
        domain_info = self.data_intel.get("domain", {})
        if domain_info and domain_info.get("domain", "general") != "general":
            domain_name = domain_info["domain"].replace("_", " ").title()
            confidence = domain_info.get("confidence", "N/A")
            parts.append(self._callout(
                f"Detected Domain: {domain_name} (confidence: {confidence})",
                "info", "Domain Detection"
            ))
            has_content = True

        # Class imbalance
        imbalance = self.data_intel.get("class_imbalance", {})
        if imbalance and imbalance.get("severity"):
            ratio = imbalance.get("ratio", "N/A")
            minority_pct = imbalance.get("minority_pct", "N/A")
            parts.append(self._callout(
                f"Severity: {imbalance['severity']} (ratio {ratio}:1, minority class {minority_pct}%)",
                "warning", "Class Imbalance"
            ))
            has_content = True

        # Outlier summary
        outliers = self.data_intel.get("outlier_report", {})
        if outliers:
            flagged = [col for col, info in outliers.items()
                       if isinstance(info, dict) and info.get("outlier_pct", 0) > 5]
            if flagged:
                parts.append(self._callout(
                    f"Columns with >5% outliers ({len(flagged)}): {', '.join(flagged[:10])}",
                    "warning", "Outlier Detection"
                ))
                has_content = True

        # Data warnings
        warnings = self.data_intel.get("data_warnings", [])
        if warnings:
            for w in warnings:
                parts.append(self._callout(w, "warning"))
            has_content = True

        # Preprocessing steps — compact badge layout
        if self.preprocessing_log:
            badges_html = self._compact_preprocessing(self.preprocessing_log)
            if badges_html:
                parts.append(f'<div class="prose"><p><strong>Applied Preprocessing:</strong></p>{badges_html}</div>')
                has_content = True

        if not has_content:
            parts.append('<div class="prose"><p>No data quality analysis available.</p></div>')

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 04: Research Findings ────────────────────────────────

    def _research_findings_section(self) -> str:
        parts = [self._section_header(4, "Prior Research")]

        has_content = False

        # Papers
        papers = self.research.get("papers", [])
        if papers:
            parts.append(f'<div class="prose"><p><strong>Academic Papers:</strong> {len(papers)} relevant papers reviewed</p></div>')

            rows = []
            for p in papers[:5]:
                title = p.get("title", "Untitled")
                authors = p.get("authors", "N/A")
                if isinstance(authors, list):
                    authors = ", ".join(authors[:3])
                    if len(p.get("authors", [])) > 3:
                        authors += " et al."
                rows.append([title[:80], authors[:60]])
            if rows:
                parts.append(self._data_table(["Title", "Authors"], rows))
            has_content = True

        # Kaggle
        kaggle = self.research.get("kaggle_solutions") or self.research.get("kaggle", {})
        if kaggle:
            competition = kaggle.get("competition", {})
            comp_title = competition.get("title", "N/A")
            techniques = kaggle.get("techniques", [])
            parts.append(f'<div class="prose"><p><strong>Kaggle Solutions:</strong> {self._esc(comp_title)}</p></div>')
            if techniques:
                parts.append('<div class="prose"><ul>')
                for tech in techniques[:8]:
                    parts.append(f"<li>{self._esc(tech)}</li>")
                parts.append("</ul></div>")
            has_content = True

        # Deep Research
        deep = self.research.get("deep_research", {})
        if deep:
            summary = deep.get("summary", "")
            if summary:
                parts.append(self._callout(summary[:500], "info", "Deep Research Summary"))
            has_content = True

        # Recommended models
        recommended = self.research.get("recommended_models", [])
        if recommended:
            parts.append(f'<div class="prose"><p><strong>Research-Recommended Models:</strong> {", ".join(recommended[:5])}</p></div>')
            has_content = True

        if not has_content:
            parts.append('<div class="prose"><p>No prior research data available.</p></div>')

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 05: Modeling Results ─────────────────────────────────

    def _modeling_results_section(self) -> str:
        parts = [self._section_header(5, "Modeling Results")]

        best_model = (self.model_data.get("best_estimator")
                      or self.model_data.get("best_model", "N/A"))
        metrics = self.model_data.get("metrics", {})

        # Best model callout
        parts.append(self._callout(f"Best Model: {best_model}", "success", "AutoML Result"))

        # Metrics table
        if metrics:
            rows = []
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    formatted = f"{value:.4f}"
                else:
                    formatted = str(value)
                rows.append([key.upper().replace("_", " "), formatted])
            parts.append(self._data_table(["Metric", "Score"], rows))

        # Training details
        training_time = self.model_data.get("training_time")
        n_trials = self.model_data.get("n_trials") or self.model_data.get("num_trials")
        if training_time or n_trials:
            detail_rows = []
            if training_time:
                detail_rows.append(("Training Time", f"{training_time:.1f}s" if isinstance(training_time, float) else str(training_time)))
            if n_trials:
                detail_rows.append(("Trials Evaluated", str(n_trials)))
            parts.append(self._dotted_table(detail_rows))

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 06: SHAP Analysis ────────────────────────────────────

    def _shap_section(self, images: List[Dict], feature_importance: Optional[List[Dict]] = None) -> str:
        feature_importance = feature_importance or []
        parts = [self._section_header(6, "Feature Importance (SHAP)")]

        # Extract top-3 feature names
        top_features = []
        if feature_importance:
            sorted_fi = sorted(feature_importance, key=lambda x: abs(x.get("importance", 0)), reverse=True)
            top_features = [f.get("feature", f.get("name", "")) for f in sorted_fi[:3] if f.get("feature") or f.get("name")]

        if images:
            for i, img in enumerate(images[:4], 1):
                filename = img.get("filename", "")
                label = filename.replace("_", " ").replace(".png", "").title()
                caption = f"Figure {i}. {label}" if label else f"Figure {i}. SHAP Analysis"
                parts.append(self._figure_with_interp(img["data_uri"], caption, filename, top_features))
        else:
            parts.append(self._callout("SHAP analysis plots are not available for this session.", "info"))

        parts.append(self._section_close())
        return "\n".join(parts)

    def _figure_with_interp(self, img_uri: str, caption: str, filename: str, top_features: List[str]) -> str:
        """Figure with auto-interpretation text."""
        # Match filename to interpretation
        interp = ""
        fname_lower = filename.lower()
        for key, text in FIGURE_INTERPRETATIONS.items():
            if key in fname_lower:
                interp = text
                break

        interp_html = ""
        if interp:
            top_html = ""
            if top_features and ("bar" in fname_lower or "summary" in fname_lower or "beeswarm" in fname_lower):
                top_html = f'<div class="top-features">상위 변수: {", ".join(self._esc(f) for f in top_features)}</div>'
            interp_html = f'<div class="figure-interp">{self._esc(interp)}{top_html}</div>'

        return f"""<div class="figure">
            <div class="figure-caption">{self._esc(caption)}</div>
            <div class="figure-frame"><img src="{img_uri}" alt="{self._esc(caption)}"></div>
            {interp_html}
        </div>"""

    # ── Section 07: Key Insights ─────────────────────────────────────

    def _key_insights_section(self) -> str:
        parts = [self._section_header(7, "Key Insights")]

        has_content = False

        # Key findings
        key_findings = self.insights.get("key_findings", [])
        if key_findings:
            parts.append('<div class="prose"><ol>')
            for finding in key_findings:
                parts.append(f"<li>{self._esc(finding)}</li>")
            parts.append("</ol></div>")
            has_content = True

        # Business insights
        business_insights = self.insights.get("business_insights", [])
        if business_insights:
            parts.append('<div class="prose"><p><strong>Business Insights:</strong></p><ul>')
            for insight in business_insights:
                parts.append(f"<li>{self._esc(insight)}</li>")
            parts.append("</ul></div>")
            has_content = True

        # Error analysis (Cohen's d, confusion matrix, etc.)
        error_analysis = self.insights.get("error_analysis", {})
        if error_analysis:
            cohens_d = error_analysis.get("cohens_d")
            if cohens_d and isinstance(cohens_d, dict):
                rows = [[feat, f"{val:.3f}"] for feat, val in list(cohens_d.items())[:5]]
                if rows:
                    parts.append('<div class="prose"><p><strong>Error Analysis (Cohen\'s d):</strong></p></div>')
                    parts.append(self._data_table(["Feature", "Cohen's d"], rows))
                    has_content = True

        if not has_content:
            parts.append('<div class="prose"><p>No insights available.</p></div>')

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 08: Recommendations ──────────────────────────────────

    def _recommendations_section(self) -> str:
        parts = [self._section_header(8, "Recommendations")]

        recommendations = self.insights.get("recommendations", [])
        if recommendations:
            for i, rec in enumerate(recommendations):
                priority = self._infer_priority(rec, i)
                parts.append(f"""<div class="rec-card">
                <span class="rec-priority {priority}">{priority.upper()}</span>
                <span class="rec-text">{self._esc(rec)}</span>
            </div>""")
        else:
            parts.append('<div class="prose"><p>No specific recommendations at this time.</p></div>')

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 09: Appendix ─────────────────────────────────────────

    def _appendix_section(self) -> str:
        parts = [self._section_header(9, "Appendix")]

        # Research comparison table
        techniques = self.research.get("techniques", [])
        recommended = self.research.get("recommended_models", [])
        best_model = (self.model_data.get("best_estimator")
                      or self.model_data.get("best_model", ""))

        if techniques or recommended:
            rows = []
            papers = self.research.get("papers", [])
            kaggle = self.research.get("kaggle_solutions") or self.research.get("kaggle", {})
            deep = self.research.get("deep_research", {})

            if papers:
                rows.append(["HuggingFace Papers", f"{len(papers)} papers reviewed"])
            if kaggle and kaggle.get("techniques"):
                rows.append(["Kaggle Solutions", ", ".join(kaggle["techniques"][:5])])
            if deep and deep.get("key_findings"):
                rows.append(["Deep Research", f"{len(deep['key_findings'])} key findings"])
            if best_model:
                rows.append(["Selected Model", best_model])

            if rows:
                parts.append('<div class="prose"><p><strong>Research Comparison:</strong></p></div>')
                parts.append(self._data_table(["Source", "Details"], rows))

        # Artifacts list
        parts.append('<div class="prose">')
        parts.append("<p><strong>Artifacts:</strong></p>")
        parts.append("<ul>")
        parts.append("<li>SHAP analysis plots</li>")
        parts.append("<li>Feature importance data</li>")
        parts.append("<li>Model performance visualizations</li>")
        parts.append("<li>Trained model binary</li>")
        parts.append("</ul>")
        parts.append("<p><strong>Reproducibility:</strong> All analysis can be reproduced using the saved model and data artifacts.</p>")
        parts.append("</div>")

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Compact Preprocessing ─────────────────────────────────────────

    @staticmethod
    def _compact_preprocessing(steps: List[str]) -> str:
        """Convert verbose preprocessing log into compact badges (max 5)."""
        matched = []
        seen_labels = set()
        for step in steps:
            step_lower = step.lower()
            for keyword, label in STEP_LABELS.items():
                if keyword in step_lower and label not in seen_labels:
                    matched.append(label)
                    seen_labels.add(label)
                    break
        if not matched:
            # Fallback: show first 5 steps truncated
            matched = [s[:30] for s in steps[:5]]

        badges = "".join(
            f'<span class="prep-badge">{html_mod.escape(label)}</span>'
            for label in matched[:5]
        )
        return f'<div class="prep-badges">{badges}</div>'

    # ── Footer ───────────────────────────────────────────────────────

    def _footer(self) -> str:
        date = self._format_date(self.timestamp)
        return f"""
        <div class="report-footer">
            <span>Generated by DA System</span>
            <span>{self._esc(date)}</span>
        </div>"""

    # ── Utilities ────────────────────────────────────────────────────

    @staticmethod
    def _esc(text: str) -> str:
        return html_mod.escape(str(text)) if text else ""

    @staticmethod
    def _format_problem_type(pt: str) -> str:
        return pt.replace("_", " ").title() if pt else "Data Analysis"

    @staticmethod
    def _format_date(ts: str) -> str:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ts[:10] if len(ts) >= 10 else ts

    @staticmethod
    def _metric_color(value: float) -> str:
        if value >= 0.9:
            return "success"
        if value >= 0.7:
            return ""
        if value >= 0.5:
            return "warning"
        return "danger"

    def _get_report_title(self) -> str:
        goal = self.problem_def.get("analysis_goal") or self.problem_def.get("goal", "")
        if goal and len(goal) > 10:
            return goal[:80]
        return "Data Analysis Report"

    @staticmethod
    def _infer_priority(text: str, index: int) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["critical", "immediately", "urgent", "must"]):
            return "high"
        if any(kw in text_lower for kw in ["consider", "optional", "future", "long-term"]):
            return "low"
        if index == 0:
            return "high"
        if index <= 2:
            return "medium"
        return "low"
