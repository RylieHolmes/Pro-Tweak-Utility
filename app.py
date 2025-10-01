import webview
import subprocess
import os
import sys
import json
import ctypes
import traceback
import shutil
import winreg

# --- Constants and Pathing ---
def get_application_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_application_path()
WEB_DIR = os.path.join(BASE_DIR, 'web')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
TWEAKS_FILE = os.path.join(BASE_DIR, 'tweaks.json')
UNDO_FILE = os.path.join(BASE_DIR, 'undo_data.json')
PRO_POWER_PLAN_GUID = "a1b2c3d4-e5f6-a1b2-c3d4-e5f6a1b2c3d4"

HKEY_MAP = {'HKCU': winreg.HKEY_CURRENT_USER, 'HKLM': winreg.HKEY_LOCAL_MACHINE}
REG_TYPE_MAP = {'REG_SZ': winreg.REG_SZ, 'REG_DWORD': winreg.REG_DWORD, 'REG_BINARY': winreg.REG_BINARY}

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError: return False

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW, shell=True)

# --- TweakManager Engine v2.2 ---
class TweakManager:
    def __init__(self, tweaks_path, undo_path):
        self.tweaks_path, self.undo_path = tweaks_path, undo_path
        self.tweaks = self._load_json(self.tweaks_path, {})
        self.undo_data = self._load_json(self.undo_path, {})

    def _load_json(self, file_path, default=None):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # This is NOT an error for undo/config files. They will be created.
            return default
        except json.JSONDecodeError as e:
            # This IS a critical error. The file is corrupted.
            raise ValueError(f"Syntax error in JSON file at {file_path}: {e}")

    def _save_json(self, file_path, data):
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

    def get_all_tweaks(self): return self.tweaks

    def get_tweak_states(self):
        states = {}
        for category in self.tweaks.values():
            for tweak in category:
                try:
                    is_applied = all(self._get_action_state(action) for action in tweak['actions'])
                    can_revert = tweak['id'] in self.undo_data and not tweak.get('one_time', False)
                    states[tweak['id']] = {'is_applied': is_applied, 'can_revert': can_revert}
                except Exception:
                    states[tweak['id']] = {'is_applied': False, 'can_revert': False, 'error': 'Failed to get state'}
        return states

    def _get_action_state(self, action):
        action_map = {'reg': self._get_reg_state, 'service': self._get_service_state, 'schtask': self._get_schtask_state, 'power': self._get_power_state}
        handler = action_map.get(action['type'])
        return handler(action) if handler else False

    def _get_reg_state(self, action):
        try:
            with winreg.OpenKey(HKEY_MAP[action['hive']], action['key'], 0, winreg.KEY_READ) as key:
                current_value, _ = winreg.QueryValueEx(key, action['name'])
            tweaked_value = action['data']
            if action['data_type'] == 'REG_BINARY': tweaked_value = bytes.fromhex(action['data'])
            return current_value == tweaked_value
        except FileNotFoundError: return False

    def _get_service_state(self, action):
        result = run_command(f'sc qc "{action["name"]}"')
        return 'START_TYPE' in result.stdout and {'disabled': '4 ( DISABLED )', 'auto': '2 ( AUTO_START )'}[action['state']] in result.stdout

    def _get_schtask_state(self, action):
        result = run_command(f'schtasks /query /tn "{action["name"]}"')
        return 'Status' in result.stdout and action['state'].upper() in result.stdout.split()[-1]

    def _get_power_state(self, action):
        result = run_command('powercfg /getactivescheme')
        return PRO_POWER_PLAN_GUID in result.stdout

    def apply_tweak(self, tweak_id):
        tweak = self._find_tweak(tweak_id)
        if not tweak: return {'success': False, 'message': f"Tweak '{tweak_id}' not found."}
        if not tweak.get('one_time', False): self._backup_tweak_state(tweak)
        try:
            for action in tweak['actions']: self._execute_action(action)
            return {'success': True, 'message': f"'{tweak['title']}' applied successfully."}
        except Exception as e: return {'success': False, 'message': f"Error applying '{tweak['title']}': {e}"}

    def revert_tweak(self, tweak_id):
        if tweak_id not in self.undo_data: return {'success': False, 'message': f"No undo data for '{tweak_id}'."}
        tweak_title = self.undo_data[tweak_id].get('title', tweak_id)
        try:
            for original_state in self.undo_data[tweak_id]['original_states']: self._restore_action_state(original_state)
            del self.undo_data[tweak_id]
            self._save_json(self.undo_path, self.undo_data)
            return {'success': True, 'message': f"'{tweak_title}' reverted successfully."}
        except Exception as e: return {'success': False, 'message': f"Error reverting '{tweak_title}': {e}"}

    def _execute_action(self, action):
        action_type = action['type']
        if action_type == 'reg':
            hive, key_path, name, data_type, data = HKEY_MAP[action['hive']], action['key'], action['name'], REG_TYPE_MAP[action['data_type']], action['data']
            if action['data_type'] == 'REG_BINARY': data = bytes.fromhex(data)
            with winreg.CreateKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE) as key: winreg.SetValueEx(key, name, 0, data_type, data)
        elif action_type == 'service': run_command(f'sc config "{action["name"]}" start={action["state"]}')
        elif action_type == 'schtask': run_command(f'schtasks /change /tn "{action["name"]}" /{action["state"]}')
        elif action_type == 'power':
            run_command(f'powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c {PRO_POWER_PLAN_GUID}')
            run_command(f'powercfg /changename {PRO_POWER_PLAN_GUID} "Pro Tweak Utility Plan"')
            run_command(f'powercfg /setactive {PRO_POWER_PLAN_GUID}')
        elif action_type == 'cmd':
            cmd = action.get('command64', action['command']) if sys.maxsize > 2**32 else action['command']
            run_command(cmd)
        elif action_type == 'cleanup' and action['target'] == 'temp':
            temp_dir = os.environ.get('TEMP', '')
            if os.path.isdir(temp_dir):
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path): os.unlink(item_path)
                        elif os.path.isdir(item_path): shutil.rmtree(item_path)
                    except Exception: continue

    def _backup_tweak_state(self, tweak):
        backup = {'title': tweak['title'], 'original_states': []}
        for action in tweak['actions']:
            try:
                original_state = self._get_backup_data(action)
                if original_state: backup['original_states'].append(original_state)
            except Exception as e: print(f"Could not back up {tweak['id']}: {e}")
        if backup['original_states']: self.undo_data[tweak['id']] = backup; self._save_json(self.undo_path, self.undo_data)

    def _get_backup_data(self, action):
        action_type = action['type']
        if action_type == 'reg':
            try:
                with winreg.OpenKey(HKEY_MAP[action['hive']], action['key'], 0, winreg.KEY_READ) as key:
                    value, value_type = winreg.QueryValueEx(key, action['name'])
                if value_type == winreg.REG_BINARY: value = value.hex()
                return {**action, 'original_value': value, 'original_type_id': value_type}
            except FileNotFoundError: return {**action, 'did_not_exist': True}
        elif action_type == 'service':
            result = run_command(f'sc qc "{action["name"]}"')
            start_type = next((line.split()[3] for line in result.stdout.splitlines() if 'START_TYPE' in line), None)
            return {**action, 'original_state': start_type} if start_type else None
        elif action_type == 'schtask':
            result = run_command(f'schtasks /query /tn "{action["name"]}"')
            state = 'Disabled' if 'Disabled' in result.stdout else 'Enabled'
            return {**action, 'original_state': state}
        return None

    def _restore_action_state(self, original_state):
        action_type = original_state['type']
        if action_type == 'reg':
            hive, key_path, name = HKEY_MAP[original_state['hive']], original_state['key'], original_state['name']
            if original_state.get('did_not_exist'):
                try:
                    with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as key: winreg.DeleteValue(key, name)
                except FileNotFoundError: pass
            else:
                value, value_type = original_state['original_value'], original_state['original_type_id']
                if value_type == winreg.REG_BINARY: value = bytes.fromhex(value)
                with winreg.CreateKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE) as key: winreg.SetValueEx(key, name, 0, value_type, value)
        elif action_type == 'service':
            state_map = {'1': 'demand', '2': 'auto', '3': 'demand', '4': 'disabled'}
            run_command(f'sc config "{original_state["name"]}" start={state_map.get(original_state["original_state"], "demand")}')
        elif action_type == 'schtask':
            run_command(f'schtasks /change /tn "{original_state["name"]}" /{original_state["original_state"].lower()}')

    def _find_tweak(self, tweak_id):
        for category in self.tweaks.values():
            for tweak in category:
                if tweak['id'] == tweak_id: return tweak
        return None

