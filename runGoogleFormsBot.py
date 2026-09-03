'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

Google Forms Auto-Apply Runner
Discovers Google Forms from LinkedIn hiring posts or applies directly to provided form links using Groq AI.
'''

import sys
import argparse
import time

from modules.helpers import print_lg, ensure_linkedin_login
from modules.open_chrome import createChromeSession
from modules.ai.connections import create_ai_client
from modules.google_form_filler import GoogleFormFiller
from modules.linkedin_posts_scraper import LinkedInPostsScraper
import config.questions as q_cfg


def main():
    parser = argparse.ArgumentParser(description="Google Forms Job Auto-Apply Bot")
    parser.add_argument("--url", type=str, help="Apply directly to a specific Google Form URL")
    parser.add_argument("--file", type=str, help="Path to a text file containing Google Form URLs (one per line)")
    parser.add_argument("--scrape-posts", action="store_true", help="Scrape LinkedIn posts for hiring Google Forms and auto-apply")
    parser.add_argument("--no-pause", action="store_true", help="Do not pause for manual review before submitting forms")

    args = parser.parse_args()

    pause_before_submit = not args.no_pause and getattr(q_cfg, "pause_before_submit", True)

    target_url = args.url
    file_path = args.file
    auto_scrape = args.scrape_posts

    if not target_url and not file_path and not auto_scrape:
        print("\n" + "="*65)
        print("📝 GOOGLE FORMS JOB AUTO-APPLY ENGINE (POWERED BY GROQ AI)")
        print("="*65)
        print("  [1] 🔍 Search LinkedIn Hiring Posts for Google Forms (Auto-Scrape & Apply)")
        print("  [2] 📋 Paste a Google Form Link (e.g. https://forms.gle/...) and Auto-Apply")
        print("  [3] 📁 Batch Apply from a Text File of Google Form URLs")
        print("  [0] ❌ Cancel & Return")
        print("="*65)

        try:
            choice = input("\n👉 Enter option (0-3) [Default: 1]: ").strip() or "1"
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return

        if choice == "0":
            return
        elif choice == "2":
            try:
                target_url = input("\n👉 Enter Google Form URL (e.g. https://forms.gle/...): ").strip()
            except (KeyboardInterrupt, EOFError):
                return
            if not target_url:
                print("No URL provided. Exiting.")
                return
        elif choice == "3":
            try:
                file_path = input("\n👉 Enter path to text file containing links: ").strip()
            except (KeyboardInterrupt, EOFError):
                return
        else:
            auto_scrape = True

    print_lg("\nLaunching Chrome browser...")
    try:
        options, driver, actions, wait = createChromeSession()
    except Exception as e:
        print_lg(f"❌ Error launching Chrome: {e}")
        sys.exit(1)

    if not driver:
        print_lg("❌ Could not launch Chrome driver. Exiting.")
        sys.exit(1)

    # 1. Check LinkedIn Authentication if scraping posts
    if auto_scrape:
        ensure_linkedin_login(driver)

    # 2. Initialize Groq AI Client
    ai_client = create_ai_client()

    # 3. Initialize Form Filler and Scraper
    filler = GoogleFormFiller(driver=driver, ai_client=ai_client)
    scraper = LinkedInPostsScraper(driver=driver)

    forms_to_process = []

    # Decide Mode
    if target_url:
        forms_to_process.append({"url": target_url, "role": "Direct URL", "snippet": ""})
    elif file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    u = line.strip()
                    if u and ("forms.gle" in u or "docs.google.com/forms" in u):
                        forms_to_process.append({"url": u, "role": "File Input", "snippet": ""})
        except Exception as e:
            print_lg(f"Error reading file {file_path}: {e}")
            driver.quit()
            sys.exit(1)
    else:
        print_lg("\n🔍 Searching LinkedIn feed and hiring posts for Google Forms matching your target roles...")
        forms_to_process = scraper.scrape_posts_for_forms()

    if not forms_to_process:
        print_lg("\nNo Google Forms to process. Exiting.")
        driver.quit()
        return

    print_lg(f"\n📋 Starting application process for {len(forms_to_process)} form(s)...")

    success_count = 0
    fail_count = 0

    for idx, item in enumerate(forms_to_process, 1):
        url = item["url"]
        print_lg(f"\n[{idx}/{len(forms_to_process)}] Processing Form: {url}")
        success = filler.apply_to_form(url, pause_before_submit=pause_before_submit)
        if success:
            success_count += 1
        else:
            fail_count += 1
        time.sleep(2)

    print_lg("\n" + "="*60)
    print_lg("🎯 GOOGLE FORMS BATCH COMPLETED")
    print_lg(f"  • Successfully submitted: {success_count}")
    print_lg(f"  • Skipped / Failed: {fail_count}")
    print_lg("  • Log saved in: all excels/applied_google_forms.csv")
    print_lg("="*60 + "\n")

    try:
        input("Press Enter to close the browser...")
    except Exception:
        pass

    driver.quit()


if __name__ == "__main__":
    main()
