'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

LinkedIn Post Scraper Module
Finds hiring posts on LinkedIn that contain Google Form links and extracts valid form URLs.
'''

import re
import time
import urllib.parse
from typing import List, Dict, Set
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

import config.search as search_cfg
from modules.helpers import print_lg
from modules.google_form_filler import is_form_already_applied

# Regex to find forms.gle and docs.google.com/forms links
GOOGLE_FORM_REGEX = re.compile(
    r'https?://(?:forms\.gle/[a-zA-Z0-9_-]+|docs\.google\.com/forms/d/(?:e/)?[a-zA-Z0-9_-]+/viewform[^\s"\'<>]*|docs\.google\.com/forms/d/[a-zA-Z0-9_-]+[^\s"\'<>]*)',
    re.IGNORECASE
)


class LinkedInPostsScraper:
    '''Scrapes LinkedIn post feed for hiring announcements containing Google Forms.'''

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def build_search_url(self, role_title: str) -> str:
        '''Build LinkedIn content search URL with date filter.'''
        query = f'"{role_title}" ("forms.gle" OR "google form" OR "application form" OR "hiring")'
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&sortBy=%22date_posted%22"
        return url

    def extract_forms_from_text(self, text: str) -> List[str]:
        '''Extract Google Form links from a block of text.'''
        if not text:
            return []
        matches = GOOGLE_FORM_REGEX.findall(text)
        cleaned = []
        for url in matches:
            # Clean trailing punctuation
            u = re.sub(r'[\.,;:\)\]\>]+$', '', url.strip())
            cleaned.append(u)
        return cleaned

    def scrape_posts_for_forms(self, role_titles: List[str] = None, max_posts_per_role: int = 25) -> List[Dict[str, str]]:
        '''
        Search LinkedIn for each role title, scroll feed, and collect unique Google Form URLs.
        Returns a list of dicts: [{"url": form_url, "post_text": ..., "role": role_title}]
        '''
        roles = role_titles or getattr(search_cfg, "search_terms", ["Program Manager", "Growth Manager", "Product Manager"])
        found_forms: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()

        for role in roles:
            search_url = self.build_search_url(role)
            print_lg(f"\n[LinkedIn Posts Search]: Looking for hiring posts for '{role}'...")
            print_lg(f"URL: {search_url}")

            try:
                self.driver.get(search_url)
                time.sleep(4)

                # Check if logged in
                if "feed" not in self.driver.current_url and "search" not in self.driver.current_url:
                    print_lg("⚠️ Please make sure you are logged into LinkedIn in the opened Chrome window.")
                    time.sleep(5)

                # Scroll and expand posts
                scroll_count = 0
                max_scrolls = 6

                while scroll_count < max_scrolls:
                    # Click all "...see more" buttons to expand post text
                    see_more_buttons = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        'button.feed-shared-inline-show-more-text__see-more-less-toggle, button.see-more, button[aria-label*="see more"]'
                    )
                    for btn in see_more_buttons:
                        try:
                            if btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", btn)
                        except Exception:
                            pass

                    time.sleep(1)

                    # Extract all post elements
                    post_containers = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        'div.feed-shared-update-v2, div[data-urn*="urn:li:activity"], div.update-components-text'
                    )

                    for container in post_containers:
                        try:
                            post_text = container.text
                            form_links = self.extract_forms_from_text(post_text)

                            # Also inspect any <a> tags in the post
                            links = container.find_elements(By.TAG_NAME, 'a')
                            for link in links:
                                href = link.get_attribute('href') or ""
                                # Follow redirected or short links if applicable
                                form_links.extend(self.extract_forms_from_text(href))

                            for form_url in form_links:
                                norm_url = form_url.split("?")[0].strip()
                                if norm_url not in seen_urls:
                                    seen_urls.add(norm_url)
                                    if is_form_already_applied(norm_url):
                                        print_lg(f"  ↪ Skipping already applied form: {norm_url}")
                                        continue
                                    print_lg(f"  ✨ Found New Google Form link: {form_url}")
                                    found_forms.append({
                                        "url": form_url,
                                        "role": role,
                                        "snippet": post_text[:200].replace("\n", " ")
                                    })
                        except Exception:
                            continue

                    # Scroll down
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    scroll_count += 1
                    time.sleep(2.5)

            except Exception as e:
                print_lg(f"Error scraping LinkedIn posts for role '{role}': {e}")

        print_lg(f"\n🎯 Total new Google Forms discovered: {len(found_forms)}")
        return found_forms
