from support.models import Conversation
from .gemini_client import Anthropic
from django.conf import settings
from .tools import get_order_details, get_refund_history, check_delivery_status, get_customer_risk_profile

# Initialize Gemini client
client = Anthropic(api_key=settings.GEMINI_API_KEY)

anthropic_model = settings.GEMINI_MODEL

# SUPPORT SYSTEM PROMPT -> Maya's job description
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
- If refund decision is needed - tell customer you are checking with your team
- While you are escalating, tell the customer you are checking with your team.
- Once the manager returns a decision, clearly and politely inform the customer of the final outcome (Approved, Denied, or currently under further review by the Risk Team).
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

#SUPPORT SYSTEN PROMPT --> Maya's job description
SUPPORT_SYSTEN_PROMPT = SUPPORT_SYSTEM_PROMPT
MANAGER_SYSTEM_PROMPT = MANAGER_SYSTEM_PROMPT
RISK_SYSTEM_PROMPT = RISK_SYSTEM_PROMPT

# SUPPORT TOOLS -> Tool schemas, that AI agents will read
SUPPORT_TOOLS = [
  {
    "name": "get_order_details",
    "description": "Fetch complete order details including product, status, tracking, and refund history for a specific order. Use this when customer mentions their order or complains about delays, damage, or refund requests. Input is order ID.",
    "input_schema" : {
      "type": "object",
      "properties": {
        "order_id":{ #This is the function parameter
          "type": "integer",
          "description": "The order ID to look up"
        }
      },
      "required": ["order_id"] # which parameter is mendatory
    }

  },
  {
    "name": "get_refund_history",
    "description": "Fetch complete refund history for a specific user. Use this when customer mentions their refund history or complains about refunds. Input is user ID.",
    "input_schema" : {
      "type": "object",
      "properties": {
        "user_id":{ #This is the function parameter
          "type": "integer",
          "description": "The user ID to look up"
        }
      },
      "required": ["user_id"] # which parameter is mendatory
    }
  },
  {
    "name": "check_delivery_status",
    "description": "Check delivery status for a specific order. Use this when customer mentions their order or complains about delays, damage, or refund requests. Input is tracking number and carrier.",
    "input_schema" : {
      "type": "object",
      "properties": {
        "tracking_number":{ #This is the function parameter
          "type": "string",
          "description": "The tracking number of the order to look up"
        },
        "carrier": {
          "type": "string",
          "description": "The carrier of the order to look up"
        }
      },
      "required": ["tracking_number", "carrier"] # which parameter is mendatory
    }

  },

   {
    "name": "escalate_to_manager",
    "description": "Escalate the case to manager for refund decision. Always include customer's user_id in the case summary so manager can assess fraud risk accurately.",
    "input_schema": {
        "type": "object",
        "properties": {
          "case_summary": {
            "type": "string",
            "description": "Complete case summary. Must include: customer user_id, order details, refund history and complaint. Format: Start with 'Customer User ID: X' on the first line."
          }
        },
      "required": ["case_summary"]
    }
  },
]


#Bridge betweeen the MANAGER and the risk AGENT
#This tool doesn't have anything to do with the database for that reason we don't have to create it inside tools.py
MANAGER_TOOLS = [
    {
        "name": "assess_fraud_risk",
        "description": "Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user_id to get a risk verdict.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The user ID to assess fraud risk for"
                }
            },
            "required": ["user_id"]
        }
    }
]


RISK_TOOLS = [
   {
        "name": "get_customer_risk_profile",
        "description": "Get complete risk profile for a customer including order history, refund patterns and ratio. Use this to assess fraud risk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The user ID to assess risk for"
                }
            },
            "required": ["user_id"]
        }
    }
]






