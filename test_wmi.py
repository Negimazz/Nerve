import wmi
import time

try:
    print("Starting WMI Query...")
    start = time.time()
    w = wmi.WMI()
    total = sum(int(item.UtilizationPercentage) for item in w.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine() if 'engtype_3D' in item.Name)
    print(f"GPU: {total}% (took {time.time() - start:.2f}s)")
except Exception as e:
    print("Error:", e)
