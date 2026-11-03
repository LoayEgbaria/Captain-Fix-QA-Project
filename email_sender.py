"""
Captain Fix - Email Sender Module
Handles sending test results via SMTP with attachments
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('properties.env')

class EmailSender:
    def __init__(self):
        """Initialize email sender with SMTP configuration"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("CAPTAIN_FIX_EMAIL")
        self.sender_password = os.getenv("CAPTAIN_FIX_EMAIL_PASSWORD")
        
        # Validate required email credentials
        if not self.sender_email or not self.sender_password:
            raise ValueError("Captain Fix email credentials not found in environment variables")
    
    def create_test_results_email(self, recipient_email, website_url, test_plan_data, excel_file_path=None, zip_file_path=None):
        """
        Create a formatted email with test results
        
        Args:
            recipient_email (str): Email address to send results to
            website_url (str): Website that was tested
            test_plan_data (dict): Test plan data from create_plan.py
            excel_file_path (str): Path to Excel file to attach
            zip_file_path (str): Path to zip file to attach
            
        Returns:
            MIMEMultipart: Formatted email message
        """
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        
        # Create subject line
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg['Subject'] = f"Captain Results — {website_url} — {timestamp}"
        
        # Extract test plan information
        test_plan = test_plan_data.get('testPlan', {})
        website_analysis = test_plan.get('websiteAnalysis', {})
        test_suites = test_plan.get('testSuites', [])
        
        # Count total test cases
        total_test_cases = sum(len(suite.get('testCases', [])) for suite in test_suites)
        
        # Create simple email body
        body = f"""Hello,

Please find attached the QA test results for: {website_url}.

The attached ZIP file contains:
📋 Test Plan (Excel)
📊 Test Results (Excel & JSON)
📄 Test Report (HTML & Markdown)
🎯 Allure Interactive Report (HTML folder)
📸 Screenshots (PNG files)
🔍 HTML Evidence Files

To view the Allure report:
1. Extract the ZIP file
2. Navigate to the 'allure-report' folder
3. Open 'index.html' in your browser

To view screenshots:
- Check the 'screenshots' folder in the extracted ZIP

To view HTML evidence:
- Check the 'html.results' folder in the extracted ZIP

Best regards,
Captain Fix - Autonomous QA Testing Platform
"""
        
        # Attach body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach Excel file if provided
        if excel_file_path and os.path.exists(excel_file_path):
            self._attach_file(msg, excel_file_path, "Test Plan")
        
        # Attach ZIP file if provided
        if zip_file_path and os.path.exists(zip_file_path):
            self._attach_file(msg, zip_file_path, "Test Evidence")
        
        return msg
    
    def _attach_file(self, msg, file_path, description):
        """
        Attach a file to the email message
        
        Args:
            msg (MIMEMultipart): Email message object
            file_path (str): Path to file to attach
            description (str): Description of the attachment
        """
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)
            
            # Add header as key/value pair to attachment part
            filename = os.path.basename(file_path)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            # Attach the part to message
            msg.attach(part)
            
        except Exception as e:
            print(f"Warning: Could not attach {file_path}: {str(e)}")
    
    def send_email(self, msg):
        """
        Send email via SMTP
        
        Args:
            msg (MIMEMultipart): Email message to send
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create secure connection and send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(self.sender_email, msg['To'], text)
            
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed. Check email credentials."
        except smtplib.SMTPRecipientsRefused:
            return False, "Recipient email address was refused."
        except smtplib.SMTPServerDisconnected:
            return False, "SMTP server disconnected unexpectedly."
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def send_test_results(self, recipient_email, website_url, test_plan_data, zip_file_path=None):
        """
        Complete workflow to send test results email
        
        Args:
            recipient_email (str): Email address to send results to
            website_url (str): Website that was tested
            test_plan_data (dict): Test plan data from create_plan.py
            zip_file_path (str): Path to zip file to attach
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create email message (only ZIP file attachment)
            msg = self.create_test_results_email(
                recipient_email, website_url, test_plan_data, None, zip_file_path
            )
            
            # Send email
            return self.send_email(msg)
            
        except Exception as e:
            return False, f"Error creating/sending email: {str(e)}"


def create_mock_zip_file(test_plan_data, output_path="generated_files/mock_test_evidence.zip"):
    """
    Create a mock ZIP file with Excel content for testing email attachments
    
    Args:
        test_plan_data (dict): Test plan data
        output_path (str): Path where to save the ZIP file
        
    Returns:
        str: Path to created ZIP file
    """
    import zipfile
    import json
    from datetime import datetime
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create ZIP file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add test plan JSON
        test_plan_json = json.dumps(test_plan_data, indent=2)
        zipf.writestr("test_plan.json", test_plan_json)
        
        # Add mock test execution log
        execution_log = f"""
Captain Fix - Test Execution Log
===============================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Website: {test_plan_data.get('websiteUrl', 'N/A')}
Test Depth: {test_plan_data.get('testDepth', 'N/A')}

Test Execution Summary:
• Total Test Cases: {sum(len(suite.get('testCases', [])) for suite in test_plan_data.get('testPlan', {}).get('testSuites', []))}
• Execution Status: Mock execution for testing
• Duration: 0.00 seconds (mock data)

Note: This is a mock ZIP file created for testing email functionality.
Actual test execution will be implemented by the development team.
"""
        zipf.writestr("execution_log.txt", execution_log)
        
        # Add mock screenshots directory structure
        zipf.writestr("screenshots/", "")  # Empty directory
        zipf.writestr("screenshots/README.txt", "Screenshots will be captured here during actual test execution.")
        
        # Add mock evidence directory
        zipf.writestr("evidence/", "")  # Empty directory
        zipf.writestr("evidence/README.txt", "Test evidence and artifacts will be stored here.")
    
    return output_path


# Example usage and testing function
def test_email_functionality():
    """
    Test function to verify email functionality
    """
    try:
        # Create email sender instance
        email_sender = EmailSender()
        
        # Mock test plan data
        mock_test_plan = {
            "websiteUrl": "https://example.com",
            "testDepth": 12,
            "testPlan": {
                "websiteUrl": "https://example.com",
                "testDepth": 12,
                "websiteAnalysis": {
                    "title": "Example Website",
                    "description": "A sample website for testing",
                    "keyFeatures": ["Navigation", "Forms", "Search"]
                },
                "testSuites": [
                    {
                        "suiteName": "Smoke Tests",
                        "suiteType": "smoke",
                        "testCases": [{"testId": "TC001", "testName": "Test 1"}]
                    }
                ]
            }
        }
        
        # Create mock ZIP file
        zip_path = create_mock_zip_file(mock_test_plan)
        print(f"Mock ZIP file created: {zip_path}")
        
        # Test email creation (without sending)
        msg = email_sender.create_test_results_email(
            recipient_email="test@example.com",
            website_url="https://example.com",
            test_plan_data=mock_test_plan,
            zip_file_path=zip_path
        )
        
        print("Email message created successfully!")
        print(f"Subject: {msg['Subject']}")
        print(f"To: {msg['To']}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run test when script is executed directly
    print("Testing Captain Fix Email Functionality...")
    test_email_functionality()
