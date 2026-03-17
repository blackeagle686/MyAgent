import subprocess, sys
with open("./heavy_tasks.txt", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        print(f"Running: {line}")
        result = subprocess.run(line, shell=True, check=False)
        if result.returncode != 0:
            print(f"Failed: {line} (exit {result.returncode})")
            sys.exit(result.returncode)
print("All tasks completed successfully.")