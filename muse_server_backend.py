import sys
import threading
import time
import webbrowser
import subprocess
import os

import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, AggOperations, WindowOperations
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from pynput.keyboard import Controller, Key

# --- Basic Flask App and SocketIO Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Dynamic HTML Generation ---
def generate_board_options():
    options_html = ""
    sorted_boards = sorted(BoardIds, key=lambda x: x.value)
    for board in sorted_boards:
        if 'SYNTHETIC' in board.name or 'PLAYBACK' in board.name:
            continue
        board_name = board.name.replace('_BOARD', '').replace('_', ' ').title()
        selected_attr = 'selected' if board.value == 41 else ''
        options_html += f'<option value="{board.value}" {selected_attr}>{board_name} (ID: {board.value})</option>\n'
    return options_html

# --- HTML Template ---
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BrainFlow Keyboard Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .log-entry {{ font-family: 'Courier New', Courier, monospace; }}
        :disabled {{ cursor: not-allowed; opacity: 0.6; }}
        input[type=range]::-webkit-slider-thumb {{
            -webkit-appearance: none; appearance: none; width: 20px; height: 20px;
            background: #4f46e5; cursor: pointer; border-radius: 50%;
        }}
        input[type=range]::-moz-range-thumb {{
            width: 20px; height: 20px; background: #4f46e5; cursor: pointer; border-radius: 50%;
        }}
        .quality-indicator {{
            transition: opacity 0.5s ease-in-out;
        }}
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body class="bg-gray-900 text-gray-200 flex items-center justify-center min-h-screen">
    <div class="w-full max-w-lg bg-gray-800 rounded-2xl shadow-2xl p-6 md:p-8 m-4">
        <h1 class="text-2xl font-bold text-center mb-6 text-indigo-400">BrainFlow Keyboard Control</h1>
        <div class="border border-gray-700 rounded-lg p-4 mb-6">
            <h2 class="text-lg font-semibold mb-3 text-gray-300">1. Connection</h2>
            <div class="space-y-4">
                <select id="boardIdSelect" class="bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5">
                    {generate_board_options()}
                </select>
                <div>
                    <label for="macAddressInput" class="block mb-2 text-sm font-medium">MAC Address / Device Name</label>
                    <input type="text" id="macAddressInput" placeholder="Optional: e.g., 00:11:22:33:FF:EE" class="bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg block w-full p-2.5">
                </div>
                <div>
                    <label for="timeoutInput" class="block mb-2 text-sm font-medium">Connection Timeout (seconds)</label>
                    <input type="number" id="timeoutInput" value="20" class="bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg block w-full p-2.5">
                </div>
                <button id="connectBtn" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    Connect
                </button>
                <div class="flex justify-between items-center">
                    <div class="text-center font-semibold text-lg" id="statusLabel">Status: Disconnected</div>
                    <div id="qualityIndicator" class="quality-indicator text-yellow-400 font-bold opacity-0">POOR SIGNAL</div>
                </div>
            </div>
        </div>
        <div class="border border-gray-700 rounded-lg p-4 mb-6">
            <h2 class="text-lg font-semibold mb-3 text-gray-300">2. Calibration</h2>
            <div class="space-y-4">
                <button id="calibrateBtn" class="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-4 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500" disabled>
                    Calibrate (Connect First)
                </button>
                 <div class="text-center text-sm" id="calibrationStatus"></div>
            </div>
        </div>
        <div class="border border-gray-700 rounded-lg p-4 mb-6">
            <h2 class="text-lg font-semibold mb-3 text-gray-300">3. Settings</h2>
            <div class="space-y-4">
                 <div>
                    <label for="metricModeSelect" class="block mb-2 text-sm font-medium">Metric Mode</label>
                    <select id="metricModeSelect" class="bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5">
                        <option value="focus">Focus Ratio (Beta/Alpha)</option>
                        <option value="alpha" selected>Alpha Power (Relaxation)</option>
                    </select>
                </div>
                <div>
                    <label for="smoothingSlider" class="block mb-2 text-sm font-medium">Smoothing Factor (<span id="smoothingValue">0.2</span>)</label>
                    <input id="smoothingSlider" type="range" min="0.01" max="1.0" value="0.2" step="0.01" class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer">
                </div>
                <div>
                    <label for="sensitivitySlider" class="block mb-2 text-sm font-medium">Activation Threshold (<span id="sensitivityValue">2.0</span>x Baseline)</label>
                    <input id="sensitivitySlider" type="range" min="1.1" max="5.0" value="2.0" step="0.1" class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer">
                </div>
                <hr class="border-gray-600">
                <div id="keyBindingsContainer" class="space-y-3">
                    <label class="block mb-2 text-sm font-medium">Key Bindings for Left/Right States</label>
                    <div class="flex items-center space-x-2">
                        <label for="key-left" class="w-1/3 text-sm font-medium">Left Side:</label>
                        <input type="text" id="key-left" data-state="left" class="key-binding-input bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg block w-2/3 p-2.5" placeholder="e.g., left">
                    </div>
                    <div class="flex items-center space-x-2">
                        <label for="key-right" class="w-1/3 text-sm font-medium">Right Side:</label>
                        <input type="text" id="key-right" data-state="right" class="key-binding-input bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg block w-2/3 p-2.5" placeholder="e.g., right">
                    </div>
                </div>
            </div>
        </div>
        <div class="border border-gray-700 rounded-lg p-4 mb-6">
            <h2 class="text-lg font-semibold mb-3 text-gray-300">Live Metrics</h2>
            <canvas id="metricChart"></canvas>
        </div>
        <div class="border border-gray-700 rounded-lg p-4">
            <h2 class="text-lg font-semibold mb-3 text-gray-300">Event Log</h2>
            <div id="logArea" class="h-40 bg-gray-900 rounded-md p-3 overflow-y-auto text-sm log-entry space-y-1"></div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/socket.io-client@4.7.2/dist/socket.io.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const socket = io('http://127.0.0.1:5000');
            let metricChart;
            const metricData = {{
                labels: [],
                datasets: [
                    {{ label: 'Left', data: [], borderColor: '#f87171', borderWidth: 2, pointRadius: 0, tension: 0.4 }},
                    {{ label: 'Right', data: [], borderColor: '#60a5fa', borderWidth: 2, pointRadius: 0, tension: 0.4 }}
                ]
            }};

            const connectBtn = document.getElementById('connectBtn');
            const statusLabel = document.getElementById('statusLabel');
            const sensitivitySlider = document.getElementById('sensitivitySlider');
            const sensitivityValue = document.getElementById('sensitivityValue');
            const boardIdSelect = document.getElementById('boardIdSelect');
            const macAddressInput = document.getElementById('macAddressInput');
            const timeoutInput = document.getElementById('timeoutInput');
            const logArea = document.getElementById('logArea');
            const calibrateBtn = document.getElementById('calibrateBtn');
            const calibrationStatus = document.getElementById('calibrationStatus');
            const metricModeSelect = document.getElementById('metricModeSelect');
            const smoothingSlider = document.getElementById('smoothingSlider');
            const smoothingValue = document.getElementById('smoothingValue');
            const qualityIndicator = document.getElementById('qualityIndicator');

            const createChart = () => {{
                const ctx = document.getElementById('metricChart').getContext('2d');
                metricChart = new Chart(ctx, {{
                    type: 'line',
                    data: metricData,
                    options: {{
                        animation: false,
                        scales: {{ y: {{ beginAtZero: true, grid: {{ color: 'rgba(255, 255, 255, 0.1)' }}, ticks: {{ color: '#9ca3af' }} }}, x: {{ display: false }} }},
                        plugins: {{ legend: {{ display: true, labels: {{ color: '#9ca3af' }} }} }}
                    }}
                }});
            }};

            const log = (message) => {{
                const time = new Date().toLocaleTimeString();
                logArea.innerHTML += `<div class="log-entry"><span class="text-gray-500">${{time}}:</span> <span class="text-gray-300">${{message}}</span></div>`;
                logArea.scrollTop = logArea.scrollHeight;
            }};
            
            socket.on('connect', () => log('Successfully connected to Python server.'));
            socket.on('log_message', (msg) => log(msg));

            socket.on('connection_status', (data) => {{
                const isStreaming = data.status === 'streaming';
                statusLabel.textContent = `Status: ${{isStreaming ? 'Streaming' : 'Disconnected'}}`;
                statusLabel.className = `text-center font-semibold text-lg ${{isStreaming ? 'text-green-400' : 'text-red-400'}}`;
                connectBtn.textContent = isStreaming ? 'Disconnect' : 'Connect';
                connectBtn.classList.toggle('bg-indigo-600', !isStreaming);
                connectBtn.classList.toggle('bg-red-600', isStreaming);
                calibrateBtn.disabled = !isStreaming;
                calibrateBtn.textContent = isStreaming ? 'Calibrate' : 'Calibrate (Connect First)';
                if (!isStreaming) calibrationStatus.textContent = '';
            }});

            socket.on('calibration_status', (data) => {{
                if (data.status === 'calibrating') {{
                    calibrationStatus.textContent = `Calibrating... Please relax. ${{data.countdown}}s remaining.`;
                    calibrateBtn.disabled = true;
                }} else if (data.status === 'complete') {{
                    calibrationStatus.textContent = `Calibration Complete! Baselines: L:${{data.baselines.left.toFixed(2)}}, R:${{data.baselines.right.toFixed(2)}}`;
                    calibrateBtn.disabled = false;
                }}
            }});
            
            let qualityTimeout;
            socket.on('signal_quality', (data) => {{
                if (data.quality === 'bad') {{
                    qualityIndicator.style.opacity = 1;
                    clearTimeout(qualityTimeout);
                    qualityTimeout = setTimeout(() => {{
                        qualityIndicator.style.opacity = 0;
                    }}, 1500);
                }}
            }});

            socket.on('metric_data', (data) => {{
                if (!metricChart) return;
                const datasets = metricChart.data.datasets;
                datasets[0].data.push(data.left_value);
                datasets[1].data.push(data.right_value);
                metricChart.data.labels.push('');

                while (datasets[0].data.length > 100) {{
                    datasets.forEach(d => d.data.shift());
                    metricChart.data.labels.shift();
                }}
                metricChart.update();
            }});
            
            connectBtn.addEventListener('click', () => {{
                if (connectBtn.textContent === 'Disconnect') {{
                    socket.emit('stop_stream');
                }} else {{
                    socket.emit('start_stream', {{ 
                        board_id: boardIdSelect.value,
                        mac_address: macAddressInput.value,
                        timeout: timeoutInput.value
                    }});
                }}
            }});

            calibrateBtn.addEventListener('click', () => {{
                socket.emit('start_calibration');
            }});
            
            const sendSettings = () => {{
                const keyBindings = {{}};
                document.querySelectorAll('.key-binding-input').forEach(input => {{
                    keyBindings[input.dataset.state] = input.value;
                }});

                socket.emit('update_settings', {{
                    sensitivity: sensitivitySlider.value,
                    key_bindings: keyBindings,
                    metric_mode: metricModeSelect.value,
                    smoothing: smoothingSlider.value,
                }});
            }};
            
            sensitivitySlider.addEventListener('input', (e) => {{
                sensitivityValue.textContent = parseFloat(e.target.value).toFixed(1);
            }});
            smoothingSlider.addEventListener('input', (e) => {{
                smoothingValue.textContent = parseFloat(e.target.value).toFixed(2);
            }});

            sensitivitySlider.addEventListener('change', sendSettings);
            smoothingSlider.addEventListener('change', sendSettings);
            
            document.querySelectorAll('.key-binding-input').forEach(input => {{
                input.addEventListener('change', sendSettings);
            }});

            metricModeSelect.addEventListener('change', sendSettings);

            createChart();
        }});
    </script>
