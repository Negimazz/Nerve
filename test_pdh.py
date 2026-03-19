import win32pdh
import time

try:
    print("Testing win32pdh...")
    # Get all instances of GPU Engine
    paths = win32pdh.ExpandCounterPath(r'\GPU Engine(*engtype_3D)\Utilization Percentage')
    print("Paths:", paths)
    
    hq = win32pdh.OpenQuery()
    counters = []
    for p in paths:
        counters.append(win32pdh.AddCounter(hq, p))
        
    win32pdh.CollectQueryData(hq)
    time.sleep(0.1) # Wait for sample to be collected
    win32pdh.CollectQueryData(hq)
    
    total = 0.0
    for c in counters:
        type, val = win32pdh.GetFormattedCounterValue(c, win32pdh.PDH_FMT_DOUBLE)
        total += val
    print(f"Total GPU: {total}%")
except Exception as e:
    print("Error:", e)
