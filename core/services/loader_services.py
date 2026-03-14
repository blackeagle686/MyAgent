import os
import time

class ProjectLoader:

    def __init__(self, path):
        self.path = path
        self.project_content = {
            "files": [],
            "folders": []
        }

    def estimate_tokens(self, text):
        # approximation: token ≈ 4 chars
        return len(text) // 4

    def scan_directory(self, path=None):

        if path is None:
            path = self.path

        for item in os.listdir(path):

            full_path = os.path.join(path, item)

            if os.path.isdir(full_path):

                self.project_content["folders"].append({
                    "name": item,
                    "path": full_path
                })
                self.scan_directory(full_path)

            elif os.path.isfile(full_path):

                file_obj = {}

                file_type = os.path.splitext(item)[1]

                file_obj["name"] = item
                file_obj["path"] = full_path
                file_obj["type"] = file_type

                # filesystem metadata
                file_obj["size_bytes"] = os.path.getsize(full_path)
                file_obj["last_modified"] = time.ctime(os.path.getmtime(full_path))

                try:

                    with open(full_path, "r", encoding="utf-8") as f:

                        content = f.read()

                        file_obj["content"] = content
                        file_obj["char_length"] = len(content)
                        file_obj["word_count"] = len(content.split())
                        file_obj["line_count"] = content.count("\n") + 1
                        file_obj["token_estimate"] = self.estimate_tokens(content)

                except Exception:

                    file_obj["content"] = None
                    file_obj["binary"] = True

                self.project_content["files"].append(file_obj)

  
  