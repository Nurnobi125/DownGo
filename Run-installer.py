import subprocess

if __name__ == "__main__":
    subprocess.run(["cmd.exe", "/c", "build_installer.bat"], check=True)
