'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

Master Control Hub
Select and run any of your automated job tools from one unified menu.
'''

import sys
import subprocess
import os

VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = "python3"


def banner():
    print("\n" + "="*65)
    print("      🚀 PULKIT'S LINKEDIN & JOB APPLICATION AUTOMATION SUITE")
    print("="*65)
    print("  [1] 🤖 LinkedIn Easy Apply Bot (Web Control Panel / Auto-Applier)")
    print("  [2] 📝 Google Forms Auto-Applier (LinkedIn Hiring Posts & Forms)")
    print("  [3] 🤝 Recruiter Cold Outreach Bot (AI Personalized InMails & Notes)")
    print("  [4] 🏃 Run LinkedIn Easy Apply directly in Terminal (CLI Mode)")
    print("  [5] 📊 View Applied Jobs & Outreach History (CSV Summary)")
    print("  [0] ❌ Exit")
    print("="*65)


def view_history_summary():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excels_dir = os.path.join(base_dir, "all excels")
    print("\n" + "-"*50)
    print("📁 Application & Outreach Logs:")
    if os.path.exists(excels_dir):
        files = os.listdir(excels_dir)
        for f in files:
            if f.endswith(".csv") or f.endswith(".xlsx"):
                fpath = os.path.join(excels_dir, f)
                size = os.path.getsize(fpath)
                print(f"  • {f} ({size} bytes)")
    else:
        print("  No log files created yet.")
    print("-"*50 + "\n")
    input("Press Enter to return to menu...")


def main():
    while True:
        banner()
        try:
            choice = input("\n👉 Choose an option (0-5): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Good luck with your job hunt!")
            break

        if choice == "1":
            print("\nStarting Web Control Panel at http://127.0.0.1:5000 ...")
            subprocess.run([VENV_PYTHON, "app.py"])
        elif choice == "2":
            print("\nStarting Google Forms Auto-Applier...")
            subprocess.run([VENV_PYTHON, "runGoogleFormsBot.py"])
        elif choice == "3":
            print("\nStarting Recruiter Cold Outreach Bot...")
            subprocess.run([VENV_PYTHON, "runColdOutreachBot.py"])
        elif choice == "4":
            print("\nRunning LinkedIn Easy Apply Bot directly in terminal...")
            subprocess.run([VENV_PYTHON, "runAiBot.py"])
        elif choice == "5":
            view_history_summary()
        elif choice == "0":
            print("\nExiting. Good luck with your job applications!")
            break
        else:
            print("Invalid option. Please enter a number between 0 and 5.")


if __name__ == "__main__":
    main()
