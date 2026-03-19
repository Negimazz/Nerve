import psutil
import time
import threading

try:
    import win32pdh
    HAS_PDH = True
except ImportError:
    HAS_PDH = False

class SystemMetrics:
    def __init__(self):
        # Initialize
        psutil.cpu_percent(interval=None)
        self.net_io_start = psutil.net_io_counters()
        self.last_net_time = time.time()
        self.last_update_time = 0
        
        self.raw_cpu = 0.0
        self.raw_mem = 0.0
        self.raw_gpu = 0.0
        self.smoothed_cpu = 0.0
        self.smoothed_mem = 0.0
        self.smoothed_gpu = 0.0
        
        self.cpu_history = []
        self.mem_history = []
        self.gpu_history = []
        self.net_send_history = []
        self.net_recv_history = []
        
        self.is_idle = False
        self.idle_start_time = 0.0
        
        # Keep track of top processes
        self.top_procs = []
        self.processes = {} # pid -> psutil.Process
        
        self.events = []
        self.last_cpu = 0
        
        self.last_net_tx = 0
        self.last_net_rx = 0
        
        self.current_tx_rate = 0.0
        self.current_rx_rate = 0.0
        self.smoothed_tx = 0.0
        self.smoothed_rx = 0.0
        
        # Start background thread for process updates
        self._running = True
        self._proc_thread = threading.Thread(target=self._proc_loop, daemon=True)
        self._proc_thread.start()

    def stop(self):
        self._running = False

    def _proc_loop(self):
        while self._running:
            self._update_top_procs()
            if HAS_PDH:
                self.raw_gpu = self._update_gpu_pdh()
            time.sleep(2.0)

    def _update_gpu_pdh(self):
        try:
            paths = win32pdh.ExpandCounterPath(r'\GPU Engine(*engtype_3D)\Utilization Percentage')
            hq = win32pdh.OpenQuery()
            counters = [win32pdh.AddCounter(hq, p) for p in paths]
            win32pdh.CollectQueryData(hq)
            time.sleep(0.1)
            win32pdh.CollectQueryData(hq)
            
            total = 0.0
            for c in counters:
                _, val = win32pdh.GetFormattedCounterValue(c, win32pdh.PDH_FMT_DOUBLE)
                total += val
                
            win32pdh.CloseQuery(hq)
            return total
        except Exception:
            return 0.0

    def add_event(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        is_spike = "spike" in msg.lower() or "burst" in msg.lower()
        self.events.append({
            'text': f"[{timestamp}] {msg}",
            'time': time.time(),
            'is_spike': is_spike
        })

    def update(self):
        curr_time = time.time()
        
        # Sampling at ~5-10 FPS
        if curr_time - self.last_update_time > 0.15:
            self.raw_cpu = psutil.cpu_percent(interval=None)
            self.raw_mem = psutil.virtual_memory().percent
            
            # System Spike Detection (CPU)
            if self.last_cpu > 0:
                diff = self.raw_cpu - self.last_cpu
                if diff > 30:
                    self.add_event(f"[!] CPU spike detected: +{diff:.1f}%")
            self.last_cpu = self.raw_cpu
            
            self.cpu_history.append(self.raw_cpu)
            self.mem_history.append(self.raw_mem)
            self.gpu_history.append(self.raw_gpu)
            if len(self.cpu_history) > 100:
                self.cpu_history.pop(0)
                self.mem_history.pop(0)
                self.gpu_history.pop(0)
                
            # Network
            net_io = psutil.net_io_counters()
            dt = curr_time - self.last_net_time
            if dt > 0:
                bytes_sent = (net_io.bytes_sent - self.net_io_start.bytes_sent) / dt
                bytes_recv = (net_io.bytes_recv - self.net_io_start.bytes_recv) / dt
                
                self.current_tx_rate = bytes_sent
                self.current_rx_rate = bytes_recv
                
                mb_sent = bytes_sent / (1024 * 1024)
                mb_recv = bytes_recv / (1024 * 1024)
                
                if (mb_sent - self.last_net_tx) > 10:
                    self.add_event(f"[!] Network TX burst: +{mb_sent - self.last_net_tx:.1f} MB/s")
                if (mb_recv - self.last_net_rx) > 10:
                    self.add_event(f"[!] Network RX burst: +{mb_recv - self.last_net_rx:.1f} MB/s")
                    
                self.last_net_tx = mb_sent
                self.last_net_rx = mb_recv
                
                self.net_send_history.append(bytes_sent)
                self.net_recv_history.append(bytes_recv)
                
                if len(self.net_send_history) > 100:
                    self.net_send_history.pop(0)
                    self.net_recv_history.pop(0)
                    
            self.net_io_start = net_io
            self.last_net_time = curr_time
            self.last_update_time = curr_time
            
            # IDLE detection
            if self.raw_cpu < 10.0 and self.raw_gpu < 10.0 and self.current_tx_rate < 51200 and self.current_rx_rate < 51200:
                if self.idle_start_time == 0:
                    self.idle_start_time = curr_time
                elif curr_time - self.idle_start_time > 3.0: # 3 seconds idle
                    self.is_idle = True
            else:
                self.idle_start_time = 0
                self.is_idle = False
                
        # Clean up old events (fade out after 6 seconds)
        self.events = [e for e in self.events if curr_time - e['time'] < 6.0]
            
        # Smoothing interpolation
        alpha = 0.15
        self.smoothed_cpu += (self.raw_cpu - self.smoothed_cpu) * alpha
        self.smoothed_mem += (self.raw_mem - self.smoothed_mem) * alpha
        self.smoothed_gpu += (self.raw_gpu - self.smoothed_gpu) * alpha
        self.smoothed_tx += (self.current_tx_rate - self.smoothed_tx) * alpha
        self.smoothed_rx += (self.current_rx_rate - self.smoothed_rx) * alpha
            
        return {
            'cpu': self.smoothed_cpu,
            'mem': self.smoothed_mem,
            'gpu': self.smoothed_gpu,
            'tx_rate': self.smoothed_tx,
            'rx_rate': self.smoothed_rx,
            'tx_history': self.net_send_history,
            'rx_history': self.net_recv_history,
            'top_procs': self.top_procs,
            'events': self.events,
            'is_idle': self.is_idle,
            'avg_cpu': sum(self.cpu_history) / max(1, len(self.cpu_history)) if self.cpu_history else 0,
            'avg_mem': sum(self.mem_history) / max(1, len(self.mem_history)) if self.mem_history else 0,
            'avg_gpu': sum(self.gpu_history) / max(1, len(self.gpu_history)) if self.gpu_history else 0
        }

    def _update_top_procs(self):
        try:
            current_pids = set(psutil.pids())
        except Exception:
            return
            
        # Clean up dead
        for pid in list(self.processes.keys()):
            if pid not in current_pids:
                del self.processes[pid]
                
        proc_list = []
        cpu_count = psutil.cpu_count() or 1
        
        for i, pid in enumerate(current_pids):
            # Yield GIL frequently to prevent 50FPS main thread stuttering!
            if i % 5 == 0:
                time.sleep(0.002)
                
            if pid not in self.processes:
                try:
                    p = psutil.Process(pid)
                    p.cpu_percent(interval=None) # init
                    self.processes[pid] = p
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            try:
                p = self.processes[pid]
                cpu = p.cpu_percent(interval=None) / cpu_count
                name = p.name()
                if pid != 0 and name != "System Idle Process":
                    proc_list.append((cpu, name, pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        proc_list.sort(key=lambda x: x[0], reverse=True)
        self.top_procs = proc_list[:3]
