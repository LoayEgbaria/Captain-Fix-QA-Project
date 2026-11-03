"""
Smart Self-Healing Module for Captain Fix
Automatically detects and fixes broken test locators using AI
"""

import json
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import openai
import os


class SmartHealer:
    def __init__(self, driver, api_key=None):
        self.driver = driver
        self.healing_log = []
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')

    def find_element_with_healing(self, locator_type, locator_value, context=""):
        """
        Try to find element, if fails, attempt AI-powered healing

        Args:
            locator_type: 'id', 'css', 'xpath', 'name', 'class', 'link_text'
            locator_value: the selector value
            context: description of what element we're looking for

        Returns:
            WebElement or None
        """
        # Convert string locator_type to By constant
        by_map = {
            'id': By.ID,
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'link_text': By.LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT,
            'tag_name': By.TAG_NAME
        }

        by_type = by_map.get(locator_type.lower(), By.CSS_SELECTOR)

        # Try original locator
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((by_type, locator_value))
            )
            return element
        except (NoSuchElementException, TimeoutException):
            print(f"[HEALER] Original locator failed: {locator_type}={locator_value}")

            # Attempt healing
            healed_element = self._attempt_healing(locator_type, locator_value, context)

            if healed_element:
                print(f"[HEALER] Successfully healed! New locator found.")
                return healed_element
            else:
                print(f"[HEALER] Healing failed. Element not found.")
                return None

    def _attempt_healing(self, original_type, original_value, context):
        """
        Use multiple strategies to find the element
        """
        strategies = [
            self._try_fuzzy_text_match,
            self._try_similar_attributes,
            self._try_ai_suggestion,
            self._try_visual_position
        ]

        for strategy in strategies:
            try:
                element = strategy(original_type, original_value, context)
                if element:
                    # Log the healing
                    self.healing_log.append({
                        'original_locator': f"{original_type}={original_value}",
                        'healing_strategy': strategy.__name__,
                        'context': context,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'success': True
                    })
                    return element
            except Exception as e:
                print(f"[HEALER] Strategy {strategy.__name__} failed: {str(e)}")
                continue

        # Log failed healing attempt
        self.healing_log.append({
            'original_locator': f"{original_type}={original_value}",
            'healing_strategy': 'all_failed',
            'context': context,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'success': False
        })

        return None

    def _try_fuzzy_text_match(self, original_type, original_value, context):
        """Try to find element by partial text match"""
        if 'button' in context.lower() or 'link' in context.lower():
            # Extract potential text from original value
            text_candidates = self._extract_text_from_selector(original_value)

            for text in text_candidates:
                try:
                    # Try partial link text
                    element = self.driver.find_element(By.PARTIAL_LINK_TEXT, text)
                    return element
                except:
                    try:
                        # Try XPath with contains
                        xpath = f"//*[contains(text(), '{text}')]"
                        element = self.driver.find_element(By.XPATH, xpath)
                        return element
                    except:
                        continue
        return None

    def _try_similar_attributes(self, original_type, original_value, context):
        """Try alternative attributes (data-*, aria-*, role, etc)"""
        # Extract ID or class from original selector
        identifier = self._extract_identifier(original_value)

        if identifier:
            # Try common alternative attributes
            alternative_selectors = [
                f"[data-testid*='{identifier}']",
                f"[data-test*='{identifier}']",
                f"[aria-label*='{identifier}']",
                f"[role][class*='{identifier}']",
                f"[id*='{identifier}']",
                f"[name*='{identifier}']"
            ]

            for selector in alternative_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    return element
                except:
                    continue

        return None

    def _try_ai_suggestion(self, original_type, original_value, context):
        """Use AI to suggest alternative locators based on page structure"""
        if not self.api_key:
            return None

        try:
            # Get page source snippet
            page_source = self.driver.page_source[:5000]  # First 5000 chars

            # Create prompt for AI
            prompt = f"""You are a Selenium expert. A test locator is broken.

Original Locator: {original_type}="{original_value}"
Context: {context}
Page HTML (snippet): {page_source}

Suggest 3 alternative CSS selectors or XPath expressions that might find this element.
Return ONLY a JSON array of strings, no explanation.

Example format: ["button.submit", "input[type='submit']", "//button[@class='submit']"]
"""

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            suggestions_text = response.choices[0].message.content.strip()

            # Parse JSON response
            suggestions = json.loads(suggestions_text)

            # Try each suggestion
            for suggestion in suggestions:
                try:
                    # Determine if it's XPath or CSS
                    if suggestion.startswith('//') or suggestion.startswith('('):
                        element = self.driver.find_element(By.XPATH, suggestion)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, suggestion)

                    if element:
                        print(f"[HEALER] AI suggested working locator: {suggestion}")
                        return element
                except:
                    continue

        except Exception as e:
            print(f"[HEALER] AI suggestion failed: {str(e)}")

        return None

    def _try_visual_position(self, original_type, original_value, context):
        """Try to find element by its position/nearby elements"""
        # This is a simplified version - can be enhanced
        # Try to find elements with similar tag names nearby

        if original_type == 'id':
            # Try to find by similar ID pattern
            try:
                # Get all elements
                all_elements = self.driver.find_elements(By.XPATH, "//*[@id]")

                # Find elements with similar IDs
                for elem in all_elements:
                    elem_id = elem.get_attribute('id')
                    if elem_id and self._similarity_score(elem_id, original_value) > 0.6:
                        return elem
            except:
                pass

        return None

    def _extract_text_from_selector(self, selector):
        """Extract potential text content from selector"""
        import re
        texts = []

        # Remove special characters and split
        clean = re.sub(r'[^\w\s-]', ' ', selector)
        words = clean.split()

        for word in words:
            if len(word) > 3:  # Only meaningful words
                texts.append(word)

        return texts

    def _extract_identifier(self, selector):
        """Extract meaningful identifier from selector"""
        import re

        # Try to extract ID or class name
        matches = re.findall(r'[#.]?([\w-]+)', selector)
        if matches:
            return matches[0]

        return None

    def _similarity_score(self, str1, str2):
        """Calculate similarity between two strings (simple version)"""
        str1, str2 = str1.lower(), str2.lower()

        # Simple character overlap ratio
        common = set(str1) & set(str2)
        total = set(str1) | set(str2)

        return len(common) / len(total) if total else 0

    def get_healing_report(self):
        """Return summary of all healing attempts"""
        total = len(self.healing_log)
        successful = sum(1 for log in self.healing_log if log['success'])

        return {
            'total_healing_attempts': total,
            'successful_heals': successful,
            'success_rate': f"{(successful / total * 100):.1f}%" if total > 0 else "0%",
            'healing_log': self.healing_log
        }

    def save_healing_report(self, filepath='generated_files/healing_report.json'):
        """Save healing report to file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        report = self.get_healing_report()

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"[HEALER] Report saved to {filepath}")
        return filepath