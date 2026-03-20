import psutil
import time
import threading

try:
    import win32pdh
    HAS_PDH = True
except ImportError:
    HAS_PDH = False

class RawMetrics:
    def __init__(self):
        psutil.cpu_percent(interval=None)
        self.net_io_start = psutil.net_io_counters()
        self.last_net_time = time.time()
        
        self.raw_cpu = 0.0
        self.raw_mem = 0.0
        self.raw_gpu = 0.0
        self.tx_rate = 0.0
        self.rx_rate = 0.0
        
        self.top_procs = []
        self.processes = {}
        
        if HAS_PDH:
            try:
                self.pdh_query = win32pdh.OpenQuery()
                self.pdh_paths = set()
                self.pdh_counters = []
            except Exception:
                pass
                
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
            new_paths = [p for p in paths if p not in self.pdh_paths]
            for p in new_paths:
                self.pdh_counters.append(win32pdh.AddCounter(self.pdh_query, p))
                self.pdh_paths.add(p)
                
            win32pdh.CollectQueryData(self.pdh_query)
            total = 0.0
            for c in self.pdh_counters:
                try:
                    _, val = win32pdh.GetFormattedCounterValue(c, win32pdh.PDH_FMT_DOUBLE)
                    total += val
                except Exception:
                    pass
            return total
        except Exception:
            return 0.0
            
    def _update_top_procs(self):
        try:
            current_pids = set(psutil.pids())
        except Exception:
            return
            
        for pid in list(self.processes.keys()):
            if pid not in current_pids:
                del self.processes[pid]
                
        proc_list = []
        cpu_count = psutil.cpu_count() or 1
        
        for i, pid in enumerate(current_pids):
            if i % 5 == 0:
                time.sleep(0.002)
            if pid not in self.processes:
                try:
                    p = psutil.Process(pid)
                    p.cpu_percent(interval=None)
                    self.processes[pid] = p
                except Exception:
                    continue
            try:
                p = self.processes[pid]
                cpu = p.cpu_percent(interval=None) / cpu_count
                name = p.name()
                if pid != 0 and name != "System Idle Process":
                    proc_list.append((cpu, name, pid))
            except Exception:
                pass
                
        proc_list.sort(key=lambda x: x[0], reverse=True)
        self.top_procs = proc_list[:3]
        
    def sample(self):
        curr_time = time.time()
        self.raw_cpu = psutil.cpu_percent(interval=None)
        self.raw_mem = psutil.virtual_memory().percent
        
        net_io = psutil.net_io_counters()
        dt = curr_time - self.last_net_time
        if dt > 0:
            self.tx_rate = (net_io.bytes_sent - self.net_io_start.bytes_sent) / dt
            self.rx_rate = (net_io.bytes_recv - self.net_io_start.bytes_recv) / dt
            self.net_io_start = net_io
            self.last_net_time = curr_time
            
        return {
            'raw_cpu': self.raw_cpu,
            'raw_mem': self.raw_mem,
            'raw_gpu': self.raw_gpu,
            'tx_rate': self.tx_rate,
            'rx_rate': self.rx_rate,
            'top_procs': self.top_procs,
            'curr_time': curr_time
        }