# --- API Class ---
class Api:
    def __init__(self, tweak_manager):
        self._window = None; self.tweak_manager = tweak_manager
    def set_window(self, window): self._window = window
    def reposition_window(self, x, y, width, height):
        if self._window: self._window.resize(width, height); self._window.move(x, y)
    def save_window_state(self):
        if self._window:
            try:
                with open(CONFIG_FILE, 'w') as f: json.dump({'size': (self._window.width, self._window.height), 'position': (self._window.x, self._window.y)}, f)
            except IOError as e: print(f"Error saving state: {e}")
    def get_tweaks(self): return self.tweak_manager.get_all_tweaks()
    def get_tweak_states(self): return self.tweak_manager.get_tweak_states()
    def apply_tweak(self, tweak_id): return self.tweak_manager.apply_tweak(tweak_id)
    def revert_tweak(self, tweak_id): return self.tweak_manager.revert_tweak(tweak_id)
    def close_app(self):
        if self._window: self.save_window_state(); self._window.destroy()
    def get_system_analysis(self):
        states = self.tweak_manager.get_tweak_states()
        recommendations = []
        recommended_ids = ["prioritize_apps", "optimize_memory", "disable_network_throttling", "disable_telemetry_services", "disable_game_bar"]
        for tweak_id in recommended_ids:
            if states.get(tweak_id) and not states[tweak_id]['is_applied']:
                recommendations.append(self.tweak_manager._find_tweak(tweak_id))
        return recommendations

# --- Main execution block ---
if __name__ == "__main__":
    if is_admin():
        try:
            # Load config first, gracefully handling its absence
            config = TweakManager(CONFIG_FILE, '')._load_json(CONFIG_FILE, {})
            size, pos = config.get('size', (1200, 800)), config.get('position', (100, 100))
            
            # Initialize the backend engine
            tweak_manager = TweakManager(TWEAKS_FILE, UNDO_FILE)
            api = Api(tweak_manager)
            
            # Create the window and inject the API
            window = webview.create_window('Pro Tweak Utility', os.path.join(WEB_DIR, 'index.html'), width=size[0], height=size[1], x=pos[0], y=pos[1], frameless=True, resizable=True, easy_drag=False, js_api=api)
            window.events.closing += api.save_window_state
            api.set_window(window)
            webview.start()
        except Exception as e:
            ctypes.windll.user32.MessageBoxW(0, f"A critical error occurred on startup:\n\n{e}\n\nPlease check your tweaks.json file for syntax errors.", "Startup Error", 0x10)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)