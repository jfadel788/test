import threading
import queue
import requests

q = queue.Queue()
valid_proxies = []

# Read the proxies from a file and populate the queue
with open('./proxy.txt') as f:
    proxies = f.read().split('\n')
    for proxy in proxies:
        q.put(proxy)

def check_proxy(q):
    while not q.empty():
        proxy = q.get()
        try:
            response = requests.get('https://httpbin.org/ip', proxies={'http': proxy, 'https': proxy}, timeout=5)
            if response.status_code == 200:
                with open('./valid_proxy.txt', 'a') as f:
                    f.write(proxy + '\n')
        except:
            continue
        finally:
            q.task_done()

# Create and start threads
threads = []

for i in range(10):
    t = threading.Thread(target=check_proxy, args=(q,))
    t.start()
    threads.append(t)

# Wait for all threads to finish
for t in threads:
    t.join()

print("Proxy check complete.")
