"""
DataIntelligence — 데이터 심층 분석 레이어
도메인 감지, 타겟 후보 점수화, 불균형/이상치/피처 품질 분석, 전처리 권장사항
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# 도메인별 키워드 사전
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "finance": ["price", "revenue", "margin", "ticker", "stock", "profit", "interest", "loan", "credit", "debt", "balance", "payment", "transaction", "forex", "dividend", "portfolio"],
    "healthcare": ["patient", "diagnosis", "blood", "bmi", "heart", "disease", "medical", "clinical", "symptom", "treatment", "hospital", "drug", "dosage", "mortality"],
    "marketing": ["campaign", "click", "conversion", "churn", "customer", "subscriber", "retention", "segment", "engagement", "impression", "bounce", "ctr", "ltv", "acquisition"],
    "energy": ["kwh", "voltage", "consumption", "tariff", "energy", "power", "solar", "wind", "grid", "emission", "carbon", "electricity", "watt", "fuel"],
    "retail": ["product", "quantity", "order", "sku", "inventory", "store", "purchase", "basket", "category", "brand", "discount", "return", "shipping"],
    "hr": ["employee", "salary", "tenure", "department", "attrition", "performance", "promotion", "hire", "resign", "satisfaction", "absence"],
    "manufacturing": ["defect", "yield", "machine", "sensor", "temperature", "pressure", "vibration", "cycle", "downtime", "quality", "batch"],
    "insurance": ["claim", "premium", "policy", "coverage", "deductible", "underwriting", "risk", "loss", "insured"],
    "telecom": ["call", "data_usage", "roaming", "plan", "network", "signal", "bandwidth", "subscriber", "churn", "contract"],
    "real_estate": ["sqft", "bedroom", "bathroom", "price", "rent", "property", "location", "neighborhood", "listing", "mortgage"],
}

# 타겟 후보 이름 점수 (일반 + 도메인 특화)
TARGET_NAME_SCORES: Dict[str, float] = {
    "target": 1.0, "label": 0.95, "y": 0.9, "outcome": 0.85,
    "class": 0.8, "flag": 0.75, "status": 0.7,
    "is_": 0.65, "has_": 0.6,
    # 분류 도메인 특화
    "churn": 0.9, "default": 0.85, "fraud": 0.9, "diagnosis": 0.85,
    "survived": 0.9, "approved": 0.85, "converted": 0.85,
    "attrition": 0.85, "defect": 0.8, "spam": 0.85,
    "sentiment": 0.8, "risk": 0.75, "result": 0.7,
    "response": 0.65, "clicked": 0.8, "purchased": 0.8,
    # 회귀 도메인 특화
    "price": 0.85, "saleprice": 0.9, "cost": 0.8, "amount": 0.8,
    "revenue": 0.85, "salary": 0.85, "income": 0.8, "profit": 0.8,
    "sales": 0.8, "median_house_value": 0.9, "medv": 0.9,
    "consumption": 0.75, "demand": 0.75, "quantity": 0.7,
}

# 서브스트링 매칭 시 오탐 방지 — 이 패턴은 정확 매칭만 허용
# 예: "class"가 "MSSubClass"에 매칭되는 것을 방지
EXACT_MATCH_ONLY: set = {"class", "y", "flag", "status", "risk", "result", "response"}

# 도메인별 타겟 힌트 — 도메인이 감지되면 해당 키워드에 보너스 부여
DOMAIN_TARGET_HINTS: Dict[str, List[str]] = {
    "real_estate": ["price", "saleprice", "rent", "value", "medv"],
    "finance": ["price", "revenue", "profit", "return", "close", "amount"],
    "hr": ["attrition", "salary", "performance", "satisfaction"],
    "healthcare": ["diagnosis", "disease", "mortality", "survived"],
    "marketing": ["churn", "conversion", "ltv", "revenue"],
    "energy": ["consumption", "price", "demand"],
    "retail": ["sales", "revenue", "quantity"],
    "insurance": ["claim", "premium", "risk"],
    "telecom": ["churn", "data_usage"],
    "manufacturing": ["defect", "yield", "quality"],
}


class DataIntelligence:
    """데이터 심층 분석 — 모든 하위 에이전트의 기반 정보 제공"""

    def analyze(self, df: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        데이터에 대한 종합 지능 분석 수행.

        Args:
            df: 원본 DataFrame
            profile: DataProfiler.profile() 결과

        Returns:
            domain, target_candidates, class_imbalance, outlier_report,
            feature_quality, preprocessing_recommendations, data_warnings
        """
        logger.info("data_intelligence_started", rows=len(df), cols=len(df.columns))

        domain = self._detect_domain(df)
        target_candidates = self._score_target_candidates(df, domain)
        class_imbalance = self._detect_imbalance(df, target_candidates)
        outlier_report = self._detect_outliers(df)
        feature_quality = self._assess_feature_quality(df, profile)
        recommendations = self._recommend_preprocessing(
            class_imbalance, outlier_report, feature_quality, df
        )
        warnings = self._collect_warnings(
            class_imbalance, outlier_report, feature_quality, df
        )

        logger.info("data_intelligence_completed",
                     domain=domain.get("domain"),
                     target_top=target_candidates[0]["column"] if target_candidates else None)

        return {
            "domain": domain,
            "target_candidates": target_candidates,
            "class_imbalance": class_imbalance,
            "outlier_report": outlier_report,
            "feature_quality": feature_quality,
            "preprocessing_recommendations": recommendations,
            "data_warnings": warnings,
        }

    # ── Domain Detection ──────────────────────────────────────────

    def _detect_domain(self, df: pd.DataFrame) -> Dict[str, Any]:
        col_names_lower = [c.lower() for c in df.columns]

        scores: Dict[str, float] = {}
        evidence: Dict[str, List[str]] = {}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            hits = []
            for kw in keywords:
                for col_lower, col_orig in zip(col_names_lower, df.columns):
                    if kw in col_lower:
                        hits.append(f"컬럼 '{col_orig}'")
                        break
            if hits:
                scores[domain] = len(hits) / len(keywords)
                evidence[domain] = hits

        if not scores:
            return {"domain": "general", "confidence": 0.0, "evidence": []}

        best_domain = max(scores, key=scores.get)
        return {
            "domain": best_domain,
            "confidence": round(min(scores[best_domain] * 2, 1.0), 2),
            "evidence": evidence[best_domain][:5],
        }

    # ── Target Candidate Scoring ──────────────────────────────────

    def _score_target_candidates(
        self, df: pd.DataFrame, domain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        candidates = []
        n_rows = len(df)

        detected_domain = domain.get("domain", "general")
        domain_hints = DOMAIN_TARGET_HINTS.get(detected_domain, [])

        for idx, col in enumerate(df.columns):
            score = 0.0
            reasons = []
            col_lower = col.lower()

            # 1) 이름 매칭 — EXACT_MATCH_ONLY 패턴은 정확 매칭만 허용
            for name_pattern, name_score in TARGET_NAME_SCORES.items():
                if name_pattern.endswith("_"):
                    if col_lower.startswith(name_pattern):
                        score += name_score * 0.4
                        reasons.append(f"이름 패턴 '{name_pattern}' 매칭")
                        break
                elif name_pattern == col_lower:
                    # 정확 매칭 → 항상 OK
                    score += name_score * 0.4
                    reasons.append(f"이름 '{name_pattern}' 정확 매칭")
                    break
                elif name_pattern not in EXACT_MATCH_ONLY and name_pattern in col_lower:
                    # 서브스트링 매칭 → EXACT_MATCH_ONLY가 아닌 경우만
                    score += name_score * 0.4
                    reasons.append(f"이름 '{name_pattern}' 매칭")
                    break

            # 1b) 도메인→타겟 힌트 보너스
            if domain_hints:
                for hint in domain_hints:
                    if hint in col_lower:
                        score += 0.25
                        reasons.append(f"도메인 '{detected_domain}' 힌트 매칭")
                        break

            # 2) 카디널리티 — 분류·회귀 모두 인식
            nunique = df[col].nunique()
            is_numeric = pd.api.types.is_numeric_dtype(df[col])
            if nunique == 2:
                score += 0.3
                reasons.append("이진 컬럼")
            elif 3 <= nunique <= 10:
                score += 0.15
                reasons.append(f"저카디널리티 ({nunique})")
            elif is_numeric and nunique > 20:
                # 연속형 수치 — 회귀 타겟 후보
                score += 0.15
                reasons.append(f"연속형 수치 ({nunique} 고유값)")
            elif not is_numeric and nunique > n_rows * 0.5:
                score -= 0.3
                reasons.append("고유값 과다 (ID 의심)")

            # 3) 위치 보너스 — 마지막 컬럼
            if idx == len(df.columns) - 1:
                score += 0.1
                reasons.append("마지막 컬럼")

            # 4) 타입 보너스
            dtype = df[col].dtype
            if dtype == "object" or dtype == "bool":
                if nunique <= 20:
                    score += 0.1
                    reasons.append("범주형")
            elif dtype.name == "category":
                score += 0.1

            # 결측치 많은 컬럼은 감점
            missing_pct = df[col].isnull().mean()
            if missing_pct > 0.3:
                score -= 0.2
                reasons.append(f"결측 {missing_pct:.0%}")

            candidates.append({
                "column": col,
                "score": round(score, 3),
                "reasons": reasons,
                "nunique": int(nunique),
                "dtype": str(dtype),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:10]

    # ── Problem Type Inference ────────────────────────────────────

    @staticmethod
    def infer_problem_type(series: pd.Series) -> str:
        """
        시리즈의 실제 특성으로 problem_type을 독립 판정.
        TypeDetector의 _is_continuous_integers 의존 없이 판정.

        Returns: "binary_classification", "multiclass_classification", "regression"
        """
        # object/category/bool → 분류
        if series.dtype.name in ("object", "category", "bool"):
            if series.nunique() == 2:
                return "binary_classification"
            return "multiclass_classification"

        # 수치형
        n_unique = series.nunique()

        # 고유값 2개 → 이진 분류
        if n_unique == 2:
            return "binary_classification"

        # 고유값 10개 이하 → 분류
        if n_unique <= 10:
            if n_unique == 2:
                return "binary_classification"
            return "multiclass_classification"

        # 고유값 비율 2% 미만 → 인코딩 라벨 의심 → 분류
        n_samples = len(series.dropna())
        if n_samples > 0 and (n_unique / n_samples) < 0.02:
            return "multiclass_classification"

        # 나머지 → 회귀
        return "regression"

    # ── Class Imbalance ───────────────────────────────────────────

    def _detect_imbalance(
        self, df: pd.DataFrame, target_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not target_candidates:
            return {"detected": False}

        top = target_candidates[0]
        col = top["column"]

        if top["nunique"] > 20 or col not in df.columns:
            return {"detected": False, "reason": "연속형 또는 고카디널리티"}

        vc = df[col].value_counts()
        if len(vc) < 2:
            return {"detected": False, "reason": "단일 클래스"}

        majority = int(vc.iloc[0])
        minority = int(vc.iloc[-1])
        ratio = round(majority / minority, 2) if minority > 0 else float("inf")
        minority_pct = round(minority / len(df) * 100, 1)

        if ratio <= 3:
            severity = "balanced"
        elif ratio <= 10:
            severity = "moderate"
        else:
            severity = "severe"

        return {
            "detected": severity != "balanced",
            "ratio": ratio,
            "severity": severity,
            "minority_class": str(vc.index[-1]),
            "majority_class": str(vc.index[0]),
            "minority_pct": minority_pct,
            "class_distribution": {str(k): int(v) for k, v in vc.items()},
        }

    # ── Outlier Detection ─────────────────────────────────────────

    def _detect_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        report: Dict[str, Any] = {}
        flagged_columns = []

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            if iqr == 0:
                continue

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = ((series < lower) | (series > upper)).sum()
            pct = round(outliers / len(series) * 100, 1)

            col_report = {
                "outlier_count": int(outliers),
                "outlier_pct": pct,
                "lower_bound": round(lower, 4),
                "upper_bound": round(upper, 4),
            }
            report[col] = col_report

            if pct > 5:
                flagged_columns.append(col)

        return {
            "columns": report,
            "flagged_columns": flagged_columns,
            "total_flagged": len(flagged_columns),
        }

    # ── Feature Quality ───────────────────────────────────────────

    def _assess_feature_quality(
        self, df: pd.DataFrame, profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        issues = []

        # 1) 근-제로-분산 컬럼
        near_zero_var = []
        for col in df.select_dtypes(include=[np.number]).columns:
            series = df[col].dropna()
            if len(series) > 0 and series.std() < 1e-8:
                near_zero_var.append(col)
        if near_zero_var:
            issues.append({"type": "near_zero_variance", "columns": near_zero_var})

        # 2) 고상관 쌍 (|r| > 0.95)
        high_corr = []
        correlations = profile.get("correlations", {})
        high_corr_list = correlations.get("high_correlations", [])
        for pair in high_corr_list:
            if abs(pair.get("correlation", 0)) > 0.95:
                high_corr.append({
                    "var1": pair["var1"],
                    "var2": pair["var2"],
                    "correlation": pair["correlation"],
                })
        if high_corr:
            issues.append({"type": "high_correlation", "pairs": high_corr})

        # 3) 결측 50%+ 컬럼
        high_missing = []
        for col in df.columns:
            pct = df[col].isnull().mean()
            if pct > 0.5:
                high_missing.append({"column": col, "missing_pct": round(pct * 100, 1)})
        if high_missing:
            issues.append({"type": "high_missing", "columns": high_missing})

        # 4) 날짜 문자열 감지
        date_strings = []
        for col in df.select_dtypes(include=["object"]).columns:
            sample = df[col].dropna().head(20)
            if len(sample) == 0:
                continue
            date_like_count = 0
            for val in sample:
                val_str = str(val)
                if any(sep in val_str for sep in ["-", "/", ":"]) and any(c.isdigit() for c in val_str):
                    try:
                        pd.to_datetime(val_str)
                        date_like_count += 1
                    except (ValueError, TypeError):
                        pass
            if date_like_count > len(sample) * 0.5:
                date_strings.append(col)
        if date_strings:
            issues.append({"type": "date_strings", "columns": date_strings})

        return {"issues": issues, "total_issues": len(issues)}

    # ── Preprocessing Recommendations ─────────────────────────────

    def _recommend_preprocessing(
        self,
        imbalance: Dict[str, Any],
        outliers: Dict[str, Any],
        quality: Dict[str, Any],
        df: pd.DataFrame,
    ) -> List[str]:
        recs = []

        # 불균형
        if imbalance.get("detected"):
            ratio = imbalance.get("ratio", 1)
            severity = imbalance.get("severity", "balanced")
            if severity == "severe":
                recs.append(f"클래스 불균형 처리 필요 (비율 {ratio}:1) — sample_weight 또는 SMOTE 권장")
            elif severity == "moderate":
                recs.append(f"클래스 불균형 주의 (비율 {ratio}:1) — sample_weight 적용 검토")

        # 이상치
        for col in outliers.get("flagged_columns", []):
            col_data = outliers["columns"][col]
            recs.append(f"컬럼 '{col}'에서 이상치 클리핑 권장 ({col_data['outlier_pct']}%)")

        # 피처 품질
        for issue in quality.get("issues", []):
            if issue["type"] == "near_zero_variance":
                cols = issue["columns"]
                recs.append(f"근-제로-분산 컬럼 제거 권장: {', '.join(cols[:3])}")
            elif issue["type"] == "high_correlation":
                for p in issue["pairs"][:2]:
                    recs.append(f"고상관 쌍 제거 검토: {p['var1']} ↔ {p['var2']} (r={p['correlation']:.2f})")
            elif issue["type"] == "high_missing":
                cols = [c["column"] for c in issue["columns"][:3]]
                recs.append(f"결측 50%+ 컬럼 제거 검토: {', '.join(cols)}")
            elif issue["type"] == "date_strings":
                recs.append(f"날짜 문자열 → datetime 변환 권장: {', '.join(issue['columns'][:3])}")

        return recs[:10]

    # ── Warnings ──────────────────────────────────────────────────

    def _collect_warnings(
        self,
        imbalance: Dict[str, Any],
        outliers: Dict[str, Any],
        quality: Dict[str, Any],
        df: pd.DataFrame,
    ) -> List[str]:
        warnings = []

        if imbalance.get("severity") == "severe":
            warnings.append(
                f"심각한 클래스 불균형: 양성 클래스 {imbalance.get('minority_pct', 0)}% — "
                f"F1 또는 PR-AUC 메트릭 권장"
            )

        if outliers.get("total_flagged", 0) > 3:
            warnings.append(
                f"이상치가 {outliers['total_flagged']}개 컬럼에서 감지됨 — 데이터 품질 확인 필요"
            )

        total_missing = df.isnull().sum().sum()
        total_cells = df.shape[0] * df.shape[1]
        if total_cells > 0 and total_missing / total_cells > 0.1:
            warnings.append(
                f"전체 결측률 {total_missing / total_cells * 100:.1f}% — 결측 패턴 확인 필요"
            )

        if len(df) < 100:
            warnings.append("데이터 행 수가 100 미만 — 모델 일반화 성능에 제약 가능")

        for issue in quality.get("issues", []):
            if issue["type"] == "near_zero_variance":
                warnings.append(f"근-제로-분산 컬럼 {len(issue['columns'])}개 — 정보 없는 피처")

        return warnings[:8]
