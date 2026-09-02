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

    print_lg("\n" + "="*60)
    print_lg("🚀 GOOGLE FORMS AUTO-APPLY BOT (POWERED BY GROQ AI)")
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

    # 2. Check LinkedIn Authentication
    ensure_linkedin_login(driver)

    # 3. Initialize Groq AI Client
    ai_client = create_ai_client()

    # 4. Initialize Form Filler and Scraper
    filler = GoogleFormFiller(driver=driver, ai_client=ai_client)
    scraper = LinkedInPostsScraper(driver=driver)

    forms_to_process = []

    # Decide Mode
    if args.url:
        forms_to_process.append({"url": args.url.strip(), "role": "Direct URL", "snippet": ""})
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                for line in f:
                    u = line.strip()
                    if u and ("forms.gle" in u or "docs.google.com/forms" in u):
                        forms_to_process.append({"url": u, "role": "File Input", "snippet": ""})
        except Exception as e:
            print_lg(f"Error reading file {args.file}: {e}")
            driver.quit()
            sys.exit(1)
    else:
        # Default: Immediately start searching LinkedIn hiring posts for Google Forms
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