</body>
</html>
"""

# --- Global state management ---
class BCIState:
    def __init__(self):
        self.board = None
        self.is_streaming = False
        self.is_calibrating = False
        self.eeg_channels = []
        self.last_detection_times = {}
        self.cooldown_s = 1.0 
        self.params = BrainFlowInputParams()
        self.keyboard = Controller()
        self.board_id = 41
        self.sensitivity = 2.0 
        self.key_bindings = {}
        self.baselines = {'left': 1.0, 'right': 1.0}
        self.channel_map = {}
        self.metric_mode = 'alpha'
        self.smoothing_factor = 0.2
        self.metric_emas = {'left': 0.0, 'right': 0.0}

bci_state = BCIState()

def get_lr_channel_map(eeg_channels):
    sorted_channels = sorted(eeg_channels)
    midpoint = len(sorted_channels) // 2
    left_channels = sorted_channels[:midpoint]
    right_channels = sorted_channels[midpoint:]
    if len(sorted_channels) % 2 != 0:
        right_channels.insert(0, sorted_channels[midpoint])
    if not left_channels: left_channels = right_channels
    if not right_channels: right_channels = left_channels
    return {'left': left_channels, 'right': right_channels}

# --- Backend Data Processing Thread ---
def data_processing_thread():
    sampling_rate = BoardShim.get_sampling_rate(bci_state.board_id)
    window_seconds = 2
    refresh_rate_hz = 5
    nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
    num_samples_in_window = int(sampling_rate * window_seconds)
    
    bci_state.channel_map = get_lr_channel_map(bci_state.eeg_channels)
    print(f"Using dynamically generated channel map: {bci_state.channel_map}")
    
    while bci_state.is_streaming:
        start_time = time.time()
        try:
            data = bci_state.board.get_current_board_data(num_samples_in_window)
            if data.shape[1] < num_samples_in_window:
                time.sleep(1.0 / refresh_rate_hz)
                continue
            
            max_std = 0
            for c in bci_state.eeg_channels:
                std = np.std(data[c])
                if std > max_std:
                    max_std = std
            if max_std > 100:
                socketio.emit('signal_quality', {'quality': 'bad'})


            metric_values = {}
            for region, channels in bci_state.channel_map.items():
                if not channels: continue
                regional_metric_vals = []
                for ch_index in channels:
                    channel_data = np.copy(data[ch_index])
                    # Perform calculations on raw data to avoid filtering issues
                    
                    psd = DataFilter.get_psd_welch(channel_data, nfft, nfft // 2, sampling_rate, WindowOperations.HANNING.value)
                    
                    if bci_state.metric_mode == 'alpha':
                        alpha_power = DataFilter.get_band_power(psd, 7.0, 13.0)
                        regional_metric_vals.append(alpha_power)
                    else: # 'focus'
                        alpha = DataFilter.get_band_power(psd, 7.0, 13.0)
                        beta = DataFilter.get_band_power(psd, 13.0, 30.0)
                        if alpha > 0.001:
                            focus = beta / alpha
                            regional_metric_vals.append(focus)
                metric_values[region] = np.mean(regional_metric_vals) if regional_metric_vals else 0.0

            alpha = bci_state.smoothing_factor
            for region in ['left', 'right']:
                raw_value = metric_values.get(region, 0)
                bci_state.metric_emas[region] = (alpha * raw_value) + (1 - alpha) * bci_state.metric_emas[region]

            if not bci_state.is_calibrating:
                 print(f"Smoothed Metrics ({bci_state.metric_mode}): L={bci_state.metric_emas.get('left',0):.2f}, R={bci_state.metric_emas.get('right',0):.2f}")

            socketio.emit('metric_data', {
                'left_value': bci_state.metric_emas.get('left', 0),
                'right_value': bci_state.metric_emas.get('right', 0),
            })

            if not bci_state.is_calibrating:
                check_metric_triggers(bci_state.metric_emas)
            
            execution_time = time.time() - start_time
            sleep_time = (1.0 / refresh_rate_hz) - execution_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        except Exception as e:
            print(f"Error in data thread: {e}")
            break
    print("Data thread stopped.")

def check_metric_triggers(metrics):
    sensitivity = bci_state.sensitivity
    left = metrics.get('left', 0)
    right = metrics.get('right', 0)

    if left > bci_state.baselines['left'] * sensitivity and left > right: 
        trigger_key_press('left')
    elif right > bci_state.baselines['right'] * sensitivity and right > left: 
        trigger_key_press('right')


def trigger_key_press(focus_state):
    # This function is correct and does not need changes
    current_time = time.time()
    last_time = bci_state.last_detection_times.get(focus_state, 0)
    if (current_time - last_time) < bci_state.cooldown_s:
        return
    bci_state.last_detection_times[focus_state] = current_time
    key_str = bci_state.key_bindings.get(focus_state, '').lower().strip()
    if not key_str:
        return
    print(f"State Detected: '{focus_state.upper()}'. Pressing '{key_str}'.")
    socketio.emit('log_message', f"State Detected: '{focus_state.upper()}'. Pressing '{key_str}'.")
    try:
        key_map = {
            'space': Key.space, 'enter': Key.enter, 'esc': Key.esc, 'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
            'shift': Key.shift, 'ctrl': Key.ctrl, 'alt': Key.alt, 'win': Key.cmd, 'cmd': Key.cmd,
            'tab': Key.tab, 'caps_lock': Key.caps_lock, 'delete': Key.delete,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
            'page_up': Key.page_up, 'pgup': Key.page_up, 'page_down': Key.page_down, 'pgdn': Key.page_down,
            'home': Key.home, 'end': Key.end, 'insert': Key.insert
        }
        keys = [k.strip() for k in key_str.split('+')]
        parsed_keys = [key_map.get(k, k) for k in keys if len(k) == 1 or k in key_map]
        if not parsed_keys: raise ValueError("No valid keys found.")
        if len(parsed_keys) > 1:
            modifiers = parsed_keys[:-1]
            primary_key = parsed_keys[-1]
            for mod in modifiers: bci_state.keyboard.press(mod)
            bci_state.keyboard.press(primary_key); bci_state.keyboard.release(primary_key)
            for mod in reversed(modifiers): bci_state.keyboard.release(mod)
        else:
            bci_state.keyboard.press(parsed_keys[0]); bci_state.keyboard.release(parsed_keys[0])
    except Exception as e:
        print(f"Error pressing key '{key_str}': {repr(e)}")
        socketio.emit('log_message', f"Error pressing key '{key_str}': {repr(e)}")


def calibration_thread():
    bci_state.is_calibrating = True
    calibration_seconds = 10
    refresh_rate_hz = 5
    calibration_data = {direction: [] for direction in ['left', 'right']}
    
    for i in range(calibration_seconds * refresh_rate_hz):
        countdown = calibration_seconds - (i // refresh_rate_hz)
        socketio.emit('calibration_status', {'status': 'calibrating', 'countdown': countdown})
        
        sampling_rate = BoardShim.get_sampling_rate(bci_state.board_id)
        nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
        data = bci_state.board.get_current_board_data(int(sampling_rate * 2))

        for region, channels in bci_state.channel_map.items():
            if not channels: continue
            regional_metric_vals = []
            for ch_index in channels:
                if ch_index < data.shape[0]:
                    channel_data = np.copy(data[ch_index])
                    psd = DataFilter.get_psd_welch(channel_data, nfft, nfft // 2, sampling_rate, WindowOperations.HANNING.value)
                    if bci_state.metric_mode == 'alpha':
                        alpha_power = DataFilter.get_band_power(psd, 7.0, 13.0)
                        regional_metric_vals.append(alpha_power)
                    else: # 'focus'
                        alpha = DataFilter.get_band_power(psd, 7.0, 13.0)
                        beta = DataFilter.get_band_power(psd, 13.0, 30.0)
                        if alpha > 0.001:
                            focus = beta / alpha
                            regional_metric_vals.append(focus)
            if regional_metric_vals:
                calibration_data[region].append(np.mean(regional_metric_vals))
        time.sleep(1.0 / refresh_rate_hz)

    for region, values in calibration_data.items():
        bci_state.baselines[region] = np.mean(values) if values else 1.0
            
    bci_state.is_calibrating = False
    print(f"Calibration complete. Baselines: {bci_state.baselines}")
    socketio.emit('calibration_status', {'status': 'complete', 'baselines': bci_state.baselines})


# --- SocketIO Event Handlers ---
@socketio.on('start_stream')
def handle_start_stream(data):
    if bci_state.is_streaming:
        emit('log_message', 'Stream is already running.')
        return
    try:
        bci_state.board_id = int(data['board_id'])
        bci_state.params = BrainFlowInputParams()
        mac_address = data.get('mac_address', '')
        timeout = data.get('timeout', '20')
        
        if mac_address: bci_state.params.mac_address = mac_address
        try:
            bci_state.params.timeout = int(timeout)
        except (ValueError, TypeError):
            bci_state.params.timeout = 20
        
        print(f"Attempting to connect to board ID: {bci_state.board_id} with mac: '{mac_address}', timeout: {bci_state.params.timeout}")
        emit('log_message', f"Initializing board ID: {bci_state.board_id}...")
        
        BoardShim.enable_dev_board_logger()
        bci_state.board = BoardShim(bci_state.board_id, bci_state.params)
        bci_state.board.prepare_session()
        bci_state.board.start_stream(450000)
        bci_state.is_streaming = True
        bci_state.metric_emas = {'left': 0.0, 'right': 0.0} # Reset EMAs
        
        socketio.emit('log_message', 'Connection successful. Filling buffer...')
        time.sleep(3) 

        bci_state.eeg_channels = BoardShim.get_eeg_channels(bci_state.board_id)
        emit('connection_status', {'status': 'streaming'})
        emit('log_message', 'Buffer filled. Ready for calibration.')
        threading.Thread(target=data_processing_thread, daemon=True).start()
    except Exception as e:
        print(f"Connection Error: {e}")
        emit('log_message', f"Error: {e}")
        bci_state.is_streaming = False
        emit('connection_status', {'status': 'disconnected'})

@socketio.on('start_calibration')
def handle_start_calibration():
    if bci_state.is_streaming and not bci_state.is_calibrating:
        threading.Thread(target=calibration_thread, daemon=True).start()

@socketio.on('stop_stream')
def handle_stop_stream():
    if bci_state.board and bci_state.is_streaming:
        bci_state.board.stop_stream()
        bci_state.board.release_session()
    bci_state.is_streaming = False; bci_state.board = None
    print("Streaming stopped.")
    emit('log_message', 'Stream stopped.'); emit('connection_status', {'status': 'disconnected'})

@socketio.on('update_settings')
def handle_update_settings(data):
    print(f"Updating settings: {data}")
    bci_state.sensitivity = float(data.get('sensitivity', bci_state.sensitivity))
    bci_state.key_bindings = data.get('key_bindings', bci_state.key_bindings)
    bci_state.metric_mode = data.get('metric_mode', bci_state.metric_mode)
    bci_state.smoothing_factor = float(data.get('smoothing', bci_state.smoothing_factor))
    if 'thresholds' in data:
        for direction, value in data['thresholds'].items():
            bci_state.thresholds[direction] = float(value)
    emit('log_message', "Settings updated.")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    try:
        import flask, flask_socketio, pynput, numpy, brainflow
    except ImportError:
        print("Missing dependencies. Please run: pip install Flask Flask-SocketIO pynput numpy brainflow")
        sys.exit(1)

    print("Starting BrainFlow BCI Server...")
    webbrowser.open_new_tab('http://127.0.0.1:5000')
    socketio.run(app, host='127.0.0.1', port=5000)

