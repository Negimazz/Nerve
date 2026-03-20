import os
import time
from colorama import init

init(autoreset=True)

BLOCKS = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
FRACTIONAL_BLOCKS = [' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']

def fade_color(r, g, b, alpha):
    return int(r * alpha), int(g * alpha), int(b * alpha)

def get_color(ratio):
    ratio = max(0.0, min(1.0, ratio))
    # Smooth gradient from Green -> Yellow -> Red
    if ratio < 0.5:
        # Green to Yellow
        r = int(255 * (ratio * 2))
        g = 255
        b = 0
    else:
        # Yellow to Red
        r = 255
        g = int(255 * (1.0 - (ratio - 0.5) * 2))
        b = 0
    return r, g, b

def rgb_fg(r, g, b):
    return f'\033[38;2;{r};{g};{b}m'

def reset_color():
    return '\033[0m'

def format_bytes(b):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024.0:
            return f"{b:5.1f} {unit}/s"
        b /= 1024.0
    return f"{b:5.1f} TB/s"

def draw_bar(value_pct, width, avg_pct=None):
    bar = ""
    filled_len = int((value_pct / 100.0) * width)
    
    avg_idx = -1
    if avg_pct is not None:
        avg_idx = int((avg_pct / 100.0) * width)
        avg_idx = max(0, min(width - 1, avg_idx))
    
    for i in range(width):
        ratio = i / max(1, width - 1)
        r, g, b = get_color(ratio)
        color = rgb_fg(r, g, b)
        
        if i == avg_idx:
            # Draw an average line
            if i < filled_len:
                bar += f"\033[38;2;255;255;255m│\033[0m"
            else:
                bar += f"\033[38;2;120;120;120m│\033[0m"
        else:
            if i < filled_len:
                bar += f"{color}■"
            else:
                bar += f"\033[38;2;40;40;40m-" # Dim gray rest
            
    return bar + reset_color()

WAVE_CHARS = [' ', '⡀', '⣀', '⣄', '⣤', '⣦', '⣶', '⣾', '⣿']

def draw_network_waveform(history, width, is_tx=True):
    if not history:
        return " " * width
        
    history = history[-width:]
    if len(history) < width:
        history = [0] * (width - len(history)) + history
        
    # Find max for glowing effect but keep a minimum scale
    max_val = max(history)
    scale = max_val if max_val > 1024 else 1024 # Min scale 1KB/s
    
    wave = ""
    # Solid bright colors for visibility instead of gradient
    base_color = "\033[38;2;50;255;50m" if is_tx else "\033[38;2;50;255;255m"
    
    for val in history:
        ratio = val / scale if scale > 0 else 0
        idx = int(ratio * 8)
        idx = max(0, min(8, idx))
        
        # Show at least a tiny dot for non-zero traffic to make it obvious
        if idx == 0 and val > 0:
            idx = 1
            
        wave += f"{base_color}{WAVE_CHARS[idx]}"
        
    return wave + reset_color()

