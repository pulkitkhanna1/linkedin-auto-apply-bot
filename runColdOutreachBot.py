'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

LinkedIn Cold Outreach Bot Runner
Automates recruiter discovery, hiring manager outreach, and sending personalized connection notes with Groq AI.
'''

import sys
import argparse
import time

from modules.helpers import print_lg
from modules.open_chrome import createChromeSession
from modules.ai.connections import create_ai_client
from modules.cold_message_generator import ColdMessageGenerator
from modules.linkedin_outreach import LinkedInOutreach
import config.search as search_cfg
import config.questions as q_cfg


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Recruiter Cold Outreach Bot")
    parser.add_argument("--profile", type=str, help="Direct LinkedIn profile URL of recruiter to message")
    parser.add_argument("--file", type=str, help="Text file containing recruiter LinkedIn URLs (one per line)")
    parser.add_argument("--company", type=str, default="", help="Target company name (e.g. 'Google', 'Pocket FM', 'Zepto')")
    parser.add_argument("--role", type=str, default="Program Manager", help="Target role (e.g. 'Program Manager', 'Growth Manager')")
    parser.add_argument("--from-jobs", action="store_true", help="Scrape job listings and message the hiring team / job posters")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of recruiters to message in this session (default: 10)")
    parser.add_argument("--no-pause", action="store_true", help="Do not pause for manual review before sending")

    args = parser.parse_args()

    pause_before_send = not args.no_pause and getattr(q_cfg, "pause_before_submit", True)

    print_lg("\n" + "="*60)
    print_lg("🤝 LINKEDIN RECRUITER COLD OUTREACH BOT (GROQ AI)")
    print_lg("="*60 + "\n")

    # 1. Initialize Chrome Browser
    print_lg("Launching Chrome browser...")
    try:
        options, driver, actions, wait = createChromeSession()
    except Exception as e:
        print_lg(f"❌ Error launching Chrome: {e}")
        sys.exit(1)

    if not driver:
        print_lg("❌ Could not launch Chrome driver. Exiting.")
        sys.exit(1)

    # 2. Initialize AI Generator and Outreach Handler
    ai_client = create_ai_client()
    generator = ColdMessageGenerator(ai_client=ai_client)
    outreach = LinkedInOutreach(driver=driver, message_generator=generator)

    targets = []

    # Decide Mode
    if args.profile:
        targets.append({
            "url": args.profile.strip(),
            "name": "",
            "company": args.company,
            "target_role": args.role
        })
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                for line in f:
                    u = line.strip()
                    if u and "linkedin.com/in/" in u:
                        targets.append({
                            "url": u,
                            "name": "",
                            "company": args.company,
                            "target_role": args.role
                        })
        except Exception as e:
            print_lg(f"Error reading file {args.file}: {e}")
            driver.quit()
            sys.exit(1)
    else:
        # Interactive Mode Selection
        print_lg("Select Outreach Mode:")
        print_lg("1. Search & Message Recruiters by Role & Company")
        print_lg("2. Reach out to a single recruiter profile URL")
        print_lg("3. Message a list of profiles from a file")

        try:
            choice = input("\nEnter choice (1, 2, or 3) [Default: 1]: ").strip() or "1"
        except Exception:
            choice = "1"

        if choice == "2":
            single_url = input("Enter LinkedIn Recruiter Profile URL: ").strip()
            if single_url:
                target_comp = input("Company name (optional): ").strip()
                target_r = input("Target role (e.g. Program Manager): ").strip() or "Program Manager"
                targets.append({
                    "url": single_url,
                    "name": "",
                    "company": target_comp,
                    "target_role": target_r
                })
        elif choice == "3":
            filepath = input("Enter path to file with URLs: ").strip()
            if filepath:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        u = line.strip()
                        if u and "linkedin.com/in/" in u:
                            targets.append({"url": u, "name": "", "company": "", "target_role": "Program Manager"})
        else:
            comp_input = args.company
            if not comp_input:
                try:
                    comp_input = input("Enter Target Company (leave blank for general recruiters in your location): ").strip()
                except Exception:
                    comp_input = ""

            role_input = args.role
            if not role_input or role_input == "Program Manager":
                try:
                    r_in = input(f"Enter Target Role [Default: {args.role}]: ").strip()
                    if r_in:
                        role_input = r_in
                except Exception:
                    role_input = "Program Manager"

            targets = outreach.search_recruiters(
                company=comp_input,
                target_role=role_input,
                max_results=args.limit
            )

    if not targets:
        print_lg("\nNo recruiters found or specified. Exiting.")
        driver.quit()
        return

    print_lg(f"\n📋 Starting outreach process for {min(len(targets), args.limit)} recruiter(s)...")

    sent_count = 0
    skipped_count = 0

    for idx, target in enumerate(targets[:args.limit], 1):
        url = target["url"]
        name = target.get("name", "")
        comp = target.get("company", "")
        role = target.get("target_role", "Program Manager")

        print_lg(f"\n[{idx}/{min(len(targets), args.limit)}] Connecting with: {url}")
        success = outreach.send_connection_request(
            profile_url=url,
            recruiter_name=name,
            company=comp,
            target_role=role,
            pause_before_send=pause_before_send
        )

        if success:
            sent_count += 1
        else:
            skipped_count += 1

        # Human-like delay between profile visits to prevent rate limiting
        time.sleep(4)

    print_lg("\n" + "="*60)
    print_lg("🎯 OUTREACH BATCH COMPLETED")
    print_lg(f"  • Successfully sent: {sent_count}")
    print_lg(f"  • Skipped / Failed: {skipped_count}")
    print_lg("  • Log saved in: all excels/sent_cold_messages.csv")
    print_lg("="*60 + "\n")

    try:
        input("Press Enter to close the browser...")
    except Exception:
        pass

    driver.quit()


if __name__ == "__main__":
    main()
