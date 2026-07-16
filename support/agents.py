from google import genai
from django.conf import settings
from .tools import get_order_details,get_refund_history,check_delivery_status,get_customer_risk_profile, search_knowledge_base
from .models import Conversation, Message, AgentLog
from google.genai import types


# Initialize the Gemini clinet.
client = genai.Client(api_key = settings.GEMINI_API_KEY)

gemini_model = settings.GEMINI_MODEL


# SUPPORT SYSTEM PROMPT --> Maya's job description

SUPPORT_SYSTEM_PROMPT = """
You are Maya, a customer support agent at CoolBreeze AC.
You help customers with issues related to their AC orders.

Your responsibilities:
- Always use your tools to gather facts before responding
- Check order details when customer mentions their order
- Check refund history before making any refund decisions
- Be empathetic but honest

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies
- No emojies

Never make refund decisions yourself.

If a refund request is made:

1. Call get_order_details.
2. Call get_refund_history.
3. Then call escalate_to_manager.
Do not answer until the manager responds.

Important rules:
- Always check order details first before responding
- Never approve or deny a refund yourself
- If refund decision is needed — tell customer you are checking with your team
- Never use bold text, bullet points or any markdown formatting. Plain text only.
- Keep replies concise and conversational. Maximum 3-4 sentences. No long paragraphs.
"""

MANAGER_SYSTEM_PROMPT = """
You are a senior support manager at CoolBreeze AC.
A support agent has escalated a customer case to you for a refund decision.

Your responsibilities:
- Review the case summary carefully
- Consider the customer's refund history
- Make a fair and final refund decision
- Give a clear reason for your decision

Your decision options:
- Approve refund — if the case is genuine and within policy
- Deny refund — if the case is suspicious or outside policy
- Escalate to risk team — if you suspect fraud
- Before making any refund decision, Always call assess_fraud_risk, Never skip this tool

Important rules:
- Be fair but firm
- Base decision on facts — not emotions
- Always give a specific reason for your decision
- Keep your response concise and professional
"""

RISK_SYSTEM_PROMPT = """
You are a fraud risk analyst at CoolBreeze AC.
A support manager has sent you a customer profile for risk assessment.

Your job:
- Analyse the customer's order and refund patterns
- Identify suspicious behaviour
- Return a clear risk verdict

Risk levels:
- LOW — genuine customer, normal behaviour
- MEDIUM — some suspicious signals, proceed with caution
- HIGH — clear fraud pattern, recommend denial

Your response format:
- Risk Level: LOW / MEDIUM / HIGH
- Key Signals: what you found suspicious or genuine
- Recommendation: what manager should do

Important:
- Be objective — base verdict on data only
- One bad refund does not make someone fraudulent
- Look for patterns — not isolated incidents
"""


# SUPPORT TOOLS --> Tool Schema, that ai agent will read
# Gemini Tool Definitions
GEMINI_SUPPORT_TOOLS = [
    types.Tool(
        function_declarations=[

            types.FunctionDeclaration(
                name="get_order_details",
                description="Fetch complete order details including status, carrier, tracking number and days since order was placed. Use this when customer mentions their order or complains about delivery.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "order_id": {
                            "type": "INTEGER",
                            "description": "The order ID to look up"
                        }
                    },
                    "required": ["order_id"]
                }
            ),

            types.FunctionDeclaration(
                name="get_refund_history",
                description="Get complete refund history for a user. Use this before making any refund related decisions.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "user_id": {
                            "type": "INTEGER",
                            "description": "The user ID to check refund history for"
                        }
                    },
                    "required": ["user_id"]
                }
            ),

            types.FunctionDeclaration(
                name="check_delivery_status",
                description="Check current delivery status using tracking number and carrier. Use this when customer complains about delayed or missing delivery.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "tracking_number": {
                            "type": "STRING",
                            "description": "The shipment tracking number"
                        },
                        "carrier": {
                            "type": "STRING",
                            "description": "The carrier name (for example BlueDart or Delhivery)"
                        }
                    },
                    "required": [
                        "tracking_number",
                        "carrier"
                    ]
                }
            ),

            types.FunctionDeclaration(
                name="escalate_to_manager",
                description="Escalate the case to manager for refund decision. Always include customer's user_id in the case summary so manager can assess fraud risk accurately.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "case_summary": {
                            "type": "STRING",
                            "description": "Complete case summary. Must include: customer user_id, order details, refund history and complaint. Format: Start with 'Customer User ID: X' on the first line."
                        }
                    },
                    "required": ["case_summary"]
                }
            ),


            types.FunctionDeclaration(
                name="search_knowledge_base",
                description="Search CoolBreeze AC company documents including refund policy, warranty policy, and product FAQs. Use this when customer asks about company policies, warranty coverage, warranty claims, refund eligibility, or any general product information that requires accurate company documentation.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "The search query to find relevant information from company documents. Be specific — for example 'refund eligibility within 30 days' instead of just 'refund'."
                        }
                    },
                    "required": ["query"]
                }
            ),

        ]
    )
]


