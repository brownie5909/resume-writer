#!/usr/bin/env python3
"""
Quick syntax test for the cover letter module
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Test imports
    from routes.cover_letter_helpers import (
        extract_role_from_posting, 
        extract_company_from_posting,
        generate_enhanced_template_cover_letter
    )
    print("✅ Helper imports successful")
    
    from routes.cover_letter import router
    print("✅ Main module import successful")
    
    # Test basic functions
    test_posting = "Software Engineer position at TechCorp Inc. We are looking for a skilled developer."
    role = extract_role_from_posting(test_posting)
    company = extract_company_from_posting(test_posting)
    print(f"✅ Role extraction: {role}")
    print(f"✅ Company extraction: {company}")
    
    # Test template generation
    template = generate_enhanced_template_cover_letter(
        job_posting=test_posting,
        applicant_name="John Doe",
        current_role="Developer",
        experience="Python development",
        achievements="Built scalable applications"
    )
    print("✅ Template generation successful")
    print(f"Template length: {len(template)} characters")
    
    print("\n🎉 All syntax checks passed! Cover letter module is ready.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)