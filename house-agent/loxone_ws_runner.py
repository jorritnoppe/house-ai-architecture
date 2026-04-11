import logging
import time

from services.loxone_history_service import build_loxone_history_state_index
from services.loxone_ws_service import start_loxone_ws_background

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

build_loxone_history_state_index()
start_loxone_ws_background()

while True:
    time.sleep(60)
