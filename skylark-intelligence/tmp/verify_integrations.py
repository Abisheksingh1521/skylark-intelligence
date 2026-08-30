import json
import os
import sys
from dotenv import load_dotenv
load_dotenv(override=True)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import settings
from monday.service import MondayService
from ai.provider import GeminiProvider

result = {}
# Monday.com verification
monday_connected, monday_msg = MondayService.validate_connection()
if monday_connected:
    service = MondayService()
    deals = service.get_raw_deals_data()
    wos = service.get_raw_work_orders_data()
    deals_count = len(deals)
    wos_count = len(wos)
else:
    deals_count = 0
    wos_count = 0
result['monday'] = {
    'connected': monday_connected,
    'message': monday_msg,
    'board_ids': {
        'deals': settings.MONDAY_DEALS_BOARD_ID,
        'work_orders': settings.MONDAY_WORK_ORDERS_BOARD_ID
    },
    'env_var': 'MONDAY_API_TOKEN',
    'deals_count': deals_count,
    'work_orders_count': wos_count
}
# Gemini verification
gemini = GeminiProvider()
gemini_connected = gemini.health_check()
if gemini_connected:
    try:
        resp = gemini.generate_response([{'role': 'user', 'content': 'Hello'}])
        gemini_model = gemini.model_name if hasattr(gemini, 'model_name') else None
        gemini_error = None
    except Exception as e:
        gemini_model = None
        gemini_error = str(e)
else:
    gemini_model = None
    gemini_error = None
result['gemini'] = {
    'connected': gemini_connected,
    'model': gemini_model,
    'error': gemini_error
}
print(json.dumps(result))
