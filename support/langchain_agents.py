from distro.distro import VersionDict
from django.db.models.fields.related_lookups import RelatedIsNull
from support.agents import RISK_SYSTEM_PROMPT
from support.agents import SUPPORT_SYSTEM_PROMPT, MANAGER_SYSTEM_PROMPT
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings
from langchain.agents import create_agent
from support.event_queue import publish, DONE
from support.langchain_tools import (
  get_order_details,
  get_refund_history,
  check_delivery_status,
  get_customer_risk_profile,
  search_knowledge_base,
)
from langgraph.checkpoint.memory import InMemorySaver
from .models import Conversation, AgentLog
from langchain.agents.middleware import wrap_tool_call
from langchain.tools import tool

SUPPORT_TOOLS = [get_order_details, get_refund_history, check_delivery_status, get_customer_risk_profile, search_knowledge_base]
RISK_TOOLS = [get_customer_risk_profile] 
checkpointer = InMemorySaver() 

# Initialize Gemini client
llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    api_key=settings.GEMINI_API_KEY,
)


#The checkpointer get the conversation history by our thread ID
def run_support_agent_langchain(user_message, conversation_id, order_id, user_id):
  conv = Conversation.objects.get(id=conversation_id)

  config = {"configurable": {"thread_id": conversation_id}}

  #Context message, providing order and user information to the agent
  contextual_message = f"[Context: This conversation is about Order #{order_id}, user:{user_id}. {user_message}]"

  #"Where is my order #105?" 
  @tool
  def escalate_to_manager(case_sumary:str) -> dict:
    """Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user_id to get a risk verdict."""
    return run_manager_agent_langchain(case_sumary, conversation_id)

  # We yse tgus function because by default here in logchain we don't have a while loop to get the tool calls and tool results.
  # Basically we don't know what we have before and after the result
  # We put this function here because we wanted to use the conversation_id
  ###########################################################################################
  #{
  #  "type": "tool_call",
  #  "message": "Calling tool check_delivery_status with {'order_id': 105}"
  #}
  @wrap_tool_call
  def log_tool_calls_middleware(request, handler):
    # Before tool execution
    print("About to call a tool")
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    # publish event to the client
    event = {"type": "tool_call", "message":f"Calling tool {tool_name} with {tool_args}"}
    publish(conversation_id, event) # Luego de publish salta source.onMessage en "conversation_detail.html"

    # log tool call
    AgentLog.objects.create(conversation=conv, event_type="tool_call", message=f"Calling tool {tool_name} with input {tool_args}")
    result = handler(request) # This is where the tools are being executed 

    # after tool execution
    #{
    #  "type": "tool_result",
    #  "message": "Tool check_delivery_status returned The package is out for delivery via FedEx."
    #}
    print("Tool cal finished")
    event = {"type": "tool_result", "message":f"Tool {tool_name} returned {str(result.content)[:200]}"}
    publish(conversation_id, event)
    # Log tool result
    AgentLog.objects.create(conversation=conv, event_type="tool_result", message=f"Tool {tool_name} returned {str(result)[:200]}")
    return result
  ###########################################################################################

##### Engine off ###########
########################################
  support_agent = create_agent(
    model = llm,
    tools=SUPPORT_TOOLS + [escalate_to_manager],
    system_prompt=SUPPORT_SYSTEM_PROMPT,
    checkpointer=checkpointer,  #Saves the conversation history and provides it to the agent, we don't need to loop the messages any more how we used to do it
    middleware=[log_tool_calls_middleware]
  )
##########################################

###### Engine started -> sends the message to Gemini model over the internet and it triggers the middleware if it needs tools help to solve the problem ##############
#################################
## Thisa acts as a loop
  result = support_agent.invoke( 
    {"messages": [{"role": "user", "content": contextual_message}]},
    config=config,
  )
#################################

  final_reply = result["messages"][-1].content[0]["text"]
  
  event = {"type": "final", "message": final_reply}
  publish(conversation_id,event)
  # Save final reply to AgentLog
  AgentLog.objects.create(conversation=conv, event_type="final", message=final_reply)
  publish(conversation_id, DONE)
  return final_reply

  



def run_manager_agent_langchain(case_summary, conversation_id):
  conv = Conversation.objects.get(id=conversation_id)

  @tool
  def assess_fraud_risk(user_id:int) -> dict:
    """Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user_id to get a risk verdict."""
    return run_risk_agent_langchain(user_id, conversation_id)
    

  event = {"type": "manager", "message":f"Case received for review: {case_summary[:200]}" }
  publish(conversation_id,event)

  AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Case received for review: {case_summary[:200]}")
 
  # middleware
  # By nesting the middleware inside the main function, it automatically inherits access to the local variables
  @wrap_tool_call
  def log_manager_tool_calls_middleware(request, handler): 
      # before executing the tool
      event = {"type": "manager", "message" : "Consulting risk agent for case" }
      publish(conversation_id,event)
      AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Consulting risk agent for case")

      result = handler(request) # tool will be executed

      # after executing the tool
      return result


  # Invoke
  #############################
  manager_agent = create_agent(
    model=llm,
    system_prompt=MANAGER_SYSTEM_PROMPT,
    tools=[assess_fraud_risk],
    middleware=[log_manager_tool_calls_middleware]
  )
  ################################


  ###### Engine started -> sends the message to Gemini model over the internet and it triggers the middleware if it needs tools help to solve the problem ##############
  #################################
  ## Thisa acts as a loop
  result = manager_agent.invoke({
    "messages": [{"role": "user", "content": case_summary}],
  })
  ################################

  final_reply = result["messages"][-1].content[0]["text"]
  
  event = {"type": "final", "message": final_reply}
  publish(conversation_id,event)

  AgentLog.objects.create(conversation=conv, event_type="final", message=final_reply)
  publish(conversation_id, DONE)
  return final_reply


  decision = result["messages"][-1].content[0]["text"]
  event = {"type": "manager", "message": decision[:200] }
  publish(conversation_id,event)

  AgentLog.objects.create(conversation=conv, event_type="manager", message=f"Manager decision: {decision[:200]}")
  return decision




def run_risk_agent_langchain(user_id,conversation_id):
  conv = Conversation.objects.get(id=conversation_id)
  
  event = {"type": "risk", "message":f"Assesment started for user {user_id}" }
  publish(conversation_id,event)

  AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Assesment started for user {user_id}")
  
  
  @wrap_tool_call
  def log_risk_tool_calls_middleware(request,handler):
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]

    event = {"type": "risk", "message":f"Calling tool {tool_name} with input {tool_args}" }
    publish(conversation_id,event)
    AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Calling tool {tool_name} with input {tool_args}")

    result = handler(request) 

    return result
    

  
  # Invoke
  #############################
  risk_agent = create_agent(
    model = llm,
    system_prompt = RISK_SYSTEM_PROMPT,
    tools = RISK_TOOLS,
    middleware=[log_risk_tool_calls_middleware]
  )
  ################################

  result = risk_agent.invoke({
    "messages": [{"role": "user", "content": f"Analyze the risk profile for the user {user_id}. Use your tool to get their profile and return a verdict." }]
  })

  verdict = result["messages"][-1].content[0]["text"]

  event = {"type": "risk", "message":f"Risk agent verdict: {verdict[:200]}" }
  publish(conversation_id,event)
  AgentLog.objects.create(conversation=conv, event_type="risk", message=f"Risk agent verdict: {verdict[:200]}")
  print("Verdict==>:", verdict)

  return verdict