GEMINI_MANAGER_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="assess_fraud_risk",
                description="Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user_id to get a risk verdict.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "user_id": {
                            "type": "INTEGER",
                            "description": "The user ID to assess fraud risk for"
                        }
                    },
                    "required": ["user_id"]
                },
            ),
        ]
    )
]


GEMINI_RISK_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_customer_risk_profile",
                description="Get complete risk profile for a customer including order history, refund patterns and ratio. Use this to assess fraud risk.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "user_id": {
                            "type": "INTEGER",
                            "description": "The user ID to assess risk for"
                        }
                    },
                    "required": ["user_id"]
                },
            ),
        ]
    )
]



# EXECUTE TOOL --> Bridge between gemini and python function (tools)
def execute_tool(tool_name, tool_input, conversation_id):
    if tool_name == "get_order_details":
        return get_order_details(tool_input["order_id"])
    
    if tool_name == "get_refund_history":
        return get_refund_history(tool_input["user_id"])
    
    if tool_name == "check_delivery_status":
        return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])
    
    if tool_name == "escalate_to_manager":
        case_summary = tool_input["case_summary"]
        print("escalating to manager ====>", case_summary)
        decision = run_manager_agent(case_summary, conversation_id)
        print("decision ====>", decision)
        return decision 
    

    if tool_name == 'assess_fraud_risk':
        user_id = tool_input['user_id']
        print("Consulting risk agent for user==>", user_id)
        verdict = run_risk_agent(user_id, conversation_id)
        print("risk verdict==>", verdict)
        return verdict
    
    if tool_name == 'get_customer_risk_profile':
        return get_customer_risk_profile(tool_input['user_id'])
    

    if tool_name == "search_knowledge_base":
        return search_knowledge_base(tool_input["query"])




# AGENT LOOP --> while loop thats loops until the task is done
def run_support_agent(user_message, conversation_id, order_id, user_id):

    conv = Conversation.objects.get(id=conversation_id)

    conversation_contents = []

    # Context
    conversation_contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"""
Context:
This conversation is about Order #{order_id}
Current User ID: {user_id}
"""
                )
            ]
        )
    )

    # Previous conversation
    for msg in conv.messages.order_by("created_at"):

        role = "model" if msg.role == "agent" else "user"

        conversation_contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(text=msg.content)
                ]
            )
        )

    while True:

        response = client.models.generate_content(
            model=gemini_model,
            contents=conversation_contents,
            config=types.GenerateContentConfig(
                system_instruction=SUPPORT_SYSTEM_PROMPT,
                tools=GEMINI_SUPPORT_TOOLS,
                max_output_tokens=1024,
            ),
        )

        # Did Gemini request a tool?
        if response.function_calls:

            tool_parts = []

            for call in response.function_calls:

                # Log tool call
                AgentLog.objects.create(conversation=conv,event_type="tool_call",message=f"Calling tool {call.name} with {call.args}")

                print("tool_call ==>", call.name)
                print("tool_input ==>", call.args)

                # Execute Python tool
                result = execute_tool(call.name, call.args, conversation_id)


                # Log tool result
                AgentLog.objects.create(conversation=conv,event_type="tool_result",message=f"{call.name} returned: {str(result)[:200]}")

                print("tool_result ==>", result)

                tool_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={
                            "result": result
                        }
                    )
                )

            # Save Gemini's function-call message
            conversation_contents.append(
                response.candidates[0].content
            )

            # Send tool result back
            conversation_contents.append(
                types.Content(
                    role="tool",
                    parts=tool_parts
                )
            )

            continue

        else:
            # log final reply.
            AgentLog.objects.create(conversation=conv,event_type="tool_result",message=response.text)         

            return response.text
        

