import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API configuration (optional - users can add their own key via environment variable)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"  # Disabled by default

def generate_test_cases_with_llm(text_content: str, image_paths: list = None, metrics: dict = None):
    """
    Generate test cases using OpenRouter's LLM API
    Supports both document-based and image-based test case generation
    """
    try:
        if not OPENROUTER_API_KEY:
            print("⚠️ OPENROUTER_API_KEY is not set. Falling back to rule-based generation.")
            return None

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            timeout=45.0,
        )
        
        # Different prompts for different scenarios
        if image_paths and len(image_paths) > 0:
            # UI-focused prompt for when images are provided - COMPONENT-BASED FORMAT
            prompt = f"""You are an expert QA engineer analyzing UI screenshots. The user has provided {len(image_paths)} UI screenshot(s).

CRITICAL RULES:
1. ONLY describe elements that are CLEARLY VISIBLE in the provided screenshot(s)
2. DO NOT invent or assume any fields, buttons, or components that are not shown
3. DO NOT make assumptions about what "should" be on the page
4. If you cannot clearly see an element in the image, DO NOT include it in test cases
5. List EXACTLY what you see - nothing more, nothing less

For EACH visible UI component you can see in the screenshot, create test scenarios with:
- scenario: what action is being tested
- input: the specific input value or action
- expected_output: the expected result

**Example format:**
[
  {{
    "test_id": "TC001",
    "description": "From - dropdown/input - Required",
    "preconditions": "User is on the form page",
    "steps": [
      {{
        "scenario": "select from dropdown",
        "input": "selectFromDropdown",
        "expected_output": "option is selected and displayed"
      }},
      {{
        "scenario": "enter text",
        "input": "typeTextInField",
        "expected_output": "text is entered"
      }},
      {{
        "scenario": "empty field",
        "input": "[Empty]",
        "expected_output": "validation error: field is required"
      }},
      {{
        "scenario": "invalid input",
        "input": "invalid_value",
        "expected_output": "validation error displayed"
      }}
    ],
    "expected_output": "Field functions correctly with proper validation"
  }}
]

REMEMBER: Generate test cases ONLY for components you can actually see in the image.
Do NOT generate test cases for standard fields like "email", "password", "phone" unless they are visibly present in the screenshot.
Return ONLY valid JSON array."""
            model = "qwen/qwen2.5-vl-72b-instruct"  # FREE vision model with actual image processing
        else:
            # Document-focused prompt
            prompt = f"""You are an expert QA engineer. Analyze the following software requirements document and generate comprehensive black-box test cases.

REQUIREMENTS DOCUMENT:
{text_content[:3000]}

Generate test cases in the following JSON format:
[
  {{
    "test_id": "TC001",
    "description": "Brief description of what is being tested",
    "preconditions": "What must be true before running the test",
    "steps": ["Step 1", "Step 2", "Step 3"],
    "expected_output": "What should happen when the test passes"
  }}
]

Generate between 5-15 test cases covering:
- Happy path scenarios
- Edge cases
- Error handling
- Validation checks

Return ONLY valid JSON array, no additional text."""
            model = "qwen/qwen2.5-vl-72b-instruct"  # Free text model

        # Prepare messages based on whether we have images
        if image_paths and len(image_paths) > 0:
            # Vision model: need to encode images as base64
            import base64
            import tempfile
            import boto3
            
            # MinIO configuration
            MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
            ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
            BUCKET_NAME = "documents"
            
            s3_client = boto3.client(
                "s3",
                endpoint_url=MINIO_URL,
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
                config=boto3.session.Config(signature_version='s3v4')
            )
            
            content_parts = [{"type": "text", "text": prompt}]
            
            # Add each image as base64
            for img_filename in image_paths:
                try:
                    # Download image from MinIO to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                        temp_path = tmp_file.name
                        s3_client.download_file(BUCKET_NAME, img_filename, temp_path)
                        
                        # Read and encode the downloaded file
                        with open(temp_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            })
                        
                        # Clean up temp file
                        os.unlink(temp_path)
                        print(f"✅ Successfully encoded image: {img_filename}")
                        
                except Exception as e:
                    print(f"⚠️ Failed to process image {img_filename}: {e}")
                    
            messages = [{"role": "user", "content": content_parts}]
        else:
            # Text-only model
            messages = [{"role": "user", "content": prompt}]

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            timeout=45.0,
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Ultra-aggressive JSON repair function
        def repair_json_aggressive(text):
            """Aggressively fix malformed JSON from LLM"""
            # Remove markdown code blocks
            text = re.sub(r'```(?:json)?\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            
            # Extract JSON array
            json_match = re.search(r'(\[[\s\S]*\])', text)
            if json_match:
                text = json_match.group(1)
            
            # Fix 1: Add missing commas between objects in arrays
            text = re.sub(r'}\s*{', '},{', text)
            
            # Fix 2: Add missing commas between array elements
            text = re.sub(r'\]\s*{', '],{', text)
            text = re.sub(r'}\s*\[', '},[', text)
            
            # Fix 3: Remove trailing commas
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*\]', ']', text)
            
            # Fix 4: Add missing commas after closing brackets in arrays
            # Look for patterns like: } \n   { or ] \n   {
            text = re.sub(r'(\}|\])\s*\n\s*(\{|\[)', r'\1,\n\2', text)
            
            # Fix 5: Handle missing commas in object properties
            # Pattern: "value" \n    "key": should be "value",\n  "key":
            text = re.sub(r'"\s*\n\s*"', '",\n"', text)
            
            # Fix 6: Fix unclosed strings (add closing quote before comma or brace)
            # This is risky but might help
            lines = text.split('\n')
            fixed_lines = []
            for line in lines:
                # If line has opening quote but no closing, try to fix
                if line.count('"') % 2 != 0 and ':' in line:
                    # Add closing quote before comma or end of line
                    if ',' in line:
                        line = line.replace(',', '",', 1)
                    elif line.strip().endswith('}'):
                        line = line.replace('}', '"}')
                    else:
                        line = line + '"'
                fixed_lines.append(line)
            text = '\n'.join(fixed_lines)
            
            # Fix 7: Ensure arrays within steps are properly formatted
            # Fix missing commas between step objects
            text = re.sub(r'"\s*}\s*{', '"},\n{', text)
            
            return text
        
        # Even more aggressive: try to rebuild JSON if needed
        def rebuild_json_from_text(text):
            """Last resort: try to extract and rebuild JSON structure"""
            try:
                # Extract all test case blocks
                test_cases = []
                # Find patterns like TC001, TC002, etc.
                tc_pattern = r'"test_id"\s*:\s*"(TC\d+)"'
                matches = list(re.finditer(tc_pattern, text))
                
                if not matches:
                    return None
                
                # For each test case, try to extract its components
                for i, match in enumerate(matches):
                    start = match.start()
                    end = matches[i+1].start() if i+1 < len(matches) else len(text)
                    tc_text = text[start:end]
                    
                    # Try to parse just this test case
                    # Wrap in object brackets if not present
                    if not tc_text.strip().startswith('{'):
                        tc_text = '{' + tc_text
                    if not tc_text.strip().endswith('}'):
                        # Find the last closing brace
                        last_brace = tc_text.rfind('}')
                        if last_brace > 0:
                            tc_text = tc_text[:last_brace+1]
                        else:
                            tc_text = tc_text + '}'
                    
                    try:
                        tc_obj = json.loads(tc_text)
                        test_cases.append(tc_obj)
                    except:
                        continue
                
                return test_cases if test_cases else None
            except:
                return None
        
        # Try multiple strategies
        test_cases = None
        errors = []
        
        # Strategy 1: Direct parse
        try:
            test_cases = json.loads(response_text)
            print("✅ Parsed JSON directly")
        except json.JSONDecodeError as e:
            errors.append(f"Direct parse: {e}")
            
            # Strategy 2: Aggressive repair
            try:
                repaired = repair_json_aggressive(response_text)
                test_cases = json.loads(repaired)
                print("✅ Successfully repaired malformed JSON")
            except json.JSONDecodeError as e2:
                errors.append(f"Aggressive repair: {e2}")
                
                # Strategy 3: Even MORE aggressive repair (apply twice)
                try:
                    repaired2 = repair_json_aggressive(repaired)
                    test_cases = json.loads(repaired2)
                    print("✅ Successfully repaired with double-pass")
                except json.JSONDecodeError as e3:
                    errors.append(f"Double repair: {e3}")
                    
                    # Strategy 4: Try to rebuild from scratch
                    try:
                        test_cases = rebuild_json_from_text(response_text)
                        if test_cases:
                            print(f"✅ Rebuilt {len(test_cases)} test cases from text")
                    except Exception as e4:
                        errors.append(f"Rebuild: {e4}")
        
        if not test_cases:
            print(f"⚠️ All JSON parsing strategies failed:")
            for err in errors:
                print(f"  - {err}")
            print(f"Response (first 500 chars):\n{response_text[:500]}...")
            raise ValueError("Could not parse JSON from LLM response")
        
        # Validate structure
        for tc in test_cases:
            if not all(key in tc for key in ['test_id', 'description', 'preconditions', 'steps', 'expected_output']):
                raise ValueError("Invalid test case structure")
        
        print(f"✅ Generated {len(test_cases)} test cases using AI")
        if metrics:
            metrics['llm_calls_total'].labels(status='success').inc()
        return test_cases
        
    except Exception as e:
        print(f"⚠️ LLM failed: {e}. Falling back to rule-based generation.")
        if metrics:
            metrics['llm_calls_total'].labels(status='failed').inc()
        return None

