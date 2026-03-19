# Nerve 📡

**Nerve** is a real-time, terminal-based system monitoring tool designed to intuitively visualize your entire system's condition (CPU, GPU, Memory, and Network).

Built around the concept of "keeping it at the edge of your screen to feel system changes," Nerve avoids heavy UI libraries. By utilizing native ANSI escape sequences and Windows Performance Counters, it achieves a perfect balance of **beautiful visuals and ultra-lightweight performance (smooth 50 FPS updates)**.

## Features 🚀
- **🔥 Smooth Animations**: Applies Exponential Smoothing to raw metrics, resulting in incredibly fluid (50 FPS) indicator movements.
- **📊 Granular Independent Bars**: Uses square blocks (■) for progress bars to achieve a clean, sophisticated look in the terminal. An average line (│) is overlaid for quick reference.
- **🌊 Network Waveforms**: Renders streaming traffic history as a beautiful line chart using Braille characters.
- **🎮 Native GPU Support**: Uses `win32pdh` to accurately and lightly measure Windows "GPU Engine 3D" utilization across any vendor (Intel / AMD / NVIDIA), including integrated graphics.
- **💤 Auto-IDLE Detection**: When system load and network traffic remain consistently low, the UI automatically shifts into a subdued `[ IDLE ]` theme.
- **🚨 Spike Detection**: Automatically logs sudden spikes in system load or network bursts. (Logs fade out smoothly to black 3 seconds after appearing).
- **💻 Standalone Executable**: Compiled into a single binary via PyInstaller. No environment setup is required—it runs instantly.

## Installation & Usage 💻

Run it as a global command from any terminal:

```powershell
# Launch Nerve from anywhere
nerve
```

> **Note**: Nerve is optimized for a horizontal layout (like a split terminal in VSCode). Press `Ctrl + C` to exit.

## Development (Local Build)
To build Nerve locally on a Python 3.11 environment:

```powershell
pip install -e .
pyinstaller --onefile nerve.py
```

## System Requirements ⚙️
- Windows 10 / 11
- (*Python 3.10+ or simply use the compiled `nerve.exe`*)

---
`// yyy was here.`