def render_frame(metrics_data, term_width, term_height):
    lines = []
    
    # IDLE Check
    is_idle = metrics_data.get('is_idle', False)
    status_tag = "\033[1;36m[ IDLE ]\033[0m" if is_idle else "\033[1;32m[ ACTIVE ]\033[0m"
    
    # Header
    title = f" \033[1;37mNerve \033[38;2;100;100;100m- Real-Time System Monitor {status_tag} "
    lines.append(title.center(term_width + 48))
    
    # Dim header line if idle
    sep_color = "\033[38;2;30;30;30m" if is_idle else "\033[38;2;50;50;50m"
    lines.append(sep_color + "━" * term_width + reset_color())
    
    left_margin = 10
    bar_width = term_width - left_margin - 12
    bar_width = max(10, bar_width)
    
    # CPU
    cpu_pct = metrics_data['cpu']
    avg_cpu = metrics_data.get('avg_cpu', 0.0)
    cpu_bar = draw_bar(cpu_pct, bar_width, avg_cpu)
    lines.append(f" \033[1;37mCPU \033[0m: {cpu_bar} {cpu_pct:5.1f}%")
    
    # GPU
    gpu_pct = metrics_data.get('gpu', 0.0)
    avg_gpu = metrics_data.get('avg_gpu', 0.0)
    gpu_bar = draw_bar(gpu_pct, bar_width, avg_gpu)
    lines.append(f" \033[1;37mGPU \033[0m: {gpu_bar} {gpu_pct:5.1f}%")
    
    # Mem
    mem_pct = metrics_data['mem']
    avg_mem = metrics_data.get('avg_mem', 0.0)
    mem_bar = draw_bar(mem_pct, bar_width, avg_mem)
    lines.append(f" \033[1;37mMEM \033[0m: {mem_bar} {mem_pct:5.1f}%")
    
    lines.append(sep_color + "━" * term_width + reset_color())
    
    # Network
    tx_rate = metrics_data['tx_rate']
    rx_rate = metrics_data['rx_rate']
    tx_str = format_bytes(tx_rate)
    rx_str = format_bytes(rx_rate)
    
    net_width = term_width - 16 - len(tx_str) # Waveform width
    net_width = max(10, net_width)
    
    tx_wave = draw_network_waveform(metrics_data['tx_history'], net_width, is_tx=True)
    rx_wave = draw_network_waveform(metrics_data['rx_history'], net_width, is_tx=False)
    
    lines.append(f" \033[1;32mTX \033[0m: [\033[38;2;150;150;150m{tx_str:10}\033[0m] {tx_wave}")
    lines.append(f" \033[1;36mRX \033[0m: [\033[38;2;150;150;150m{rx_str:10}\033[0m] {rx_wave}")
    
    lines.append(sep_color + "━" * term_width + reset_color())
    
    # Top Processes
    lines.append(" \033[1;37mTop Processes (CPU)\033[0m")
    for cpu, name, pid in metrics_data['top_procs']:
        r, g, b = get_color(cpu / 100.0)
        color = rgb_fg(r, g, b)
        lines.append(f"  {color}{cpu:5.1f}%\033[0m \033[38;2;150;150;150m{pid:<6}\033[0m {name[:term_width-20]}")
    
    lines.append(sep_color + "━" * term_width + reset_color())
    
    # Events section with overflow protection
    remaining_lines = term_height - len(lines) - 2 # 1 title, 1 safety margin
    if remaining_lines > 0:
        lines.append(" \033[1;37mEvent Logs\033[0m")
        if not metrics_data['events']:
            lines.append("  \033[38;2;100;100;100mNo events detected yet...\033[0m")
        else:
            curr_time = time.time()
            visible_events = metrics_data['events'][-remaining_lines:]
            for event in visible_events:
                age = curr_time - event['time']
                alpha = 1.0 if age < 3.0 else max(0.0, 1.0 - (age - 3.0) / 3.0)
                
                severity = event.get('severity', 'low')
                if severity == 'high':
                    r, g, b = fade_color(255, 50, 50, alpha)
                elif severity == 'mid':
                    r, g, b = fade_color(255, 200, 50, alpha)
                elif severity == 'low':
                    r, g, b = fade_color(50, 200, 255, alpha)
                else:
                    if event.get('is_spike'): r, g, b = fade_color(255, 50, 50, alpha)
                    else: r, g, b = fade_color(200, 200, 200, alpha)
                    
                lines.append(f"  \033[38;2;{r};{g};{b}m{event['text']}\033[0m\033[K")
                
    # Force strictly padding up to term height limits
    while len(lines) < term_height - 1:
        lines.append("")
        
    if len(lines) >= term_height:
        lines = lines[:term_height-1]
        
    # Apply clear-to-end-of-line (\033[K) globally to all lines to prevent horizontal ghosting
    lines = [l + "\033[K" for l in lines]
            
    return "\n".join(lines)
