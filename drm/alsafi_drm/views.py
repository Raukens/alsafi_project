import requests
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from alsafi_drm.utils.corr_accounts import get_corr_accounts
import json


@login_required
def home(request):
    data = get_corr_accounts()
    return render(request, "home.html", {"user": request.user})
    # return JsonResponse({"data": data}, json_dumps_params={"ensure_ascii": False})

@login_required
def lcr(request):
    return render(request, "lcr.html", {"user": request.user})


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