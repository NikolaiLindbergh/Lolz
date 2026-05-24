import anthropic
import os
import json

def get_ai_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

def analyze_patient(patient_data: dict, symptoms: str, vital_signs: dict = None) -> dict:
    """
    Send patient info + symptoms to Claude for clinical analysis.
    Returns a dict with analysis, possible_diagnoses, recommended_tests, warnings, recommendations.
    """
    client = get_ai_client()

    if not client:
        return {
            "error": True,
            "message": "API key not configured. Please set ANTHROPIC_API_KEY in your .env file.",
            "analysis": "",
            "possible_diagnoses": [],
            "recommended_tests": [],
            "warnings": [],
            "recommendations": []
        }

    # Build context from patient data
    vitals_text = ""
    if vital_signs:
        vitals_text = f"""
Vital Signs:
- Blood Pressure: {vital_signs.get('bp', 'N/A')}
- Heart Rate: {vital_signs.get('hr', 'N/A')} bpm
- Temperature: {vital_signs.get('temp', 'N/A')} °C
- SpO2: {vital_signs.get('spo2', 'N/A')}%
- Respiratory Rate: {vital_signs.get('rr', 'N/A')} breaths/min
"""

    prompt = f"""You are a clinical AI assistant supporting healthcare professionals in the Philippines. 
You are NOT a replacement for the clinician — you provide decision SUPPORT only.

PATIENT INFORMATION:
- Name: {patient_data.get('full_name', 'Unknown')}
- Age: {patient_data.get('age', 'Unknown')} years old
- Gender: {patient_data.get('gender', 'Unknown')}
- Blood Type: {patient_data.get('blood_type', 'Unknown')}
- Known Allergies: {patient_data.get('allergies', 'None reported')}
- Current Medications: {patient_data.get('current_medications', 'None reported')}
- Medical History: {patient_data.get('medical_history', 'None reported')}

CHIEF COMPLAINT / SYMPTOMS:
{symptoms}

{vitals_text}

Please provide a structured clinical analysis in the following JSON format ONLY (no extra text):
{{
  "clinical_summary": "Brief summary of the clinical picture in 2-3 sentences",
  "possible_diagnoses": [
    {{"diagnosis": "Diagnosis name", "likelihood": "High/Moderate/Low", "reasoning": "Brief clinical reasoning"}},
    {{"diagnosis": "Diagnosis name", "likelihood": "High/Moderate/Low", "reasoning": "Brief clinical reasoning"}}
  ],
  "recommended_tests": [
    "Test 1",
    "Test 2"
  ],
  "red_flags": [
    "Any urgent warning sign to watch for"
  ],
  "immediate_actions": "What should be done immediately if any urgent concern",
  "recommendations": [
    "Clinical recommendation 1",
    "Clinical recommendation 2"
  ],
  "disclaimer": "This AI analysis is a decision-support tool only and should be reviewed by a licensed healthcare professional before any clinical action is taken."
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = response.content[0].text.strip()

        # Try to parse JSON
        try:
            result = json.loads(raw_text)
            result["error"] = False
            return result
        except json.JSONDecodeError:
            # If JSON parse fails, return raw text
            return {
                "error": False,
                "clinical_summary": raw_text,
                "possible_diagnoses": [],
                "recommended_tests": [],
                "red_flags": [],
                "immediate_actions": "",
                "recommendations": [],
                "disclaimer": "This AI analysis is a decision-support tool only."
            }

    except anthropic.AuthenticationError:
        return {
            "error": True,
            "message": "Invalid API key. Please check your ANTHROPIC_API_KEY.",
            "clinical_summary": "", "possible_diagnoses": [],
            "recommended_tests": [], "red_flags": [],
            "immediate_actions": "", "recommendations": [], "disclaimer": ""
        }
    except Exception as e:
        return {
            "error": True,
            "message": f"AI service error: {str(e)}",
            "clinical_summary": "", "possible_diagnoses": [],
            "recommended_tests": [], "red_flags": [],
            "immediate_actions": "", "recommendations": [], "disclaimer": ""
        }
