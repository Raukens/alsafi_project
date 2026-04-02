import json
import sys
from pathlib import Path

import requests
import datetime as dt
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.cache import cache
from django.conf import settings
from alsafi_drm.utils.corr_accounts import get_corr_accounts, invalidate_cache
from collections import defaultdict
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    
    def form_invalid(self, form):
        if getattr(self.request, 'ldap_access_denied', False):
            raise PermissionDenied
        return super().form_invalid(form)


def clear_cache(request):
    invalidate_cache()
    return redirect('home')


def _get_rag_answer(question: str):
    """Вызов RAG (pdf_rag.ask_return). Путь к проекту добавляется в sys.path."""
    base_dir = Path(settings.BASE_DIR)
    project_root = base_dir.parent
    # Загружаем .env из drm/ и из корня проекта, чтобы OPENAI_API_KEY был доступен
    load_dotenv(base_dir / ".env")
    load_dotenv(project_root / ".env")
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        from pdf_rag import ask_return
        result = ask_return(question)
        return result.get("result", ""), result.get("source_documents") or []
    except Exception as e:
        return f"Ошибка при запросе к RAG: {e}", []


@login_required
@ensure_csrf_cookie
def chat(request):
    """Страница чата по документу (RAG). Устанавливает CSRF-куку для POST /api/chat/."""
    return render(request, "chat.html", {"user": request.user})


@require_http_methods(["POST"])
@ensure_csrf_cookie
def chat_api(request):
    """API для чата: POST JSON {query} → {answer, sources}."""
    try:
        body = json.loads(request.body)
        query = (body.get("query") or "").strip()
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"answer": "Неверный JSON.", "sources": []}, status=400)
    if not query:
        return JsonResponse({"answer": "Введите вопрос.", "sources": []}, status=400)
    answer, source_docs = _get_rag_answer(query)
    sources = []
    for doc in source_docs[:5]:
        meta = getattr(doc, "metadata", None) or {}
        page = meta.get("page", "?")
        content = (getattr(doc, "page_content", None) or "")[:300]
        sources.append({"page": page, "snippet": content})
    return JsonResponse({"answer": answer, "sources": sources})


@login_required
def home(request):
    data = get_corr_accounts()
    return render(request, "home.html", {"user": request.user})
    # return JsonResponse({"data": data}, json_dumps_params={"ensure_ascii": False})

@login_required
def lcr(request):
    hqla_banks = [
        'BANK OF LANGFANG CO LTD',
        'COMMERCIAL BANK OF DUBAI',
        'MASHREQBANK PSC',
        'ZHEJIANG CHOUZHOU COMMERCIAL BANK CO.,LTD',
        'Акционерное общество ADCB Islamic Bank JSC',
    ]
    today = dt.date.today()
    data = get_corr_accounts()
    assets_raw = data["data"]["assets"]
    hqla_assets_inUsd = sum(
        float(item.get("inUsd") or 0)
        for item in assets_raw
        if not item.get("isTotal") and item.get("bank").replace('\xa0', ' ').strip() in hqla_banks
        )
    total_assets_inUsd = sum(float(item.get("inUsd") or 0) for item in assets_raw if not item.get("isTotal"))
    liabilities_raw = data["data"]["liabilities"]
    total_liabilities_inUsd = sum(float(item.get("inUsd") or 0) for item in liabilities_raw if not item.get("isTotal"))
    print(f'hqla_assets_inUsd: {hqla_assets_inUsd}, total_assets_inUsd: {total_assets_inUsd}, total_liabilities_inUsd: {total_liabilities_inUsd}')
    grouped_banks = defaultdict(float)
    for item in assets_raw:
        if not item.get("isTotal"):
            grouped_banks[item.get("bank")] += float(item.get("inUsd") or 0)

    lcr = hqla_assets_inUsd / (total_liabilities_inUsd * 0.4)
    print(f'lcr: {lcr}')
    print(grouped_banks)
    if lcr < 1.2:

        banks_to_increase_liquidity = [bank for bank, amount in grouped_banks.items() if amount > 0.05 * total_assets_inUsd and bank not in hqla_banks]
        recomendation = f"Необходимо снизить остатки в следующих банках: {', '.join(banks_to_increase_liquidity)}"
    else:
        recomendation = "LCR имеет хорошее значение"
    return render(request, "lcr.html", {
        "user": request.user,
        "today": today.strftime("%d.%m.%Y"),
        "lcr": round(lcr, 2),
        "lcr_raw": lcr,
        "recomendation": recomendation,
    })


def get_assets(request):
    data = get_corr_accounts()
    assets_raw = data["data"]["assets"]
    assets = [item for item in data["data"]["assets"] if not item.get("isTotal")]
    total = next((item for item in assets_raw if item.get("isTotal")), None)
    return render(request, "assets.html", {"assets": assets, "total": total})


def get_liquidity(request):
    return render(request, "liquidity.html", {"user": request.user})


def get_liquidity_json(request):
    data = get_corr_accounts()
    return render(request, "liquidity.html", {"data": data})


def get_liabilities(request):
    data = get_corr_accounts()
    liabilities = data["data"]["liabilities"]
    return render(request, "liabilities.html", {"liabilities": liabilities})


def tab_assets(request):
    data = get_corr_accounts()
    assets_raw = data["data"]["assets"]
    assets = [item for item in data["data"]["assets"] if not item.get("isTotal")]
    total = next((item for item in assets_raw if item.get("isTotal")), None)
    return render(request, 'assets.html', {"assets": assets, "total": total})  # partial template


def tab_liabilities(request):
    data = get_corr_accounts()
    liabilities_raw = data["data"]["liabilities"]
    
    # Группируем по валюте
    from collections import defaultdict
    groups = defaultdict(lambda: {"rows": [], "total": None})
    
    for item in liabilities_raw:
        currency = item["currency"]
        if item.get("isTotal"):
            groups[currency]["total"] = item
        else:
            groups[currency]["rows"].append(item)
    
    return render(request, 'liabilities.html', {"groups": dict(groups)})


def get_bank_buffers(request):
    data = get_corr_accounts()
    if not data:
        return render(request, "bank_buffers.html", {"bank_buffers": []})
    # data.data.data.bufferByBank или data.data.bufferByBank
    inner = (data.get("data") or {})
    inner2 = inner.get("data") if isinstance(inner, dict) else {}
    payload = inner2 if isinstance(inner2, dict) else inner
    bank_buffers = (
        payload.get("bufferByBank")
        or payload.get("BufferByBank")
        or payload.get("buffer_by_bank")
    )
    if not isinstance(bank_buffers, list):
        bank_buffers = []
    return render(request, "bank_buffers.html", {"bank_buffers": bank_buffers})