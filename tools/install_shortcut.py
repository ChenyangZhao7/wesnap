"""Create the Desktop shortcut for WeSnap via WScript.Shell."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYW = Path(r"C:\Users\21165\AppData\Local\Python\bin\pythonw.exe")
SCRIPT = ROOT / "wesnap" / "main.pyw"
WORKDIR = ROOT / "wesnap"
ICON = ROOT / "wesnap" / "wesnap.ico"
LNK_NAME = "微截.lnk"


def main() -> None:
    ps = "\n".join([
        "$ws = New-Object -ComObject WScript.Shell",
        "$desktop = [Environment]::GetFolderPath('Desktop')",
        f"$lnk = $ws.CreateShortcut((Join-Path $desktop '{LNK_NAME}'))",
        f"$lnk.TargetPath = '{PYW}'",
        f"$lnk.Arguments = '\"{SCRIPT}\"'",
        f"$lnk.WorkingDirectory = '{WORKDIR}'",
        f"$lnk.IconLocation = '{ICON}'",
        "$lnk.Save()",
    ])
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-Command", ps], check=True)
    print(f"desktop shortcut created: {LNK_NAME}")


if __name__ == "__main__":
    sys.exit(main())
