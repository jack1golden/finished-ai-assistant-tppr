import numpy as np
import time

def gas_data_stream():
    t = 0
    while True:
        base = np.sin(t/10.0) * 5 + 20
        spike = 0
        if np.random.rand() < 0.01:  # occasional spike
            spike = np.random.randint(30, 80)
        yield base + spike + np.random.randn()*2
        t += 1
        time.sleep(0.5)
