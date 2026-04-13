import boto3
import json

def call_bedrock_nova(prompt: str, system_prompt: str) -> str:
    """Invokes Amazon Nova Pro model via Bedrock."""
    try:
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        payload = {
            "schemaVersion": "messages-v1",
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "system": [{"text": system_prompt}]
        }
        
        response = client.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', 'No response generated.')
    except Exception as e:
        return f"Error communicating with AWS Bedrock: {str(e)}"

def process_architect_chat(user_input: str, infra_state: dict) -> str:
    """Processes the main AWS Cloud Architect chat."""
    system_prompt = "You are an expert AWS Cloud Architect reviewing the user's infrastructure setup. Provide professional, encouraging guidance, point out what's missing or could be improved, and recommend best practices (like using private subnets for DBs/compute instead of public). Be concise."
    prompt = f"Current Infrastructure State: {json.dumps(infra_state, indent=2)}\n\nUser Question: {user_input}"
    return call_bedrock_nova(prompt, system_prompt)

def process_builder_chat(chat_history: list, infra_state: dict, user_msg_count: int) -> dict:
    """Uses Nova Pro to act as a step-by-step builder wizard returning generic JSON service instructions."""
    
    if user_msg_count < 5:
        phase_instruction = f"PHASE 1 (Question {user_msg_count}/5): You MUST ask exactly ONE intuitive question right now to refine their architecture needs. DO NOT generate any infrastructure yet. Always leave 'add_services' empty."
    elif user_msg_count == 5:
        phase_instruction = "PHASE 2 (Confirmation): You have asked 5 questions. Now, summarize what you understand briefly and say: 'If you feel the information provided is enough, please click the \"Give me the infrastructure design\" button to proceed.' DO NOT generate any infrastructure yet. Always leave 'add_services' empty."
    else:
        phase_instruction = "PHASE 3 (Generation): The user has given the go-ahead. Based on the entire chat history, generate the final comprehensive AWS infrastructure design. Populate 'add_services' fully."

    system_prompt = f'''You are an interactive AWS Infrastructure Builder Wizard. The user can request ANY AWS service (e.g. VPC, EC2, Migration Hub, S3, RDS, etc). 
{phase_instruction}

You MUST ONLY return a valid JSON object with the following generic structure:
{{
  "message": "Your conversational reply (e.g., your next question, or your explanation of the final design).",
  "add_services": {{
    "ServiceName (e.g. EC2, S3, Migration Hub)": [
      {{
        "Property1": "Value1",
        "NestedService (e.g. Subnets)": [
           {{"NestedProp": "Val"}}
        ]
      }}
    ]
  }}
}}
If no new services need to be added right now (which is TRUE for Phase 1 and 2), leave "add_services" strictly empty: {{}}.
Do NOT include Markdown formatting (like ```json), just raw JSON. ABSOLUTELY NO JSON COMMENTS OR TRAILING COMMAS. Your output must instantly parse with json.loads() without errors.'''

    # Format the chat history for context
    history_text = ""
    for msg in chat_history[-10:]:  # Keep last 10 messages for context
        history_text += f"{msg['role'].capitalize()}: {msg['content']}\n"

    prompt = f"Current Infrastructure State: {json.dumps(infra_state, indent=2)}\n\nChat History:\n{history_text}\n\nPlease respond with the JSON object for the next step."
    
    response_text = call_bedrock_nova(prompt, system_prompt).strip()
    
    # Clean up markdown
    if response_text.startswith("```json"):
        response_text = response_text.replace("```json", "", 1).replace("```", "")
    elif response_text.startswith("```"):
        response_text = response_text.replace("```", "")
        
    try:
        return json.loads(response_text)
    except Exception as e:
        return {"message": f"I couldn't process that structurally. Here's my raw thought: {response_text}", "add_services": {}}

def process_component_chat(component: str, user_input: str, infra_state: dict) -> dict:
    """Processes component-specific 'what if' queries, returning JSON to dynamically add configured fields."""
    system_prompt = f'''You are a friendly, patient teacher explaining AWS {component} to a beginner. 
Explain 'what if', 'why', and always suggest best practices. Be extremely educational but concise.

Furthermore, if the user asks what to configure or how to configure this component, you MUST suggest fields to add to their UI.
Return your entire response as a raw JSON object containing:
{{
  "message": "Your conversational explanation...",
  "suggested_fields": {{"field_name_1": "default_value", "field_name_2": ""}}
}}
If no fields are needed, make "suggested_fields" an empty dictionary {{}}. Do NOT include markdown blocks like ```json.'''
    
    prompt = f"Current Infrastructure State: {json.dumps(infra_state, indent=2)}\n\nUser Question about {component}: {user_input}"
    response_text = call_bedrock_nova(prompt, system_prompt).strip()
    
    # Clean up markdown
    if response_text.startswith("```json"):
        response_text = response_text.replace("```json", "", 1).replace("```", "")
    elif response_text.startswith("```"):
        response_text = response_text.replace("```", "")
        
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"message": f"Couldn't parse fields, here is my thought: {response_text}", "suggested_fields": {}}

def process_explain_fields(component: str, fields) -> str:
    """Explains specific suggested fields for a component to the user (what, why, how)."""
    if isinstance(fields, dict):
        field_names = list(fields.keys())
    elif isinstance(fields, list):
        field_names = [str(x) for x in fields]
    else:
        field_names = [str(fields)]
        
    if not field_names:
        return "No fields to explain."
        
    system_prompt = f"You are a friendly AWS teacher. The user has been suggested to add the following configuration fields to their {component}: {field_names}. For each field, briefly explain what it is, why it's important, and how it impacts the infrastructure. Keep it beginner-friendly and formatted cleanly."
    prompt = "Please explain these suggested fields."
    return call_bedrock_nova(prompt, system_prompt)

def generate_terraform(infra_state: dict) -> str:
    """Generates AWS Terraform configuration based on the infrastructure state."""
    system_prompt = '''You are an expert AWS DevOps Engineer. 
The user has designed an AWS architecture. Your task is to output ONLY valid HashiCorp Terraform configuration (HCL) that implements this exact architecture.
Do NOT output any markdown blocks. Do NOT output any explanations. Your output MUST start exactly with 'provider "aws"' or similar.'''
    
    prompt = f"Infrastructure State JSON: {json.dumps(infra_state, indent=2)}\n\nPlease convert this to raw Terraform code."
    response = call_bedrock_nova(prompt, system_prompt).strip()
    
    # Strip markdown if any
    if response.startswith("```hcl") or response.startswith("```terraform"):
        response = "\n".join(response.split("\n")[1:])
    if response.startswith("```"):
        response = "\n".join(response.split("\n")[1:])
    if response.endswith("```"):
        response = "\n".join(response.split("\n")[:-1])
        
    return response.strip()
