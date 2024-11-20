import subprocess

def run_go_script():
    result = subprocess.run(["./crons"], capture_output=True, text=True)
    if result.returncode == 0:
        print("Go script output:", result.stdout)
    else:
        print("Error:", result.stderr)

if __name__ == "__main__":
    run_go_script()
