import os
import json


class CanvasDataUrl:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.results_file_path = os.path.join(self.script_dir, 'canvas', 'results.jsonl')
        self.is_file_exists = os.path.exists(self.results_file_path)
        
        if not self.is_file_exists:
            self.fingerprints = []
        else:
            self._load_fingerprints()


    def _load_fingerprints(self):
        with open(self.results_file_path, 'r') as f:
            self.fingerprints = f.readlines()


    def _save_fingerprints(self):
        with open(self.results_file_path, 'w') as f:
            f.writelines(self.fingerprints)


    def get_fingerprint(self):
        if len(self.fingerprints) == 0:
            raise ValueError("URL fingerprints are empty")
        
        fingerprint_json = self.fingerprints.pop(0).strip()
        self._save_fingerprints()
        fingerprint_dict = json.loads(fingerprint_json)
        
        return fingerprint_dict['fingerprint']


    def add_fingerprints(self, new_fingerprints):
        with open(self.results_file_path, 'a') as f:
            for fingerprint in new_fingerprints:
                f.write(json.dumps({"fingerprint": fingerprint}) + "\n")
        
        self._load_fingerprints()


    def check_if_empty(self):
        return len(self.fingerprints) == 0