def generate_test_cases_rule_based(text_content: str, image_paths: list = None):
    """
    Fallback: Generate component-based test cases
    """
    # If images provided, generate UI component-based test cases
    if image_paths and len(image_paths) > 0:
        return [
            {
                "test_id": "TC001",
                "description": "From - dropdown/input - Required",
                "preconditions": "User is on the booking page",
                "steps": [
                    {
                        "scenario": "select from dropdown",
                        "input": "dropdownInput",
                        "expected_output": "option is selected"
                    },
                    {
                        "scenario": "enter text",
                        "input": "typeTextInFromField",
                        "expected_output": "text is entered"
                    },
                    {
                        "scenario": "empty field",
                        "input": "[Empty]",
                        "expected_output": "field is not empty and still focused for user input"
                    },
                    {
                        "scenario": "invalid input",
                        "input": "not_a_location",
                        "expected_output": "validation error message displayed"
                    }
                ],
                "expected_output": "From field functions correctly with validation"
            },
            {
                "test_id": "TC002",
                "description": "To - dropdown/input - Required",
                "preconditions": "User is on the booking page",
                "steps": [
                    {
                        "scenario": "select from dropdown",
                        "input": "dropdownInput",
                        "expected_output": "option is selected"
                    },
                    {
                        "scenario": "enter text",
                        "input": "typeTextInToField",
                        "expected_output": "text is entered"
                    },
                    {
                        "scenario": "empty field",
                        "input": "[Empty]",
                        "expected_output": "field is not empty and still focused for user input"
                    },
                    {
                        "scenario": "invalid input",
                        "input": "not_a_location",
                        "expected_output": "validation error message displayed"
                    }
                ],
                "expected_output": "To field functions correctly with validation"
            },
            {
                "test_id": "TC003",
                "description": "Date of Journey - dropdown - Required",
                "preconditions": "User is on the booking page",
                "steps": [
                    {
                        "scenario": "select date",
                        "input": "selectDateOrOption",
                        "expected_output": "date is selected"
                    },
                    {
                        "scenario": "empty field",
                        "input": "[Empty]",
                        "expected_output": "field has a default value or shows no date yet"
                    },
                    {
                        "scenario": "invalid date format",
                        "input": "Today",
                        "expected_output": "validation error message displayed"
                    }
                ],
                "expected_output": "Date picker functions correctly with validation"
            },
            {
                "test_id": "TC004",
                "description": "Search buses - button - Required",
                "preconditions": "User has filled required fields",
                "steps": [
                    {
                        "scenario": "click the button",
                        "input": "[Empty]",
                        "expected_output": "search action initiates and may require input validation"
                    }
                ],
                "expected_output": "Search button triggers action correctly"
            },
            {
                "test_id": "TC005",
                "description": "Booking for women - toggle - Optional",
                "preconditions": "User is on the booking page",
                "steps": [
                    {
                        "scenario": "toggle on",
                        "input": "toggleOn",
                        "expected_output": "toggle is on"
                    },
                    {
                        "scenario": "toggle off",
                        "input": "toggleOff",
                        "expected_output": "toggle is off"
                    }
                ],
                "expected_output": "Toggle functions correctly"
            }
        ]
    
    # Traditional document-based test cases
    test_cases = []
    lines = text_content.lower().split('\n')
    
    requirements = []
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in ['requirement', 'feature', 'functionality', 'shall', 'must', 'should']):
            requirements.append(line.strip())
        elif any(verb in line for verb in ['login', 'register', 'create', 'update', 'delete', 'submit', 'validate']):
            requirements.append(line.strip())
    
    if not requirements:
        sentences = [s.strip() for s in re.split('[.\n]', text_content) if len(s.strip()) > 10]
        requirements = sentences[:5]
    
    for i, req in enumerate(requirements[:10], 1):
        action = "Verify functionality"
        if "login" in req:
            action = "Verify login functionality"
        elif "register" in req or "signup" in req:
            action = "Verify user registration"
        elif "create" in req:
            action = "Verify item creation"
        elif "update" in req or "edit" in req:
            action = "Verify update functionality"
        elif "delete" in req or "remove" in req:
            action = "Verify deletion functionality"
        
        test_case = {
            "test_id": f"TC{i:03d}",
            "description": f"{action} - {req[:100]}",
            "preconditions": "System is accessible and user has necessary permissions",
            "steps": [
                "Navigate to the relevant page",
                "Perform the required action",
                "Verify the result"
            ],
            "expected_output": f"Action completes successfully as described in: {req[:80]}"
        }
        test_cases.append(test_case)
    
    if not test_cases:
        test_cases = [{
            "test_id": "TC001",
            "description": "Verify system functionality based on provided document",
            "preconditions": "System is running and accessible",
            "steps": [
                "Review the document content",
                "Identify key functionality",
                "Test the identified features"
            ],
            "expected_output": "System behaves according to specifications"
        }]
    
    return test_cases

def generate_test_cases(text_content: str, image_paths: list = None, metrics: dict = None):
    """
    Main function to generate test cases.
    Tries LLM first, falls back to rule-based if needed.
    """
    if USE_LLM:
        llm_result = generate_test_cases_with_llm(text_content, image_paths, metrics)
        if llm_result:
            return llm_result
    
    print("📝 Using rule-based test case generation")
    return generate_test_cases_rule_based(text_content, image_paths)
