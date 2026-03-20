import time
from metrics import RawMetrics

class SystemState:
    def __init__(self):
        self.reader = RawMetrics()
        
        self.smoothed_cpu = 0.0
        self.smoothed_mem = 0.0
        self.smoothed_gpu = 0.0
        self.smoothed_tx = 0.0
        self.smoothed_rx = 0.0
        
        self.cpu_history = []
        self.mem_history = []
        self.gpu_history = []
        self.net_send_history = []
        self.net_recv_history = []
        
        self.events = []
        self.last_cpu = 0
        self.last_net_tx = 0
        self.last_net_rx = 0
        
        self.is_idle = False
        self.idle_start_time = 0.0
        self.last_sample_time = 0.0
        self.latest_raw = None
        
    def stop(self):
        self.reader.stop()
        
    def add_event(self, msg, severity="low"):
        timestamp = time.strftime("%H:%M:%S")
        self.events.append({
            'text': f"[{timestamp}] {msg}",
            'time': time.time(),
            'severity': severity
        })
        
    def update(self):
        curr_time = time.time()
        
        # Sample processing at intervals (~5-10 FPS limit)
        if curr_time - self.last_sample_time > 0.15:
            raw = self.reader.sample()
            self.latest_raw = raw
            self.last_sample_time = curr_time
            
            raw_cpu = raw['raw_cpu']
            raw_gpu = raw['raw_gpu']
            tx_rate = raw['tx_rate']
            rx_rate = raw['rx_rate']
            
            # Spike CPU
            if self.last_cpu > 0:
                diff = raw_cpu - self.last_cpu
                if diff > 15:
                    sev = "high" if diff > 40 else "mid" if diff > 25 else "low"
                    self.add_event(f"[!] CPU spike detected: +{diff:.1f}%", sev)
            self.last_cpu = raw_cpu
            
            # Burst Network
            mb_tx = tx_rate / (1024 * 1024)
            mb_rx = rx_rate / (1024 * 1024)
            if (mb_tx - self.last_net_tx) > 5.0:
                diff = mb_tx - self.last_net_tx
                sev = "high" if diff > 40.0 else "mid" if diff > 15.0 else "low"
                self.add_event(f"[!] Network TX burst: +{diff:.1f} MB/s", sev)
            if (mb_rx - self.last_net_rx) > 5.0:
                diff = mb_rx - self.last_net_rx
                sev = "high" if diff > 40.0 else "mid" if diff > 15.0 else "low"
                self.add_event(f"[!] Network RX burst: +{diff:.1f} MB/s", sev)
            self.last_net_tx = mb_tx
            self.last_net_rx = mb_rx
            
            self.cpu_history.append(raw_cpu)
            self.mem_history.append(raw['raw_mem'])
            self.gpu_history.append(raw_gpu)
            self.net_send_history.append(tx_rate)
            self.net_recv_history.append(rx_rate)
            
            if len(self.cpu_history) > 100:
                self.cpu_history.pop(0)
                self.mem_history.pop(0)
                self.gpu_history.pop(0)
                self.net_send_history.pop(0)
                self.net_recv_history.pop(0)
                
            # IDLE detection
            if raw_cpu < 10.0 and raw_gpu < 10.0 and tx_rate < 51200 and rx_rate < 51200:
                if self.idle_start_time == 0:
                    self.idle_start_time = curr_time
                elif curr_time - self.idle_start_time > 3.0:
                    self.is_idle = True
            else:
                self.idle_start_time = 0
                self.is_idle = False
                
        # Clean events gracefully fading out
        self.events = [e for e in self.events if curr_time - e['time'] < 6.0]
        
        # UI Interpolation at current framerate
        if self.latest_raw:
            alpha = 0.15
            self.smoothed_cpu += (self.latest_raw['raw_cpu'] - self.smoothed_cpu) * alpha
            self.smoothed_mem += (self.latest_raw['raw_mem'] - self.smoothed_mem) * alpha
            self.smoothed_gpu += (self.latest_raw['raw_gpu'] - self.smoothed_gpu) * alpha
            self.smoothed_tx += (self.latest_raw['tx_rate'] - self.smoothed_tx) * alpha
            self.smoothed_rx += (self.latest_raw['rx_rate'] - self.smoothed_rx) * alpha
            
        return {
            'cpu': self.smoothed_cpu,
            'mem': self.smoothed_mem,
            'gpu': self.smoothed_gpu,
            'tx_rate': self.smoothed_tx,
            'rx_rate': self.smoothed_rx,
            'tx_history': self.net_send_history,
            'rx_history': self.net_recv_history,
            'top_procs': self.latest_raw['top_procs'] if self.latest_raw else [],
            'events': self.events,
            'is_idle': self.is_idle,
            'avg_cpu': sum(self.cpu_history) / max(1, len(self.cpu_history)) if self.cpu_history else 0,
            'avg_mem': sum(self.mem_history) / max(1, len(self.mem_history)) if self.mem_history else 0,
            'avg_gpu': sum(self.gpu_history) / max(1, len(self.gpu_history)) if self.gpu_history else 0
        }
