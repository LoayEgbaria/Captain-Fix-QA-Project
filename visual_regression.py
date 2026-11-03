"""
Visual Regression Detection Module for Captain Fix
Compares screenshots and detects visual changes using AI
"""

import os
import base64
import json
from PIL import Image, ImageChops, ImageDraw
from selenium import webdriver
import openai


class VisualRegression:
    def __init__(self, driver, baseline_dir='generated_files/screenshots/baseline',
                 current_dir='generated_files/screenshots/current', api_key=None):
        self.driver = driver
        self.baseline_dir = baseline_dir
        self.current_dir = current_dir
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.changes_detected = []

        # Create directories
        os.makedirs(baseline_dir, exist_ok=True)
        os.makedirs(current_dir, exist_ok=True)

    def capture_baseline(self, page_name):
        """Capture baseline screenshot for a page"""
        filepath = os.path.join(self.baseline_dir, f"{page_name}.png")
        self.driver.save_screenshot(filepath)
        print(f"[VISUAL] Baseline captured: {filepath}")
        return filepath

    def capture_current(self, page_name):
        """Capture current screenshot for comparison"""
        filepath = os.path.join(self.current_dir, f"{page_name}.png")
        self.driver.save_screenshot(filepath)
        print(f"[VISUAL] Current screenshot captured: {filepath}")
        return filepath

    def compare_screenshots(self, page_name, threshold=0.05):
        """
        Compare baseline and current screenshots

        Args:
            page_name: name of the page/component
            threshold: percentage difference threshold (0.05 = 5%)

        Returns:
            dict with comparison results
        """
        baseline_path = os.path.join(self.baseline_dir, f"{page_name}.png")
        current_path = os.path.join(self.current_dir, f"{page_name}.png")

        # Check if baseline exists
        if not os.path.exists(baseline_path):
            print(f"[VISUAL] No baseline found for {page_name}. Capturing baseline...")
            self.capture_baseline(page_name)
            return {
                'status': 'baseline_created',
                'page': page_name,
                'message': 'Baseline screenshot created. Run again to detect changes.'
            }

        # Capture current
        self.capture_current(page_name)

        # Load images
        baseline_img = Image.open(baseline_path)
        current_img = Image.open(current_path)

        # Resize if dimensions don't match
        if baseline_img.size != current_img.size:
            print(f"[VISUAL] Resizing images to match...")
            current_img = current_img.resize(baseline_img.size)

        # Calculate pixel difference
        diff = ImageChops.difference(baseline_img.convert('RGB'), current_img.convert('RGB'))
        diff_bbox = diff.getbbox()

        # Calculate difference percentage
        if diff_bbox:
            # Count non-zero pixels
            diff_pixels = sum(sum(pixel) for pixel in diff.getdata())
            total_pixels = baseline_img.size[0] * baseline_img.size[1] * 3  # RGB
            diff_percentage = diff_pixels / total_pixels
        else:
            diff_percentage = 0.0

        # Save diff image if changes detected
        diff_path = None
        if diff_percentage > threshold:
            diff_path = os.path.join(self.current_dir, f"{page_name}_diff.png")

            # Create visual diff with red overlay
            diff_highlight = Image.blend(baseline_img.convert('RGB'), current_img.convert('RGB'), 0.5)
            draw = ImageDraw.Draw(diff_highlight, 'RGBA')
            if diff_bbox:
                draw.rectangle(diff_bbox, outline='red', width=3)

            diff_highlight.save(diff_path)
            print(f"[VISUAL] Diff image saved: {diff_path}")

        result = {
            'status': 'changed' if diff_percentage > threshold else 'no_change',
            'page': page_name,
            'diff_percentage': f"{diff_percentage * 100:.2f}%",
            'threshold': f"{threshold * 100:.2f}%",
            'baseline_path': baseline_path,
            'current_path': current_path,
            'diff_path': diff_path,
            'changes_detected': diff_percentage > threshold
        }

        if diff_percentage > threshold:
            self.changes_detected.append(result)

            # Use AI to analyze the change
            if self.api_key:
                ai_analysis = self._analyze_change_with_ai(baseline_path, current_path)
                result['ai_analysis'] = ai_analysis

        return result

    def _analyze_change_with_ai(self, baseline_path, current_path):
        """Use AI vision to analyze what changed"""
        try:
            client = openai.OpenAI(api_key=self.api_key)

            # Encode images
            def encode_image(image_path):
                with open(image_path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')

            baseline_b64 = encode_image(baseline_path)
            current_b64 = encode_image(current_path)

            prompt = """Compare these two screenshots (baseline vs current) and identify:
1. What visual elements changed?
2. Are these changes likely bugs or intentional updates?
3. Severity: Critical, Major, Minor, or Cosmetic?

Provide a concise analysis in 2-3 sentences."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{baseline_b64}"}
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{current_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=300
            )

            analysis = response.choices[0].message.content.strip()
            print(f"[VISUAL-AI] Analysis: {analysis}")

            return analysis

        except Exception as e:
            print(f"[VISUAL-AI] AI analysis failed: {str(e)}")
            return "AI analysis unavailable"

    def run_full_visual_test(self, pages_to_test):
        """
        Run visual regression on multiple pages

        Args:
            pages_to_test: list of dicts like [{'name': 'homepage', 'url': 'https://...'}]

        Returns:
            dict with full report
        """
        results = []

        for page in pages_to_test:
            print(f"\n[VISUAL] Testing page: {page['name']}")

            # Navigate to page
            self.driver.get(page['url'])
            self.driver.implicitly_wait(3)

            # Compare
            result = self.compare_screenshots(page['name'])
            results.append(result)

        # Generate summary
        summary = {
            'total_pages_tested': len(results),
            'pages_with_changes': sum(1 for r in results if r.get('changes_detected')),
            'pages_unchanged': sum(1 for r in results if not r.get('changes_detected')),
            'new_baselines': sum(1 for r in results if r['status'] == 'baseline_created'),
            'results': results
        }

        # Save report
        report_path = 'generated_files/visual_regression_report.json'
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[VISUAL] Report saved: {report_path}")

        return summary

    def reset_baselines(self):
        """Delete all baseline screenshots (use with caution!)"""
        import shutil
        if os.path.exists(self.baseline_dir):
            shutil.rmtree(self.baseline_dir)
            os.makedirs(self.baseline_dir)
            print("[VISUAL] All baselines deleted. Next run will create new baselines.")