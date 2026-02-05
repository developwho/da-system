"""Agent data contracts and normalization helpers."""
from typing import Any, Dict, List


def _dedupe_list(values: List[Any]) -> List[Any]:
    seen = set()
    deduped: List[Any] = []
    for value in values:
        if isinstance(value, (str, int, float, bool, tuple)):
            if value in seen:
                continue
            seen.add(value)
        deduped.append(value)
    return deduped


def empty_research_results() -> Dict[str, Any]:
    return {
        "papers": [],
        "kaggle_solutions": {},
        "deep_research": {},
        "summary": "",
        "summary_file": "",
        "techniques": [],
        "recommended_models": [],
        "key_insights": [],
    }


def normalize_problem_definition(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}

    normalized = dict(data)

    if "analysis_goal" not in normalized and "goal" in normalized:
        normalized["analysis_goal"] = normalized.get("goal")

    if "target_column" not in normalized:
        if "target_variable" in normalized:
            normalized["target_column"] = normalized.get("target_variable")
        elif "target" in normalized:
            normalized["target_column"] = normalized.get("target")

    if "evaluation_metric" not in normalized and "metric" in normalized:
        normalized["evaluation_metric"] = normalized.get("metric")

    return normalized


def normalize_research_results(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = empty_research_results()
    if not data:
        return normalized

    integrated = data.get("integrated_data")
    if isinstance(integrated, dict):
        if integrated.get("papers") is not None:
            normalized["papers"] = integrated.get("papers") or []
        kaggle = integrated.get("kaggle_solutions") or integrated.get("kaggle") or {}
        if kaggle is not None:
            normalized["kaggle_solutions"] = kaggle
        deep_research = integrated.get("deep_research") or {}
        if deep_research is not None:
            normalized["deep_research"] = deep_research
        normalized["techniques"] = integrated.get("techniques") or []
        normalized["recommended_models"] = integrated.get("recommended_models") or []
        normalized["key_insights"] = integrated.get("key_insights") or []

    if data.get("papers") is not None:
        normalized["papers"] = data.get("papers") or []

    if data.get("kaggle_solutions") is not None:
        normalized["kaggle_solutions"] = data.get("kaggle_solutions") or {}
    elif data.get("kaggle") is not None:
        normalized["kaggle_solutions"] = data.get("kaggle") or {}

    if data.get("deep_research") is not None:
        normalized["deep_research"] = data.get("deep_research") or {}

    if data.get("summary") is not None:
        normalized["summary"] = data.get("summary") or ""

    if data.get("summary_file") is not None:
        normalized["summary_file"] = data.get("summary_file") or ""

    papers_result = data.get("papers_result") or {}
    if not normalized["papers"] and isinstance(papers_result, dict):
        normalized["papers"] = papers_result.get("papers", []) or []
        if not normalized["summary"]:
            normalized["summary"] = papers_result.get("summary", "") or ""

    solutions_result = data.get("solutions_result") or {}
    if isinstance(solutions_result, dict):
        if not normalized["kaggle_solutions"]:
            normalized["kaggle_solutions"] = solutions_result.get("insight") or {}
        if not normalized["summary"]:
            normalized["summary"] = solutions_result.get("summary", "") or ""

    deep_result = data.get("deep_research_result") or {}
    if isinstance(deep_result, dict):
        if not normalized["deep_research"]:
            normalized["deep_research"] = deep_result.get("result") or {}

    if not normalized["recommended_models"]:
        deep_research = normalized.get("deep_research", {})
        if isinstance(deep_research, dict):
            normalized["recommended_models"] = deep_research.get("recommendations", []) or []

    normalized["techniques"] = _dedupe_list(normalized.get("techniques", []))
    normalized["recommended_models"] = _dedupe_list(normalized.get("recommended_models", []))
    normalized["key_insights"] = _dedupe_list(normalized.get("key_insights", []))

    return normalized


def normalize_modeling_result(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}

    model_data = {}
    if isinstance(data.get("model_data"), dict):
        model_data.update(data["model_data"])

    for key in [
        "model_path",
        "mlflow_run_id",
        "problem_type",
        "metrics",
        "best_estimator",
        "best_model",
        "feature_importance",
        "training_time",
    ]:
        if data.get(key) is not None:
            model_data[key] = data.get(key)

    if "best_estimator" not in model_data and "best_model" in model_data:
        model_data["best_estimator"] = model_data.get("best_model")
    if "best_model" not in model_data and "best_estimator" in model_data:
        model_data["best_model"] = model_data.get("best_estimator")

    return model_data


def normalize_insights_result(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}

    normalized: Dict[str, Any] = {}

    if isinstance(data.get("insights"), dict):
        normalized.update(data.get("insights") or {})
    else:
        normalized.update(data)

    if data.get("shap_results") is not None:
        normalized["shap_results"] = data.get("shap_results")
    if data.get("error_analysis") is not None:
        normalized["error_analysis"] = data.get("error_analysis")
    if data.get("insights_file") is not None:
        normalized["insights_file"] = data.get("insights_file")

    if "shap_summary" not in normalized and isinstance(normalized.get("shap_results"), dict):
        normalized["shap_summary"] = normalized["shap_results"].get("top_features", [])[:10]

    if "error_summary" not in normalized and normalized.get("error_analysis") is not None:
        normalized["error_summary"] = normalized.get("error_analysis")

    return normalized
