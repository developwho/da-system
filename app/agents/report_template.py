"""McKinsey-Quality HTML Report Template — Mock-Level Design

Professional HTML report generator with consulting-grade design:
- Hero Verdict with auto-grading, CSS bar charts, Pull Quotes
- Table of Contents, collapsible Appendix, Methodology section
- Pretendard/Inter typography, Slate color palette
- Print-ready A4 layout (@media print)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import html as html_mod
import re


# ── Constants ─────────────────────────────────────────────────

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

METRIC_DISPLAY = {
    "r2": "R\u00B2",
    "roc_auc": "ROC AUC",
    "log_loss": "Log Loss",
    "rmse": "RMSE",
    "mae": "MAE",
    "mse": "MSE",
    "mape": "MAPE",
    "f1": "F1",
    "accuracy": "Accuracy",
    "precision": "Precision",
    "recall": "Recall",
}

LOWER_IS_BETTER = {"rmse", "mae", "mse", "log_loss", "mape"}

GRADE_THRESHOLDS_HIGHER = [
    (0.95, "A+", "var(--success)"),
    (0.90, "A", "var(--success)"),
    (0.80, "B", "var(--accent)"),
    (0.70, "C", "var(--warning)"),
    (0.0, "D", "var(--danger)"),
]

GRADE_THRESHOLDS_LOWER = [
    (0.03, "A+", "var(--success)"),
    (0.05, "A", "var(--success)"),
    (0.10, "B", "var(--accent)"),
    (0.15, "C", "var(--warning)"),
    (float("inf"), "D", "var(--danger)"),
]

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

SECTION_DEFS = [
    (1, "Executive Summary"),
    (2, "Problem Definition"),
    (3, "Data Quality & Preprocessing"),
    (4, "Prior Research"),
    (5, "Methodology"),
    (6, "Modeling Results"),
    (7, "Feature Importance (SHAP)"),
    (8, "Key Insights"),
    (9, "Recommendations"),
    (10, "Appendix"),
]

CHECK_SVG = '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>'


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
        self._fi_pct: List[Dict] = []

    def render(
        self,
        executive_summary: str = "",
        shap_images: Optional[List[Dict]] = None,
        feature_importance: Optional[List[Dict]] = None,
    ) -> str:
        """Render the full HTML report."""
        shap_images = shap_images or []
        feature_importance = feature_importance or []

        # Pre-compute SHAP percentages with fallbacks
        self._fi_pct = self._compute_shap_percentages(feature_importance)
        if not self._fi_pct:
            shap_summary = self.insights.get("shap_summary", [])
            if shap_summary:
                self._fi_pct = self._compute_shap_percentages(shap_summary)
        if not self._fi_pct:
            fi_from_model = self.model_data.get("feature_importance", [])
            if fi_from_model:
                self._fi_pct = self._compute_shap_percentages(fi_from_model)

        sections = [
            self._executive_summary_section(executive_summary),
            self._problem_definition_section(),
            self._data_overview_section(),
            self._research_findings_section(),
            self._methodology_section(),
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
        {self._toc_section()}
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
        --primary: #0F172A;
        --primary-mid: #1E293B;
        --body: #475569;
        --muted: #94A3B8;
        --accent: #2563EB;
        --accent-light: #3B82F6;
        --accent-bg: #EFF6FF;
        --accent-bg-deep: #DBEAFE;
        --success: #059669;
        --success-bg: #ECFDF5;
        --warning: #D97706;
        --warning-bg: #FFFBEB;
        --danger: #DC2626;
        --danger-bg: #FEF2F2;
        --border: #E2E8F0;
        --border-light: #F1F5F9;
        --divider: #CBD5E1;
        --bg: #FFFFFF;
        --bg-subtle: #F8FAFC;
        --bg-muted: #F1F5F9;
        --font: 'Pretendard Variable', 'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }

    body {
        font-family: var(--font);
        font-size: 15px;
        line-height: 1.75;
        color: var(--body);
        background: #F0F2F5;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    .report {
        max-width: 960px;
        margin: 0 auto;
        background: var(--bg);
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06);
    }

    /* ═══ COVER PAGE ═══ */
    .cover {
        padding: 72px 64px 56px;
        border-bottom: 4px solid var(--accent);
        position: relative;
        min-height: 420px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .cover-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 48px;
    }
    .cover-brand {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 4px;
        text-transform: uppercase;
        color: var(--accent);
    }
    .cover-confidential {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--danger);
        border: 1.5px solid var(--danger);
        padding: 4px 12px;
        border-radius: 2px;
    }
    .cover-body {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .cover-title {
        font-size: 36px;
        font-weight: 800;
        color: var(--primary);
        line-height: 1.2;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }
    .cover-subtitle {
        font-size: 18px;
        font-weight: 400;
        color: var(--muted);
        margin-bottom: 24px;
        line-height: 1.4;
    }
    .cover-badges {
        display: flex;
        gap: 8px;
        margin-bottom: 40px;
    }
    .cover-badge {
        display: inline-block;
        padding: 5px 16px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 100px;
    }
    .cover-badge.type {
        color: var(--accent);
        background: var(--accent-bg);
    }
    .cover-badge.domain {
        color: var(--success);
        background: var(--success-bg);
    }
    .cover-badge.version {
        color: var(--muted);
        background: var(--bg-muted);
    }
    .cover-meta-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0;
        border-top: 1px solid var(--border);
        padding-top: 24px;
    }
    .cover-meta-item {
        padding: 0 16px;
        border-right: 1px solid var(--border);
    }
    .cover-meta-item:first-child { padding-left: 0; }
    .cover-meta-item:last-child { border-right: none; }
    .cover-meta-label {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 4px;
    }
    .cover-meta-value {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary);
    }

    /* ═══ TABLE OF CONTENTS ═══ */
    .toc {
        padding: 40px 64px;
        border-bottom: 1px solid var(--border);
        background: var(--bg-subtle);
    }
    .toc-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 20px;
    }
    .toc-list {
        list-style: none;
        columns: 2;
        column-gap: 48px;
    }
    .toc-item {
        break-inside: avoid;
        margin-bottom: 8px;
    }
    .toc-item a {
        display: flex;
        align-items: baseline;
        gap: 12px;
        text-decoration: none;
        color: var(--body);
        font-size: 14px;
        padding: 6px 0;
        transition: color 0.15s;
    }
    .toc-item a:hover { color: var(--accent); }
    .toc-num {
        font-size: 13px;
        font-weight: 700;
        color: var(--divider);
        min-width: 24px;
    }
    .toc-label { font-weight: 500; }
    .toc-dots {
        flex: 1;
        border-bottom: 1px dotted var(--divider);
        margin: 0 4px;
        min-width: 20px;
        align-self: center;
        transform: translateY(-3px);
    }

    /* ═══ CONTENT AREA ═══ */
    .content { padding: 56px 64px 64px; }

    /* ── Section Header ── */
    .section {
        margin-bottom: 56px;
        page-break-inside: avoid;
    }
    .section-header {
        display: flex;
        align-items: baseline;
        gap: 16px;
        margin-bottom: 6px;
    }
    .section-number {
        font-size: 32px;
        font-weight: 800;
        color: var(--border);
        line-height: 1;
        min-width: 40px;
        letter-spacing: -1px;
    }
    .section-title {
        font-size: 22px;
        font-weight: 700;
        color: var(--primary);
        line-height: 1.3;
    }
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, var(--border) 0%, transparent 100%);
        margin-bottom: 28px;
    }

    /* ═══ HERO VERDICT ═══ */
    .hero-verdict {
        background: linear-gradient(135deg, var(--accent-bg) 0%, var(--bg) 100%);
        border: 1px solid var(--accent-bg-deep);
        border-radius: 12px;
        padding: 28px 32px;
        margin: 24px 0;
        display: flex;
        align-items: center;
        gap: 24px;
    }
    .hero-verdict-icon {
        width: 52px;
        height: 52px;
        background: var(--accent);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .hero-verdict-icon svg {
        width: 28px;
        height: 28px;
        fill: white;
    }
    .hero-verdict-text { flex: 1; }
    .hero-verdict-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 4px;
    }
    .hero-verdict-message {
        font-size: 17px;
        font-weight: 600;
        color: var(--primary);
        line-height: 1.45;
    }
    .hero-verdict-grade {
        text-align: center;
        flex-shrink: 0;
    }
    .hero-verdict-grade-value {
        font-size: 40px;
        font-weight: 800;
        line-height: 1;
    }
    .hero-verdict-grade-label {
        font-size: 11px;
        font-weight: 600;
        color: var(--muted);
        margin-top: 4px;
    }

    /* ── KPI Cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }
    .kpi-card {
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--border);
    }
    .kpi-card.success::before { background: var(--success); }
    .kpi-card.warning::before { background: var(--warning); }
    .kpi-card.accent::before  { background: var(--accent); }
    .kpi-label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: var(--muted);
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 30px;
        font-weight: 800;
        color: var(--primary);
        line-height: 1.1;
        letter-spacing: -0.5px;
    }
    .kpi-value.success { color: var(--success); }
    .kpi-value.warning { color: var(--warning); }
    .kpi-value.danger  { color: var(--danger); }
    .kpi-value.accent  { color: var(--accent); }
    .kpi-hint {
        font-size: 11px;
        color: var(--muted);
        margin-top: 6px;
        line-height: 1.35;
    }

    /* ── SCR Bullets ── */
    .scr-list {
        list-style: none;
        margin: 20px 0;
    }
    .scr-item {
        display: flex;
        gap: 14px;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-light);
        align-items: flex-start;
    }
    .scr-item:last-child { border-bottom: none; }
    .scr-marker {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--accent);
        flex-shrink: 0;
        margin-top: 8px;
    }
    .scr-text {
        font-size: 15px;
        color: var(--body);
        line-height: 1.65;
    }

    /* ═══ PULL QUOTE ═══ */
    .pull-quote {
        margin: 32px 0;
        padding: 32px 40px;
        background: var(--bg-subtle);
        border-left: 4px solid var(--accent);
        border-radius: 0 8px 8px 0;
    }
    .pull-quote-value {
        font-size: 42px;
        font-weight: 800;
        color: var(--accent);
        line-height: 1;
        margin-bottom: 8px;
        letter-spacing: -1px;
    }
    .pull-quote-text {
        font-size: 16px;
        font-weight: 500;
        color: var(--primary);
        line-height: 1.5;
    }
    .pull-quote-sub {
        font-size: 13px;
        color: var(--muted);
        margin-top: 4px;
    }

    /* ═══ TABLES ═══ */
    .dotted-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }
    .dotted-table tr { border-bottom: 1px dotted var(--divider); }
    .dotted-table tr:last-child { border-bottom: none; }
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

    .data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 14px;
    }
    .data-table th {
        text-align: left;
        padding: 12px 16px;
        font-weight: 700;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--muted);
        border-bottom: 2px solid var(--primary-mid);
        background: var(--bg-subtle);
    }
    .data-table th.num { text-align: right; }
    .data-table td {
        padding: 11px 16px;
        border-bottom: 1px solid var(--border-light);
        color: var(--body);
    }
    .data-table td.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
        font-weight: 500;
    }
    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover td { background: var(--bg-subtle); }
    .data-table tr.champion td {
        font-weight: 700;
        color: var(--primary);
        background: var(--accent-bg);
    }
    .data-table .indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .indicator.green  { background: var(--success); }
    .indicator.yellow { background: var(--warning); }
    .indicator.red    { background: var(--danger); }
    .indicator.blue   { background: var(--accent); }

    /* ── Model Comparison Bar Chart ── */
    .model-compare { margin: 24px 0; }
    .model-bar-row {
        display: grid;
        grid-template-columns: 140px 1fr 60px;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .model-bar-name {
        font-size: 13px;
        font-weight: 600;
        color: var(--primary);
        text-align: right;
    }
    .model-bar-name.champion-label { color: var(--accent); }
    .model-bar-track {
        height: 28px;
        background: var(--bg-muted);
        border-radius: 4px;
        overflow: hidden;
    }
    .model-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    .model-bar-fill.rank-1 { background: var(--accent); }
    .model-bar-fill.rank-2 { background: var(--accent-light); }
    .model-bar-fill.rank-3 { background: #93C5FD; }
    .model-bar-fill.rank-4 { background: #CBD5E1; }
    .model-bar-score {
        font-size: 14px;
        font-weight: 700;
        color: var(--primary);
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .model-bar-score.champion-score { color: var(--accent); }
    .model-compare-caption {
        font-size: 12px;
        color: var(--muted);
        text-align: center;
        margin-top: 8px;
        font-style: italic;
    }

    /* ═══ SHAP BAR CHART ═══ */
    .shap-chart { margin: 24px 0; }
    .shap-bar-row {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        gap: 12px;
    }
    .shap-bar-label {
        width: 160px;
        font-size: 13px;
        font-weight: 600;
        color: var(--primary);
        text-align: right;
        flex-shrink: 0;
        font-variant-numeric: tabular-nums;
    }
    .shap-bar-track {
        flex: 1;
        height: 26px;
        background: var(--bg-muted);
        border-radius: 4px;
        overflow: hidden;
    }
    .shap-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.6s ease;
    }
    .shap-bar-fill.rank-1 { background: var(--accent); }
    .shap-bar-fill.rank-2 { background: var(--accent-light); }
    .shap-bar-fill.rank-3 { background: #60A5FA; }
    .shap-bar-fill.rank-4 { background: #93C5FD; }
    .shap-bar-fill.rank-5 { background: #BFDBFE; }
    .shap-bar-fill.rank-6 { background: #DBEAFE; }
    .shap-bar-value {
        width: 56px;
        font-size: 13px;
        font-weight: 700;
        color: var(--primary);
        flex-shrink: 0;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }

    /* ═══ CALLOUTS ═══ */
    .callout {
        border-radius: 8px;
        padding: 16px 20px;
        margin: 16px 0;
        font-size: 14px;
        line-height: 1.65;
    }
    .callout.info {
        background: var(--accent-bg);
        border-left: 3px solid var(--accent);
        color: #1E40AF;
    }
    .callout.success {
        background: var(--success-bg);
        border-left: 3px solid var(--success);
        color: #065F46;
    }
    .callout.warning {
        background: var(--warning-bg);
        border-left: 3px solid var(--warning);
        color: #92400E;
    }
    .callout.danger {
        background: var(--danger-bg);
        border-left: 3px solid var(--danger);
        color: #991B1B;
    }
    .callout-title {
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
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
        gap: 6px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 500;
        background: #F0FDF4;
        color: #166534;
        border-radius: 100px;
        border: 1px solid #BBF7D0;
    }
    .prep-badge::before {
        content: '';
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: #22C55E;
    }

    /* ═══ FIGURES ═══ */
    .figure {
        margin: 28px 0;
        page-break-inside: avoid;
    }
    .figure-caption {
        font-size: 12px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .figure-frame {
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
        background: var(--bg-subtle);
        padding: 24px;
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
        margin-top: 12px;
        line-height: 1.65;
        padding: 12px 16px;
        background: var(--bg-subtle);
        border-radius: 6px;
        border-left: 3px solid var(--border);
    }
    .figure-interp .top-features {
        font-size: 12px;
        color: var(--muted);
        margin-top: 4px;
    }

    /* ═══ METHODOLOGY ═══ */
    .method-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin: 20px 0;
    }
    .method-card {
        background: var(--bg-subtle);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 20px;
    }
    .method-card-label {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 8px;
    }
    .method-card-value {
        font-size: 16px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 4px;
    }
    .method-card-desc {
        font-size: 12px;
        color: var(--muted);
        line-height: 1.5;
    }

    /* ═══ RECOMMENDATION CARDS ═══ */
    .rec-card {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px 24px;
        margin: 12px 0;
        display: flex;
        gap: 16px;
        align-items: flex-start;
        transition: box-shadow 0.15s;
    }
    .rec-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .rec-left {
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        min-width: 72px;
    }
    .rec-priority {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 3px 10px;
        border-radius: 4px;
        white-space: nowrap;
    }
    .rec-priority.high   { background: #FEE2E2; color: var(--danger); }
    .rec-priority.medium { background: #FEF3C7; color: var(--warning); }
    .rec-priority.low    { background: #D1FAE5; color: var(--success); }
    .rec-number {
        font-size: 20px;
        font-weight: 800;
        color: var(--border);
    }
    .rec-body { flex: 1; }
    .rec-text {
        font-size: 14px;
        color: var(--body);
        line-height: 1.6;
        margin-bottom: 6px;
    }
    .rec-impact {
        font-size: 12px;
        color: var(--muted);
        display: flex;
        gap: 16px;
    }
    .rec-impact span {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .rec-impact-tag {
        font-weight: 600;
        color: var(--primary-mid);
    }

    /* ═══ APPENDIX ═══ */
    .appendix-details {
        margin: 16px 0;
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
    }
    .appendix-details summary {
        padding: 14px 20px;
        font-size: 14px;
        font-weight: 600;
        color: var(--primary);
        background: var(--bg-subtle);
        cursor: pointer;
        list-style: none;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: background 0.15s;
    }
    .appendix-details summary:hover { background: var(--bg-muted); }
    .appendix-details summary::before {
        content: '';
        width: 0;
        height: 0;
        border-left: 5px solid var(--muted);
        border-top: 4px solid transparent;
        border-bottom: 4px solid transparent;
        transition: transform 0.2s;
    }
    .appendix-details[open] summary::before { transform: rotate(90deg); }
    .appendix-details summary::-webkit-details-marker { display: none; }
    .appendix-content {
        padding: 20px;
        border-top: 1px solid var(--border);
    }

    /* ── Prose ── */
    .prose p { margin-bottom: 14px; }
    .prose p:last-child { margin-bottom: 0; }
    .prose ul, .prose ol { padding-left: 20px; margin-bottom: 14px; }
    .prose li { margin-bottom: 6px; }
    .prose strong { color: var(--primary-mid); font-weight: 700; }

    /* ═══ FOOTER ═══ */
    .report-footer {
        padding: 24px 64px;
        border-top: 1px solid var(--border);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11px;
        color: var(--muted);
    }
    .footer-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .footer-brand {
        font-weight: 700;
        color: var(--primary-mid);
    }
    .footer-divider {
        width: 1px;
        height: 12px;
        background: var(--divider);
    }
    .footer-disclaimer {
        max-width: 420px;
        line-height: 1.4;
    }

    /* ═══ PRINT ═══ */
    @media print {
        body {
            background: white;
            font-size: 10.5pt;
            color: #1a1a1a;
        }
        .report {
            max-width: none;
            box-shadow: none;
            margin: 0;
        }
        .cover {
            padding: 2cm;
            page-break-after: always;
            min-height: auto;
        }
        .toc {
            padding: 1.5cm 2cm;
            page-break-after: always;
        }
        .content { padding: 1.5cm 2cm; }
        .section { page-break-inside: avoid; }
        .kpi-grid { grid-template-columns: repeat(4, 1fr); }
        .kpi-card { border: 1px solid #ccc; }
        .kpi-card::before { display: none; }
        .kpi-value { color: #000 !important; }
        .callout { border-left-width: 2px; }
        .figure-frame { border: 1px solid #ccc; }
        .hero-verdict { border: 1px solid #ccc; background: #f5f5f5; }
        .hero-verdict-icon { background: #333; }
        .hero-verdict-grade-value { color: #000 !important; }
        .pull-quote { border-left-width: 3px; background: #f5f5f5; }
        .pull-quote-value { color: #000 !important; }
        .rec-card:hover { box-shadow: none; }
        .appendix-details { border: 1px solid #ccc; }
        .appendix-details[open] .appendix-content { border-top: 1px solid #ccc; }
        .report-footer { padding: 1cm 2cm; }
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

        goal = self.problem_def.get("analysis_goal") or self.problem_def.get("goal", "")

        # Badges
        badges_html = f'<span class="cover-badge type">{self._esc(badge_label)}</span>'
        if domain_display:
            badges_html += f'\n                    <span class="cover-badge domain">{self._esc(domain_display)}</span>'
        badges_html += '\n                    <span class="cover-badge version">v1.0</span>'

        # Meta grid — always 4 items
        meta_items = [("Date", date_str)]
        if domain_display:
            meta_items.append(("Domain", domain_display))
        else:
            meta_items.append(("Prepared For", "Data Analysis Team"))
        if best_model:
            meta_items.append(("Model", best_model))
        else:
            meta_items.append(("Model", "AutoML"))
        meta_items.append(("Session", short_session))

        meta_html = "\n                ".join(
            f'''<div class="cover-meta-item">
                    <div class="cover-meta-label">{self._esc(k)}</div>
                    <div class="cover-meta-value">{self._esc(v)}</div>
                </div>'''
            for k, v in meta_items
        )

        subtitle = ""
        if goal and len(goal) > 10:
            subtitle = f'<div class="cover-subtitle">{self._esc(goal)}</div>'

        return f"""
        <div class="cover">
            <div class="cover-top">
                <div class="cover-brand">DA SYSTEM</div>
                <div class="cover-confidential">Confidential</div>
            </div>
            <div class="cover-body">
                <div class="cover-title">{self._esc(self._get_report_title())}</div>
                {subtitle}
                <div class="cover-badges">
                    {badges_html}
                </div>
            </div>
            <div class="cover-meta-grid">
                {meta_html}
            </div>
        </div>"""

    # ── TOC ──────────────────────────────────────────────────────────

    def _toc_section(self) -> str:
        items = []
        for num, title in SECTION_DEFS:
            items.append(
                f'<li class="toc-item">'
                f'<a href="#section-{num}">'
                f'<span class="toc-num">{num:02d}</span>'
                f'<span class="toc-label">{self._esc(title)}</span>'
                f'<span class="toc-dots"></span>'
                f'</a></li>'
            )
        return f"""
        <div class="toc">
            <div class="toc-title">Contents</div>
            <ul class="toc-list">
                {"".join(items)}
            </ul>
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

    def _kpi_card(self, label: str, value: str, color: str = "",
                  hint: str = "", card_class: str = "") -> str:
        val_cls = f" {color}" if color else ""
        card_cls = f" {card_class}" if card_class else ""
        hint_html = f'<div class="kpi-hint">{self._esc(hint)}</div>' if hint else ""
        return f"""<div class="kpi-card{card_cls}">
                <div class="kpi-label">{self._esc(label)}</div>
                <div class="kpi-value{val_cls}">{self._esc(value)}</div>
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

    def _pull_quote(self, value: str, text: str, sub: str = "") -> str:
        if not value:
            return ""
        sub_html = f'<div class="pull-quote-sub">{self._esc(sub)}</div>' if sub else ""
        return f"""<div class="pull-quote">
            <div class="pull-quote-value">{self._esc(value)}</div>
            <div class="pull-quote-text">{self._esc(text)}</div>
            {sub_html}
        </div>"""

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

        # Hero Verdict
        parts.append(self._hero_verdict(text))

        # KPI cards from metrics — max 4
        metrics = self.model_data.get("metrics", {})
        if metrics:
            cards = []
            for key, value in metrics.items():
                if isinstance(value, (int, float)) and len(cards) < 4:
                    display = self._format_kpi_value(key, value)
                    color = self._metric_color_class(key, value)
                    card_cls = self._kpi_card_class(key, value)
                    label = METRIC_DISPLAY.get(key.lower(), key.upper().replace("_", " "))
                    hint = METRIC_DESCRIPTIONS.get(key.lower(), "")
                    cards.append(self._kpi_card(label, display, color, hint, card_cls))
            if cards:
                parts.append(self._kpi_grid(cards))

        # SCR Bullets from key findings
        parts.append(self._scr_bullets())

        # Summary prose
        if text:
            parts.append('<div class="prose">')
            for para in text.strip().split("\n\n"):
                para = para.strip()
                if para:
                    parts.append(f"<p>{self._esc(para)}</p>")
            parts.append("</div>")

        parts.append(self._section_close())
        return "\n".join(parts)

    def _hero_verdict(self, summary: str) -> str:
        """Hero Verdict box with auto-grading."""
        grade, color = self._grade_model()
        if grade == "\u2014":
            return ""

        # Build verdict message
        message = self._extract_first_sentence(summary) if summary else ""
        if not message:
            best_model = (self.model_data.get("best_estimator")
                          or self.model_data.get("best_model", ""))
            metric_name = self.problem_def.get("evaluation_metric", "")
            metrics = self.model_data.get("metrics", {})
            val = None
            for k, v in metrics.items():
                if k.lower() == metric_name.lower() and isinstance(v, (int, float)):
                    val = v
                    break
            if best_model and val is not None:
                display_name = METRIC_DISPLAY.get(metric_name.lower(), metric_name.upper())
                display_val = self._format_kpi_value(metric_name, val)
                message = f"{best_model} \ubaa8\ub378\uc774 {display_name} = {display_val}\uc758 \uc131\ub2a5\uc744 \ub2ec\uc131\ud588\uc2b5\ub2c8\ub2e4."
            else:
                return ""

        return f"""<div class="hero-verdict">
            <div class="hero-verdict-icon">{CHECK_SVG}</div>
            <div class="hero-verdict-text">
                <div class="hero-verdict-label">Analysis Verdict</div>
                <div class="hero-verdict-message">{self._esc(message)}</div>
            </div>
            <div class="hero-verdict-grade">
                <div class="hero-verdict-grade-value" style="color: {color}">{self._esc(grade)}</div>
                <div class="hero-verdict-grade-label">Model Grade</div>
            </div>
        </div>"""

    def _scr_bullets(self) -> str:
        """SCR (Situation-Complication-Resolution) bullets from key findings."""
        key_findings = self.insights.get("key_findings", [])
        if len(key_findings) < 3:
            return ""

        scr_labels = ["Situation", "Complication", "Resolution"]
        items = []
        for i, label in enumerate(scr_labels):
            if i < len(key_findings):
                items.append(f"""<li class="scr-item">
                    <div class="scr-marker"></div>
                    <div class="scr-text"><strong>{label}:</strong> {self._esc(key_findings[i])}</div>
                </li>""")

        if not items:
            return ""
        return f'<ul class="scr-list">{"".join(items)}</ul>'

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

    # ── Section 05: Methodology (NEW) ────────────────────────────────

    def _methodology_section(self) -> str:
        parts = [self._section_header(5, "Methodology")]

        # Validation strategy description
        n_trials = self.model_data.get("n_trials") or self.model_data.get("num_trials", "")
        validation = "Holdout 80:20"
        validation_desc = "\ub370\uc774\ud130\ub97c 80:20\uc73c\ub85c \ubd84\ub9ac\ud558\uc5ec \ubaa8\ub378\uc744 \ud559\uc2b5\ud558\uace0 \ud3c9\uac00\ud569\ub2c8\ub2e4."

        # Method cards
        parts.append(f"""<div class="method-grid">
            <div class="method-card">
                <div class="method-card-label">AutoML Framework</div>
                <div class="method-card-value">FLAML</div>
                <div class="method-card-desc">Fast Lightweight AutoML. Cost-effective hyperparameter optimization with early stopping.</div>
            </div>
            <div class="method-card">
                <div class="method-card-label">Validation Strategy</div>
                <div class="method-card-value">{self._esc(validation)}</div>
                <div class="method-card-desc">{self._esc(validation_desc)}</div>
            </div>
            <div class="method-card">
                <div class="method-card-label">Explainability</div>
                <div class="method-card-value">SHAP</div>
                <div class="method-card-desc">SHapley Additive exPlanations. \uac01 \ubcc0\uc218\uc758 \uac1c\ubcc4 \uc608\uce21 \uae30\uc5ec\ub3c4\ub97c \uc815\ub7c9\uc801\uc73c\ub85c \ubd84\ud574.</div>
            </div>
        </div>""")

        # Prose: Search Space, Preprocessing, Reproducibility
        recommended = self.research.get("recommended_models", [])
        search_models = ", ".join(recommended[:5]) if recommended else "LightGBM, XGBoost, RandomForest"
        trials_text = f", \ucd1d {n_trials}\ud68c \uc2dc\ub3c4(trial) \ud6c4 \ucd5c\uc801 \ubaa8\ub378\uc744 \uc120\uc815\ud588\uc2b5\ub2c8\ub2e4" if n_trials else "\ub97c \ud0d0\uc0c9\ud588\uc2b5\ub2c8\ub2e4"

        prose_parts = [
            f"<p><strong>Search Space:</strong> \uc120\ud589\uc5f0\uad6c \uacb0\uacfc\ub97c \ubc18\uc601\ud558\uc5ec {self._esc(search_models)} \ubaa8\ub378\uc744 \ud0d0\uc0c9 \ub300\uc0c1\uc73c\ub85c \uc124\uc815\ud588\uc2b5\ub2c8\ub2e4. FLAML\uc774 \uac01 \ubaa8\ub378\uc758 \ud558\uc774\ud37c\ud30c\ub77c\ubbf8\ud130\ub97c \uc790\ub3d9 \ucd5c\uc801\ud654\ud558\uba70{self._esc(trials_text)}.</p>",
        ]

        if self.preprocessing_log:
            n_steps = len(self.preprocessing_log)
            prose_parts.append(
                f"<p><strong>Preprocessing Pipeline:</strong> {n_steps}\ub2e8\uacc4 \uc790\ub3d9 \uc804\ucc98\ub9ac\ub97c \uc801\uc6a9\ud588\uc2b5\ub2c8\ub2e4. "
                "\uc804\ucc98\ub9ac \ud30c\uc774\ud504\ub77c\uc778\uc740 \ud559\uc2b5/\ucd94\ub860 \uc2dc \ub3d9\uc77c\ud558\uac8c \uc801\uc6a9\ub429\ub2c8\ub2e4.</p>"
            )

        prose_parts.append(
            "<p><strong>Reproducibility:</strong> \ubaa8\ub4e0 \uc2e4\ud5d8\uc740 MLflow\ub85c \ucd94\uc801\ub418\uba70, \ubaa8\ub378 \ubc14\uc774\ub108\ub9ac, \uc804\ucc98\ub9ac \ud30c\uc774\ud504\ub77c\uc778, "
            "\ud558\uc774\ud37c\ud30c\ub77c\ubbf8\ud130\uac00 \uc544\ud2f0\ud329\ud2b8\ub85c \uc800\uc7a5\ub429\ub2c8\ub2e4.</p>"
        )

        parts.append(f'<div class="prose">{"".join(prose_parts)}</div>')

        parts.append(self._section_close())
        return "\n".join(parts)

    # ── Section 06: Modeling Results ──────────────────────────────────

    def _modeling_results_section(self) -> str:
        parts = [self._section_header(6, "Modeling Results")]

        best_model = (self.model_data.get("best_estimator")
                      or self.model_data.get("best_model", "N/A"))
        metrics = self.model_data.get("metrics", {})
        training_time = self.model_data.get("training_time")
        n_trials = self.model_data.get("n_trials") or self.model_data.get("num_trials")

        # Best model callout with training details
        detail_parts = [f"Best Model: {best_model}"]
        if training_time:
            t = f"{training_time:.0f}\ucd08" if isinstance(training_time, (int, float)) else str(training_time)
            detail_parts.append(t)
        if n_trials:
            detail_parts.append(f"{n_trials} trials evaluated")
        parts.append(self._callout(" \u2014 ".join(detail_parts), "success", "AutoML Result"))

        # CSS bar chart for metrics (0-1 range metrics only)
        bar_chart = self._model_metrics_bar_chart(metrics)
        if bar_chart:
            parts.append(bar_chart)

        # Enhanced metrics table
        if metrics:
            primary_metric = self.problem_def.get("evaluation_metric", "").lower()
            rows_html = []
            for key, value in metrics.items():
                if not isinstance(value, (int, float)):
                    continue
                is_champion = key.lower() == primary_metric
                display_name = METRIC_DISPLAY.get(key.lower(), key.upper().replace("_", " "))
                formatted = self._format_kpi_value(key, value)
                champion_cls = ' class="champion"' if is_champion else ''
                indicator = '<span class="indicator blue"></span>' if is_champion else ''
                rows_html.append(
                    f'<tr{champion_cls}>'
                    f'<td>{indicator}{self._esc(display_name)}</td>'
                    f'<td class="num">{self._esc(formatted)}</td>'
                    f'</tr>'
                )

            if rows_html:
                parts.append(
                    '<table class="data-table">'
                    '<thead><tr><th>Metric</th><th class="num">Score</th></tr></thead>'
                    f'<tbody>{"".join(rows_html)}</tbody>'
                    '</table>'
                )

        parts.append(self._section_close())
        return "\n".join(parts)

    def _model_metrics_bar_chart(self, metrics: Dict[str, Any]) -> str:
        """CSS bar chart for model metrics (only 0-1 range metrics)."""
        if not metrics:
            return ""

        bar_metrics = []
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                width = self._metric_to_bar_width(key, value)
                if width > 0:
                    bar_metrics.append((key, value, width))

        if not bar_metrics:
            return ""

        primary_metric = self.problem_def.get("evaluation_metric", "").lower()
        rows = []
        for i, (key, value, width) in enumerate(bar_metrics):
            rank = min(i + 1, 4)
            is_primary = key.lower() == primary_metric
            label_cls = " champion-label" if is_primary else ""
            score_cls = " champion-score" if is_primary else ""
            display_name = METRIC_DISPLAY.get(key.lower(), key.upper().replace("_", " "))
            display_val = self._format_kpi_value(key, value)

            rows.append(
                f'<div class="model-bar-row">'
                f'<span class="model-bar-name{label_cls}">{self._esc(display_name)}</span>'
                f'<div class="model-bar-track">'
                f'<div class="model-bar-fill rank-{rank}" style="width: {width:.0f}%"></div>'
                f'</div>'
                f'<span class="model-bar-score{score_cls}">{self._esc(display_val)}</span>'
                f'</div>'
            )

        if not rows:
            return ""

        best_model = (self.model_data.get("best_estimator")
                      or self.model_data.get("best_model", "Model"))
        return (
            '<div class="figure">'
            f'<div class="figure-caption">{self._esc(best_model)} Performance Metrics</div>'
            '<div class="figure-frame">'
            f'<div class="model-compare">{"".join(rows)}</div>'
            f'<div class="model-compare-caption">{self._esc(best_model)} champion model performance visualization</div>'
            '</div></div>'
        )

    # ── Section 07: SHAP Analysis ────────────────────────────────────

    def _shap_section(self, images: List[Dict], feature_importance: Optional[List[Dict]] = None) -> str:
        feature_importance = feature_importance or []
        parts = [self._section_header(7, "Feature Importance (SHAP)")]

        # Pull Quote: top-3 feature contribution
        if self._fi_pct and len(self._fi_pct) >= 3:
            top3_sum = sum(item["pct"] for item in self._fi_pct[:3])
            top3_names = ", ".join(item["feature"] for item in self._fi_pct[:3])
            rest_sum = 100 - top3_sum
            parts.append(self._pull_quote(
                f"{top3_sum:.1f}%",
                f"{top3_names} \u2014 \uc0c1\uc704 3\uac1c \ubcc0\uc218\uac00 \uc804\uccb4 \uc608\uce21\ub825\uc758 {top3_sum:.1f}%\ub97c \ucc28\uc9c0",
                f"\ub098\uba38\uc9c0 \ubcc0\uc218\ub4e4\uc740 \ud569\uc0b0 {rest_sum:.1f}%\uc758 \ubcf4\uc870\uc801 \uae30\uc5ec"
            ))

        # CSS SHAP bar chart
        shap_chart = self._shap_bar_chart()
        if shap_chart:
            parts.append(shap_chart)

        # SHAP images (base64 embedded)
        top_features = []
        if self._fi_pct:
            top_features = [f["feature"] for f in self._fi_pct[:3]]

        if images:
            for i, img in enumerate(images[:4], 1):
                filename = img.get("filename", "")
                label = filename.replace("_", " ").replace(".png", "").title()
                caption = f"Figure {i + 1}. {label}" if label else f"Figure {i + 1}. SHAP Analysis"
                parts.append(self._figure_with_interp(img["data_uri"], caption, filename, top_features))
        elif not shap_chart:
            parts.append(self._callout("SHAP analysis plots are not available for this session.", "info"))

        parts.append(self._section_close())
        return "\n".join(parts)

    def _shap_bar_chart(self) -> str:
        """CSS bar chart from feature importance data."""
        if not self._fi_pct:
            return ""

        max_pct = self._fi_pct[0]["pct"] if self._fi_pct else 1
        rows = []
        for i, item in enumerate(self._fi_pct[:8]):
            rank = min(i + 1, 6)
            width = (item["pct"] / max_pct) * 100 if max_pct > 0 else 0
            rows.append(
                f'<div class="shap-bar-row">'
                f'<span class="shap-bar-label">{self._esc(item["feature"])}</span>'
                f'<div class="shap-bar-track">'
                f'<div class="shap-bar-fill rank-{rank}" style="width: {width:.1f}%"></div>'
                f'</div>'
                f'<span class="shap-bar-value">{item["pct"]:.1f}%</span>'
                f'</div>'
            )

        if not rows:
            return ""

        top_features_text = ""
        if len(self._fi_pct) >= 3:
            top_features_text = (
                "<br><strong>Top 3:</strong> "
                + ", ".join(f'{f["feature"]} ({f["pct"]:.1f}%)' for f in self._fi_pct[:3])
            )

        return (
            '<div class="figure">'
            '<div class="figure-caption">Feature Importance (Mean |SHAP Value|)</div>'
            '<div class="figure-frame">'
            f'<div class="shap-chart">{"".join(rows)}</div>'
            '</div>'
            '<div class="figure-interp">'
            '\uac01 \ubcc0\uc218\uac00 \ubaa8\ub378 \uc608\uce21\uc5d0 \uae30\uc5ec\ud558\ub294 \ud3c9\uade0 \uc601\ud5a5\ub825(Mean |SHAP Value|)\uc744 \ubcf4\uc5ec\uc90d\ub2c8\ub2e4. '
            '\ub9c9\ub300\uac00 \uae38\uc218\ub85d \ud574\ub2f9 \ubcc0\uc218\uac00 \uc608\uce21\uc5d0 \ub354 \ud070 \uc601\ud5a5\uc744 \ubbf8\uce69\ub2c8\ub2e4.'
            f'{top_features_text}'
            '</div></div>'
        )

    def _figure_with_interp(self, img_uri: str, caption: str, filename: str, top_features: List[str]) -> str:
        """Figure with auto-interpretation text."""
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
                top_html = f'<div class="top-features">\uc0c1\uc704 \ubcc0\uc218: {", ".join(self._esc(f) for f in top_features)}</div>'
            interp_html = f'<div class="figure-interp">{self._esc(interp)}{top_html}</div>'

        return f"""<div class="figure">
            <div class="figure-caption">{self._esc(caption)}</div>
            <div class="figure-frame"><img src="{img_uri}" alt="{self._esc(caption)}"></div>
            {interp_html}
        </div>"""

    # ── Section 08: Key Insights ─────────────────────────────────────

    def _key_insights_section(self) -> str:
        parts = [self._section_header(8, "Key Insights")]

        has_content = False

        # Key findings
        key_findings = self.insights.get("key_findings", [])
        if key_findings:
            parts.append('<div class="prose"><ol>')
            for finding in key_findings:
                parts.append(f"<li>{self._esc(finding)}</li>")
            parts.append("</ol></div>")
            has_content = True

        # Pull Quote: primary metric as hero stat
        metric_name = self.problem_def.get("evaluation_metric", "").lower()
        metrics = self.model_data.get("metrics", {})
        for k, v in metrics.items():
            if k.lower() == metric_name and isinstance(v, (int, float)):
                display_name = METRIC_DISPLAY.get(k.lower(), k.upper())
                display_val = self._format_kpi_value(k, v)
                parts.append(self._pull_quote(
                    display_val,
                    f"{display_name} \ub2ec\uc131",
                    "\ubaa8\ub378 \uc608\uce21 \uc815\ud655\ub3c4 \uc9c0\ud45c"
                ))
                has_content = True
                break

        # Business insights
        business_insights = self.insights.get("business_insights", [])
        if business_insights:
            parts.append('<div class="prose"><p><strong>Business Insights:</strong></p><ul>')
            for insight in business_insights:
                parts.append(f"<li>{self._esc(insight)}</li>")
            parts.append("</ul></div>")
            has_content = True

        # Error analysis
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

    # ── Section 09: Recommendations ──────────────────────────────────

    def _recommendations_section(self) -> str:
        parts = [self._section_header(9, "Recommendations")]

        recommendations = self.insights.get("recommendations", [])
        if recommendations:
            for i, rec in enumerate(recommendations):
                priority = self._infer_priority(rec, i)
                num = f"{i + 1:02d}"
                impact_html = self._extract_impact_effort(rec, priority)

                parts.append(f"""<div class="rec-card">
                <div class="rec-left">
                    <span class="rec-priority {priority}">{priority.upper()}</span>
                    <span class="rec-number">{num}</span>
                </div>
                <div class="rec-body">
                    <div class="rec-text">{self._esc(rec)}</div>
                    {impact_html}
                </div>
            </div>""")
        else:
            parts.append('<div class="prose"><p>No specific recommendations at this time.</p></div>')

        parts.append(self._section_close())
        return "\n".join(parts)

    def _extract_impact_effort(self, text: str, priority: str) -> str:
        """Extract impact/effort from recommendation text or infer from priority."""
        # Try to find percentage for impact
        pct_match = re.search(r'(\d+[~\-]?\d*%[p]?)', text)
        impact = pct_match.group(1) if pct_match else {"high": "High", "medium": "Medium", "low": "Low"}.get(priority, "Medium")

        # Try to find time period for effort
        time_match = re.search(r'(\d+[~\-]?\d*\s*(?:\uc8fc|\uac1c\uc6d4|\uc77c|week|month|day))', text)
        effort = time_match.group(1) if time_match else {"high": "Medium", "medium": "Medium", "low": "Low"}.get(priority, "Medium")

        return (
            f'<div class="rec-impact">'
            f'<span><span class="rec-impact-tag">Impact:</span> {self._esc(str(impact))}</span>'
            f'<span><span class="rec-impact-tag">Effort:</span> {self._esc(str(effort))}</span>'
            f'</div>'
        )

    # ── Section 10: Appendix ─────────────────────────────────────────

    def _appendix_section(self) -> str:
        parts = [self._section_header(10, "Appendix")]

        # 1. Research Comparison (open by default)
        research_table = self._appendix_research_comparison()
        if research_table:
            parts.append(f"""<details class="appendix-details" open>
                <summary>Research Comparison</summary>
                <div class="appendix-content">{research_table}</div>
            </details>""")

        # 2. Artifacts & Reproducibility (collapsed)
        parts.append("""<details class="appendix-details">
                <summary>Artifacts &amp; Reproducibility</summary>
                <div class="appendix-content">
                    <div class="prose">
                        <ul>
                            <li>SHAP analysis plots (bar, summary, waterfall)</li>
                            <li>Feature importance data (JSON)</li>
                            <li>Model performance visualizations</li>
                            <li>Trained model binary</li>
                            <li>MLflow experiment tracking (run ID linked)</li>
                        </ul>
                        <p><strong>Reproducibility:</strong> All analysis can be reproduced using the saved model and data artifacts.</p>
                    </div>
                </div>
            </details>""")

        # 3. Glossary (collapsed) — auto-generated from used metrics
        glossary = self._appendix_glossary()
        if glossary:
            parts.append(f"""<details class="appendix-details">
                <summary>Glossary</summary>
                <div class="appendix-content">{glossary}</div>
            </details>""")

        parts.append(self._section_close())
        return "\n".join(parts)

    def _appendix_research_comparison(self) -> str:
        """Research comparison table with indicator dots and champion row."""
        best_model = (self.model_data.get("best_estimator")
                      or self.model_data.get("best_model", ""))

        papers = self.research.get("papers", [])
        kaggle = self.research.get("kaggle_solutions") or self.research.get("kaggle", {})
        deep = self.research.get("deep_research", {})

        rows = []
        if papers:
            rows.append(
                f'<tr><td>HuggingFace Papers</td>'
                f'<td>{len(papers)} papers reviewed</td>'
                f'<td><span class="indicator green"></span>High</td></tr>'
            )
        if kaggle and kaggle.get("techniques"):
            techs = ", ".join(kaggle["techniques"][:5])
            rows.append(
                f'<tr><td>Kaggle Solutions</td>'
                f'<td>{self._esc(techs)}</td>'
                f'<td><span class="indicator green"></span>High</td></tr>'
            )
        if deep and (deep.get("summary") or deep.get("key_findings")):
            n_findings = len(deep.get("key_findings", []))
            detail = f"{n_findings} key findings" if n_findings else "Summary available"
            rows.append(
                f'<tr><td>Deep Research</td>'
                f'<td>{self._esc(detail)}</td>'
                f'<td><span class="indicator yellow"></span>Medium</td></tr>'
            )
        if best_model:
            rows.append(
                f'<tr class="champion"><td>Selected Model</td>'
                f'<td><span class="indicator blue"></span>{self._esc(best_model)}</td>'
                f'<td><span class="indicator blue"></span>Selected</td></tr>'
            )

        if not rows:
            return ""

        return (
            '<table class="data-table">'
            '<thead><tr><th>Source</th><th>Details</th><th>Relevance</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            '</table>'
        )

    def _appendix_glossary(self) -> str:
        """Auto-generate glossary from used metrics."""
        metrics = self.model_data.get("metrics", {})
        if not metrics:
            return ""

        rows = []
        for key in metrics:
            k = key.lower()
            desc = METRIC_DESCRIPTIONS.get(k)
            if desc:
                display = METRIC_DISPLAY.get(k, key.upper())
                rows.append(f"<tr><td>{self._esc(display)}</td><td>{self._esc(desc)}</td></tr>")

        # Always add SHAP
        rows.append("<tr><td>SHAP</td><td>SHapley Additive exPlanations. \uac8c\uc784 \uc774\ub860 \uae30\ubc18 \ubcc0\uc218 \uae30\uc5ec\ub3c4 \ubd84\ud574 \uae30\ubc95</td></tr>")

        if not rows:
            return ""

        return (
            '<table class="dotted-table">'
            f'{"".join(rows)}'
            '</table>'
        )

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
            <div class="footer-left">
                <span class="footer-brand">DA SYSTEM</span>
                <span class="footer-divider"></span>
                <span class="footer-disclaimer">This document is confidential and intended solely for the use of the individual or entity to whom it is addressed.</span>
            </div>
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

    def _grade_model(self) -> Tuple[str, str]:
        """Auto-grade model based on primary metric. Returns (grade, color)."""
        metric_name = self.problem_def.get("evaluation_metric", "").lower()
        metrics = self.model_data.get("metrics", {})

        # Find primary metric value
        value = None
        for k, v in metrics.items():
            if k.lower() == metric_name and isinstance(v, (int, float)):
                value = v
                break

        # Fallback: use first numeric metric
        if value is None:
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    value = v
                    metric_name = k.lower()
                    break

        if value is None:
            return ("\u2014", "var(--muted)")

        # Choose threshold direction
        if metric_name in LOWER_IS_BETTER:
            v = value / 100 if value > 1 else value
            for threshold, grade, color in GRADE_THRESHOLDS_LOWER:
                if v <= threshold:
                    return (grade, color)
        else:
            for threshold, grade, color in GRADE_THRESHOLDS_HIGHER:
                if value >= threshold:
                    return (grade, color)

        return ("D", "var(--danger)")

    @staticmethod
    def _compute_shap_percentages(feature_importance: List[Dict]) -> List[Dict]:
        """Normalize feature importance values to percentages."""
        if not feature_importance:
            return []

        sorted_fi = sorted(
            feature_importance,
            key=lambda x: abs(x.get("importance", 0)),
            reverse=True,
        )
        total = sum(abs(f.get("importance", 0)) for f in sorted_fi)
        if total == 0:
            return []

        result = []
        for f in sorted_fi[:8]:
            name = f.get("feature") or f.get("name", "Unknown")
            importance = abs(f.get("importance", 0))
            pct = (importance / total) * 100
            result.append({"feature": name, "importance": importance, "pct": pct})
        return result

    def _metric_to_bar_width(self, metric_name: str, value: float) -> float:
        """Convert metric value to CSS bar width (5-100%). Returns 0 if not bar-friendly."""
        name = metric_name.lower()

        if name in LOWER_IS_BETTER:
            if name == "mape":
                v = value / 100 if value > 1 else value
                return max(5, min(100, (1 - v) * 100))
            # RMSE, MAE, MSE — unbounded, skip bar
            return 0

        # Higher is better (0-1 range)
        if 0 <= value <= 1:
            return max(5, value * 100)
        return 0

    def _format_kpi_value(self, name: str, value: float) -> str:
        """Format metric value for display in KPI cards."""
        n = name.lower()
        if n == "mape":
            if value < 1:
                return f"{value * 100:.1f}%"
            return f"{value:.1f}%"
        if n in ("accuracy", "f1", "precision", "recall"):
            return f"{value:.1%}" if value <= 1 else f"{value:.1f}%"
        if n in ("r2", "roc_auc"):
            return f"{value:.2f}" if value <= 1 else f"{value:.1f}"
        if value < 10:
            return f"{value:.2f}"
        if value < 1000:
            return f"{value:.1f}"
        return f"{value:,.0f}"

    def _metric_color_class(self, name: str, value: float) -> str:
        """CSS color class for KPI value text."""
        n = name.lower()
        if n in LOWER_IS_BETTER:
            v = value / 100 if value > 1 else value
            if v < 0.05:
                return "success"
            if v < 0.15:
                return "accent"
            return "warning"
        # Higher is better
        if value >= 0.9:
            return "success"
        if value >= 0.7:
            return "accent"
        return "warning"

    def _kpi_card_class(self, name: str, value: float) -> str:
        """Card-level class for ::before color strip."""
        n = name.lower()
        if n in LOWER_IS_BETTER:
            v = value / 100 if value > 1 else value
            if v < 0.05:
                return "success"
            if v < 0.15:
                return "accent"
            return "warning"
        if value >= 0.9:
            return "success"
        if value >= 0.7:
            return "accent"
        return "warning"

    @staticmethod
    def _extract_first_sentence(text: str) -> str:
        """Extract first meaningful sentence from text."""
        if not text:
            return ""
        text = text.strip()
        for i, ch in enumerate(text):
            if ch == "." and i > 10:
                next_ch = text[i + 1] if i + 1 < len(text) else " "
                if next_ch in (" ", "\n", "\r", "\t") or i + 1 >= len(text):
                    return text[: i + 1].strip()
        return text[:150].strip() + ("..." if len(text) > 150 else "")
