from flask import Flask
from flask_cors import CORS

from extensions import app
from services.buderus_legacy_core import load_buderus_module

from services.loxone_ws_service import start_loxone_ws_background

# ROUTES
from routes.health_routes import health_bp
from routes.price_routes import price_bp
from routes.water_routes import water_bp
from routes.pdata_routes import pdata_bp
from routes.sma_routes import sma_bp
from routes.agent_routes import agent_bp
from routes.power_routes import power_bp
from routes.openai_routes import openai_bp
from routes.loxone_routes import loxone_bp

from routes.tool_routes import tools_bp
from routes.voice_routes import voice_bp
from services.loxone_music_controls import music_controls_bp

from routes.voice_input_routes import voice_input_bp
from routes.house_routes import house_bp
from routes.status import status_bp

from routes.loxone_routes import loxone_bp
from routes.audio_tool_routes import audio_tools_bp
from routes.agent_execute_routes import agent_exec_bp
from routes.agenda_routes import agenda_bp

from routes.audio_routes import audio_bp

from services.loxone_history_service import rebuild_state_uuid_index
from routes.conversation_routes import conversation_bp

from routes.feedback_probe_routes import feedback_probe_bp

from routes.audio_test_routes import bp as audio_test_bp
from routes.audio_timing_routes import audio_timing_bp
from routes.audio_validation_routes import audio_validation_bp

from routes.netdata_routes import netdata_bp

from routes.service_health_routes import service_health_bp

from routes.unifi_routes import unifi_bp
from services.unifi_collector import collector

from routes.safe_action_routes import safe_action_bp
from routes.ai_safe_action_routes import ai_safe_action_bp

from routes.voice_node_routes import voice_node_bp
from routes.playback_state_routes import playback_state_bp
from routes.house_state_routes import house_state_bp


from routes.node_capability_routes import node_capability_bp

from routes.action_auth_routes import action_auth_bp


from routes.pending_approval_routes import pending_approval_bp

from routes.approved_action_routes import approved_action_bp

from routes.approval_execution_routes import approval_execution_bp

from routes.approval_signal_routes import approval_signal_bp

from routes.house_analysis_routes import house_analysis_bp

from routes.trade_routes import trade_bp


# Enable CORS
# CORS(app) -> Already loading in extensions


# Load Buderus integration
load_buderus_module(app)


# Register Blueprints
app.register_blueprint(health_bp)
app.register_blueprint(price_bp)
app.register_blueprint(water_bp)
app.register_blueprint(pdata_bp)
app.register_blueprint(sma_bp)
app.register_blueprint(agent_bp)

app.register_blueprint(power_bp)
app.register_blueprint(openai_bp)

app.register_blueprint(tools_bp)
app.register_blueprint(voice_bp)

# Loxone integration
app.register_blueprint(loxone_bp)
app.register_blueprint(agenda_bp)

app.register_blueprint(music_controls_bp)

app.register_blueprint(voice_input_bp)
app.register_blueprint(house_bp)
app.register_blueprint(status_bp)

app.register_blueprint(audio_tools_bp)
app.register_blueprint(agent_exec_bp)

app.register_blueprint(audio_bp)

app.register_blueprint(conversation_bp)


app.register_blueprint(feedback_probe_bp)
app.register_blueprint(audio_test_bp)
app.register_blueprint(audio_timing_bp)

app.register_blueprint(audio_validation_bp)

app.register_blueprint(netdata_bp)

app.register_blueprint(service_health_bp)


app.register_blueprint(unifi_bp)
collector.start()
try:
    collector.refresh()
except Exception as exc:
    app.logger.warning(f"Initial UniFi collector refresh failed: {exc}")


app.register_blueprint(safe_action_bp)
app.register_blueprint(ai_safe_action_bp)

app.register_blueprint(voice_node_bp)
app.register_blueprint(playback_state_bp)
app.register_blueprint(house_state_bp)
app.register_blueprint(node_capability_bp)

app.register_blueprint(action_auth_bp)

app.register_blueprint(pending_approval_bp)


app.register_blueprint(approved_action_bp)
app.register_blueprint(approval_execution_bp)

app.register_blueprint(approval_signal_bp)


app.register_blueprint(house_analysis_bp)

app.register_blueprint(trade_bp)


# Start Loxone websocket background listener
start_loxone_ws_background()



rebuild_state_uuid_index()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