# Execute tool -> Bridge betweem calude and python functions (tools)
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
    print("Manager decision====>", decision)
    return decision

  if tool_name == "assess_fraud_risk":
    user_id = tool_input['user_id'] #We get the user ID from the input schema
    print("Consulting risk agent for user==>", user_id)
    veredict = run_risk_agent(user_id)
    print("Risk agent verdict====>",veredict)
    return veredict

  
  if tool_name == "get_customer_risk_profile":
    return get_customer_risk_profile(tool_input['user_id'])
    




# Agent Loop -> While loop that loops until the task is done
def run_support_agent(user_message, conversation_id, order_id, user_id):
  conv = Conversation.objects.get(id=conversation_id)

  conversation_messages = []
  for msg in conv.messages.order_by("created_at"):
    role = "assistant" if msg.role in ("agent", "assistant") else "user"
    conversation_messages.append({
      "role": role,
      "content": msg.content,
    })

  while True:
    # Send this conversation to LLM
    response = client.messages.create(
      model=anthropic_model,
      max_tokens=1024,
      system=f"{SUPPORT_SYSTEM_PROMPT}\n\nContext: This conversation is about Order #{order_id}, user:{user_id}",
      tools=SUPPORT_TOOLS,
      messages=conversation_messages
    )

    print('agent response==>', response.stop_reason)
    print('agent content==>', response.content)

    if response.stop_reason == 'tool_use':
      tool_result = []
      for block in response.content:
        if block.type == 'tool_use':
          print("agent tool call=>", block.name)
          print("agent tool input=>", block.input)

          result = execute_tool(block.name, block.input)
          print("agent tool result=>", result)

          tool_result.append({
            "type": "tool_result",
            "tool_use_id": block.id, #OUR AGENT KNOWS WHICH RESPONSE BELONGS TO WHICH INPUT
            "content": str(result)
          })

      #Here we append the previous messages before sending them to the LLM again

      # Add assistant's tool call turn to conversation history
      conversation_messages.append({
        "role": "assistant",
        "content": response.content
      })

      # Add user's tool results turn to conversation history
      conversation_messages.append({
        "role": "user",
        "content": tool_result
      })

    else:
      return response.content[0].text


def run_manager_agent(case_summary):
  manager_messages = [
    {"role": "user", "content": case_summary} # user is task giver
  ]

  while True:
    response= client.messages.create(
      model = anthropic_model,
      max_tokens = 1024,
      system = MANAGER_SYSTEM_PROMPT,
      tools = MANAGER_TOOLS,
      messages=manager_messages
    )

    if response.stop_reason == 'tool_use':
      tool_result = []
      for block in response.content:
        if block.type == "tool_use":
          # execute the tool
          result = execute_tool(block.name, block.input)
          print("manager executing tool ==>", block.name)
          print("manager tool result ==>", result)

          tool_result.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(result)
          })

      manager_messages.append({
        "role": "assistant",
        "content": response.content
      })

      manager_messages.append({
        "role": "user",
        "content": tool_result
      })
    else:
      return response.content[0].text

  
def run_risk_agent(user_id):
  risk_messages = [
    {"role":"user","content":f"Analyze the risk profile for the user {user_id}. Use your tool to get their profile and return a verdict."}
  ]

  while True:
    response = client.messages.create(
      model = anthropic_model,
      max_tokens=1024,
      system=RISK_SYSTEM_PROMPT,
      tools=RISK_TOOLS,
      messages=risk_messages
    )

    print(f'response stop reason ==> {response.stop_reason}')
    print(f'response content ==> {response.content}')

    if response.stop_reason == 'tool_use':
      tool_result = []
      for block in response.content:
        if block.type == 'tool_use':
          print(f"risk tool call => {block.name}")
          print(f"risk tool input => {block.input}")

          result = execute_tool(block.name, block.input)
          print(f"risk tool result => {result}")

          tool_result.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(result)
          })

        risk_messages.append({
          "role": "assistant",
          "content": response.content
        })

        risk_messages.append({
          "role": "user",
          "content": tool_result
        })
    else:
      return response.content[0].text
      
        

      










