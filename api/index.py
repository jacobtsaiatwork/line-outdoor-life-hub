# -*- coding: utf-8 -*-
"""
Vercel Serverless Function 入口點
將所有 HTTP 請求路由導向 FastAPI app
"""
import sys
import os

# 將專案根目錄加入模組搜尋路徑
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app
