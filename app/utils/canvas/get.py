import time
import json
import undetected_chromedriver as uc
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'canvas.html')
results_path = os.path.join(script_dir, 'results.jsonl')

options = uc.ChromeOptions()
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = uc.Chrome(options=options)

try:
    driver.get(f"file://{file_path}")

    time.sleep(5)

    fingerprints = driver.execute_script("""
        const fps = generateMultipleFingerprints(10000);
        return Array.from(fps);
    """)

    with open(results_path, 'a') as f:
        for fingerprint in fingerprints:
            f.write(json.dumps({"fingerprint": fingerprint}) + "\n")

    print(f"Сохранено {len(fingerprints)} отпечатков в {results_path}")

finally:
    driver.quit()
