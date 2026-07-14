from google import genai
from django.conf import settings
from .tools import get_order_details,get_refund_history,check_delivery_status
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

Important rules:
- Be fair but firm
- Base decision on facts — not emotions
- Always give a specific reason for your decision
- Keep your response concise and professional
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

        ]
    )
]



# EXECUTE TOOL --> Bridge between gemini and python function (tools)
def execute_tool(tool_name, tool_input):
    if tool_name == "get_order_details":
        return get_order_details(tool_input["order_id"])
    
    if tool_name == "get_refund_history":
        return get_refund_history(tool_input["user_id"])
    
    if tool_name == "check_delivery_status":
        return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])
    
    if tool_name == "escalate_to_manager":
        case_summary = tool_input["case_summary"]
        print("escalating to manager ====>", case_summary)
        decision = run_manager_agent(case_summary)
        print("decision ====>", decision)
        return decision 




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

                # print("tool_call ==>", call.name)
                # print("tool_input ==>", call.args)

                # Execute Python tool
                result = execute_tool(call.name, call.args)

               # print("tool_result ==>", result)

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

            return response.text
        

def run_manager_agent(case_summary):

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
                tools=GEMINI_SUPPORT_TOOLS,
                max_output_tokens=1024,
            ),
        )

        if response.function_calls:

            tool_parts = []

            for call in response.function_calls:

                print("tool_call ==>", call.name)
                print("tool_input ==>", call.args)

                result = execute_tool(call.name, call.args)

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

            return response.text