def run_manager_agent(case_summary, conversation_id):

    conv = Conversation.objects.get(id=conversation_id)
    AgentLog.objects.create(conversation=conv,event_type="manager",message=f"case received for review {case_summary[:200]}") 
    manager_messages = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=case_summary)
            ]
        )
    ]

    while True:

        response = client.models.generate_content(
            model=gemini_model,
            contents=manager_messages,
            config=types.GenerateContentConfig(
                system_instruction=MANAGER_SYSTEM_PROMPT,
                tools=GEMINI_MANAGER_TOOLS,
                max_output_tokens=1024,
            ),
        )

        if response.function_calls:

            tool_parts = []

            for call in response.function_calls:
                
                # log consulting risk agent
                AgentLog.objects.create(conversation=conv,event_type="manager",message=f"Consulting risk agent for fraud assessment")

                print("tool_call ==>", call.name)
                print("tool_input ==>", call.args)

                result = execute_tool(call.name, call.args, conversation_id)

                print("tool_result ==>", result)

                tool_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={
                            "result": result
                        }
                    )
                )

            manager_messages.append(
                response.candidates[0].content
            )

            manager_messages.append(
                types.Content(
                    role="tool",
                    parts=tool_parts
                )
            )

            continue

        else:

            decision = response.text
             # log final reply.
            AgentLog.objects.create(conversation=conv,event_type="tool_result",message=f"Decision: {decision}")

            return decision
        


def run_risk_agent(user_id, conversation_id):

    conv = Conversation.objects.get(id = conversation_id)

    # log assessment started
    AgentLog.objects.create(conversation=conv,event_type="risk",message=f"Starting fraud assessment for {user_id}")
    risk_messages = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"Please assess the fraud risk for user ID {user_id}. Use your tool to get their profile and return a verdict."
                )
            ]
        )
    ]

    while True:

        response = client.models.generate_content(
            model=gemini_model,
            contents=risk_messages,
            config=types.GenerateContentConfig(
                system_instruction=RISK_SYSTEM_PROMPT,
                tools=GEMINI_RISK_TOOLS,
                max_output_tokens=1024,
            ),
        )

        if response.function_calls:

            tool_parts = []

            for call in response.function_calls:

                AgentLog.objects.create(conversation=conv,event_type="risk",message=f"Calling {call.name} to get customer risk profile...")


                print("risk_tool_call ==>", call.name)
                print("risk_tool_input ==>", call.args)

                result = execute_tool(call.name, call.args, conversation_id)

                print("risk_tool_result ==>", result)

                tool_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={
                            "result": result
                        }
                    )
                )

            # Add Gemini's function call message
            risk_messages.append(
                response.candidates[0].content
            )

            # Add tool response
            risk_messages.append(
                types.Content(
                    role="tool",
                    parts=tool_parts
                )
            )

            continue

        else:

            verdict = response.text
            AgentLog.objects.create(conversation=conv,event_type="risk",message=f"verdict: {verdict[:200]}")

            return verdict